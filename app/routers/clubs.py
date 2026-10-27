from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.deps import DB, CurrentUser, Teacher
from app.models import Club, ClubActivity, ClubMember, ClubRole, ClubType, Role, User
from app.schemas.user import UserOut

router = APIRouter(prefix="/clubs", tags=["clubs"])


class ClubIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: ClubType
    description: str = ""
    room: str | None = None
    advisor_id: int | None = None


class ClubOut(BaseModel):
    id: int
    name: str
    type: ClubType
    description: str
    room: str | None
    advisor_name: str | None
    member_count: int


class MemberIn(BaseModel):
    student_id: int
    role: ClubRole = ClubRole.member


class MemberOut(BaseModel):
    student: UserOut
    role: ClubRole


class ClubDetail(ClubOut):
    members: list[MemberOut]


class ActivityIn(BaseModel):
    date: date
    title: str = Field(min_length=1, max_length=100)
    content: str = ""


class ActivityOut(ActivityIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


def _out(club: Club) -> ClubOut:
    return ClubOut(
        id=club.id,
        name=club.name,
        type=club.type,
        description=club.description,
        room=club.room,
        advisor_name=club.advisor.name if club.advisor else None,
        member_count=len(club.members),
    )


def _detail(club: Club) -> ClubDetail:
    order = {ClubRole.leader: 0, ClubRole.member: 1}
    members = sorted(club.members, key=lambda m: (order[m.role], m.student.student_id or ""))
    return ClubDetail(
        **_out(club).model_dump(),
        members=[MemberOut(student=UserOut.model_validate(m.student), role=m.role) for m in members],
    )


def _get(db: DB, club_id: int) -> Club:
    club = db.get(Club, club_id)
    if club is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "동아리를 찾을 수 없습니다")
    return club


@router.get("", response_model=list[ClubOut])
def list_clubs(db: DB, _: CurrentUser, type: ClubType | None = None) -> list[ClubOut]:
    query = select(Club).order_by(Club.type, Club.name)
    if type:
        query = query.where(Club.type == type)
    return [_out(c) for c in db.scalars(query)]


@router.get("/me", response_model=list[ClubDetail])
def my_clubs(db: DB, user: CurrentUser) -> list[ClubDetail]:
    if user.role == Role.teacher:
        clubs = db.scalars(select(Club).where(Club.advisor_id == user.id))
    else:
        clubs = db.scalars(select(Club).join(ClubMember).where(ClubMember.student_id == user.id))
    return [_detail(c) for c in clubs]


@router.get("/{club_id}", response_model=ClubDetail)
def get_club(club_id: int, db: DB, _: CurrentUser) -> ClubDetail:
    return _detail(_get(db, club_id))


@router.post("", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
def create_club(body: ClubIn, db: DB, _: Teacher) -> ClubOut:
    club = Club(**body.model_dump())
    db.add(club)
    db.commit()
    return _out(club)


@router.put("/{club_id}", response_model=ClubOut)
def update_club(club_id: int, body: ClubIn, db: DB, _: Teacher) -> ClubOut:
    club = _get(db, club_id)
    for key, value in body.model_dump().items():
        setattr(club, key, value)
    db.commit()
    db.refresh(club)
    return _out(club)


@router.put("/{club_id}/members", response_model=ClubDetail)
def set_members(club_id: int, body: list[MemberIn], db: DB, _: Teacher) -> ClubDetail:
    """부원 명단을 통째로 바꾼다."""
    club = _get(db, club_id)
    ids = [m.student_id for m in body]
    if len(ids) != len(set(ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "같은 학생이 중복됩니다")
    found = set(db.scalars(select(User.id).where(User.id.in_(ids), User.role == Role.student)))
    if missing := set(ids) - found:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"학생을 찾을 수 없습니다: {sorted(missing)}")

    club.members.clear()
    db.flush()
    club.members.extend(ClubMember(student_id=m.student_id, role=m.role) for m in body)
    db.commit()
    db.refresh(club)
    return _detail(club)


@router.get("/{club_id}/activities", response_model=list[ActivityOut])
def list_activities(club_id: int, db: DB, _: CurrentUser) -> list[ClubActivity]:
    _get(db, club_id)
    query = select(ClubActivity).where(ClubActivity.club_id == club_id).order_by(ClubActivity.date.desc())
    return list(db.scalars(query))


@router.post("/{club_id}/activities", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def add_activity(club_id: int, body: ActivityIn, db: DB, user: CurrentUser) -> ClubActivity:
    """활동 기록은 교사 또는 해당 동아리 부장이 쓴다."""
    club = _get(db, club_id)
    is_leader = any(m.student_id == user.id and m.role == ClubRole.leader for m in club.members)
    if user.role != Role.teacher and not is_leader:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "교사 또는 부장만 작성할 수 있습니다")
    activity = ClubActivity(club_id=club_id, written_by=user.id, **body.model_dump())
    db.add(activity)
    db.commit()
    return activity
