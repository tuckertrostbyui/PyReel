import json
import logging
from typing import Optional

from .config import PyReelConfig
from .exceptions import PyReelLLMError

logger = logging.getLogger(__name__)


def words_for_duration(seconds: int) -> int:
    return int(seconds * 2.5)


def _word_count_target(config: PyReelConfig) -> str:
    """Return a word-count instruction that respects both min and max duration."""
    max_words = words_for_duration(config.max_duration)
    if config.min_duration is not None:
        min_words = words_for_duration(config.min_duration)
        return f"between {min_words} and {max_words} words (aim for at least {min_words})"
    return f"approximately {max_words} words"


def _require_llm(config: PyReelConfig) -> None:
    if not config.llm_provider:
        raise PyReelLLMError("llm_provider is required in PyReelConfig for LLM features.")
    if not config.llm_api_key:
        raise PyReelLLMError("llm_api_key is required in PyReelConfig for LLM features.")


def _call_llm(prompt: str, config: PyReelConfig, retries: int = 3, backoff: float = 10.0) -> str:
    try:
        import litellm
    except ImportError as e:
        raise PyReelLLMError("litellm is not installed.") from e

    import time

    try:
        retryable_exc = (litellm.RateLimitError, litellm.ServiceUnavailableError)
    except AttributeError:
        retryable_exc = ()

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = litellm.completion(
                model=config.llm_provider,
                messages=[{"role": "user", "content": prompt}],
                api_key=config.llm_api_key,
            )
            return response.choices[0].message.content
        except Exception as e:
            last_exc = e
            if retryable_exc and isinstance(e, retryable_exc) and attempt < retries:
                wait = backoff * attempt
                logger.warning(f"LLM call failed (attempt {attempt}/{retries}), retrying in {wait:.0f}s: {e}")
                time.sleep(wait)
            else:
                break

    raise PyReelLLMError(f"LLM call failed after {retries} attempts: {last_exc}") from last_exc


def rewrite_for_social(text: str, config: PyReelConfig) -> str:
    _require_llm(config)
    target = _word_count_target(config)
    prompt = (
        f"Rewrite the following story for short-form social media video. "
        f"Use first person, present tense. Write punchy sentences. "
        f"No markdown, no headers, no bullet points. "
        f"Target {target}.\n\n"
        f"Story:\n{text}"
    )
    return _call_llm(prompt, config)


def rewrite_with_hook(text: str, config: PyReelConfig) -> str:
    """Rewrite for social media, opening with the title as a natural hook.

    Assumes the first line of `text` is the Reddit post title (as stored by
    pipeline Stage 2 which writes ``title + "\\n\\n" + body``).
    """
    _require_llm(config)
    target = _word_count_target(config)
    prompt = (
        f"You are rewriting a Reddit post as a short spoken script for a social media video.\n\n"
        f"Rules:\n"
        f"- The first line of the story is the post title. Open with it as a natural hook question — "
        f"keep its authentic Reddit phrasing but expand any acronyms into their full phrase so it sounds "
        f"natural when spoken aloud (e.g. 'AITA' → 'Am I the asshole', 'TIFU' → 'Today I messed up', "
        f"'WIBTA' → 'Would I be the asshole'). Only improve the title if it is genuinely vague or boring.\n"
        f"- Tell the story in first person, past tense, the way someone would naturally "
        f"explain it out loud to a friend — conversational, honest, a little casual. "
        f"Not theatrical. Not overdramatic. No cliffhanger narration style.\n"
        f"- Keep the emotional honesty of the original. Don't punch up the drama beyond what's there.\n"
        f"- Expand all Reddit acronyms throughout the script — never leave AITA, NTA, YTA, ESH, "
        f"NAH, TIFU, WIBTA, or similar abbreviations in the output as the script will be read aloud.\n"
        f"- No markdown, no headers, no bullet points, no emojis.\n"
        f"- Target {target}.\n\n"
        f"Story:\n{text}"
    )
    return _call_llm(prompt, config)


def summarize_to_fit(text: str, config: PyReelConfig) -> str:
    _require_llm(config)
    target = _word_count_target(config)
    prompt = (
        f"Summarize the following story to {target}. "
        f"Preserve the narrative arc. Write in first person. "
        f"No markdown.\n\n"
        f"Story:\n{text}"
    )
    return _call_llm(prompt, config)


def split_into_parts(text: str, config: PyReelConfig) -> list[str]:
    _require_llm(config)
    target = _word_count_target(config)
    prompt = (
        f"Split the following story into multiple parts for a video series. "
        f"Each part should be {target} and end on a cliffhanger. "
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
    target = _word_count_target(config)
    llm_prompt = (
        f"Write an original short story on this topic: {prompt}\n\n"
        f"Write in first person, present tense. No markdown. "
        f"Target {target}."
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
