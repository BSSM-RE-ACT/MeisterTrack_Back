from pydantic import BaseModel, ConfigDict

from app.models import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: Role
    grade: int | None
    class_no: int | None
    number: int | None
    student_id: str | None
    position: str | None
    phone: str | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
