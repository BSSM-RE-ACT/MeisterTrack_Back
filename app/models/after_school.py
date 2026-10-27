from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.user import User


class AfterSchoolCourse(Base):
    __tablename__ = "after_school_courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # 0=월 ~ 4=금
    weekday: Mapped[int]
    start_time: Mapped[str] = mapped_column(String(5))  # "16:40"
    end_time: Mapped[str] = mapped_column(String(5))
    room: Mapped[str | None] = mapped_column(String(50))
    capacity: Mapped[int]
    # 예: "2026-2"
    semester: Mapped[str] = mapped_column(String(10), index=True)
    is_open: Mapped[bool] = mapped_column(default=True)

    teacher: Mapped[User] = relationship()
    enrollments: Mapped[list["AfterSchoolEnrollment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class AfterSchoolEnrollment(Base):
    __tablename__ = "after_school_enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("after_school_courses.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    course: Mapped[AfterSchoolCourse] = relationship(back_populates="enrollments")
    student: Mapped[User] = relationship()
