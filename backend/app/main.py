"""FastAPI app entry point with CORS, router mount, static file serving."""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import accounts as accounts_api
from app.api import auth as auth_api
from app.api import config as config_api
from app.api import family as family_api
from app.api import income as income_api
from app.api import redemption as redemption_api
from app.api import settlement as settlement_api
from app.api import transactions as transactions_api
from app.api import violations as violations_api
from app.api import wishlist as wishlist_api
from app.logging_config import setup_logging
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.schemas.common import HealthResponse

logger = structlog.get_logger("fambank")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    setup_logging()
    logger.info("app_started", version="0.2.0")
    yield
    logger.info("app_stopped")


app = FastAPI(
    title="FamBank 家庭内部银行",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:8000",
        "http://21.214.116.91:5175",
        "http://21.214.116.91:5174",
        "http://21.214.116.91:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# API routes
app.include_router(auth_api.router, prefix="/api/v1")
app.include_router(family_api.router, prefix="/api/v1")
app.include_router(income_api.router, prefix="/api/v1")
app.include_router(accounts_api.router, prefix="/api/v1")
app.include_router(settlement_api.router, prefix="/api/v1")
app.include_router(redemption_api.router, prefix="/api/v1")
app.include_router(config_api.router, prefix="/api/v1")
app.include_router(wishlist_api.router, prefix="/api/v1")
app.include_router(transactions_api.router, prefix="/api/v1")
app.include_router(violations_api.router, prefix="/api/v1")


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version="0.2.0")


# Mount static files for production (frontend build output) with SPA fallback
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    # Serve static assets (js, css, images, etc.)
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    # SPA fallback: any non-API route returns index.html for client-side routing
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # Try to serve the exact file first (e.g. favicon.ico)
        file_path = frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
