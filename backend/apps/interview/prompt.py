import json

from apps.jd_profile.formatting import build_jd_profile_prompt_block
from chiren_backend.platform.models import InterviewRound, utc_now
from shared.types.jd_profile import JdProfileData


def build_interview_system_prompt(
    round_obj: InterviewRound,
    resume_sections: list[dict],
    job_description: str,
    jd_profile: JdProfileData | None = None,
    question_count: int = 10,
) -> str:
    assessment_dims = json.loads(round_obj.assessment_dimensions)
    personality_traits = json.loads(round_obj.personality_traits)

    dims_text = "\n".join(f"  - {dim}" for dim in assessment_dims)
    traits_text = "、".join(personality_traits)

    resume_json = json.dumps(resume_sections, ensure_ascii=False, indent=2)

    profile_block = (
        "\n\n" + build_jd_profile_prompt_block(jd_profile, "interview")
        if jd_profile is not None
        else ""
    )

    return f"""\
当前时间: {utc_now().strftime("%Y年%m月%d日 %H:%M")}

你是一场模拟面试的面试官。你的角色设定如下：

## 你的身份
- 姓名: {round_obj.interviewer_name}
- 头衔: {round_obj.interviewer_title}
- 简介: {round_obj.interviewer_bio}

## 提问风格
{round_obj.question_style}

## 考察维度
{dims_text}

## 性格特征
{traits_text}

## 岗位描述 (JD)
<job_description>
{job_description}
</job_description>
{profile_block}

请你聚焦于该岗位的核心要求进行提问。

## 候选人简历
<resume>
{resume_json}
</resume>

## 面试规则
- 本轮面试预计约 {question_count} 个问题，请合理分配问题的深度和广度
- 针对候选人的回答进行深入追问，挖掘细节和思考过程
- 使用自然的口语化表达，不要读稿式的生硬提问
- 当候选人回答过于简略时，请适当追问
- 考察维度要覆盖全面，不要只盯着一个点问
- 提问要像真人聊天一样有来有回，适当回应候选人的回答内容再追问，不要机械地一问一答

## 特殊指令
当你在对话历史中看到以下特殊标记时，请执行对应操作：
- `<INTERVIEW_START>`: 面试刚开始。请以自然的面试官口吻开场，先简单介绍自己和本次面试的安排（时长、目的），让候选人放松一些，然后自然地引出第一个问题。不要读稿感，用口语化的表达，像真正在和人聊天一样。
- `<SKIP>`: 候选人选择了跳过上一个问题。请忽略上一个问题，直接提出下一个新问题，不要评论跳过行为。
- `<HINT>`: 候选人请求当前问题的提示。请以面试官口吻给出简短提示（引导思路但不给出答案），然后等待候选人回答。"""


def format_sections_for_prompt(sections: list[dict]) -> list[dict]:
    result = []
    for s in sections:
        section_type = s.get("type", "")
        content = s.get("content", {})
        title = s.get("title", "")
        entry = {"type": section_type, "title": title}
        if section_type == "personal_info" and isinstance(content, dict):
            entry["fields"] = {
                k: v
                for k, v in content.items()
                if v not in (None, "", [], {}) and k not in ("id", "image_url")
            }
        elif section_type == "summary" and isinstance(content, dict):
            entry["text"] = content.get("text", "")
        elif isinstance(content, dict) and "items" in content:
            items = content["items"]
            if isinstance(items, list) and len(items) > 0:
                entry["items"] = items[:5]
            else:
                entry["items_count"] = len(items) if isinstance(items, list) else 0
        elif isinstance(content, dict) and "categories" in content:
            cats = content["categories"]
            if isinstance(cats, list) and len(cats) > 0:
                entry["categories"] = cats[:3]
            else:
                entry["categories_count"] = len(cats) if isinstance(cats, list) else 0
        result.append(entry)
    return result
