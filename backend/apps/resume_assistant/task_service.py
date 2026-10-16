import asyncio
import json
import logging
import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from apps.jd_profile.formatting import build_jd_profile_prompt_block
from apps.jd_profile.service import (
    ProviderRuntimeConfig,
    calculate_jd_source_hash,
    parse_jd_profile,
    persist_profile_result,
)
from apps.resume_assistant.schemas import (
    PersonalInfo,
    SubResumeCreateRequest,
    SubResumeResult,
    Summary,
)
from chiren_backend.platform.llm import call_structured_json
from chiren_backend.platform.llm.client import SupportsStreamingMessages
from chiren_backend.platform.models import Resume, ResumeSection
from chiren_backend.platform.resume_prompt import (
    ItemFields,
    PersonalInfoFields,
    ResumePromptBuilder,
    SectionHeaderConfig,
)
from chiren_backend.platform.resume_sections import (
    SectionConfig,
    create_resume_sections,
)
from chiren_backend.platform.task_state import (
    cleanup_task,
    update_task_error,
    update_task_result,
    update_task_status,
)
from chiren_backend.platform.work_records import update_work_status
from shared.types.jd_profile import JdProfileData
from shared.types.resume import ResumeSectionSchema
from shared.types.task import TaskStatus

log = logging.getLogger(__name__)

MAX_RETRIES = 3

RESUME_PERSONAL_INFO_FIELDS = PersonalInfoFields(
    full_name=True,
    age=True,
    gender=True,
    email=True,
    phone=True,
    education_level=True,
    job_title=True,
    salary=True,
    location=True,
    political_status=True,
    ethnicity=True,
    hometown=True,
    marital_status=True,
    years_of_experience=True,
    wechat=True,
    website=True,
    linkedin=True,
)

RESUME_ITEM_FIELDS = ItemFields(location=True)

RESUME_SECTION_HEADER = SectionHeaderConfig(include_section_id=False)

RESUME_ASSISTANT_BUILDER = ResumePromptBuilder(
    personal_info_fields=RESUME_PERSONAL_INFO_FIELDS,
    item_fields=RESUME_ITEM_FIELDS,
    section_header=RESUME_SECTION_HEADER,
)


async def executor_llm(
    client: SupportsStreamingMessages,
    model: str,
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None = None,
    jd_profile: JdProfileData | None = None,
) -> SubResumeResult:
    system_prompt = SYSTEM.format(
        json_schema=json.dumps(
            SubResumeResult.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )
    )
    user_prompt = RESUME_ASSISTANT_BUILDER.build_user_prompt(
        sections, job_description, job_title
    )
    if jd_profile is not None:
        user_prompt = (
            f"{build_jd_profile_prompt_block(jd_profile, 'resume')}\n\n{user_prompt}"
        )
    return await call_structured_json(
        client,
        model,
        system_prompt,
        user_prompt,
        SubResumeResult,
        max_retries=MAX_RETRIES,
    )


async def run_sub_resume_task(
    db: AsyncSession,
    task_id: str,
    client: SupportsStreamingMessages,
    request: SubResumeCreateRequest,
    workspace_sections: list[ResumeSectionSchema],
) -> None:
    """根据 JD 创建子简历的后台任务"""
    try:
        await update_work_status(db, task_id, TaskStatus.RUNNING)
        await update_task_status(task_id, TaskStatus.RUNNING)

        provider = ProviderRuntimeConfig(
            provider_type=request.type,
            api_key=request.api_key,
            base_url=request.base_url,
            model=request.model,
        )
        source_hash = calculate_jd_source_hash(
            request.job_description, request.job_title
        )
        jd_profile: JdProfileData | None = None
        jd_profile_error: str | None = None
        try:
            jd_profile = await parse_jd_profile(
                client,
                request.model,
                request.job_description,
                request.job_title,
                source_hash,
            )
        except Exception as exc:
            jd_profile_error = str(exc)
            log.warning("JD profile parse failed during sub resume generation: %s", exc)

        result = await executor_llm(
            client,
            request.model,
            workspace_sections,
            request.job_description,
            request.job_title,
            jd_profile,
        )

        meta_info = {"job_description": request.job_description}

        if request.job_title:
            meta_info["job_title"] = request.job_title

        resume = Resume(
            id=task_id,
            workspace_id=request.workspace_id,
            title=request.title,
            template=request.template,
            theme_config=json.dumps(request.theme_config, ensure_ascii=False),
            language=request.language,
            meta_info=meta_info,
        )
        db.add(resume)

        _create_resume_sections(db, task_id, result)
        await persist_profile_result(
            db,
            resume_id=task_id,
            job_description=request.job_description,
            job_title=request.job_title,
            provider=provider,
            trigger="ai_generate",
            profile_data=jd_profile,
            error_message=jd_profile_error,
        )

        await db.commit()

        await update_work_status(db, task_id, TaskStatus.SUCCESS)
        await update_task_result(task_id, {"resume_id": task_id})

        asyncio.create_task(cleanup_task(task_id, None))

    except Exception as e:
        await db.rollback()
        log.error(f"Failed to run sub resume task: {e}")
        await update_work_status(db, task_id, TaskStatus.ERROR)
        await update_task_error(task_id, f"run_sub_resume_task error: {str(e)}")
        asyncio.create_task(cleanup_task(task_id, None))
        raise


