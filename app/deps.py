from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_db
from app.models import Role, User

DB = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


def get_current_user(db: DB, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    user_id = decode_access_token(credentials.credentials) if credentials else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "로그인이 필요합니다")
    return user


def require_teacher(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != Role.teacher:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "교사만 사용할 수 있습니다")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
Teacher = Annotated[User, Depends(require_teacher)]
