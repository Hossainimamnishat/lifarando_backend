# app/main.py (relevant bits)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.api.router import api_router
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda _: None)
        print(f"[startup] Connected to DB: {settings.DATABASE_URL}")
    except Exception as e:
        print(f"[startup] DB connection failed: {e}")
        raise
    yield


Path(settings.MEDIA_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV != "prod" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=settings.MEDIA_DIR), name="static")
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
