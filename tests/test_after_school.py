from tests.conftest import auth

COURSE = {
    "name": "알고리즘 심화",
    "weekday": 1,
    "start_time": "16:40",
    "end_time": "18:20",
    "capacity": 1,
    "semester": "2026-2",
}


def create(client, teacher, **overrides):
    res = client.post("/after-school/courses", json={**COURSE, **overrides}, headers=auth(teacher))
    assert res.status_code == 201
    return res.json()["id"]


def test_enroll_flow(client, db, student, teacher):
    from app.models import Role, User

    course_id = create(client, teacher)
    res = client.post(f"/after-school/courses/{course_id}/enroll", headers=auth(student))
    assert res.status_code == 200
    assert res.json()["enrolled_by_me"] is True

    assert client.post(f"/after-school/courses/{course_id}/enroll", headers=auth(student)).status_code == 409

    other = User(email="o@bssm.hs.kr", name="이소마", role=Role.student, grade=2, class_no=1, number=4)
    db.add(other)
    db.commit()
    res = client.post(f"/after-school/courses/{course_id}/enroll", headers=auth(other))
    assert res.status_code == 409
    assert res.json()["detail"] == "정원이 찼습니다"

    students = client.get(f"/after-school/courses/{course_id}/students", headers=auth(teacher)).json()
    assert [s["name"] for s in students] == ["김부마"]

    assert client.delete(f"/after-school/courses/{course_id}/enroll", headers=auth(student)).status_code == 200
    assert client.get("/after-school/me", headers=auth(student)).json() == []


def test_time_conflict_and_closed(client, student, teacher):
    first = create(client, teacher, capacity=10)
    overlapping = create(client, teacher, name="웹 개발", start_time="17:30", end_time="19:00", capacity=10)
    closed = create(client, teacher, name="마감", weekday=3, is_open=False)

    client.post(f"/after-school/courses/{first}/enroll", headers=auth(student))
    res = client.post(f"/after-school/courses/{overlapping}/enroll", headers=auth(student))
    assert res.status_code == 409
    assert "시간이 겹칩니다" in res.json()["detail"]
    assert client.post(f"/after-school/courses/{closed}/enroll", headers=auth(student)).status_code == 409


def test_course_validation(client, teacher):
    bad = {**COURSE, "start_time": "18:00", "end_time": "17:00"}
    assert client.post("/after-school/courses", json=bad, headers=auth(teacher)).status_code == 422
