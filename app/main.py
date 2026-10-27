from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import after_school, attendance, auth, calendar, clubs, meal, meister, mileage, timetable, users

settings = get_settings()
if not settings.debug and settings.jwt_secret == "change-me":
    raise RuntimeError("운영 환경에서는 JWT_SECRET을 설정해야 합니다")

app = FastAPI(title="BSSM ALL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(meister.router)
app.include_router(attendance.router)
app.include_router(timetable.router)
app.include_router(meal.router)
app.include_router(calendar.router)
app.include_router(mileage.router)
app.include_router(clubs.router)
app.include_router(after_school.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
