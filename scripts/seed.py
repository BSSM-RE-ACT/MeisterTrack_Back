"""개발용 샘플 데이터. 실행: uv run python -m scripts.seed"""

from datetime import date, timedelta

from app.db import SessionLocal
from app.models import (
    AfterSchoolCourse,
    Attendance,
    AttendanceStatus,
    Club,
    ClubActivity,
    ClubMember,
    ClubRole,
    ClubType,
    MeisterCategory,
    MeisterSubmission,
    MileageRecord,
    MileageType,
    Role,
    SchoolEvent,
    SubmissionStatus,
    TimetableSlot,
    User,
)


def main() -> None:
    with SessionLocal() as db:
        if db.query(User).count():
            print("이미 데이터가 있어 건너뜁니다")
            return

        teacher = User(email="teacher@bssm.hs.kr", name="이선생", role=Role.teacher, position="담임교사")
        students = [
            User(email=f"student{i}@bssm.hs.kr", name=name, role=Role.student, grade=2, class_no=1, number=i)
            for i, name in enumerate(["김부마", "이소마", "박마고"], start=1)
        ]
        db.add_all([teacher, *students])
        db.flush()

        db.add_all(
            [
                MeisterSubmission(
                    student_id=students[0].id,
                    category=MeisterCategory.technical,
                    item="전공관련 자격증",
                    title="정보처리기능사",
                ),
                MeisterSubmission(
                    student_id=students[1].id,
                    category=MeisterCategory.language,
                    item="공인어학성적",
                    title="TOEIC 800",
                    status=SubmissionStatus.approved,
                    score=20,
                    reviewer_id=teacher.id,
                ),
            ]
        )

        today = date.today()
        # 대부분 출석, 가끔 지각·조퇴·결석
        rare = [AttendanceStatus.late, AttendanceStatus.early_leave, AttendanceStatus.absent]
        for offset in range(10):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            for i, student in enumerate(students):
                status = rare[(offset + i) % 3] if (offset + i) % 4 == 0 else AttendanceStatus.present
                db.add(Attendance(student_id=student.id, date=day, status=status, recorded_by=teacher.id))

        subjects = ["프로그래밍", "자료구조", "국어", "수학", "영어", "체육", "네트워크"]
        db.add_all(
            TimetableSlot(grade=2, class_no=1, weekday=w, period=p, subject=subjects[(w + p) % len(subjects)])
            for w in range(5)
            for p in range(1, 8)
        )

        db.add_all(
            [
                MileageRecord(
                    student_id=students[0].id,
                    type=MileageType.merit,
                    points=3,
                    reason="교내 봉사활동",
                    date=today,
                    given_by=teacher.id,
                ),
                MileageRecord(
                    student_id=students[0].id,
                    type=MileageType.demerit,
                    points=1,
                    reason="지각",
                    date=today,
                    given_by=teacher.id,
                ),
            ]
        )

        club = Club(name="BSM 로봇부", type=ClubType.creative, room="3층 실습실", advisor_id=teacher.id)
        club.members = [
            ClubMember(student_id=students[0].id, role=ClubRole.leader),
            ClubMember(student_id=students[1].id),
        ]
        db.add(club)
        db.flush()
        db.add(ClubActivity(club_id=club.id, date=today, title="라인트레이서 제작", written_by=teacher.id))

        db.add(
            AfterSchoolCourse(
                name="알고리즘 심화",
                teacher_id=teacher.id,
                weekday=1,
                start_time="16:40",
                end_time="18:20",
                room="2층 컴퓨터실",
                capacity=20,
                semester=f"{today.year}-{1 if today.month < 8 else 2}",
            )
        )
        db.add(
            SchoolEvent(title="2학년 현장체험학습", start_date=today, end_date=today, grade=2, created_by=teacher.id)
        )

        db.commit()
        print("샘플 데이터를 넣었습니다")


if __name__ == "__main__":
    main()
