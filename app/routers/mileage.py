from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.deps import DB, CurrentUser, Teacher, ensure_self_or_teacher
from app.models import MileageRecord, MileageType, Role, User
from app.schemas.user import UserOut

router = APIRouter(prefix="/mileage", tags=["mileage"])


class GiveIn(BaseModel):
    """여러 학생에게 같은 상벌점을 한 번에 부여한다."""

    student_ids: list[int] = Field(min_length=1)
    type: MileageType
    points: int = Field(ge=1, le=100)
    reason: str = Field(min_length=1, max_length=200)
    date: date


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    type: MileageType
    points: int
    reason: str
    date: date
    teacher_name: str


class Summary(BaseModel):
    merit: int
    demerit: int
    total: int


class StudentMileage(BaseModel):
    summary: Summary
    records: list[RecordOut]


class StudentSummary(BaseModel):
    student: UserOut
    summary: Summary


def _out(record: MileageRecord) -> RecordOut:
    return RecordOut(
        id=record.id,
        student_id=record.student_id,
        type=record.type,
        points=record.points,
        reason=record.reason,
        date=record.date,
        teacher_name=record.teacher.name,
    )


def _summary(merit: int, demerit: int) -> Summary:
    return Summary(merit=merit, demerit=demerit, total=merit - demerit)


@router.post("", response_model=list[RecordOut], status_code=status.HTTP_201_CREATED)
def give(body: GiveIn, db: DB, teacher: Teacher) -> list[RecordOut]:
    found = set(db.scalars(select(User.id).where(User.id.in_(body.student_ids), User.role == Role.student)))
    missing = set(body.student_ids) - found
    if missing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"학생을 찾을 수 없습니다: {sorted(missing)}")
    records = [
        MileageRecord(
            student_id=sid, type=body.type, points=body.points, reason=body.reason, date=body.date, given_by=teacher.id
        )
        for sid in body.student_ids
    ]
    db.add_all(records)
    db.commit()
    return [_out(r) for r in records]


@router.get("/students/{student_id}", response_model=StudentMileage)
def student_mileage(student_id: int, db: DB, user: CurrentUser) -> StudentMileage:
    ensure_self_or_teacher(user, student_id)
    records = list(
        db.scalars(
            select(MileageRecord)
            .where(MileageRecord.student_id == student_id)
            .order_by(MileageRecord.date.desc(), MileageRecord.id.desc())
        )
    )
    merit = sum(r.points for r in records if r.type == MileageType.merit)
    demerit = sum(r.points for r in records if r.type == MileageType.demerit)
    return StudentMileage(summary=_summary(merit, demerit), records=[_out(r) for r in records])


@router.get("/students", response_model=list[StudentSummary])
def class_summary(db: DB, _: Teacher, grade: int = Query(ge=1, le=3), class_no: int | None = None):
    """반 학생별 상점·벌점 합계 (교사 상벌점 관리 표)"""
    query = select(User).where(User.role == Role.student, User.grade == grade)
    if class_no is not None:
        query = query.where(User.class_no == class_no)
    students = list(db.scalars(query.order_by(User.class_no, User.number)))

    totals = db.execute(
        select(MileageRecord.student_id, MileageRecord.type, func.sum(MileageRecord.points))
        .where(MileageRecord.student_id.in_([s.id for s in students]))
        .group_by(MileageRecord.student_id, MileageRecord.type)
    ).all()
    points = {(sid, t): p for sid, t, p in totals}
    return [
        StudentSummary(
            student=UserOut.model_validate(s),
            summary=_summary(points.get((s.id, MileageType.merit), 0), points.get((s.id, MileageType.demerit), 0)),
        )
        for s in students
    ]


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel(record_id: int, db: DB, _: Teacher) -> None:
    record = db.get(MileageRecord, record_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "기록을 찾을 수 없습니다")
    db.delete(record)
    db.commit()
