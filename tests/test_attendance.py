from tests.conftest import auth


def test_upsert_and_monthly(client, student, teacher):
    body = [
        {"student_id": student.id, "date": "2026-10-26", "status": "출석"},
        {"student_id": student.id, "date": "2026-10-27", "status": "지각", "reason": "버스 지연"},
    ]
    assert client.put("/attendance", json=body, headers=auth(teacher)).status_code == 200

    # 같은 날짜는 덮어쓴다
    body = [{"student_id": student.id, "date": "2026-10-27", "status": "결석"}]
    assert client.put("/attendance", json=body, headers=auth(teacher)).status_code == 200

    res = client.get(f"/attendance/students/{student.id}?month=2026-10", headers=auth(student))
    data = res.json()
    assert len(data["records"]) == 2
    assert data["counts"] == {"출석": 1, "지각": 0, "조퇴": 0, "결석": 1}

    daily = client.get("/attendance?date=2026-10-27&grade=2&class_no=1", headers=auth(teacher)).json()
    assert [r["status"] for r in daily] == ["결석"]


def test_student_cannot_see_others(client, student, teacher, db):
    from app.models import Role, User

    other = User(email="o@bssm.hs.kr", name="이소마", role=Role.student, grade=2, class_no=1, number=4)
    db.add(other)
    db.commit()
    res = client.get(f"/attendance/students/{other.id}?month=2026-10", headers=auth(student))
    assert res.status_code == 403


def test_rejects_non_student(client, student, teacher):
    for target in (teacher.id, 99999):
        body = [{"student_id": target, "date": "2026-10-27", "status": "출석"}]
        assert client.put("/attendance", json=body, headers=auth(teacher)).status_code == 400
