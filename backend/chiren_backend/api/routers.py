"""集中管理公开路由，保持 API 兼容。"""

from fastapi import FastAPI
from fastapi.routing import APIRouter

from apps.config.router import router as config_router
from apps.conversation_message import router as conversation_message_router
from apps.cover_letter import router as cover_letter_router
from apps.export import router as export_router
from apps.interview import router as interview_router
from apps.greeting.router import router as greeting_router
from apps.jd_analysis.router import router as jd_analysis_router
from apps.jd_profile.router import router as jd_profile_router
from apps.parser import router as parser_router
from apps.resume import router as resume_router
from apps.resume_assistant import router as resume_assistant_router
from apps.resume_section import router as resume_section_router
from apps.work import router as work_router

PUBLIC_ROUTERS: tuple[APIRouter, ...] = (
    config_router,
    parser_router,
    work_router,
    resume_router,
    resume_section_router,
    jd_profile_router,
    jd_analysis_router,
    cover_letter_router,
    resume_assistant_router,
    conversation_message_router,
    interview_router,
    greeting_router,
    export_router,
)


def register_routers(app: FastAPI) -> None:
    """注册全部公开路由，不改变 URL 契约。"""
    for router in PUBLIC_ROUTERS:
        app.include_router(router)
