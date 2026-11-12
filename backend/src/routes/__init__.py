"""路由聚合：统一 /api 前缀（Nginx 反代时剥掉 /api）。"""
from fastapi import APIRouter

from src.routes.audit import router as audit_router
from src.routes.auth import router as auth_router
from src.routes.episodes import router as episodes_router
from src.routes.exports import router as exports_router
from src.routes.feeds import router as feeds_router
from src.routes.health import router as health_router
from src.routes.issues import router as issues_router
from src.routes.summary import router as summary_router
from src.routes.tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(summary_router)
api_router.include_router(feeds_router)
api_router.include_router(episodes_router)
api_router.include_router(tasks_router)
api_router.include_router(issues_router)
api_router.include_router(exports_router)
api_router.include_router(audit_router)
