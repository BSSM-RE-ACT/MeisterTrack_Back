from datetime import date

import httpx
import pytest

from app.services import neis
from tests.conftest import auth


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


@pytest.fixture
def neis_rows(monkeypatch):
    """서비스 이름별 NEIS 응답 행을 지정한다."""
    rows: dict[str, list[dict]] = {}
    neis._cache.clear()

    def fake_get(url, params, timeout):
        service = url.rsplit("/", 1)[-1]
        if service not in rows:
            return FakeResponse({"RESULT": {"CODE": "INFO-200", "MESSAGE": "해당하는 데이터가 없습니다."}})
        return FakeResponse({service: [{"head": []}, {"row": rows[service]}]})

    monkeypatch.setattr(httpx, "get", fake_get)
    return rows


def test_meals(client, student, neis_rows):
    neis_rows["mealServiceDietInfo"] = [
        {
            "MLSV_YMD": "20261027",
            "MMEAL_SC_NM": "중식",
            "DDISH_NM": "현미밥<br/>돈육김치찌개 (5.9.10.13)<br/>깍두기(9.13.)",
            "CAL_INFO": "812.3 Kcal",
        }
    ]
    res = client.get("/meals?start=2026-10-27&end=2026-10-27", headers=auth(student))
    assert res.status_code == 200
    meal = res.json()[0]
    assert meal["type"] == "중식"
    assert meal["dishes"] == [
        {"name": "현미밥", "allergies": []},
        {"name": "돈육김치찌개", "allergies": [5, 9, 10, 13]},
        {"name": "깍두기", "allergies": [9, 13]},
    ]


def test_meals_empty_and_range(client, student, neis_rows):
    assert client.get("/meals?start=2026-10-27&end=2026-10-27", headers=auth(student)).json() == []
    assert client.get("/meals?start=2026-10-01&end=2026-12-01", headers=auth(student)).status_code == 400


def test_neis_error(monkeypatch):
    neis._cache.clear()

    def fail(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", fail)
    with pytest.raises(neis.NeisError):
        neis.get_meals(date(2026, 10, 27), date(2026, 10, 27))


def test_calendar_merges_neis_and_school_events(client, student, teacher, neis_rows):
    neis_rows["SchoolSchedule"] = [
        {"AA_YMD": "20261103", "EVENT_NM": "2학기 중간고사"},
        {"AA_YMD": "20261031", "EVENT_NM": "토요휴업일"},
    ]
    for body in [
        {"title": "2학년 현장체험", "start_date": "2026-10-29", "end_date": "2026-10-30", "grade": 2},
        {"title": "1학년 진로캠프", "start_date": "2026-10-28", "end_date": "2026-10-28", "grade": 1},
    ]:
        assert client.post("/calendar", json=body, headers=auth(teacher)).status_code == 201

    events = client.get("/calendar?start=2026-10-01&end=2026-11-30", headers=auth(student)).json()
    # 2학년 학생에게는 1학년 일정과 토요휴업일이 안 보인다
    assert [(e["title"], e["source"]) for e in events] == [("2학년 현장체험", "school"), ("2학기 중간고사", "neis")]

    teacher_events = client.get("/calendar?start=2026-10-01&end=2026-11-30", headers=auth(teacher)).json()
    assert len(teacher_events) == 3


def test_calendar_rejects_bad_range(client, teacher):
    body = {"title": "x", "start_date": "2026-10-30", "end_date": "2026-10-29"}
    assert client.post("/calendar", json=body, headers=auth(teacher)).status_code == 422
