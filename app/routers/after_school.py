from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from app.deps import DB, CurrentUser, Teacher
from app.models import AfterSchoolCourse, AfterSchoolEnrollment, Role, User
from app.schemas.user import UserOut

router = APIRouter(prefix="/after-school", tags=["after-school"])

TIME = r"^([01]\d|2[0-3]):[0-5]\d$"


class CourseIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    weekday: int = Field(ge=0, le=4)
    start_time: str = Field(pattern=TIME)
    end_time: str = Field(pattern=TIME)
    room: str | None = None
    capacity: int = Field(ge=1)
    semester: str = Field(pattern=r"^\d{4}-[12]$")
    is_open: bool = True

    @model_validator(mode="after")
    def check_time(self):
        if self.end_time <= self.start_time:
            raise ValueError("종료 시간은 시작 시간 이후여야 합니다")
        return self


class CourseOut(CourseIn):
    id: int
    teacher_name: str
    enrolled: int
    enrolled_by_me: bool


def _out(course: AfterSchoolCourse, user: User) -> CourseOut:
    return CourseOut(
        id=course.id,
        teacher_name=course.teacher.name,
        enrolled=len(course.enrollments),
        enrolled_by_me=any(e.student_id == user.id for e in course.enrollments),
        **CourseIn.model_validate(course, from_attributes=True).model_dump(),
    )


def _get(db: DB, course_id: int) -> AfterSchoolCourse:
    course = db.get(AfterSchoolCourse, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "강좌를 찾을 수 없습니다")
    return course


@router.get("/courses", response_model=list[CourseOut])
def list_courses(semester: str, db: DB, user: CurrentUser) -> list[CourseOut]:
    query = select(AfterSchoolCourse).where(AfterSchoolCourse.semester == semester)
    courses = db.scalars(query.order_by(AfterSchoolCourse.weekday, AfterSchoolCourse.start_time))
    return [_out(c, user) for c in courses]


@router.get("/me", response_model=list[CourseOut])
def my_courses(db: DB, user: CurrentUser) -> list[CourseOut]:
    if user.role == Role.teacher:
        courses = db.scalars(select(AfterSchoolCourse).where(AfterSchoolCourse.teacher_id == user.id))
    else:
        courses = db.scalars(
            select(AfterSchoolCourse).join(AfterSchoolEnrollment).where(AfterSchoolEnrollment.student_id == user.id)
        )
    return [_out(c, user) for c in courses]


@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(body: CourseIn, db: DB, teacher: Teacher) -> CourseOut:
    course = AfterSchoolCourse(teacher_id=teacher.id, **body.model_dump())
    db.add(course)
    db.commit()
    return _out(course, teacher)


@router.put("/courses/{course_id}", response_model=CourseOut)
def update_course(course_id: int, body: CourseIn, db: DB, teacher: Teacher) -> CourseOut:
    course = _get(db, course_id)
    if body.capacity < len(course.enrollments):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "정원을 현재 신청 인원보다 적게 줄일 수 없습니다")
    for key, value in body.model_dump().items():
        setattr(course, key, value)
    db.commit()
    return _out(course, teacher)


@router.post("/courses/{course_id}/enroll", response_model=CourseOut)
def enroll(course_id: int, db: DB, user: CurrentUser) -> CourseOut:
    if user.role != Role.student:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "학생만 신청할 수 있습니다")
    course = _get(db, course_id)
    if not course.is_open:
        raise HTTPException(status.HTTP_409_CONFLICT, "신청 기간이 아닙니다")
    if any(e.student_id == user.id for e in course.enrollments):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 신청한 강좌입니다")
    if len(course.enrollments) >= course.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "정원이 찼습니다")

    mine = db.scalars(
        select(AfterSchoolCourse)
        .join(AfterSchoolEnrollment)
        .where(
            AfterSchoolEnrollment.student_id == user.id,
            AfterSchoolCourse.semester == course.semester,
            AfterSchoolCourse.weekday == course.weekday,
        )
    )
    for other in mine:
        if other.start_time < course.end_time and course.start_time < other.end_time:
            raise HTTPException(status.HTTP_409_CONFLICT, f"'{other.name}' 강좌와 시간이 겹칩니다")

    course.enrollments.append(AfterSchoolEnrollment(student_id=user.id))
    db.commit()
    return _out(course, user)


@router.delete("/courses/{course_id}/enroll", response_model=CourseOut)
def cancel_enrollment(course_id: int, db: DB, user: CurrentUser) -> CourseOut:
    course = _get(db, course_id)
    enrollment = next((e for e in course.enrollments if e.student_id == user.id), None)
    if enrollment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "신청 내역이 없습니다")
    course.enrollments.remove(enrollment)
    db.commit()
    return _out(course, user)


@router.get("/courses/{course_id}/students", response_model=list[UserOut])
def course_students(course_id: int, db: DB, _: Teacher) -> list[User]:
    course = _get(db, course_id)
    return sorted((e.student for e in course.enrollments), key=lambda s: s.student_id or "")
