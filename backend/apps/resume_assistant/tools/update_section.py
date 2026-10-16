import json
import re
import secrets
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from chiren_backend.platform.db import async_session
from chiren_backend.platform.models import ResumeSection, utc_now
from shared.types.base_tool import BaseTool, ToolExecutionContext, ToolResult
from shared.types.resume import SECTION_TYPE_TO_MODEL

_ID_FORMAT = re.compile(r"^[0-9a-f]{8}-\d{4}$")

# 各 section 类型的字段结构和示例
_SECTION_CONTENT_SCHEMAS = {
    "personal_info": {
        "fields": "full_name, job_title, email, phone, location, salary, age, gender, political_status, education_level, ethnicity, hometown, marital_status, years_of_experience, wechat, website, linkedin",
        "example": '{ "full_name": "John", "email": "john@example.com" }',
    },
    "summary": {
        "fields": "text",
        "example": '{ "text": "Experienced engineer..." }',
    },
    "work_experience": {
        "fields": "items: [{ id, company, position, location, start_date, end_date, current, description, technologies: string[], highlights: string[] }]",
        "example": '{ "items": [{ "company": "Google", "position": "Engineer", "start_date": "2020.01", "end_date": "2023.12", "description": "...", "technologies": ["Python", "Go"] }] }',
    },
    "education": {
        "fields": "items: [{ id, institution, degree, field, location, start_date, end_date, gpa, highlights: string[] }]",
        "example": '{ "items": [{ "institution": "MIT", "degree": "Master", "field": "CS", "start_date": "2018", "end_date": "2020" }] }',
    },
    "projects": {
        "fields": "items: [{ id, name, url, description, technologies: string[], highlights: string[], start_date, end_date }]",
        "example": '{ "items": [{ "name": "AI Project", "description": "...", "technologies": ["Python", "PyTorch"] }] }',
    },
    "certifications": {
        "fields": "items: [{ id, name, issuer, date, description }]",
        "example": '{ "items": [{ "name": "AWS Solutions Architect", "issuer": "Amazon", "date": "2023.01", "description": "..." }] }',
    },
    "languages": {
        "fields": "items: [{ id, language, proficiency, description }]",
        "example": '{ "items": [{ "language": "English", "proficiency": "CET-6" }] }',
    },
    "github": {
        "fields": "items: [{ id, repo_url, name, stars, language, description }] — repo_url/name/stars/language are READ-ONLY, only modify description",
        "example": '{ "items": [{ "name": "my-repo", "description": "A cool project" }] }',
    },
    "custom": {
        "fields": "items: [{ id, title, date, description }]",
        "example": '{ "items": [{ "title": "Awards", "description": "..." }] }',
    },
    "skills": {
        "fields": "categories: [{ id, name, skills: string[] }]",
        "example": '{ "categories": [{ "name": "Programming", "skills": ["Python", "Java"] }] }',
    },
}


def build_tool_description(sections: list[dict]) -> str:
    """
    根据激活的 sections 构建工具描述中的 'Section content structures' 部分。

    Args:
        sections: 已排序的可见 section 列表，每个元素包含 type 和其他字段的 dict

    Returns:
        动态生成的字段结构说明字符串
    """
    lines = []
    for section in sections:
        section_type = section.get("type")
        if section_type in _SECTION_CONTENT_SCHEMAS:
            schema = _SECTION_CONTENT_SCHEMAS[section_type]
            lines.append(f"- {section_type}: {schema['fields']}")
            lines.append(f"  → e.g. {schema['example']}")
    return "\n".join(lines)


def _generate_prefix() -> str:
    return secrets.token_hex(4)


def _generate_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index:04d}"


def _assign_ids(submitted_items: list, existing_items: list) -> list:
    if existing_items:
        last_id = (
            existing_items[-1].get("id", "")
            if isinstance(existing_items[-1], dict)
            else existing_items[-1].get("id", "")
        )
        # 兼容外部 id 格式（如 GitHub 的 UUID），不符合预期格式时生成全新前缀
        if _ID_FORMAT.match(last_id):
            prefix = last_id.split("-")[0]
            last_index = int(last_id.split("-")[1])
        else:
            prefix = _generate_prefix()
            last_index = 0
    else:
        prefix = _generate_prefix()
        last_index = 0

    next_index = last_index + 1
    result = []
    for item in submitted_items:
        if isinstance(item, dict):
            if "id" not in item or not item["id"]:
                item["id"] = _generate_id(prefix, next_index)
                next_index += 1
            result.append(item)
        else:
            result.append(item)
    return result


def _collect_existing_ids(items: list[dict]) -> set[str]:
    """收集已存在 items 的 id 集合。"""
    return {item["id"] for item in items if isinstance(item, dict) and item.get("id")}


def _validate_item_id(item: dict, field_path: str, existing_ids: set[str]) -> list[str]:
    """
    验证单个 item 的 id。

    - 如果提供了 id，则必须是已存在的 id（新 item 不应带 id）
    - 已存在 id 的格式不限（兼容 GitHub 等外部来源的 UUID id）
    """
    errors = []
    item_id = item.get("id")
    if not item_id:
        return errors

    if item_id not in existing_ids:
        errors.append(
            f"  - {field_path}.id: '{item_id}' is invalid. Omit the id field for new items (it will be auto-generated); preserve the original id for existing items."
        )
        return errors
    return errors


