from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.deps import DB, CurrentUser, Teacher
from app.models import MeisterCategory, MeisterSubmission, Role, SubmissionStatus
from app.services import ai

router = APIRouter(prefix="/ai", tags=["ai"])


class ClassifyIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    content: str = Field("", max_length=4000)


class ClassifyOut(BaseModel):
    category: MeisterCategory
    item: str
    reason: str


class SimilarCase(BaseModel):
    id: int
    title: str
    item: str
    score: float


class ReviewAssistOut(BaseModel):
    summary: str
    checks: list[str]
    suggested_score: float
    score_reason: str
    similar: list[SimilarCase]
    score_min: float | None
    score_max: float | None
    score_avg: float | None


def _call(fn, *args):
    try:
        return fn(*args)
    except ai.AIDisabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AI 기능이 꺼져 있습니다") from None
    except ai.AIFailed:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 응답을 받지 못했습니다. 잠시 후 다시 시도하세요") from None


@router.get("/items")
def items() -> dict[MeisterCategory, list[str]]:
    """영역별 세부 항목 목록"""
    return ai.ITEMS


@router.post("/classify", response_model=ClassifyOut)
def classify(body: ClassifyIn, user: CurrentUser) -> ai.Classification:
    if user.role != Role.student:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "학생만 사용할 수 있습니다")
    return _call(ai.classify, body.title, body.content)


@router.get("/review/{submission_id}", response_model=ReviewAssistOut)
def review_assist(submission_id: int, db: DB, _: Teacher) -> ReviewAssistOut:
    submission = db.get(MeisterSubmission, submission_id)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "신청을 찾을 수 없습니다")

    approved = select(MeisterSubmission).where(
        MeisterSubmission.status == SubmissionStatus.approved,
        MeisterSubmission.category == submission.category,
        MeisterSubmission.id != submission.id,
        MeisterSubmission.score.is_not(None),
    )
    same_item = list(db.scalars(approved.where(MeisterSubmission.item == submission.item)))
    # 같은 항목 승인 사례가 없으면 같은 영역으로 넓힌다
    cases = same_item or list(db.scalars(approved))
    cases.sort(key=lambda s: s.reviewed_at or s.created_at, reverse=True)
    similar = [SimilarCase(id=s.id, title=s.title, item=s.item, score=s.score) for s in cases[:5]]
    scores = [s.score for s in cases]
    score_range = (min(scores), max(scores)) if scores else None

    advice = _call(
        ai.review,
        {
            "category": submission.category.value,
            "item": submission.item,
            "title": submission.title,
            "content": submission.content,
            "attachment_url": submission.attachment_url,
            "acquired_at": submission.acquired_at.date().isoformat() if submission.acquired_at else None,
        },
        [s.model_dump() for s in similar],
        score_range,
    )
    return ReviewAssistOut(
        **advice.model_dump(),
        similar=similar,
        score_min=score_range[0] if score_range else None,
        score_max=score_range[1] if score_range else None,
        score_avg=round(sum(scores) / len(scores), 1) if scores else None,
    )
