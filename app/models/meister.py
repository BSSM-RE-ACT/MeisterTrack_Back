import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.user import User


class MeisterCategory(enum.StrEnum):
    basic = "직업기초능력"
    technical = "전문기술역량"
    character = "인성·직업의식"
    humanities = "인문학적 소양"
    language = "외국어능력"


class SubmissionStatus(enum.StrEnum):
    pending = "대기"
    approved = "승인"
    rejected = "반려"


class MeisterSubmission(Base):
    """학생의 마이스터역량 인증 신청 1건. 교사가 승인하면서 점수를 매긴다."""

    __tablename__ = "meister_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[MeisterCategory] = mapped_column(Enum(MeisterCategory))
    # 세부 항목 (예: 전공관련 자격증, SW관련 대회)
    item: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")
    attachment_url: Mapped[str | None] = mapped_column(String(500))
    acquired_at: Mapped[datetime | None] = mapped_column(DateTime)

    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.pending, index=True
    )
    score: Mapped[float | None]
    review_memo: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    student: Mapped[User] = relationship(foreign_keys=[student_id])
