from app.core.config import get_settings
from tests.conftest import auth


def test_me_requires_login(client):
    assert client.get("/auth/me").status_code == 401


def test_me(client, student):
    res = client.get("/auth/me", headers=auth(student))
    assert res.status_code == 200
    assert res.json()["student_id"] == "2103"


def test_dev_login_disabled_by_default(client, student):
    assert client.post("/auth/dev-login", json={"email": student.email}).status_code == 404


def test_dev_login(client, student, monkeypatch):
    monkeypatch.setattr(get_settings(), "debug", True)
    res = client.post("/auth/dev-login", json={"email": student.email})
    assert res.status_code == 200
    assert res.json()["user"]["name"] == "김부마"
    assert client.post("/auth/dev-login", json={"email": "nobody@bssm.hs.kr"}).status_code == 403


def test_update_me(client, student):
    res = client.patch("/users/me", json={"phone": "010-1111-2222"}, headers=auth(student))
    assert res.status_code == 200
    assert res.json()["phone"] == "010-1111-2222"
