from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from shared.types.strict_model import StrictBaseModel


class BuiltInInterviewerType(StrEnum):
    """内置面试官类型枚举"""

    HR = "hr"
    TECHNICAL = "technical"
    SCENARIO = "scenario"
    PROJECT = "project"
    BEHAVIORAL = "behavioral"
    LEADER = "leader"


class BuiltInInterviewerProfile(StrictBaseModel):
    """内置面试官个人资料"""

    name: str = Field(description="面试官名称")
    title: str = Field(description="面试官头衔")
    round_name: str = Field(description="轮次名称，如'技术面'")
    bio: str = Field(description="面试官简介")
    question_style: str = Field(description="提问风格")
    assessment_dimensions: list[str] = Field(description="考察维度")
    personality_traits: list[str] = Field(description="性格特征")
    avatar_color: str = Field(description="头像背景色")
    avatar_text: str = Field(description="头像文字")


BUILT_IN_INTERVIEWERS: dict[BuiltInInterviewerType, BuiltInInterviewerProfile] = {
    BuiltInInterviewerType.HR: BuiltInInterviewerProfile(
        name="李莉",
        title="HR",
        round_name="HR面",
        bio="资深人力资源专家，擅长人才筛选与岗位匹配，"
        "能够从综合素质角度评估候选人与团队文化的契合度",
        question_style="结构化提问，关注候选人动机、职业规划与价值观",
        assessment_dimensions=[
            "沟通表达",
            "职业稳定性",
            "文化契合度",
            "学习意愿",
            "薪资期望匹配",
        ],
        personality_traits=["亲和", "细致", "善于观察", "客观公正"],
        avatar_color="#EC4899",
        avatar_text="李",
    ),
    BuiltInInterviewerType.TECHNICAL: BuiltInInterviewerProfile(
        name="张明",
        title="技术专家",
        round_name="技术面",
        bio="拥有15年互联网行业技术经验，曾在多家知名科技公司担任技术负责人，"
        "擅长深度技术问答和系统设计考察",
        question_style="深入浅出，层层递进，从基础概念到架构设计",
        assessment_dimensions=[
            "技术基础",
            "系统设计能力",
            "问题解决能力",
            "代码质量意识",
            "技术视野",
        ],
        personality_traits=["严谨", "专业", "富有洞察力", "善于引导"],
        avatar_color="#3B82F6",
        avatar_text="张",
    ),
    BuiltInInterviewerType.SCENARIO: BuiltInInterviewerProfile(
        name="王强",
        title="场景面试专家",
        round_name="场景面",
        bio="专注于场景化面试方法论，通过真实业务场景考察候选人的"
        "综合应对能力和业务理解能力",
        question_style="场景驱动，注重实战模拟和应变能力评估",
        assessment_dimensions=[
            "问题分析能力",
            "决策能力",
            "沟通表达能力",
            "压力应对",
            "业务理解",
        ],
        personality_traits=["务实", "灵活", "善于追问", "注重细节"],
        avatar_color="#F59E0B",
        avatar_text="王",
    ),
    BuiltInInterviewerType.BEHAVIORAL: BuiltInInterviewerProfile(
        name="刘芳",
        title="行为面试专家",
        round_name="行为面",
        bio="资深HR专家，精通STAR面试法，通过行为事件访谈深入评估"
        "候选人的软技能和综合素质",
        question_style="亲和力强，循循善诱，基于STAR法则深入追问",
        assessment_dimensions=[
            "团队协作",
            "领导力",
            "沟通能力",
            "自我认知",
            "抗压能力",
        ],
        personality_traits=["亲和", "耐心", "善于倾听", "敏锐"],
        avatar_color="#A855F7",
        avatar_text="刘",
    ),
    BuiltInInterviewerType.PROJECT: BuiltInInterviewerProfile(
        name="陈刚",
        title="项目深挖专家",
        round_name="项目深挖",
        bio="资深项目经理和架构师，擅长深度挖掘候选人的项目经验和"
        "实际贡献，区分真伪经验",
        question_style="刨根问底，由表及里，聚焦实际贡献和技术决策",
        assessment_dimensions=[
            "项目经验真实性",
            "技术贡献度",
            "项目管理能力",
            "团队合作",
            "技术深度",
        ],
        personality_traits=["犀利", "专注", "善于质疑", "逻辑清晰"],
        avatar_color="#22C55E",
        avatar_text="陈",
    ),
    BuiltInInterviewerType.LEADER: BuiltInInterviewerProfile(
        name="赵总",
        title="管理层",
        round_name="Leader面",
        bio="拥有20年企业管理经验，关注候选人的战略思维、团队管理和长期发展潜力",
        question_style="宏观视角，关注大局观，聚焦领导力和战略思维",
        assessment_dimensions=[
            "领导力",
            "战略思维",
            "团队建设",
            "商业敏感度",
            "行业洞察",
        ],
        personality_traits=["沉稳", "睿智", "富有远见", "包容"],
        avatar_color="#6B7280",
        avatar_text="赵",
    ),
}


