import json

from shared.types.greeting import GreetingGenerationResult

STYLE_EXAMPLES = """\
Examples are for writing style only; never copy their facts:

JD: business-backend API development and data visualization.
Resume: independently built an inventory system, including REST APIs, permissions,
and frontend integration.
Good: "您好，我独立完成过库存管理系统，负责 REST 接口、权限逻辑和前端联调，和贵司
业务后台开发方向有直接联系，希望有机会进一步交流。"

Weak: "您好，我熟悉 Python、React、数据库和接口开发，能力很强，非常匹配贵司岗位。"
Reason: keywords and self-evaluation do not show a concrete action or job connection.
"""


SYSTEM_PROMPT = """\
You help a candidate write a concise first-contact message to a recruiter on Boss.
The goal is to present the candidate's strongest credible connections to the current JD,
without turning the messages into a requirement checklist.

Use the original JD for wording and context, the structured Profile for priorities, and every
visible resume section as the only source of candidate facts. Before writing, silently scan the
whole resume evidence pool, including summary, skills, education, work experience, projects,
and links. Build a small pool of the strongest JD-to-resume matches. Rank them by JD importance,
evidence specificity, concrete action or outcome, and usefulness for this role. Do not stop at
the first strong project. Scanning the whole resume is for discovery, not for inclusion: discard
facts that are unrelated to this JD, too generic to support a claim, or weaker than a relevant
alternative. When multiple strong sources exist, distribute the variants across different
projects, experiences, or sections; do not force diversity by using a weak match.

For each variant, choose one main match from that pool, then:
1. name the relevant project or experience;
2. state one concrete action, problem, result, or impact;
3. connect what the role needs, what the candidate did, and why it matters.
Optional bonuses may be included when they strengthen this single thesis.

Write natural Chinese suitable for first contact. Keep it concise but complete; roughly 60-110
characters is only a guide. Prefer concrete actions over technology lists and vague claims such as
"非常匹配"、"能力很强"、"相信能胜任". Paraphrase supported facts naturally, but do not add
experience, tools, qualifications, results, links, or certainty. Do not write a cover letter,
generic self-introduction, or markdown list.

Variant focus: professional is measured and evidence-led; natural is human and conversational;
match_focused directly answers the JD's most important requirement. They should differ in
emphasis or selected match when the evidence supports it, but may share a stronger match when
that is more honest than inventing variety.

Every match point must support something actually expressed in that variant's text. Use one main
point and at most one supporting point; do not add unrelated evidence just to increase coverage.

Return one JSON object matching the schema with exactly three unique variants. Use
selection_criterion_id only from jd_profile.core_selection_criteria[].id and
match_points[].requirement_id only from jd_profile.requirements[].id.

{style_examples}

JSON schema:
<json_schema>
{json_schema}
</json_schema>"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(
        style_examples=STYLE_EXAMPLES,
        json_schema=json.dumps(
            GreetingGenerationResult.model_json_schema(),
            ensure_ascii=False,
            indent=2,
        )
    )


def build_user_prompt(
    job_title: str | None,
    raw_job_description: str,
    jd_profile_block: str,
    resume_sections: str,
) -> str:
    return "\n\n".join(
        part
        for part in (
            f"Target role: {job_title}" if job_title else None,
            f"<raw_job_description>\n{raw_job_description}\n</raw_job_description>",
            jd_profile_block,
            f"<resume_sections>\n{resume_sections}\n</resume_sections>",
        )
        if part
    )
