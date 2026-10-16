"""Parser 解析领域。"""

# TODO: 这个模块还未考虑如果用户上传的pdf是空的或者信息不够ai会乱填的情况, 需要优化
from apps.parser.router import router

__all__ = ["router"]
