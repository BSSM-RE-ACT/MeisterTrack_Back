from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SchoolEvent(Base):
    """교사가 직접 등록한 학사일정. NEIS 일정과 합쳐서 보여준다."""

    __tablename__ = "school_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date)
    # 비우면 전체, 값이 있으면 해당 학년만
    grade: Mapped[int | None]
    memo: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
