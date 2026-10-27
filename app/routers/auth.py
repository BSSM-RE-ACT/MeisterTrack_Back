from fastapi import APIRouter, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import create_access_token
from app.deps import DB, CurrentUser
from app.models import User
from app.schemas.user import TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginIn(BaseModel):
    id_token: str


class DevLoginIn(BaseModel):
    email: str


def _login(db: DB, email: str) -> TokenOut:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "등록되지 않은 사용자입니다")
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/google", response_model=TokenOut)
def google_login(body: GoogleLoginIn, db: DB) -> TokenOut:
    settings = get_settings()
    try:
        info = id_token.verify_oauth2_token(body.id_token, google_requests.Request(), settings.google_client_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 Google 토큰입니다") from e

    email: str = info["email"]
    if settings.allowed_email_domain and not email.endswith(f"@{settings.allowed_email_domain}"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "학교 계정으로만 로그인할 수 있습니다")
    return _login(db, email)


@router.post("/dev-login", response_model=TokenOut, include_in_schema=False)
def dev_login(body: DevLoginIn, db: DB) -> TokenOut:
    if not get_settings().debug:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return _login(db, body.email)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
