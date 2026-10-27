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

## NEIS 연동

급식·학사일정은 [NEIS 교육정보 개방 포털](https://open.neis.go.kr)에서 가져옵니다. 같은 요청은 1시간 캐시합니다.

- `NEIS_API_KEY`: 없으면 호출당 5건으로 제한되니 운영에선 꼭 발급받아 넣기
- `NEIS_OFFICE_CODE` (기본 C10 부산), `NEIS_SCHOOL_CODE` (기본 7150658)

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
| 시간표 | GET | `/timetable/me` | 학생 |
| | GET | `/timetable?grade&class_no` | 로그인 |
| | PUT | `/timetable?grade&class_no` (반 전체 저장) | 교사 |
| 급식 | GET | `/meals?start&end` (NEIS, 31일 이내) | 로그인 |
| 학사일정 | GET | `/calendar?start&end` (NEIS + 학교 등록) | 로그인 |
| | POST / PUT / DELETE | `/calendar`, `/calendar/{id}` | 교사 |
| 상벌점 | POST | `/mileage` (여러 학생 한 번에) | 교사 |
| | GET | `/mileage/students/{id}` | 교사, 본인 |
| | GET | `/mileage/students?grade&class_no` (반별 합계) | 교사 |
| | DELETE | `/mileage/{id}` | 교사 |
| 동아리 | GET | `/clubs?type`, `/clubs/me`, `/clubs/{id}` | 로그인 |
| | POST / PUT | `/clubs`, `/clubs/{id}` | 교사 |
| | PUT | `/clubs/{id}/members` (명단 교체) | 교사 |
| | GET / POST | `/clubs/{id}/activities` | 로그인 / 교사·부장 |
| 방과후 | GET | `/after-school/courses?semester=2026-2`, `/after-school/me` | 로그인 |
| | POST / PUT | `/after-school/courses`, `/after-school/courses/{id}` | 교사 |
| | POST / DELETE | `/after-school/courses/{id}/enroll` | 학생 |
| | GET | `/after-school/courses/{id}/students` | 교사 |

## 모델 변경 시

```bash
uv run alembic revision --autogenerate -m "설명"
uv run alembic upgrade head
```
