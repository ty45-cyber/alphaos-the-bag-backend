from fastapi import APIRouter
from app.api.v1 import signals, portfolios, pools, leaderboard, auth
from app.api.websocket import router as ws_router

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(signals.router)
api_router.include_router(portfolios.router)
api_router.include_router(pools.router)
api_router.include_router(leaderboard.router)
api_router.include_router(ws_router)