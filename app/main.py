from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.auth import router as auth_router
from app.routers.projects import router as projects_router
from app.routers.calcs import router as calcs_router
from app.routers.visualizations import router as visualizations_router
from app.routers.reports import router as reports_router
from app.routers.payments import router as payments_router
from app.routers.users import router as users_router
from app.routers.notifications import router as notifications_router

app = FastAPI(title="Solar Sizing API", version="0.1.0")

# CORS
explicit = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=explicit,                             # localhost, prod site, etc.
    allow_origin_regex=r"^https://.*\.usercontent\.goog$",  # AI Studio rotating origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(calcs_router, prefix="/projects", tags=["calculations"])
app.include_router(visualizations_router, prefix="/projects", tags=["visualizations"])
app.include_router(reports_router, prefix="/projects", tags=["reports"])
app.include_router(payments_router, prefix="/payments", tags=["payments"])
app.include_router(users_router, prefix="/users/me", tags=["users"])
app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
