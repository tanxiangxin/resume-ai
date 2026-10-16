"""统一异常定义。"""


class AppException(Exception):
    """应用层基础异常。"""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code or "APP_ERROR"
        super().__init__(self.message)


class ParseError(AppException):
    """文档解析异常。"""

    def __init__(self, message: str):
        super().__init__(message, code="PARSE_ERROR")


class ValidationError(AppException):
    """数据校验异常。"""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")
