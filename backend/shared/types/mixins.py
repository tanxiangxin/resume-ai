"""Pydantic 模型公共 mixin。"""

from pydantic import model_validator


class NoneToDefaultMixin:
    """将 None 值转换为字段默认值的 mixin。

    当模型字段收到 None 时，自动使用字段的默认值进行替换。
    """

    @model_validator(mode="before")
    @classmethod
    def _none_to_default(cls, v):
        """将 None 值转换为字段默认值。"""
        if v is None:
            v = {}
        if not isinstance(v, dict):
            return v
        result = {}
        for key, value in v.items():
            if value is None:
                field = cls.model_fields.get(key)
                if field is not None:
                    default = field.default
                    result[key] = default() if callable(default) else default
                else:
                    result[key] = None
            else:
                result[key] = value
        return result
