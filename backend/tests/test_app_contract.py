"""后端公开契约保护测试。"""

from fastapi.routing import APIRoute

from chiren_backend.api import create_app


def test_public_routes_remain_registered() -> None:
    """确保架构迁移后公开路由仍然注册在应用上。"""
    app = create_app()
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    expected_paths = {
        "/config/provider",
        "/parser",
        "/parser/retry/{task_id}",
        "/work/list",
        "/work/{id}",
        "/work/delete/{id}",
        "/work/stream/{task_id}",
        "/resume/list",
        "/resume/{id}",
        "/resume/create",
        "/resume/sub/create",
        "/resume/update",
        "/resume/delete",
        "/resume-section/one",
        "/resume-section/{id}",
        "/resume-section/create",
        "/resume-section/update",
        "/resume-section/delete",
        "/resume-section/delete/all",
        "/jd-profile/{resume_id}/current",
        "/jd-profile/{resume_id}/retry",
        "/jd-analysis/list/{resume_id}",
        "/jd-analysis/{jd_analysis_id}",
        "/jd-analysis/match",
        "/cover-letter",
        "/cover-letter/{resume_id}/list",
        "/cover-letter/batch/{batch_id}",
        "/greeting/generate",
        "/greeting/{resume_id}/list",
        "/greeting/batch/{batch_id}",
        "/resume-assistant",
        "/resume-assistant/sub-resumes",
        "/conversation-message/list/{conversation_id}",
        "/conversation-message/create",
        "/conversation-message/delete",
        "/conversation-message/delete/conversation",
        "/interview/built-in-interviewers",
        "/interview/collection",
        "/interview/collection/with-rounds",
        "/interview/collection/list/{sub_resume_id}",
        "/interview/collection/{collection_id}",
        "/interview/round",
        "/interview/collection/delete",
        "/interview/round/update",
        "/interview/round/status",
        "/interview/round/{round_id}/chat",
        "/interview/round/delete",
        "/interview/round/{round_id}/regenerate-summary",
        "/interview/collection/{collection_id}/regenerate-summary",
        "/export/pdf",
        "/export/txt/{resume_id}",
        "/export/json/{resume_id}",
    }

    assert expected_paths <= paths
    assert not any(path.startswith("/template") for path in paths)


def test_response_models_use_aliases() -> None:
    """确保响应模型继续使用 camelCase 等公开别名。"""
    app = create_app()
    for route in app.routes:
        if isinstance(route, APIRoute):
            assert route.response_model_by_alias is True
