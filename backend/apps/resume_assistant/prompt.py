import json
from typing import Any

from chiren_backend.platform.models import utc_now
from shared.types.jd_analysis import JobDescriptionAnalysisSchema


def build_sections_prompt(sections: list[dict]) -> str:
    lines = []
    for section in sections:
        lines.append(
            f'  - [{section["type"]}] "{section["title"]}" (section_id: {section["id"]})'
        )
    return "\n".join(lines)


def build_jd_prompt(
    jd_analysis: JobDescriptionAnalysisSchema,
    sections: list[dict[str, Any]],
) -> str:
    now = utc_now().isoformat()
    jd_analysis_time = (
        jd_analysis.created_at.isoformat() if jd_analysis.created_at else "N/A"
    )

    section_id_to_type = {s["id"]: s["type"] for s in sections}

    suggestions_by_section: dict[str, list[dict]] = {}
    for sug in jd_analysis.suggestions:
        sec_type = section_id_to_type.get(sug.section_id, sug.section_id)
        if sec_type not in suggestions_by_section:
            suggestions_by_section[sec_type] = []
        suggestions_by_section[sec_type].append(sug.model_dump(mode="json"))

    data = jd_analysis.model_dump(
        mode="json",
        exclude={"id", "resume_id", "job_description", "suggestions"},
    )
    data["optimization_suggestions"] = suggestions_by_section

    return (
        f"# Resume Optimization Suggestions Based on JD Analysis\n\n"
        f"Below is the latest Job Description (JD) analysis result. "
        f"Please optimize the resume accordingly.\n"
        f"- Analysis Generated At: {jd_analysis_time}\n"
        f"- Current Time: {now}\n\n"
        f"<jd_analysis_result>\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2)}\n"
        f"</jd_analysis_result>"
    )


SYSTEM = """\
You are Chiren, a resume optimization expert assistant.
Your task is to help users enhance the professionalism, impact, and ATS-friendliness of their resumes.

# Guidelines
- Provide specific, actionable suggestions.
- Use strong action verbs and quantifiable achievements.
- Maintain a professional and concise tone.

# Key Rules — Section Handling
- **Strictly prohibit** removing, deleting, or skipping any existing sections. The user has manually selected the sections to be included.
- When asked to fill, generate, or refine a resume, you **must** iterate through **all** the sections listed below and attempt to fill them. Do not stop prematurely.
- When updating list-type sections, preserve the `id` of existing items exactly as they are. For any new items added, completely omit the `id` field.

# Key Rules — Information Integrity
- Use only the information provided by the user as the sole source, mapping it to the corresponding fields in each section.
- Call the tool to update a section **only if** the user-provided information matches fields within that section.
- If a section cannot be matched with any provided information, skip it directly. Do not call the tool, and do not insert empty values or placeholders.
- Do not infer, guess, or fabricate any information not explicitly provided by the user.

# The resume currently contains the following sections
{sections}
"""


SUB_SYSTEM = """

# Job Description (JD)
<job_description>
{job_description}
</job_description>

Please optimize the resume based on this JD to improve role alignment and ATS performance.

Requirements:
- Use keywords and phrasing from the JD where appropriate
- Highlight the most relevant experience and skills
- Keep the content concise and focused

Note: Do not fabricate or introduce any information not provided by the user"""
