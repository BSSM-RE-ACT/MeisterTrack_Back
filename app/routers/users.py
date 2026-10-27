from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.deps import DB, CurrentUser, Teacher
from app.models import Role, User
from app.schemas.user import UserOut
from app.services.user_import import build_template, import_users

router = APIRouter(prefix="/users", tags=["users"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class MeUpdate(BaseModel):
    phone: str | None = Field(None, max_length=20)


class ImportOut(BaseModel):
    created: int
    updated: int


@router.patch("/me", response_model=UserOut)
def update_me(body: MeUpdate, db: DB, user: CurrentUser) -> User:
    """내 정보 수정. 이름·학년반은 학교에서 일괄 등록하므로 연락처만 바꿀 수 있다."""
    user.phone = body.phone
    db.commit()
    return user


@router.get("/students", response_model=list[UserOut])
def list_students(db: DB, _: Teacher, grade: int | None = None, class_no: int | None = None) -> list[User]:
    query = select(User).where(User.role == Role.student)
    if grade is not None:
        query = query.where(User.grade == grade)
    if class_no is not None:
        query = query.where(User.class_no == class_no)
    return list(db.scalars(query.order_by(User.grade, User.class_no, User.number)))


@router.get("/teachers", response_model=list[UserOut])
def list_teachers(db: DB, _: Teacher) -> list[User]:
    """동아리 지도교사 지정 등에 쓰는 교사 목록"""
    return list(db.scalars(select(User).where(User.role == Role.teacher).order_by(User.name)))


@router.get("/import/template")
def import_template(_: Teacher) -> Response:
    return Response(
        build_template(),
        media_type=XLSX,
        headers={"Content-Disposition": "attachment; filename*=UTF-8''user_import_template.xlsx"},
    )


@router.post("/import", response_model=ImportOut)
async def import_users_from_excel(file: UploadFile, db: DB, _: Teacher) -> ImportOut:
    """엑셀로 학생·교사 일괄 등록. 오류가 있으면 422와 행별 오류 목록을 돌려주고 아무것도 저장하지 않는다."""
    result = import_users(db, await file.read())
    if result.errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=result.errors)
    return ImportOut(created=result.created, updated=result.updated)
