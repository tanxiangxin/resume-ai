"""对话缓存存储工具。"""

import json
from pathlib import Path

from shared.types.messages import ConversationMessage

_BASE_DIR = Path(__file__).parent.parent.parent / ".conversation_store"


class ConversationStore:
    """对话缓存存储工具类。

    操作 .conversation_store 目录下的 JSONL 缓存文件。
    """

    def __init__(self, base_dir: str | Path = _BASE_DIR):
        if isinstance(base_dir, str):
            self.base_dir = Path(base_dir)
        elif isinstance(base_dir, Path):
            self.base_dir = Path(base_dir)
        else:
            raise ValueError("base_dir must be a string or Path")

        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_file(self, resume_id: str) -> Path:
        """获取指定 resume_id 对应的缓存文件路径。"""
        return self.base_dir / f"{resume_id}.jsonl"

    def exists(self, resume_id: str) -> bool:
        """检查指定 resume_id 的缓存是否存在。"""
        return self._get_cache_file(resume_id).exists()

    def read(self, resume_id: str) -> list[ConversationMessage]:
        """读取指定 resume_id 的全部缓存 messages。"""
        cache_file = self._get_cache_file(resume_id)
        if not cache_file.exists():
            return []
        messages = []
        for line in cache_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                messages.append(ConversationMessage.model_validate(json.loads(line)))
        return messages

    def append(self, resume_id: str, message: ConversationMessage) -> None:
        """尾追加一条 message 到指定 resume_id 的缓存文件。"""
        cache_file = self._get_cache_file(resume_id)
        line = json.dumps(message.model_dump(mode="json"), ensure_ascii=False)
        with open(cache_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def extend(self, resume_id: str, messages: list[ConversationMessage]) -> None:
        """尾追加多条 messages 到指定 resume_id 的缓存文件。"""
        cache_file = self._get_cache_file(resume_id)
        with open(cache_file, "a", encoding="utf-8") as f:
            for msg in messages:
                line = json.dumps(msg.model_dump(mode="json"), ensure_ascii=False)
                f.write(line + "\n")

    def pop(self, resume_id: str) -> ConversationMessage | None:
        """弹出一条 message（从文件末尾读取并删除最后一行）。"""
        cache_file = self._get_cache_file(resume_id)
        if not cache_file.exists():
            return None
        lines = cache_file.read_text(encoding="utf-8").splitlines()
        if not lines:
            return None
        last_line = lines.pop()
        # 重写文件（去掉最后一行）
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        return ConversationMessage.model_validate(json.loads(last_line))

    def write(self, resume_id: str, messages: list[ConversationMessage]) -> None:
        """全量覆盖写入 messages 到指定 resume_id 的缓存文件。"""
        cache_file = self._get_cache_file(resume_id)
        with open(cache_file, "w", encoding="utf-8") as f:
            for msg in messages:
                line = json.dumps(msg.model_dump(mode="json"), ensure_ascii=False)
                f.write(line + "\n")

    def delete(self, resume_id: str) -> None:
        """删除指定 resume_id 的缓存文件。"""
        cache_file = self._get_cache_file(resume_id)
        if cache_file.exists():
            cache_file.unlink()
