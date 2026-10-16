"""Task 相关类型定义。"""

from enum import StrEnum


class TaskType(StrEnum):
    """任务类型枚举。"""

    PARSE = "parse"
    SUB_RESUME_GENERATE = "sub_resume_generate"
    JD_PARSE = "jd_parse"
    JD_SCORE = "jd_score"
    INTERVIEW_SUMMARY = "interview_summary"
    COLLECTION_SUMMARY = "collection_summary"
    GREETING_GENERATE = "greeting_generate"
    COVER_LETTER_GENERATE = "cover_letter_generate"


class TaskStatus(StrEnum):
    """任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
