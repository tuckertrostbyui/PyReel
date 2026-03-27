import json
import logging
from typing import Optional

from .config import PyReelConfig
from .exceptions import PyReelLLMError

logger = logging.getLogger(__name__)


def words_for_duration(seconds: int) -> int:
    return int(seconds * 2.5)


def _require_llm(config: PyReelConfig) -> None:
    if not config.llm_provider:
        raise PyReelLLMError("llm_provider is required in PyReelConfig for LLM features.")
    if not config.llm_api_key:
        raise PyReelLLMError("llm_api_key is required in PyReelConfig for LLM features.")


def _call_llm(prompt: str, config: PyReelConfig) -> str:
    try:
        import litellm
    except ImportError as e:
        raise PyReelLLMError("litellm is not installed.") from e

    try:
        response = litellm.completion(
            model=config.llm_provider,
            messages=[{"role": "user", "content": prompt}],
            api_key=config.llm_api_key,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise PyReelLLMError(f"LLM call failed: {e}") from e


def rewrite_for_social(text: str, config: PyReelConfig) -> str:
    _require_llm(config)
    target_words = words_for_duration(config.max_duration)
    prompt = (
        f"Rewrite the following story for short-form social media video. "
        f"Use first person, present tense. Write punchy sentences. "
        f"No markdown, no headers, no bullet points. "
        f"Target approximately {target_words} words.\n\n"
        f"Story:\n{text}"
    )
    return _call_llm(prompt, config)


def summarize_to_fit(text: str, config: PyReelConfig) -> str:
    _require_llm(config)
    target_words = words_for_duration(config.max_duration)
    prompt = (
        f"Summarize the following story to approximately {target_words} words. "
        f"Preserve the narrative arc. Write in first person. "
        f"No markdown.\n\n"
        f"Story:\n{text}"
    )
    return _call_llm(prompt, config)


def split_into_parts(text: str, config: PyReelConfig) -> list[str]:
    _require_llm(config)
    target_words = words_for_duration(config.max_duration)
    prompt = (
        f"Split the following story into multiple parts for a video series. "
        f"Each part should be approximately {target_words} words and end on a cliffhanger. "
        f"Return ONLY a valid JSON array of strings, one string per part. "
        f"No other text.\n\n"
        f"Story:\n{text}"
    )
    raw = _call_llm(prompt, config)

    try:
        parts = json.loads(raw)
        if isinstance(parts, list) and all(isinstance(p, str) for p in parts):
            return parts
        raise ValueError("Not a list of strings")
    except Exception:
        logger.warning("LLM returned invalid JSON for split_into_parts; falling back to paragraph split.")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs if paragraphs else [text]


def write_story(prompt: str, config: PyReelConfig) -> str:
    _require_llm(config)
    target_words = words_for_duration(config.max_duration)
    llm_prompt = (
        f"Write an original short story on this topic: {prompt}\n\n"
        f"Write in first person, present tense. No markdown. "
        f"Target approximately {target_words} words."
    )
    return _call_llm(llm_prompt, config)


def generate_metadata(story: str, config: PyReelConfig) -> dict:
    _require_llm(config)
    prompt = (
        "Generate social media metadata for the following story. "
        "Return ONLY valid JSON with these exact keys:\n"
        '  "title": string under 100 characters\n'
        '  "description": string, 2-3 sentences\n'
        '  "hashtags": list of 10-15 strings, no # symbol\n'
        '  "platforms": always ["tiktok", "reels", "shorts"]\n\n'
        f"Story:\n{story}"
    )
    raw = _call_llm(prompt, config)

    try:
        raw_stripped = raw.strip()
        if raw_stripped.startswith("```"):
            raw_stripped = raw_stripped.split("```")[1]
            if raw_stripped.startswith("json"):
                raw_stripped = raw_stripped[4:]
        return json.loads(raw_stripped)
    except Exception as e:
        raise PyReelLLMError(f"LLM returned invalid JSON for metadata: {e}") from e
