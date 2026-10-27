from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, Teacher
from app.models import Role, User
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/students", response_model=list[UserOut])
def list_students(db: DB, _: Teacher, grade: int | None = None, class_no: int | None = None) -> list[User]:
    query = select(User).where(User.role == Role.student)
    if grade is not None:
        query = query.where(User.grade == grade)
    if class_no is not None:
        query = query.where(User.class_no == class_no)
    return list(db.scalars(query.order_by(User.grade, User.class_no, User.number)))
