import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.user import User


class ClubType(enum.StrEnum):
    creative = "창체"
    self_directed = "자율"


class ClubRole(enum.StrEnum):
    leader = "부장"
    member = "부원"


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    type: Mapped[ClubType] = mapped_column(Enum(ClubType), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    room: Mapped[str | None] = mapped_column(String(50))
    advisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    advisor: Mapped[User | None] = relationship()
    members: Mapped[list["ClubMember"]] = relationship(back_populates="club", cascade="all, delete-orphan")


class ClubMember(Base):
    __tablename__ = "club_members"
    __table_args__ = (UniqueConstraint("club_id", "student_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[ClubRole] = mapped_column(Enum(ClubRole), default=ClubRole.member)

    club: Mapped[Club] = relationship(back_populates="members")
    student: Mapped[User] = relationship()


class ClubActivity(Base):
    __tablename__ = "club_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text, default="")
    written_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
