from pydantic import BaseModel


class UsageSnapshot(BaseModel):
    """模型供应商返回的 token 用量。"""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """返回计入统计的总 token 数。"""
        return self.input_tokens + self.output_tokens
