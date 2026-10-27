import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.user import User


class MileageType(enum.StrEnum):
    merit = "상점"
    demerit = "벌점"


class MileageRecord(Base):
    """상벌점(그림마일리지) 1건. points는 항상 양수, 부호는 type으로 구분한다."""

    __tablename__ = "mileage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[MileageType] = mapped_column(Enum(MileageType))
    points: Mapped[int]
    reason: Mapped[str] = mapped_column(String(200))
    date: Mapped[date] = mapped_column(Date)
    given_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    student: Mapped[User] = relationship(foreign_keys=[student_id])
    teacher: Mapped[User] = relationship(foreign_keys=[given_by])
