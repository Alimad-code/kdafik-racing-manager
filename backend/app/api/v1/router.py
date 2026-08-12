from fastapi import APIRouter

from app.api.v1.endpoints import auth, catalog, health, legal, live_race, seasons, stage_sessions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(health.router)
api_router.include_router(legal.router)
api_router.include_router(live_race.router)
api_router.include_router(seasons.router)
api_router.include_router(stage_sessions.router)
