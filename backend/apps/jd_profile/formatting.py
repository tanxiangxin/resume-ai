import json
from typing import Literal

from shared.types.jd_profile import JdProfileData

JdProfilePromptView = Literal[
    "greeting",
    "cover_letter",
    "interview",
    "resume",
]


def _pick(data: dict, fields: tuple[str, ...]) -> dict:
    return {
        field: data[field]
        for field in fields
        if field in data and data[field] not in (None, "", [], {})
    }


def _requirements(
    profile: dict,
    *,
    include_ids: bool = True,
    include_interview_topics: bool = False,
) -> list[dict]:
    fields = ("name", "category", "importance", "level")
    if include_interview_topics:
        fields += ("interview_probe_topics",)
    if include_ids:
        fields = ("id",) + fields
    return [_pick(item, fields) for item in profile["requirements"]]


def _responsibilities(profile: dict) -> list[dict]:
    return [
        _pick(item, ("name", "output_expectations"))
        for item in profile["responsibilities"]
    ]


def _fit_signals(profile: dict) -> list[dict]:
    return [
        _pick(item, ("name", "resume_hint", "weight"))
        for item in profile["fit_signals"]
    ]


def _project_profile(profile: JdProfileData, view: JdProfilePromptView) -> dict:
    data = profile.model_dump(mode="json")

    if view == "greeting":
        return {
            "role_profile": _pick(
                data["role_profile"], ("role_family", "domain", "team_context")
            ),
            "requirements": _requirements(data),
            "responsibilities": _responsibilities(data),
            "core_selection_criteria": [
                _pick(item, ("id", "criterion", "priority"))
                for item in data["core_selection_criteria"]
            ],
            "fit_signals": _fit_signals(data),
        }

    if view == "cover_letter":
        return {
            "role_profile": data["role_profile"],
            "requirements": _requirements(data, include_ids=False),
            "responsibilities": _responsibilities(data),
            "resume_strategy": data["resume_strategy"],
        }

    if view == "interview":
        return {
            "requirements": _requirements(data, include_interview_topics=True),
            "responsibilities": _responsibilities(data),
            "core_selection_criteria": [
                _pick(item, ("id", "criterion", "priority"))
                for item in data["core_selection_criteria"]
            ],
            "interview_strategy": data["interview_strategy"],
        }

    return {
        "role_profile": data["role_profile"],
        "requirements": _requirements(data),
        "responsibilities": _responsibilities(data),
        "resume_strategy": data["resume_strategy"],
    }


def format_jd_profile_for_prompt(
    profile: JdProfileData, view: JdProfilePromptView
) -> str:
    """Format only the JD profile projection required by one consumer."""
    return json.dumps(
        _project_profile(profile, view),
        ensure_ascii=False,
        indent=2,
    )


def build_jd_profile_prompt_block(
    profile: JdProfileData, view: JdProfilePromptView
) -> str:
    return (
        "# Structured JD Profile\n"
        "Use this focused profile projection together with the original JD.\n\n"
        "<jd_profile>\n"
        f"{format_jd_profile_for_prompt(profile, view)}\n"
        "</jd_profile>"
    )
