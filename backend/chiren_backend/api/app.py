"""FastAPI 应用工厂。"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from chiren_backend.api.lifecycle import create_lifespan
from chiren_backend.api.routers import register_routers

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    """创建并配置后端 FastAPI 应用。"""
    app = FastAPI(lifespan=create_lifespan)
    _configure_cors(app)
    register_routers(app)
    _enable_response_aliases(app)
    return app


def _configure_cors(app: FastAPI) -> None:
    """配置本地前端访问所需的 CORS。"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _enable_response_aliases(app: FastAPI) -> None:
    """让路由响应模型使用公开别名序列化。"""
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.response_model_by_alias = True