def _make_sub_resume_section_configs(result: SubResumeResult) -> list[SectionConfig]:
    """构建 SubResumeResult 对应的 section 配置列表。"""
    configs: list[SectionConfig] = [
        SectionConfig(
            type="personal_info",
            title="个人信息",
            content_fn=lambda: result.personal_info.model_dump(),
            default_fn=lambda: PersonalInfo().model_dump(),
            field_name="personal_info",
        ),
        SectionConfig(
            type="summary",
            title="个人简介",
            content_fn=lambda: {"text": result.summary.text},
            default_fn=lambda: Summary().model_dump(),
            field_name="summary",
        ),
        SectionConfig(
            type="work_experience",
            title="工作经历",
            content_fn=lambda: _build_items_content(
                result.work_experience, "work_experience"
            ),
            default_fn=lambda: {"items": []},
            field_name="work_experience",
        ),
        SectionConfig(
            type="education",
            title="教育背景",
            content_fn=lambda: _build_items_content(result.education, "education"),
            default_fn=lambda: {"items": []},
            field_name="education",
        ),
        SectionConfig(
            type="skills",
            title="技能特长",
            content_fn=lambda: _build_categories_content(result.skills),
            default_fn=lambda: {"categories": []},
            field_name="skills",
        ),
        SectionConfig(
            type="projects",
            title="项目经历",
            content_fn=lambda: _build_items_content(result.projects, "projects"),
            default_fn=lambda: {"items": []},
            field_name="projects",
        ),
        SectionConfig(
            type="languages",
            title="语言能力",
            content_fn=lambda: _build_items_content(result.languages, "languages"),
            default_fn=lambda: {"items": []},
            field_name="languages",
        ),
        SectionConfig(
            type="certifications",
            title="资格证书",
            content_fn=lambda: _build_items_content(
                result.certifications, "certifications"
            ),
            default_fn=lambda: {"items": []},
            field_name="certifications",
        ),
        SectionConfig(
            type="github",
            title="GitHub",
            content_fn=lambda: _build_items_content(result.github, "github"),
            default_fn=lambda: {"items": []},
            field_name="github",
        ),
    ]
    return configs


_prefix_store: dict[str, str] = {}


def _get_prefix(section_type: str) -> str:
    """获取或生成 section 类型的随机前缀。"""
    if section_type not in _prefix_store:
        _prefix_store[section_type] = secrets.token_hex(4)
    return _prefix_store[section_type]


def _ensure_id_local(obj: dict, prefix: str, index: int) -> dict:
    """确保对象有 id 字段。"""
    if "id" not in obj or not obj["id"]:
        obj["id"] = f"{prefix}-{index:04d}"
    return obj


def _build_items_content(items: list, prefix: str) -> dict:
    """构建 items 类型的 section content。"""
    p = _get_prefix(prefix)
    return {
        "items": [
            _ensure_id_local(item.model_dump(), p, idx)
            for idx, item in enumerate(items, start=1)
        ]
    }


def _build_categories_content(categories: list) -> dict:
    """构建 categories 类型的 section content（如 skills）。"""
    p = _get_prefix("skills")
    return {
        "categories": [
            _ensure_id_local(cat.model_dump(), p, idx)
            for idx, cat in enumerate(categories, start=1)
        ]
    }


def _create_custom_sections(
    result: SubResumeResult, resume_id: str, start_sort_order: int
) -> list[ResumeSection]:
    """创建 custom 类型的 section（每个 item 单独一个 section）。"""
    sections = []
    sort_order = start_sort_order
    for item in result.custom:
        sections.append(
            ResumeSection(
                resume_id=resume_id,
                type="custom",
                title=item.title,
                sort_order=sort_order,
                visible=True,
                content=json.dumps(item.model_dump(), ensure_ascii=False),
            )
        )
        sort_order += 1
    return sections


def _create_resume_sections(
    db: AsyncSession,
    resume_id: str,
    result: SubResumeResult,
) -> None:
    """创建简历的所有区块。

    按照预定义的固定顺序创建 section，缺失的 section 使用默认空内容填充。
    custom 类型每个 item 单独创建一个 section。
    不自行 commit/rollback，由调用方管理事务。

    Args:
        db: 数据库会话。
        resume_id: 简历 ID。
        result: LLM 解析结果。
    """
    global _prefix_store
    _prefix_store = {}
    configs = _make_sub_resume_section_configs(result)
    create_resume_sections(
        db,
        resume_id,
        result,
        configs,
        extra_sections_fn=_create_custom_sections,
    )


SYSTEM = """\
You are a professional resume optimization expert and career coach. Please tailor the provided resume to better match the job description (JD).


# Core Rules:
- Return JSON only — no additional text, explanations, or commentary
- Resume optimization is limited to rewording and reformatting existing content only. Never invent or add information not present in the original resume. Even if the job description explicitly requires certain skills, experience, or qualifications you must not fabricate them (e.g., if the original resume does not mention Rust, you cannot claim the candidate is familiar with Rust in the optimized resume)


Below is the JSON schema definition you must follow:
<json_schema>
{json_schema}
</json_schema>"""
