from collections import Counter
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.deps import DB, CurrentUser, Teacher
from app.models import MeisterCategory, MeisterSubmission, Role, SubmissionStatus, User
from app.schemas.meister import (
    ApproveIn,
    CategoryScore,
    RejectIn,
    ReviewSummary,
    StudentScore,
    SubmissionCreate,
    SubmissionOut,
    SubmissionPage,
    SubmissionWithStudent,
)
from app.schemas.user import UserOut

router = APIRouter(prefix="/meister", tags=["meister"])


@router.post("/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def create_submission(body: SubmissionCreate, db: DB, user: CurrentUser) -> MeisterSubmission:
    if user.role != Role.student:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "학생만 신청할 수 있습니다")
    submission = MeisterSubmission(student_id=user.id, **body.model_dump())
    db.add(submission)
    db.commit()
    return submission


@router.get("/submissions/me", response_model=list[SubmissionOut])
def my_submissions(db: DB, user: CurrentUser) -> list[MeisterSubmission]:
    query = select(MeisterSubmission).where(MeisterSubmission.student_id == user.id)
    return list(db.scalars(query.order_by(MeisterSubmission.created_at.desc())))


@router.get("/submissions", response_model=SubmissionPage)
def list_submissions(
    db: DB,
    _: Teacher,
    status_: SubmissionStatus | None = Query(None, alias="status"),
    category: MeisterCategory | None = None,
    grade: int | None = None,
    student_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(15, ge=1, le=100),
) -> SubmissionPage:
    query = select(MeisterSubmission).join(MeisterSubmission.student)
    if status_:
        query = query.where(MeisterSubmission.status == status_)
    if category:
        query = query.where(MeisterSubmission.category == category)
    if grade is not None:
        query = query.where(User.grade == grade)
    if student_id is not None:
        query = query.where(MeisterSubmission.student_id == student_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MeisterSubmission.created_at.desc(), MeisterSubmission.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return SubmissionPage(
        items=[SubmissionWithStudent.model_validate(r) for r in rows], total=total, page=page, size=size
    )


@router.get("/submissions/summary", response_model=ReviewSummary)
def review_summary(db: DB, _: Teacher) -> ReviewSummary:
    pending = db.execute(
        select(User.grade, MeisterSubmission.category)
        .join(MeisterSubmission.student)
        .where(MeisterSubmission.status == SubmissionStatus.pending)
    ).all()
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    reviewed = Counter(db.scalars(select(MeisterSubmission.status).where(MeisterSubmission.reviewed_at >= month_start)))
    return ReviewSummary(
        pending_by_grade=dict(Counter(g for g, _ in pending if g is not None)),
        approved_this_month=reviewed[SubmissionStatus.approved],
        rejected_this_month=reviewed[SubmissionStatus.rejected],
        pending_by_category={c: sum(1 for _, pc in pending if pc == c) for c in MeisterCategory},
    )


def _get_submission(db: DB, submission_id: int) -> MeisterSubmission:
    submission = db.get(MeisterSubmission, submission_id)
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "신청을 찾을 수 없습니다")
    return submission


@router.get("/submissions/{submission_id}", response_model=SubmissionWithStudent)
def get_submission(submission_id: int, db: DB, user: CurrentUser) -> MeisterSubmission:
    submission = _get_submission(db, submission_id)
    if user.role != Role.teacher and submission.student_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "볼 수 없는 신청입니다")
    return submission


def _review(db: DB, submission_id: int, reviewer: User, new_status: SubmissionStatus, memo: str | None):
    submission = _get_submission(db, submission_id)
    if submission.status != SubmissionStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 처리된 신청입니다")
    submission.status = new_status
    submission.review_memo = memo
    submission.reviewer_id = reviewer.id
    submission.reviewed_at = datetime.now()
    return submission


@router.post("/submissions/{submission_id}/approve", response_model=SubmissionOut)
def approve(submission_id: int, body: ApproveIn, db: DB, teacher: Teacher) -> MeisterSubmission:
    submission = _review(db, submission_id, teacher, SubmissionStatus.approved, body.memo)
    submission.score = body.score
    db.commit()
    return submission


@router.post("/submissions/{submission_id}/reject", response_model=SubmissionOut)
def reject(submission_id: int, body: RejectIn, db: DB, teacher: Teacher) -> MeisterSubmission:
    submission = _review(db, submission_id, teacher, SubmissionStatus.rejected, body.memo)
    db.commit()
    return submission


@router.get("/scores/{student_id}", response_model=StudentScore)
def student_score(student_id: int, db: DB, user: CurrentUser) -> StudentScore:
    if user.role != Role.teacher and user.id != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "볼 수 없는 학생입니다")
    student = db.get(User, student_id)
    if student is None or student.role != Role.student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "학생을 찾을 수 없습니다")

    approved = list(
        db.scalars(
            select(MeisterSubmission).where(
                MeisterSubmission.student_id == student_id,
                MeisterSubmission.status == SubmissionStatus.approved,
            )
        )
    )
    categories = []
    for category in MeisterCategory:
        items = [s for s in approved if s.category == category]
        categories.append(
            CategoryScore(
                category=category,
                score=sum(s.score or 0 for s in items),
                items=[SubmissionOut.model_validate(s) for s in items],
            )
        )
    return StudentScore(
        student=UserOut.model_validate(student),
        total=sum(c.score for c in categories),
        categories=categories,
    )
