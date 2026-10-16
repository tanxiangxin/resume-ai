import json

from shared.types.jd_profile import JdProfileExtractionResult

SYSTEM = """\
You are a senior recruiting analyst. Convert the provided job description (JD)
into a structured profile that can be reused by resume scoring, resume writing,
and mock interviews.

# Core Rules
- Return ONLY valid JSON; no markdown, no explanations.
- Extract not only explicit skills, but also evaluation criteria, fit signals,
  anti-fit signals, work style expectations, product sense, and evidence needed
  to prove each requirement.
- Treat sections such as "what kind of person is not a fit", "what we care about",
  "team direction", and explicit product principles as core selection criteria.
  Convert each negative signal into the positive ability the candidate must prove.
- Do not leave responsibilities, evaluationRubric, fitSignals, antiFitSignals, or
  coreSelectionCriteria empty when the JD contains corresponding sections.
- Do not invent company facts. If the JD is ambiguous, record it in ambiguities.
- Keep requirement.category within the enum values from the schema. Put product
  judgment, work style, and "why/how/trade-off" expectations into
  evaluationRubric, fitSignals, or antiFitSignals when they are not plain skills.

Below is the JSON schema definition you must follow:
<json_schema>
{json_schema}
</json_schema>"""


def build_system_prompt() -> str:
    return SYSTEM.format(
        json_schema=json.dumps(
            JdProfileExtractionResult.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )
    )


def build_user_prompt(job_description: str, job_title: str | None = None) -> str:
    parts: list[str] = []
    if job_title:
        parts.append(f"Job Title: {job_title}")
    parts.append(f"<job_description>\n{job_description}\n</job_description>")
    return "\n\n".join(parts)
