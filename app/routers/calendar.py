from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import or_, select

from app.deps import DB, CurrentUser, Teacher
from app.models import Role, SchoolEvent
from app.services import neis

router = APIRouter(prefix="/calendar", tags=["calendar"])


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    grade: int | None = Field(None, ge=1, le=3)
    memo: str | None = None

    @model_validator(mode="after")
    def check_range(self):
        if self.end_date < self.start_date:
            raise ValueError("종료일은 시작일 이후여야 합니다")
        return self


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None
    title: str
    start_date: date
    end_date: date
    grade: int | None
    memo: str | None = None
    # neis: NEIS 학사일정(수정 불가) / school: 교사 등록
    source: str = "school"


@router.get("", response_model=list[EventOut])
def list_events(start: date, end: date, db: DB, user: CurrentUser) -> list[EventOut]:
    query = select(SchoolEvent).where(SchoolEvent.start_date <= end, SchoolEvent.end_date >= start)
    if user.role == Role.student:
        query = query.where(or_(SchoolEvent.grade.is_(None), SchoolEvent.grade == user.grade))
    events = [EventOut.model_validate(e) for e in db.scalars(query.order_by(SchoolEvent.start_date))]

    try:
        neis_events = neis.get_school_schedule(start, end)
    except neis.NeisError:
        neis_events = []  # NEIS 장애 시 학교 등록 일정만 보여준다
    events += [
        EventOut(id=None, title=e["title"], start_date=e["date"], end_date=e["date"], grade=None, source="neis")
        for e in neis_events
    ]
    return sorted(events, key=lambda e: e.start_date)


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(body: EventIn, db: DB, teacher: Teacher) -> SchoolEvent:
    event = SchoolEvent(**body.model_dump(), created_by=teacher.id)
    db.add(event)
    db.commit()
    return event


def _get(db: DB, event_id: int) -> SchoolEvent:
    event = db.get(SchoolEvent, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "일정을 찾을 수 없습니다")
    return event


@router.put("/{event_id}", response_model=EventOut)
def update_event(event_id: int, body: EventIn, db: DB, _: Teacher) -> SchoolEvent:
    event = _get(db, event_id)
    for key, value in body.model_dump().items():
        setattr(event, key, value)
    db.commit()
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: DB, _: Teacher) -> None:
    db.delete(_get(db, event_id))
    db.commit()
