# BSSM ALL API

BSSM ALL 데스크톱 앱([MeisterTrack_Front](https://github.com/BSSM-RE-ACT/MeisterTrack_Front))의 백엔드입니다.

- FastAPI + SQLAlchemy 2 + Alembic
- 로컬은 SQLite, 운영은 `DATABASE_URL`로 PostgreSQL 등 지정
- 패키지 관리: [uv](https://docs.astral.sh/uv/)

## 실행

```bash
uv sync
cp .env.example .env              # JWT_SECRET 꼭 바꾸기
uv run alembic upgrade head
uv run python -m scripts.seed     # 샘플 데이터 (선택)
uv run uvicorn app.main:app --reload
```

API 문서: http://localhost:8000/docs

`DEBUG=true`이면 `POST /auth/dev-login {"email": "teacher@bssm.hs.kr"}`로 Google 없이 로그인할 수 있습니다.

## 계정 일괄 등록

`/users/import/template`로 받은 양식에 채워서 `/users/import`에 올립니다.

- 열: 이메일, 이름, 구분(학생/교사), 학년, 반, 번호, 직위, 연락처
- 학생은 학년·반·번호 필수. 이메일이 이미 있으면 정보를 덮어씁니다.
- 한 행이라도 오류가 있으면 아무것도 저장하지 않고 행별 오류를 돌려줍니다.

## 테스트

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## API

| 영역 | 메서드 | 경로 | 권한 |
|---|---|---|---|
| 인증 | POST | `/auth/google` | 누구나 (학교 도메인 + 등록된 사용자) |
| | GET | `/auth/me` | 로그인 |
| 사용자 | GET | `/users/students?grade&class_no` | 교사 |
| | GET | `/users/import/template` (엑셀 양식) | 교사 |
| | POST | `/users/import` (엑셀 일괄 등록) | 교사 |
| 마이스터역량 | POST | `/meister/submissions` | 학생 |
| | GET | `/meister/submissions/me` | 학생 |
| | GET | `/meister/submissions?status&category&grade&student_id&page&size` | 교사 |
| | GET | `/meister/submissions/summary` | 교사 |
| | GET | `/meister/submissions/{id}` | 교사, 본인 |
| | POST | `/meister/submissions/{id}/approve` `{score, memo}` | 교사 |
| | POST | `/meister/submissions/{id}/reject` `{memo}` | 교사 |
| | GET | `/meister/scores/{student_id}` | 교사, 본인 |
| 출결 | PUT | `/attendance` (여러 건 upsert) | 교사 |
| | GET | `/attendance?date&grade&class_no` | 교사 |
| | GET | `/attendance/students/{id}?month=2026-10` | 교사, 본인 |

## 모델 변경 시

```bash
uv run alembic revision --autogenerate -m "설명"
uv run alembic upgrade head
```
