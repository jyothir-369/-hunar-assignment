"""FastAPI application entry point for the Hunar AI Hiring Assistant backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.database import init_db
from src.routers import (
    admin,
    agents,
    calls,
    campaigns,
    candidates,
    people,
    settings as settings_router,
    webhooks,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Initialize the database on startup, log on shutdown."""
    logger.info("Initialising database...")
    init_db()
    logger.info("Database initialised")
    yield
    logger.info("Shutting down Hunar API")


app = FastAPI(
    title=settings.APP_NAME,
    description="Hunar AI Hiring Assistant — FastAPI backend for agents, campaigns, candidates, and webhooks.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    # Starlette's allow_origins is an exact-match list — wildcards are NOT
    # expanded, so "https://*.vercel.app" would only ever match a request
    # whose Origin header is literally the string "https://*.vercel.app".
    # We use allow_origin_regex (Python regex) to match every Vercel
    # preview + production deployment of the frontend. Lock this down to
    # your actual project domain once you have one.
    allow_origin_regex=r"https://[a-zA-Z0-9-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(campaigns.router)
app.include_router(candidates.router)
app.include_router(people.router)
app.include_router(calls.router)
app.include_router(settings_router.router)
app.include_router(webhooks.router)
app.include_router(admin.router)


@app.get("/")
def root() -> dict:
    return {
        "message": "Hunar Voice Agents API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> dict:
    return {"status": "healthy"}
