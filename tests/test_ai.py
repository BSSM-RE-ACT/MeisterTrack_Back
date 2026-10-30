from app.models import MeisterCategory, MeisterSubmission, SubmissionStatus
from app.services import ai
from tests.conftest import auth


def fake_ask(result):
    calls = []

    def _ask(system, prompt, schema):
        calls.append(prompt)
        return schema.model_validate(result)

    return _ask, calls


def test_disabled_without_key(client, student):
    res = client.post("/ai/classify", json={"title": "정보처리기능사 합격"}, headers=auth(student))
    assert res.status_code == 503


def test_classify(client, student, teacher, monkeypatch):
    ask, calls = fake_ask({"category": "전문기술역량", "item": "전공관련 자격증", "reason": "국가기술자격"})
    monkeypatch.setattr(ai, "_ask", ask)
    res = client.post("/ai/classify", json={"title": " 정보처리기능사 ", "content": "합격"}, headers=auth(student))
    assert res.status_code == 200
    assert res.json() == {"category": "전문기술역량", "item": "전공관련 자격증", "reason": "국가기술자격"}
    assert "제목: 정보처리기능사" in calls[0]

    assert client.post("/ai/classify", json={"title": " "}, headers=auth(student)).status_code == 422
    assert client.post("/ai/classify", json={"title": "x"}, headers=auth(teacher)).status_code == 403


def test_classify_fixes_unknown_item(client, student, monkeypatch):
    ask, _ = fake_ask({"category": "외국어능력", "item": "없는 항목", "reason": "-"})
    monkeypatch.setattr(ai, "_ask", ask)
    res = client.post("/ai/classify", json={"title": "TOEIC 850"}, headers=auth(student))
    assert res.json()["item"] == ai.ITEMS[MeisterCategory.language][0]


def test_ai_failure_is_502(client, student, monkeypatch):
    def boom(*_):
        raise ai.AIFailed

    monkeypatch.setattr(ai, "_ask", boom)
    assert client.post("/ai/classify", json={"title": "x"}, headers=auth(student)).status_code == 502


def add(db, student, title, item="전공관련 자격증", status=SubmissionStatus.approved, score=None):
    s = MeisterSubmission(
        student_id=student.id, category=MeisterCategory.technical, item=item, title=title, status=status, score=score
    )
    db.add(s)
    db.commit()
    return s


def test_review_assist(client, db, student, teacher, monkeypatch):
    add(db, student, "정보처리기능사", score=10)
    add(db, student, "리눅스마스터 2급", score=6)
    add(db, student, "해커톤 대상", item="SW관련 대회", score=30)
    target = add(db, student, "정보처리산업기사", status=SubmissionStatus.pending)
    ask, calls = fake_ask({"summary": "요약", "checks": ["합격증 확인"], "suggested_score": 10, "score_reason": "비슷"})
    monkeypatch.setattr(ai, "_ask", ask)

    res = client.get(f"/ai/review/{target.id}", headers=auth(teacher))
    assert res.status_code == 200
    body = res.json()
    assert body["summary"] == "요약"
    assert {s["title"] for s in body["similar"]} == {"정보처리기능사", "리눅스마스터 2급"}
    assert (body["score_min"], body["score_max"], body["score_avg"]) == (6, 10, 8)
    assert "승인 점수 범위: 6.0~10.0점" in calls[0]

    assert client.get(f"/ai/review/{target.id}", headers=auth(student)).status_code == 403
    assert client.get("/ai/review/999", headers=auth(teacher)).status_code == 404


def test_review_assist_falls_back_to_category(client, db, student, teacher, monkeypatch):
    add(db, student, "해커톤 대상", item="SW관련 대회", score=30)
    target = add(db, student, "새 자격증", status=SubmissionStatus.pending)
    ask, _ = fake_ask({"summary": "s", "checks": [], "suggested_score": 5, "score_reason": "r"})
    monkeypatch.setattr(ai, "_ask", ask)
    body = client.get(f"/ai/review/{target.id}", headers=auth(teacher)).json()
    assert [s["title"] for s in body["similar"]] == ["해커톤 대상"]
