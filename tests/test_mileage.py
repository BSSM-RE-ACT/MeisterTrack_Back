from app.models import Role, User
from tests.conftest import auth


def test_give_and_summaries(client, db, student, teacher):
    other = User(email="o@bssm.hs.kr", name="이소마", role=Role.student, grade=2, class_no=1, number=4)
    db.add(other)
    db.commit()

    give = {"type": "상점", "points": 3, "reason": "봉사활동", "date": "2026-10-27"}
    res = client.post("/mileage", json={**give, "student_ids": [student.id, other.id]}, headers=auth(teacher))
    assert res.status_code == 201
    assert res.json()[0]["teacher_name"] == "이선생"

    demerit = {"type": "벌점", "points": 1, "reason": "지각", "date": "2026-10-27", "student_ids": [student.id]}
    client.post("/mileage", json=demerit, headers=auth(teacher))

    mine = client.get(f"/mileage/students/{student.id}", headers=auth(student)).json()
    assert mine["summary"] == {"merit": 3, "demerit": 1, "total": 2}
    assert len(mine["records"]) == 2

    table = client.get("/mileage/students?grade=2&class_no=1", headers=auth(teacher)).json()
    assert [(r["student"]["name"], r["summary"]["total"]) for r in table] == [("김부마", 2), ("이소마", 3)]

    # 취소
    record_id = mine["records"][0]["id"]
    assert client.delete(f"/mileage/{record_id}", headers=auth(teacher)).status_code == 204


def test_give_rejects_unknown_student_and_student_caller(client, student, teacher):
    body = {"type": "상점", "points": 1, "reason": "x", "date": "2026-10-27", "student_ids": [999]}
    assert client.post("/mileage", json=body, headers=auth(teacher)).status_code == 400
    body["student_ids"] = [student.id]
    assert client.post("/mileage", json=body, headers=auth(student)).status_code == 403
    assert client.get(f"/mileage/students/{teacher.id}", headers=auth(student)).status_code == 403
