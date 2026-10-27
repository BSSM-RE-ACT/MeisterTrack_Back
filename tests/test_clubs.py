from app.models import Role, User
from tests.conftest import auth


def test_club_flow(client, db, student, teacher):
    other = User(email="o@bssm.hs.kr", name="이소마", role=Role.student, grade=2, class_no=1, number=4)
    db.add(other)
    db.commit()

    body = {"name": "BSM 로봇부", "type": "창체", "room": "3층 실습실", "advisor_id": teacher.id}
    club_id = client.post("/clubs", json=body, headers=auth(teacher)).json()["id"]

    members = [{"student_id": other.id}, {"student_id": student.id, "role": "부장"}]
    detail = client.put(f"/clubs/{club_id}/members", json=members, headers=auth(teacher)).json()
    assert [(m["student"]["name"], m["role"]) for m in detail["members"]] == [("김부마", "부장"), ("이소마", "부원")]
    assert detail["advisor_name"] == "이선생"

    assert [c["name"] for c in client.get("/clubs/me", headers=auth(other)).json()] == ["BSM 로봇부"]
    assert client.get("/clubs?type=자율", headers=auth(student)).json() == []

    activity = {"date": "2026-10-27", "title": "라인트레이서 제작"}
    assert client.post(f"/clubs/{club_id}/activities", json=activity, headers=auth(student)).status_code == 201
    assert client.post(f"/clubs/{club_id}/activities", json=activity, headers=auth(other)).status_code == 403
    assert len(client.get(f"/clubs/{club_id}/activities", headers=auth(other)).json()) == 1

    # 명단 교체
    detail = client.put(f"/clubs/{club_id}/members", json=[{"student_id": other.id}], headers=auth(teacher)).json()
    assert detail["member_count"] == 1


def test_members_validation(client, student, teacher):
    club_id = client.post("/clubs", json={"name": "a", "type": "자율"}, headers=auth(teacher)).json()["id"]
    dup = [{"student_id": student.id}, {"student_id": student.id}]
    assert client.put(f"/clubs/{club_id}/members", json=dup, headers=auth(teacher)).status_code == 400
    bad = [{"student_id": teacher.id}]
    assert client.put(f"/clubs/{club_id}/members", json=bad, headers=auth(teacher)).status_code == 400
