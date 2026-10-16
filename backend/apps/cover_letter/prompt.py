from apps.jd_profile.formatting import build_jd_profile_prompt_block
from chiren_backend.platform.resume_prompt import (
    ItemFields,
    PersonalInfoFields,
    ResumePromptBuilder,
    SectionHeaderConfig,
)
from shared.types.jd_profile import JdProfileData

JD_ANALYSIS_PERSONAL_INFO_FIELDS = PersonalInfoFields(
    full_name=True,
    age=True,
    gender=True,
    email=False,
    phone=False,
    education_level=True,
    job_title=True,
    salary=True,
    location=True,
    political_status=True,
    ethnicity=True,
    hometown=True,
    marital_status=True,
    years_of_experience=True,
    wechat=False,
    website=True,
    linkedin=True,
)

JD_ANALYSIS_ITEM_FIELDS = ItemFields(location=False)

JD_ANALYSIS_SECTION_HEADER = SectionHeaderConfig(include_section_id=True)

JD_ANALYSIS_BUILDER = ResumePromptBuilder(
    personal_info_fields=JD_ANALYSIS_PERSONAL_INFO_FIELDS,
    item_fields=JD_ANALYSIS_ITEM_FIELDS,
    section_header=JD_ANALYSIS_SECTION_HEADER,
)

# 求职信风格对应的人口学描述
COVER_LETTER_STYLE_PROMPTS = {
    "正式": "使用正式、专业的语言风格，语气庄重，结构严谨，适合传统行业和知名企业",
    "亲切": "使用亲切、温暖的语言风格，语气友好但不失专业，适合创业公司和中小企业",
    "自信": "使用自信、有力的语言风格，突出个人优势和成就，适合竞争激烈的职位",
}


def build_cover_letter_system_prompt(
    style: str = "正式", language: str = "中文", length: str = "standard"
) -> str:
    """构建求职信生成的 system prompt。

    Args:
        style: 求职信风格，可选 "正式"、"亲切"、"自信"
        language: 求职信语言，可选 "中文"、"English"
    """
    style_instruction = COVER_LETTER_STYLE_PROMPTS.get(
        style, COVER_LETTER_STYLE_PROMPTS["正式"]
    )
    lang_instruction = (
        "请使用简体中文输出" if language == "中文" else "Please write in English"
    )
    length_instruction = (
        "控制在约 250-400 字，重点突出且适合快速阅读"
        if length == "short"
        else "控制在约 450-700 字，包含清晰的开场、匹配论据和结尾"
    )

    return f"""\
Role: You are a professional career coach and expert cover letter writer.
Task: Write a persuasive cover letter tailored to a specific job application.
Inputs:
The candidate's Resume (including name, email, phone).
The original Target Job Description (JD) and its Structured JD Profile.
Goal: Create a highly customized cover letter that aligns the candidate's strengths with the job requirements,
thereby significantly increasing the likelihood of securing an interview.
Important: The cover letter MUST include the candidate's name, email and phone number in the signature/closing section.
Never invent experience, skills, achievements, company facts, or contact details.
Output only the generated cover letter content, without including your own reasoning logic.
Style Requirements: {style_instruction}
Language Requirement: {lang_instruction}
Length Requirement: {length_instruction}
"""


def build_cover_letter_user_prompt(
    sections,
    job_description: str,
    jd_profile: JdProfileData,
    full_name: str,
    email: str,
    phone: str,
    company_name: str | None = None,
    recipient_name: str | None = None,
    additional_instructions: str | None = None,
) -> str:
    """构建求职信生成的用户 prompt，包含个人信息用于生成求职信签名。

    Args:
        sections: 简历区块列表
        job_description: 岗位描述
        full_name: 用户姓名
        email: 用户邮箱
        phone: 用户电话
    """
    # 使用 JD_ANALYSIS_BUILDER 构建简历内容
    resume_content = JD_ANALYSIS_BUILDER.build_user_prompt(
        sections, job_description, None
    )
    optional_context = "\n".join(
        value
        for value in (
            f"Target Company: {company_name}" if company_name else None,
            f"Recipient: {recipient_name}" if recipient_name else None,
            f"Additional Candidate Instructions: {additional_instructions}"
            if additional_instructions
            else None,
        )
        if value is not None
    )

    # 添加个人信息用于求职信签名
    personal_info = f"""
Candidate Contact Information (MUST include in cover letter signature):
- Name: {full_name}
- Email: {email}
- Phone: {phone}

{build_jd_profile_prompt_block(jd_profile, "cover_letter")}

<original_job_description>
{job_description}
</original_job_description>

{optional_context}

<resume_content>
{resume_content}
</resume_content>
"""
    return personal_info
