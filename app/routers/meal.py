from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import CurrentUser
from app.services import neis

router = APIRouter(prefix="/meals", tags=["meals"])


class Dish(BaseModel):
    name: str
    allergies: list[int]


class Meal(BaseModel):
    date: date
    type: str  # 조식 / 중식 / 석식
    dishes: list[Dish]
    calories: str | None


@router.get("", response_model=list[Meal])
def list_meals(start: date, end: date, _: CurrentUser) -> list[dict]:
    if (end - start).days > 31 or end < start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "기간은 31일 이내여야 합니다")
    try:
        return neis.get_meals(start, end)
    except neis.NeisError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
