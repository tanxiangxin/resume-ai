"""上游 API 错误类型。"""

from __future__ import annotations


class ChirenApiError(RuntimeError):
    """上游 API 失败的基类。"""


class AuthenticationFailure(ChirenApiError):
    """上游服务拒绝当前凭证时抛出。"""


class RateLimitFailure(ChirenApiError):
    """上游服务因限流拒绝请求时抛出。"""


class RequestFailure(ChirenApiError):
    """通用请求失败或传输失败。"""
