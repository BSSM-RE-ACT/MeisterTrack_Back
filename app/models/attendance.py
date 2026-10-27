import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AttendanceStatus(enum.StrEnum):
    present = "출석"
    late = "지각"
    early_leave = "조퇴"
    absent = "결석"


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("student_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus))
    reason: Mapped[str | None] = mapped_column(String(200))
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
