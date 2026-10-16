from apps.cover_letter.prompt import build_cover_letter_user_prompt
from shared.types.jd_profile import JdProfileData


def test_cover_letter_prompt_allows_empty_optional_context() -> None:
    prompt = build_cover_letter_user_prompt(
        [],
        "熟练使用 Python",
        JdProfileData(),
        "张三",
        "zhang@example.com",
        "13800000000",
    )

    assert "Candidate Contact Information" in prompt
    assert "Target Company: None" not in prompt
    assert "Recipient: None" not in prompt
    assert "Additional Candidate Instructions: None" not in prompt