def _validate_items(
    submitted_items: list, existing_items: list, item_type: str
) -> list[str]:
    """
    验证提交的 items 的 id。

    - id 格式必须正确
    - 新增的 item 不应带 id（应自动生成）
    - 只有现有 item 的 id 才能保留
    """
    errors = []
    existing_ids = _collect_existing_ids(existing_items)
    for i, item in enumerate(submitted_items):
        if not isinstance(item, dict):
            continue
        field_path = f"{item_type}[{i}]"
        errors.extend(_validate_item_id(item, field_path, existing_ids))
    return errors


class UpdateSectionToolInput(BaseModel):
    section_id: str = Field(description="The ID of the section to update")
    value: dict = Field(
        description="Partial update object. For scalar sections (personal_info, summary), include only the fields to change. For array sections, pass the complete items/categories array."
    )


class UpdateSectionTool(BaseTool):
    name = "update_section"
    description = (
        "Update the content of a specific resume section using a partial update object.\n\n"
        "Pass only the fields you want to update. Unmentioned fields remain unchanged.\n\n"
        "Section content structures and update examples:\n"
        "{content_structures}\n\n"
        "For all array sections, pass the COMPLETE items/categories array.\n\n"
        "Item ID rules:\n"
        "- Existing items: preserve their id field exactly as-is\n"
        "- New items: omit the id field entirely — it will be generated automatically"
    )
    input_model = UpdateSectionToolInput

    async def execute(
        self, arguments: UpdateSectionToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        id_to_type: dict[str, str] = context.metadata.get("id_to_type", {})
        section_type = id_to_type.get(arguments.section_id)

        # 验证section_id
        if section_type is None:
            return ToolResult(
                is_error=True, output=f"Unknown Section ID: {arguments.section_id}"
            )

        model = SECTION_TYPE_TO_MODEL.get(section_type)

        # 验证value
        try:
            if section_type in ("personal_info", "summary", "custom"):
                model.model_validate(arguments.value)
            elif section_type in (
                "work_experience",
                "education",
                "projects",
                "certifications",
                "languages",
                "github",
            ):
                for item_data in arguments.value.get("items", []):
                    model.model_validate(item_data)
            elif section_type == "skills":
                for category_data in arguments.value.get("categories", []):
                    model.model_validate(category_data)
        except ValidationError as e:
            errors = []
            for err in e.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                errors.append(f"  - {field}: {err['msg']}")
            error_msg = f"[{section_type}] Validation failed:\n" + "\n".join(errors)

            return ToolResult(
                is_error=True,
                output=error_msg,
            )

        # 验证并执行更新
        for section in context.sections:
            if section["id"] != arguments.section_id:
                continue

            content = section.get("content", {})

            # 验证 item id（新 item 不应带 id，只有现有 item 才能保留原 id）
            if section_type in (
                "work_experience",
                "education",
                "projects",
                "certifications",
                "languages",
                "github",
            ):
                id_errors = _validate_items(
                    arguments.value.get("items", []),
                    content.get("items", []),
                    "items",
                )
                if id_errors:
                    error_msg = (
                        f"[{section_type}] Item ID validation failed:\n"
                        + "\n".join(id_errors)
                    )
                    return ToolResult(is_error=True, output=error_msg)
                content["items"] = _assign_ids(
                    arguments.value.get("items", []), content.get("items", [])
                )
            elif section_type == "skills":
                id_errors = _validate_items(
                    arguments.value.get("categories", []),
                    content.get("categories", []),
                    "categories",
                )
                if id_errors:
                    error_msg = (
                        f"[{section_type}] Item ID validation failed:\n"
                        + "\n".join(id_errors)
                    )
                    return ToolResult(is_error=True, output=error_msg)
                content["categories"] = _assign_ids(
                    arguments.value.get("categories", []), content.get("categories", [])
                )
            elif section_type in ("personal_info", "summary"):
                content.update(arguments.value)
            break

        # 同步更新到数据库
        resume_id = context.sections[0]["resume_id"]
        async with async_session() as db:
            result = await db.execute(
                select(ResumeSection).where(
                    ResumeSection.id == arguments.section_id,
                    ResumeSection.resume_id == resume_id,
                )
            )
            db_section = result.scalar_one_or_none()
            if db_section is not None:
                # 从 context.sections 中获取更新后的 content
                for section in context.sections:
                    if section["id"] == arguments.section_id:
                        db_section.content = json.dumps(
                            section.get("content", {}), ensure_ascii=False
                        )
                        break
                db_section.updated_at = utc_now()
                db.add(db_section)
            await db.commit()

        return ToolResult(
            output=f"Successfully updated section {arguments.section_id}."
        )

    def to_api_schema_v2(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description.format(
                content_structures=build_tool_description(sections)
            ),
            "input_schema": self.input_model.model_json_schema(),
        }


if __name__ == "__main__":
    # 示例：模拟已激活的 sections
    sections = [
        {
            "id": "ae6b2c85-a093-415a-8a47-47ac5dba5fee",
            "type": "personal_info",
            "title": "个人信息",
        },
        {
            "id": "5a79c9c4-e8ad-494e-a471-76d3ada55ec1",
            "type": "summary",
            "title": "个人简介",
        },
        {
            "id": "4f4eb8be-7bff-4fbb-bc5e-69217fd87838",
            "type": "work_experience",
            "title": "工作经历",
        },
        {
            "id": "fdd57768-1fa2-4ff0-9bff-8c237b25dded",
            "type": "education",
            "title": "教育背景",
        },
        {
            "id": "e279a487-2825-486c-97cc-2a2d3e9a1fcf",
            "type": "skills",
            "title": "技能特长",
        },
    ]

    import pprint

    tool = UpdateSectionTool()
    print(f"工具名称: {tool.name}")
    print("工具schema:")
    pprint.pp(tool.to_api_schema(sections))
