from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select

from app.deps import DB, CurrentUser, Teacher
from app.models import Role, TimetableSlot

router = APIRouter(prefix="/timetable", tags=["timetable"])


class SlotIn(BaseModel):
    weekday: int = Field(ge=0, le=4)
    period: int = Field(ge=1, le=8)
    subject: str = Field(min_length=1, max_length=50)
    teacher_name: str | None = None
    room: str | None = None


class SlotOut(SlotIn):
    model_config = ConfigDict(from_attributes=True)


class Timetable(BaseModel):
    grade: int
    class_no: int
    slots: list[SlotOut]


def _load(db: DB, grade: int, class_no: int) -> Timetable:
    slots = db.scalars(
        select(TimetableSlot)
        .where(TimetableSlot.grade == grade, TimetableSlot.class_no == class_no)
        .order_by(TimetableSlot.weekday, TimetableSlot.period)
    )
    return Timetable(grade=grade, class_no=class_no, slots=[SlotOut.model_validate(s) for s in slots])


@router.get("/me", response_model=Timetable)
def my_timetable(db: DB, user: CurrentUser) -> Timetable:
    if user.role != Role.student or user.grade is None or user.class_no is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "학년·반 정보가 없습니다")
    return _load(db, user.grade, user.class_no)


@router.get("", response_model=Timetable)
def class_timetable(db: DB, _: CurrentUser, grade: int = Query(ge=1, le=3), class_no: int = Query(ge=1)) -> Timetable:
    return _load(db, grade, class_no)


@router.put("", response_model=Timetable)
def save_timetable(
    body: list[SlotIn], db: DB, teacher: Teacher, grade: int = Query(ge=1, le=3), class_no: int = Query(ge=1)
) -> Timetable:
    """편집 그리드 저장: 해당 반 시간표를 통째로 바꾼다. 빈 칸은 보내지 않는다."""
    keys = [(s.weekday, s.period) for s in body]
    if len(keys) != len(set(keys)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "같은 요일·교시가 중복됩니다")
    db.execute(delete(TimetableSlot).where(TimetableSlot.grade == grade, TimetableSlot.class_no == class_no))
    db.add_all(
        TimetableSlot(grade=grade, class_no=class_no, updated_by=teacher.id, **slot.model_dump()) for slot in body
    )
    db.commit()
    return _load(db, grade, class_no)
