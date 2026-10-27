from tests.conftest import auth


def test_teacher_saves_and_student_reads(client, student, teacher):
    body = [
        {"weekday": 0, "period": 1, "subject": "프로그래밍", "teacher_name": "이선생"},
        {"weekday": 0, "period": 2, "subject": "국어"},
    ]
    res = client.put("/timetable?grade=2&class_no=1", json=body, headers=auth(teacher))
    assert res.status_code == 200

    # 다시 저장하면 통째로 바뀐다
    body = [{"weekday": 4, "period": 7, "subject": "체육"}]
    client.put("/timetable?grade=2&class_no=1", json=body, headers=auth(teacher))

    mine = client.get("/timetable/me", headers=auth(student)).json()
    assert [(s["weekday"], s["period"], s["subject"]) for s in mine["slots"]] == [(4, 7, "체육")]


def test_duplicate_slot_and_permission(client, student, teacher):
    dup = [{"weekday": 0, "period": 1, "subject": "a"}, {"weekday": 0, "period": 1, "subject": "b"}]
    assert client.put("/timetable?grade=2&class_no=1", json=dup, headers=auth(teacher)).status_code == 400
    assert client.put("/timetable?grade=2&class_no=1", json=[], headers=auth(student)).status_code == 403
    assert client.get("/timetable/me", headers=auth(teacher)).status_code == 400
