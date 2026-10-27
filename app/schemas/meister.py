from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import MeisterCategory, SubmissionStatus
from app.schemas.user import UserOut


class SubmissionCreate(BaseModel):
    category: MeisterCategory
    item: str = Field(max_length=100)
    title: str = Field(max_length=200)
    content: str = ""
    attachment_url: str | None = None
    acquired_at: datetime | None = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    category: MeisterCategory
    item: str
    title: str
    content: str
    attachment_url: str | None
    acquired_at: datetime | None
    status: SubmissionStatus
    score: float | None
    review_memo: str | None
    reviewed_at: datetime | None
    created_at: datetime


class SubmissionWithStudent(SubmissionOut):
    student: UserOut


class SubmissionPage(BaseModel):
    items: list[SubmissionWithStudent]
    total: int
    page: int
    size: int


class ApproveIn(BaseModel):
    # 등급은 자동 계산이라 점수만 받는다
    score: float = Field(ge=0)
    memo: str | None = None


class RejectIn(BaseModel):
    memo: str = Field(min_length=1)


class ReviewSummary(BaseModel):
    pending_by_grade: dict[int, int]
    approved_this_month: int
    rejected_this_month: int
    pending_by_category: dict[MeisterCategory, int]


class CategoryScore(BaseModel):
    category: MeisterCategory
    score: float
    # TODO: 환산등급 계산 규칙 확정 후 채우기
    grade: str | None = None
    items: list[SubmissionOut]


class StudentScore(BaseModel):
    student: UserOut
    total: float
    categories: list[CategoryScore]
