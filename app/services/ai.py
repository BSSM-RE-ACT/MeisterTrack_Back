"""Claude API로 마이스터역량 신청을 분류하고 심사를 돕는다."""

from functools import lru_cache

import anthropic
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models import MeisterCategory

# 학교 마이스터역량 인증제 세부 항목. 분류 결과의 item은 이 중에서 고른다.
ITEMS: dict[MeisterCategory, list[str]] = {
    MeisterCategory.basic: ["직업기초능력평가", "독서활동", "교과성적"],
    MeisterCategory.technical: ["전공관련 자격증", "SW관련 대회", "프로젝트·포트폴리오", "현장실습·인턴십"],
    MeisterCategory.character: ["봉사활동", "동아리활동", "학생회·리더십", "표창"],
    MeisterCategory.humanities: ["인문학 강좌", "독서토론", "예술·체육 활동"],
    MeisterCategory.language: ["공인어학성적", "외국어 대회", "외국어 자격증"],
}


class AIDisabled(Exception):
    pass


class AIFailed(Exception):
    pass


class Classification(BaseModel):
    category: MeisterCategory
    item: str
    reason: str = Field(description="한 문장 근거")


class ReviewAdvice(BaseModel):
    summary: str = Field(description="증빙 요약 2~3문장")
    checks: list[str] = Field(description="교사가 확인할 점 0~3개")
    suggested_score: float
    score_reason: str = Field(description="점수 근거 한 문장")


@lru_cache
def _client() -> anthropic.Anthropic:
    key = get_settings().anthropic_api_key
    if not key:
        raise AIDisabled
    return anthropic.Anthropic(api_key=key, max_retries=2, timeout=60)


def _ask[T: BaseModel](system: str, prompt: str, schema: type[T]) -> T:
    try:
        response = _client().messages.parse(
            model=get_settings().anthropic_model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low"},
            output_format=schema,
        )
    except anthropic.APIError as e:
        raise AIFailed from e
    if response.parsed_output is None:
        raise AIFailed
    return response.parsed_output


def _items_text() -> str:
    return "\n".join(f"- {c.value}: {', '.join(items)}" for c, items in ITEMS.items())


def classify(title: str, content: str) -> Classification:
    system = (
        "너는 부산소프트웨어마이스터고 마이스터역량 인증제 담당 보조다. "
        "학생이 쓴 신청 제목과 내용을 보고 영역(category)과 세부 항목(item)을 고른다. "
        "item은 아래 목록에서 그 영역에 속한 것 하나를 그대로 쓴다.\n" + _items_text()
    )
    result = _ask(system, f"제목: {title}\n내용: {content or '(없음)'}", Classification)
    if result.item not in ITEMS[result.category]:
        result.item = ITEMS[result.category][0]
    return result


def review(submission: dict, similar: list[dict], score_range: tuple[float, float] | None) -> ReviewAdvice:
    system = (
        "너는 마이스터역량 인증 심사를 돕는 보조다. 최종 판단은 교사가 한다. "
        "신청 내용을 요약하고, 증빙에서 교사가 확인할 점을 짚고, 비슷한 승인 사례에 맞춰 점수를 제안한다. "
        "사례가 없으면 항목 성격에 맞게 보수적으로 제안한다. 한국어로 짧게 쓴다."
    )
    lines = [
        f"영역: {submission['category']}",
        f"항목: {submission['item']}",
        f"제목: {submission['title']}",
        f"내용: {submission['content'] or '(없음)'}",
        f"증빙 첨부: {'있음' if submission['attachment_url'] else '없음'}",
        f"취득일: {submission['acquired_at'] or '(없음)'}",
        "",
        "비슷한 승인 사례:",
        *([f"- {s['title']}: {s['score']}점" for s in similar] or ["- 없음"]),
    ]
    if score_range:
        lines.append(f"승인 점수 범위: {score_range[0]}~{score_range[1]}점")
    advice = _ask(system, "\n".join(lines), ReviewAdvice)
    advice.suggested_score = max(advice.suggested_score, 0)
    return advice
