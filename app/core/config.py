from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./meistertrack.db"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24 * 7

    google_client_id: str = ""
    # 학교 Google Workspace 도메인만 로그인 허용. 비우면 도메인 검사 안 함.
    allowed_email_domain: str = "bssm.hs.kr"

    # NEIS 교육정보 개방 포털 (https://open.neis.go.kr). 키 없으면 호출당 5건으로 제한된다.
    neis_api_key: str = ""
    neis_office_code: str = "C10"  # 부산광역시교육청
    neis_school_code: str = "7150658"  # 부산소프트웨어마이스터고

    cors_origins: list[str] = ["http://localhost:5173", "tauri://localhost", "http://tauri.localhost"]

    # 개발용 로그인(/auth/dev-login) 허용 여부. 운영에서는 반드시 false.
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
