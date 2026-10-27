import os

# 로컬 .env 값과 상관없이 테스트는 같은 설정으로 돈다
os.environ["JWT_SECRET"] = "test-secret-key-that-is-long-enough-32b"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db import Base, get_db
from app.main import app
from app.models import Role, User


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def teacher(db):
    user = User(email="t@bssm.hs.kr", name="이선생", role=Role.teacher, position="담임교사")
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def student(db):
    user = User(email="s@bssm.hs.kr", name="김부마", role=Role.student, grade=2, class_no=1, number=3)
    db.add(user)
    db.commit()
    return user


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}
