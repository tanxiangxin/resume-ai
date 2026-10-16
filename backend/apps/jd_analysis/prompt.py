import json

from apps.jd_analysis.schemas import JdExtractionResult
from shared.types.resume import (
    PersonalInfoSection,
    ResumeSectionSchema,
    SummarySection,
)

JD_PERSONAL_INFO_FIELDS = {
    "full_name",
    "age",
    "gender",
    "education_level",
    "job_title",
    "salary",
    "location",
    "political_status",
    "ethnicity",
    "hometown",
    "marital_status",
    "years_of_experience",
    "website",
    "linkedin",
}

_EXCLUDE_SECTION_KEYS = {
    "resume_id",
    "visible",
    "sort_order",
    "created_at",
    "updated_at",
}

_EXCLUDE_CONTENT_KEYS = {"id", "image_url"}


def _strip_dict(d: dict, exclude_keys: set[str]) -> dict:
    return {
        k: v
        for k, v in d.items()
        if k not in exclude_keys and v not in (None, "", [], {})
    }


def _section_to_dict(section: ResumeSectionSchema) -> dict | None:
    if isinstance(section, PersonalInfoSection):
        if section.content is None:
            return None
        content = _strip_dict(section.content.model_dump(), _EXCLUDE_CONTENT_KEYS)
        content = {
            k: v for k, v in content.items() if k in JD_PERSONAL_INFO_FIELDS and v
        }
        if not content:
            return None
        return {"id": section.id, "type": section.type, "content": content}

    if isinstance(section, SummarySection):
        if section.content is None or not section.content.text:
            return None
        return {
            "id": section.id,
            "type": section.type,
            "content": {"text": section.content.text},
        }

    base = _strip_dict(section.model_dump(by_alias=False), _EXCLUDE_SECTION_KEYS)
    if "content" in base and isinstance(base["content"], dict):
        if "items" in base["content"]:
            base["content"]["items"] = [
                _strip_dict(item, _EXCLUDE_CONTENT_KEYS)
                for item in base["content"]["items"]
            ]
        elif "categories" in base["content"]:
            base["content"]["categories"] = [
                _strip_dict(cat, _EXCLUDE_CONTENT_KEYS)
                for cat in base["content"]["categories"]
            ]
    return base


def build_match_user_prompt(
    sections: list[ResumeSectionSchema],
    job_description: str,
    job_title: str | None,
) -> str:
    sections_data = []
    for section in sections:
        section_dict = _section_to_dict(section)
        if section_dict is not None:
            sections_data.append(section_dict)

    resume_json = json.dumps(sections_data, ensure_ascii=False, indent=2)
    parts = ["<resume>", resume_json, "</resume>"]
    if job_title:
        parts.append(f"\nJob Title: {job_title}")
    parts.append(f"<job_description>\n{job_description}\n</job_description>")
    return "\n".join(parts)


EXTRACTION_SYSTEM = """\
You are a professional job description analyst. Extract structured requirements from the provided job description (JD).

# Core Rules:
- Return ONLY valid JSON content, no additional descriptions or explanations
- Extract EVERY requirement, skill, qualification, and expectation mentioned in the JD
- Classify each requirement accurately by category and importance

Below is the JSON schema definition you must follow:
<json_schema>
{json_schema}
</json_schema>"""


def build_extraction_user_prompt(
    job_description: str, job_title: str | None = None
) -> str:
    parts = []
    if job_title:
        parts.append(f"Job Title: {job_title}")
    parts.append(f"<job_description>\n{job_description}\n</job_description>")
    return "\n\n".join(parts)


def derive_requirements_summary(extraction: JdExtractionResult) -> str:
    mandatory = [r for r in extraction.requirements if r.importance == "mandatory"]
    preferred = [r for r in extraction.requirements if r.importance == "preferred"]
    bonus = [r for r in extraction.requirements if r.importance == "bonus"]

    lines: list[str] = []

    if mandatory:
        lines.append("## Mandatory Requirements (must-have)")
        for r in mandatory:
            level_str = f" ({r.level})" if r.level else ""
            lines.append(f"- {r.name}{level_str}")

    if preferred:
        lines.append("## Preferred Requirements (nice-to-have)")
        for r in preferred:
            level_str = f" ({r.level})" if r.level else ""
            lines.append(f"- {r.name}{level_str}")

    if bonus:
        lines.append("## Bonus Requirements (a plus)")
        for r in bonus:
            level_str = f" ({r.level})" if r.level else ""
            lines.append(f"- {r.name}{level_str}")

    return "\n".join(lines)


SYSTEM = """\
You are a professional job description analyst. Analyze the match between the provided resume and the job description (JD).

# Pre-extracted JD Requirements
The following structured requirements were extracted from the JD. Use them as authoritative guidance for scoring, classification, and determining importance weights:

<requirements>
{requirements}
</requirements>

# Core Rules:
- Return ONLY valid JSON content, no additional descriptions or explanations
- Your analysis should be accurate and provide practical suggestions
- Use the pre-extracted requirements above to guide your keyword_matches, missing_keywords, and skill_matches classification (especially the category and importance fields)

Below is the JSON schema definition you must follow:
<json_schema>
{json_schema}
</json_schema>"""
