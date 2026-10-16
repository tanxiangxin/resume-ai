import asyncio
import json
import re
from collections import Counter

import json_repair
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from chiren_backend.platform.db import async_session
from chiren_backend.platform.llm.client import (
    ApiMessageCompleteEvent,
    ApiMessageRequest,
    ApiTextDeltaEvent,
    SupportsStreamingMessages,
)
from chiren_backend.platform.models import ResumeSection, utc_now
from shared.types.base_tool import BaseTool, ToolExecutionContext, ToolResult
from shared.types.messages import ConversationMessage, TextBlock
from shared.types.resume import SECTION_TYPE_TO_MODEL

_ID_FORMAT = re.compile(r"^[0-9a-f]{8}-\d{4}$")
_MAX_RETRIES = 5


def _collect_existing_ids(content: dict, section_type: str) -> set[str]:
    """Collect existing item/category IDs from original content."""
    if section_type in (
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
        "custom",
    ):
        items = content.get("items", [])
        return {
            item["id"] for item in items if isinstance(item, dict) and item.get("id")
        }
    if section_type == "skills":
        categories = content.get("categories", [])
        return {
            cat["id"] for cat in categories if isinstance(cat, dict) and cat.get("id")
        }
    return set()


def _validate_item_ids(
    submitted_items: list[dict],
    existing_ids: set[str],
    item_type: str,
) -> list[str]:
    """
    Validate that all submitted items have IDs that exist in original content,
    and that no ID appears more than once.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []
    submitted_ids = []

    for i, item in enumerate(submitted_items):
        if not isinstance(item, dict):
            continue

        item_id = item.get("id")
        field_path = f"{item_type}[{i}]"

        # Check for missing ID
        if not item_id:
            errors.append(
                f"  - {field_path}: missing 'id' field. "
                f"Each item must preserve its original ID from the source content."
            )
            continue

        # Check ID format
        if not _ID_FORMAT.match(item_id):
            errors.append(
                f"  - {field_path}.id '{item_id}': invalid format. "
                f"Expected 8-hex-4-digit pattern like 'a1b2c3d4-0001'."
            )
            continue

        # Check if ID exists in original content
        if item_id not in existing_ids:
            errors.append(
                f"  - {field_path}.id '{item_id}': not found in original content. "
                f"Each item must use the exact ID from the source. "
                f"Available IDs: {sorted(existing_ids)}"
            )
            continue

        submitted_ids.append(item_id)

    # Check for duplicate IDs
    duplicates = [id_ for id_, count in Counter(submitted_ids).items() if count > 1]
    if duplicates:
        errors.append(
            f"  - Duplicate IDs found: {duplicates}. "
            f"Each item ID must appear exactly once."
        )

    return errors


def validate_translated_content(
    content: dict,
    section_type: str,
    original_content: dict,
) -> tuple[bool, str | None]:
    """
    Validate translated content against Pydantic model and ID consistency.

    Returns:
        (is_valid, error_message)
    """
    model = SECTION_TYPE_TO_MODEL.get(section_type)
    if model is None:
        return False, f"Unknown section type: {section_type}"

    # Schema validation
    try:
        if section_type in ("personal_info", "summary", "custom"):
            model.model_validate(content)
        elif section_type in (
            "work_experience",
            "education",
            "projects",
            "certifications",
            "languages",
            "github",
        ):
            for item_data in content.get("items", []):
                model.model_validate(item_data)
        elif section_type == "skills":
            for category_data in content.get("categories", []):
                model.model_validate(category_data)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            errors.append(f"  - {field}: {err['msg']}")
        return False, f"[{section_type}] Schema validation failed:\n" + "\n".join(
            errors
        )

    # ID validation for array sections
    existing_ids = _collect_existing_ids(original_content, section_type)

    if section_type in (
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
    ):
        id_errors = _validate_item_ids(content.get("items", []), existing_ids, "items")
        if id_errors:
            return False, f"[{section_type}] ID validation failed:\n" + "\n".join(
                id_errors
            )

    elif section_type == "skills":
        id_errors = _validate_item_ids(
            content.get("categories", []), existing_ids, "categories"
        )
        if id_errors:
            return False, f"[{section_type}] ID validation failed:\n" + "\n".join(
                id_errors
            )

    return True, None


def _is_content_empty(content: dict, section_type: str) -> bool:
    """Check if section content is empty to avoid unnecessary translation token cost."""
    if not content:
        return True

    if section_type in ("personal_info", "summary", "custom"):
        return not any(content.values())

    if section_type in (
        "work_experience",
        "education",
        "projects",
        "certifications",
        "languages",
        "github",
    ):
        return not content.get("items")

    if section_type == "skills":
        return not content.get("categories")

    return False


def build_system_prompt(target_language: str) -> str:
    """Build system prompt with generic translation instructions."""
    return f"""\
