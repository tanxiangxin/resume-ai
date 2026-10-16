import json

from apps.parser.prompt import CONTENT, SYSTEM
from apps.parser.schemas import ParserResult
from chiren_backend.platform.llm import call_structured_json
from chiren_backend.platform.llm.client import SupportsStreamingMessages

MAX_RETRIES = 3


async def executor_llm(
    client: SupportsStreamingMessages, model: str, content: str
) -> ParserResult:
    system_prompt = SYSTEM.format(
        json_schema=json.dumps(
            ParserResult.model_json_schema(),
            indent=2,
            ensure_ascii=False,
        )
    )
    return await call_structured_json(
        client,
        model,
        system_prompt,
        CONTENT.format(content=content),
        ParserResult,
        max_retries=MAX_RETRIES,
    )
