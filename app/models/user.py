import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(enum.StrEnum):
    student = "student"
    teacher = "teacher"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    role: Mapped[Role] = mapped_column(Enum(Role))

    # 학생 전용
    grade: Mapped[int | None]
    class_no: Mapped[int | None]
    number: Mapped[int | None]

    # 교사 전용 (예: 담임교사, 교무부장)
    position: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20))

    @property
    def student_id(self) -> str | None:
        """학번 (예: 2학년 1반 3번 → 2103)"""
        if self.grade is None or self.class_no is None or self.number is None:
            return None
        return f"{self.grade}{self.class_no}{self.number:02d}"
