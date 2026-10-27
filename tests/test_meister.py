from tests.conftest import auth

SUBMISSION = {"category": "전문기술역량", "item": "전공관련 자격증", "title": "정보처리기능사"}


def submit(client, student):
    res = client.post("/meister/submissions", json=SUBMISSION, headers=auth(student))
    assert res.status_code == 201
    return res.json()["id"]


def test_student_submits_and_teacher_approves(client, student, teacher):
    submission_id = submit(client, student)

    page = client.get("/meister/submissions?status=대기", headers=auth(teacher)).json()
    assert page["total"] == 1
    assert page["items"][0]["student"]["name"] == "김부마"

    summary = client.get("/meister/submissions/summary", headers=auth(teacher)).json()
    assert summary["pending_by_grade"] == {"2": 1}
    assert summary["pending_by_category"]["전문기술역량"] == 1

    res = client.post(f"/meister/submissions/{submission_id}/approve", json={"score": 30}, headers=auth(teacher))
    assert res.status_code == 200
    assert res.json()["status"] == "승인"

    # 이미 처리된 신청은 다시 처리할 수 없다
    res = client.post(f"/meister/submissions/{submission_id}/reject", json={"memo": "x"}, headers=auth(teacher))
    assert res.status_code == 409

    score = client.get(f"/meister/scores/{student.id}", headers=auth(student)).json()
    assert score["total"] == 30
    assert len(score["categories"]) == 5
    technical = next(c for c in score["categories"] if c["category"] == "전문기술역량")
    assert technical["score"] == 30


def test_reject_requires_memo(client, student, teacher):
    submission_id = submit(client, student)
    res = client.post(f"/meister/submissions/{submission_id}/reject", json={"memo": ""}, headers=auth(teacher))
    assert res.status_code == 422


def test_student_cannot_review(client, student):
    submission_id = submit(client, student)
    res = client.post(f"/meister/submissions/{submission_id}/approve", json={"score": 10}, headers=auth(student))
    assert res.status_code == 403
    assert client.get("/meister/submissions", headers=auth(student)).status_code == 403


def test_cancel_own_pending(client, student, teacher):
    submission_id = submit(client, student)
    assert client.delete(f"/meister/submissions/{submission_id}", headers=auth(teacher)).status_code == 403
    assert client.delete(f"/meister/submissions/{submission_id}", headers=auth(student)).status_code == 204

    submission_id = submit(client, student)
    client.post(f"/meister/submissions/{submission_id}/approve", json={"score": 5}, headers=auth(teacher))
    assert client.delete(f"/meister/submissions/{submission_id}", headers=auth(student)).status_code == 409


def test_score_list(client, student, teacher):
    approved = submit(client, student)
    client.post(f"/meister/submissions/{approved}/approve", json={"score": 12.5}, headers=auth(teacher))
    submit(client, student)

    rows = client.get("/meister/scores?grade=2", headers=auth(teacher)).json()
    assert len(rows) == 1
    assert rows[0]["total"] == 12.5
    assert rows[0]["scores"]["전문기술역량"] == 12.5
    assert rows[0]["scores"]["외국어능력"] == 0
    assert rows[0]["pending"] == 1
    assert client.get("/meister/scores", headers=auth(student)).status_code == 403


def test_submission_requires_title_and_item(client, student):
    for blank in ({"title": "  "}, {"item": ""}):
        body = {**SUBMISSION, **blank}
        assert client.post("/meister/submissions", json=body, headers=auth(student)).status_code == 422
