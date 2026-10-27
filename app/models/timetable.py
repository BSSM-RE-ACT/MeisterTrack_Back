from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TimetableSlot(Base):
    """반별 주간 시간표 한 칸. weekday 0=월 ~ 4=금, period 1~8."""

    __tablename__ = "timetable_slots"
    __table_args__ = (UniqueConstraint("grade", "class_no", "weekday", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    grade: Mapped[int]
    class_no: Mapped[int]
    weekday: Mapped[int]
    period: Mapped[int]
    subject: Mapped[str] = mapped_column(String(50))
    teacher_name: Mapped[str | None] = mapped_column(String(50))
    room: Mapped[str | None] = mapped_column(String(50))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
