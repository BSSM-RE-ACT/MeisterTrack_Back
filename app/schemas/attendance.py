from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models import AttendanceStatus


class AttendanceIn(BaseModel):
    student_id: int
    date: date
    status: AttendanceStatus
    reason: str | None = None


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    date: date
    status: AttendanceStatus
    reason: str | None


class MonthlyAttendance(BaseModel):
    month: str
    counts: dict[AttendanceStatus, int]
    records: list[AttendanceOut]