You will receive a JSON array of resume sections.
Your task is to translate the resume content to {target_language}.
Return a JSON array only, no explanation.
Keep the original JSON array structure and order.
"""


def build_sections_user_prompt(sections: list[dict]) -> str:
    """
    Build user prompt containing all sections to translate in a single request.

    Args:
        sections: List of section dicts with type, id, title, content
    """
    filtered = [
        {k: v for k, v in s.items() if k not in ("updated_at", "created_at")}
        for s in sections
    ]
    return f"""\
Here is the JSON resume content:

<resume_content>
{json.dumps(filtered, indent=2, ensure_ascii=False)}
</resume_content>
"""


class TranslateResumeToolInput(BaseModel):
    target_language: str = Field(description="Target language code, e.g. zh, en")
    section_id: str | None = Field(
        default=None,
        description="Resume section ID to translate. Defaults to entire resume if omitted.",
    )


class TranslateResumeTool(BaseTool):
    name = "translate_resume"
    description = "Translate a resume (or a specific section) to the target language."
    input_model = TranslateResumeToolInput

    async def execute(
        self, arguments: TranslateResumeToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        id_to_type = context.metadata.get("id_to_type", {})
        if arguments.section_id is not None and arguments.section_id not in id_to_type:
            return ToolResult(
                output=f"Invalid section ID: {arguments.section_id}",
                is_error=True,
            )

        # 确定要翻译的 sections
        if arguments.section_id is not None:
            target_sections = [
                s for s in context.sections if s["id"] == arguments.section_id
            ]
        else:
            target_sections = list(context.sections)

        # 过滤出非空的 sections
        non_empty = []
        for section in target_sections:
            if not _is_content_empty(section.get("content", {}), section["type"]):
                non_empty.append(section)

        skipped = len(target_sections) - len(non_empty)

        # 一次性翻译所有 sections，统一验证，失败则只重试失败的
        section_results = await _translate_all_sections(
            non_empty, arguments.target_language, context.metadata
        )

        # 汇总结果
        success = sum(1 for r in section_results if r["success"])
        failed = len(section_results) - success

        lines = []
        for r in section_results:
            if r["success"]:
                lines.append(f"✓ {r['section_id']} ({r['section_type']})")
            else:
                lines.append(f"✗ {r['section_id']} ({r['section_type']}): {r['error']}")

        if skipped:
            lines.append(f"Skipped {skipped} empty section(s)")

        lines.append(
            f"\nTotal: {len(non_empty)} translated, {success} succeeded, {failed} failed"
        )

        # 同步成功的翻译结果到数据库
        if success:
            resume_id = context.sections[0]["resume_id"]
            now = utc_now()
            async with async_session() as db:
                for r in section_results:
                    if not r["success"]:
                        continue
                    section_id = r["section_id"]
                    for section in context.sections:
                        if section["id"] == section_id:
                            result = await db.execute(
                                select(ResumeSection).where(
                                    ResumeSection.id == section_id,
                                    ResumeSection.resume_id == resume_id,
                                )
                            )
                            db_section = result.scalar_one_or_none()
                            if db_section is not None:
                                db_section.content = json.dumps(
                                    section.get("content", {}), ensure_ascii=False
                                )
                                db_section.updated_at = now
                                db.add(db_section)
                            break
                await db.commit()

        return ToolResult(output="\n".join(lines))


async def _translate_all_sections(
    sections: list[dict], target_language: str, metadata: dict
) -> list[dict]:
    """
    Translate all sections in a single LLM call, then validate each.
    If any validation fails, retry all sections with error context.

    Returns:
        List of {"success": bool, "section_id": str, "section_type": str, "error": str | None}
        All items have the same success status on completion.
    """
    client: SupportsStreamingMessages = metadata.get("client")
    model: str = metadata.get("model")

    system_prompt = build_system_prompt(target_language)
    user_prompt = build_sections_user_prompt(sections)

    # 按 section_id 建立索引
    section_map: dict[str, dict] = {s["id"]: s for s in sections}

    # 初始化 messages 列表
    messages: list[ConversationMessage] = [
        ConversationMessage.from_user_text(user_prompt),
    ]

    for attempt in range(1, _MAX_RETRIES + 1):
        # 单次 LLM 调用，翻译所有 sections
        raw_content, call_error = await _call_translation(
            client, model, messages, system_prompt
        )
        if call_error:
            return [
                {
                    "success": False,
                    "section_id": s["id"],
                    "section_type": s["type"],
                    "error": call_error,
                }
                for s in sections
            ]

        # 解析响应
        try:
            translated_list = json_repair.loads(raw_content)
            if not isinstance(translated_list, list):
                raise ValueError(f"Expected list, got {type(translated_list).__name__}")
        except Exception as e:
            return [
                {
                    "success": False,
                    "section_id": s["id"],
                    "section_type": s["type"],
                    "error": f"JSON parse error: {e}",
                }
                for s in sections
            ]

        # 逐个验证
        results: list[dict] = []
        all_valid = True
        for i, translated_item in enumerate(translated_list):
            if i >= len(sections):
                break
            original = sections[i]
            section_id = original["id"]
            section_type = original["type"]
            original_content = original.get("content", {})
            new_content = translated_item.get("content", {})

            is_valid, error_msg = validate_translated_content(
                new_content, section_type, original_content
            )

            if is_valid:
                section_map[section_id]["content"] = new_content
                results.append(
                    {
                        "success": True,
                        "section_id": section_id,
                        "section_type": section_type,
                        "error": None,
                    }
                )
            else:
                all_valid = False
                results.append(
                    {
                        "success": False,
                        "section_id": section_id,
                        "section_type": section_type,
                        "error": error_msg,
                    }
                )

        if all_valid:
            return results

        # 有验证失败：追加到 messages 列表，让 LLM 重新翻译所有 sections
        messages.append(
            ConversationMessage(
                role="assistant", content=[TextBlock(text=raw_content)]
            ),
        )

        # 收集所有错误，生成统一的修正请求
        error_summary_parts = []
        for r in results:
            if not r["success"]:
                error_summary_parts.append(
                    f"**Section {r['section_id']} ({r['section_type']}) errors:**\n{r['error']}"
                )

        retry_msg = (
            "Some sections failed validation. Please fix ALL sections below and "
            "return the complete corrected JSON array (all sections, not just the failed ones).\n\n"
            + "\n\n".join(error_summary_parts)
        )
        messages.append(ConversationMessage.from_user_text(retry_msg))

        if attempt < _MAX_RETRIES:
            await asyncio.sleep(0.5 * attempt)

    # 达到最大重试次数，全部标记为失败
    return [
        {
            "success": False,
            "section_id": s["id"],
            "section_type": s["type"],
            "error": "Max retries exceeded after validation failures",
        }
        for s in sections
    ]


async def _call_translation(
    client: SupportsStreamingMessages,
    model: str,
    messages: list[ConversationMessage],
    system_prompt: str | None,
) -> tuple[str, str | None]:
    """
    Execute a single translation LLM call.

    Returns:
        (content, error_message)
    """
    request = ApiMessageRequest(
        model=model,
        messages=messages,
        system_prompt=system_prompt,
    )

    accumulated_content = ""
    try:
        async for event in client.stream_message(request):
            if isinstance(event, ApiTextDeltaEvent):
                if event.is_think:
                    continue
                accumulated_content += event.text
            elif isinstance(event, ApiMessageCompleteEvent):
                pass
    except Exception as e:
        return "", f"Stream error: {type(e).__name__}: {e}"

    if not accumulated_content:
        return "", "No content in response"

    return accumulated_content, None
