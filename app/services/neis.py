"""NEIS 교육정보 개방 포털 클라이언트. 같은 요청은 1시간 동안 메모리에 캐시한다."""

import re
import time
from datetime import date

import httpx

from app.core.config import get_settings

BASE_URL = "https://open.neis.go.kr/hub"
CACHE_TTL = 60 * 60
_cache: dict[tuple, tuple[float, list[dict]]] = {}


class NeisError(Exception):
    pass


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _parse_ymd(value: str) -> date:
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def fetch(service: str, **params: str) -> list[dict]:
    settings = get_settings()
    key = (service, tuple(sorted(params.items())))
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_TTL:
        return cached[1]

    query = {
        "Type": "json",
        "pIndex": "1",
        "pSize": "1000",
        "ATPT_OFCDC_SC_CODE": settings.neis_office_code,
        "SD_SCHUL_CODE": settings.neis_school_code,
        **params,
    }
    if settings.neis_api_key:
        query["KEY"] = settings.neis_api_key
    try:
        res = httpx.get(f"{BASE_URL}/{service}", params=query, timeout=10)
        res.raise_for_status()
        data = res.json()
    except (httpx.HTTPError, ValueError) as e:
        raise NeisError("NEIS 서버에 연결할 수 없습니다") from e

    if service not in data:
        # 데이터 없음(INFO-200)은 빈 목록, 그 외는 오류
        code = data.get("RESULT", {}).get("CODE")
        if code == "INFO-200":
            rows: list[dict] = []
        else:
            raise NeisError(data.get("RESULT", {}).get("MESSAGE", "NEIS 오류"))
    else:
        rows = data[service][1]["row"]
    _cache[key] = (time.monotonic(), rows)
    return rows


ALLERGY = re.compile(r"\s*\(([\d.]+)\)")


def _parse_dish(raw: str) -> dict:
    """'돈육김치찌개(5.9.10.13)' → {'name': '돈육김치찌개', 'allergies': [5, 9, 10, 13]}"""
    match = ALLERGY.search(raw)
    allergies = [int(n) for n in match.group(1).split(".") if n] if match else []
    return {"name": ALLERGY.sub("", raw).strip(), "allergies": allergies}


def get_meals(start: date, end: date) -> list[dict]:
    rows = fetch("mealServiceDietInfo", MLSV_FROM_YMD=_ymd(start), MLSV_TO_YMD=_ymd(end))
    return [
        {
            "date": _parse_ymd(row["MLSV_YMD"]),
            "type": row["MMEAL_SC_NM"],
            "dishes": [_parse_dish(d) for d in row["DDISH_NM"].split("<br/>") if d.strip()],
            "calories": row.get("CAL_INFO"),
        }
        for row in rows
    ]


def get_school_schedule(start: date, end: date) -> list[dict]:
    rows = fetch("SchoolSchedule", AA_FROM_YMD=_ymd(start), AA_TO_YMD=_ymd(end))
    return [
        {"date": _parse_ymd(row["AA_YMD"]), "title": row["EVENT_NM"]}
        for row in rows
        if row.get("EVENT_NM") and row["EVENT_NM"] != "토요휴업일"
    ]