class BuiltInInterviewerResponse(StrictBaseModel):
    """内置面试官响应"""

    type: str = Field(description="面试官类型")
    name: str = Field(description="面试官名称")
    title: str = Field(description="面试官头衔")
    round_name: str = Field(description="轮次名称")
    bio: str = Field(description="面试官简介")
    question_style: str = Field(description="提问风格")
    assessment_dimensions: list[str] = Field(description="考察维度")
    personality_traits: list[str] = Field(description="性格特征")
    avatar_color: str = Field(description="头像背景色")
    avatar_text: str = Field(description="头像文字")


class InterviewCollectionCreate(StrictBaseModel):
    """创建面试集合请求"""

    name: str = Field(description="面试集合名称")
    sub_resume_id: str = Field(description="关联的子简历ID")


class InterviewCollectionUpdate(StrictBaseModel):
    """更新面试集合请求"""

    name: str | None = Field(default=None, description="面试集合名称")
    status: str | None = Field(
        default=None,
        description="状态：not_started/in_progress/completed",
    )


class InterviewRoundUpdate(StrictBaseModel):
    """更新面试轮次请求"""

    id: str = Field(description="轮次ID")
    name: str | None = Field(default=None, description="轮次名称")
    interviewer_name: str | None = Field(default=None, description="面试官名称")
    interviewer_title: str | None = Field(default=None, description="面试官头衔")
    interviewer_bio: str | None = Field(default=None, description="面试官简介")
    question_style: str | None = Field(default=None, description="提问风格")
    assessment_dimensions: list[str] | None = Field(
        default=None, description="考察维度"
    )
    personality_traits: list[str] | None = Field(default=None, description="性格特征")
    status: str | None = Field(
        default=None,
        description="状态：not_started/in_progress/completed",
    )
    sort_order: int | None = Field(default=None, description="排序序号")


class InterviewRoundDraft(StrictBaseModel):
    """面试轮次草稿（创建时内嵌，不含 id/collection_id/status）"""

    name: str = Field(description="轮次名称，如'技术一面'")
    interviewer_type: BuiltInInterviewerType | None = Field(
        default=None,
        description="内置面试官类型，设置后自动填充面试官资料，"
        "此时 interviewer_name 等字段可为空",
    )
    interviewer_name: str = Field(default="", description="面试官名称")
    interviewer_title: str = Field(default="", description="面试官头衔")
    interviewer_bio: str = Field(default="", description="面试官简介")
    question_style: str = Field(default="", description="提问风格")
    assessment_dimensions: list[str] = Field(
        default_factory=list, description="考察维度"
    )
    personality_traits: list[str] = Field(default_factory=list, description="性格特征")


class InterviewRoundCreate(StrictBaseModel):
    """创建单个面试轮次请求。

    为现有面试集合动态添加轮次，新轮次默认放到最后。
    若集合状态为 completed，添加后自动回退为 not_started。
    """

    interview_collection_id: str = Field(description="所属面试集合ID")
    name: str = Field(description="轮次名称，如'技术一面'")
    interviewer_name: str = Field(default="", description="面试官名称")
    interviewer_title: str = Field(default="", description="面试官头衔")
    interviewer_bio: str = Field(default="", description="面试官简介")
    question_style: str = Field(default="", description="提问风格")
    assessment_dimensions: list[str] = Field(
        default_factory=list, description="考察维度"
    )
    personality_traits: list[str] = Field(default_factory=list, description="性格特征")
    sort_order: int | None = Field(default=None, description="排序序号，不传则放到最后")


class InterviewCollectionCreateWithRounds(StrictBaseModel):
    """创建面试集合（含多个轮次）请求"""

    name: str = Field(description="面试集合名称")
    sub_resume_id: str = Field(description="关联的子简历ID")
    rounds: list[InterviewRoundDraft] = Field(
        default_factory=list,
        description="面试轮次列表，按 sort_order 顺序排列",
    )


class InterviewChatRequest(StrictBaseModel):
    action: Literal["start", "answer", "skip", "hint"] = Field(
        description="对话操作类型：start=开始面试, answer=回答问题, skip=跳过, hint=请求提示"
    )
    content: str = Field(
        default="",
        description="候选人回答内容，仅 action=answer 时需要",
    )
    model: str = Field(description="AI 模型名称")
    type: str = Field(default="anthropic", description="LLM 供应商类型")
    api_key: str = Field(description="API 密钥")
    base_url: str | None = Field(default=None, description="API 地址")
