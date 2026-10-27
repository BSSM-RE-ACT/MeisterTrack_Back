from collections import Counter
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import extract, select

from app.deps import DB, CurrentUser, Teacher
from app.models import Attendance, AttendanceStatus, Role, User
from app.schemas.attendance import AttendanceIn, AttendanceOut, MonthlyAttendance

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.put("", response_model=list[AttendanceOut])
def upsert_attendance(body: list[AttendanceIn], db: DB, teacher: Teacher) -> list[Attendance]:
    """같은 학생·날짜 기록이 있으면 덮어쓴다."""
    saved = []
    for entry in body:
        record = db.scalar(
            select(Attendance).where(Attendance.student_id == entry.student_id, Attendance.date == entry.date)
        )
        if record is None:
            record = Attendance(student_id=entry.student_id, date=entry.date)
            db.add(record)
        record.status = entry.status
        record.reason = entry.reason
        record.recorded_by = teacher.id
        saved.append(record)
    db.commit()
    return saved


@router.get("", response_model=list[AttendanceOut])
def list_attendance(
    db: DB, _: Teacher, day: date = Query(alias="date"), grade: int | None = None, class_no: int | None = None
) -> list[Attendance]:
    query = select(Attendance).join(User, User.id == Attendance.student_id).where(Attendance.date == day)
    if grade is not None:
        query = query.where(User.grade == grade)
    if class_no is not None:
        query = query.where(User.class_no == class_no)
    return list(db.scalars(query.order_by(User.number)))


@router.get("/students/{student_id}", response_model=MonthlyAttendance)
def monthly_attendance(
    student_id: int, db: DB, user: CurrentUser, month: str = Query(pattern=r"^\d{4}-\d{2}$")
) -> MonthlyAttendance:
    """월별 출결 (캘린더 + 요약 카드 4종용). month 형식: 2026-10"""
    if user.role != Role.teacher and user.id != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "볼 수 없는 학생입니다")
    year, mon = map(int, month.split("-"))
    records = list(
        db.scalars(
            select(Attendance)
            .where(
                Attendance.student_id == student_id,
                extract("year", Attendance.date) == year,
                extract("month", Attendance.date) == mon,
            )
            .order_by(Attendance.date)
        )
    )
    counts = Counter(r.status for r in records)
    return MonthlyAttendance(
        month=month,
        counts={s: counts[s] for s in AttendanceStatus},
        records=[AttendanceOut.model_validate(r) for r in records],
    )
