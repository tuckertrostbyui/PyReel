import json
import os
from datetime import datetime, timezone
from typing import Optional

from .config import PyReelConfig
from .exceptions import PyReelError


def generate_metadata(
    story: str,
    title: str,
    run_id: str,
    config: PyReelConfig,
    source_url: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict:
    if config.llm_provider and config.llm_api_key:
        from . import llm
        meta = llm.generate_metadata(story, config)
    else:
        meta = _heuristic_metadata(story)

    meta["generated_at"] = datetime.now(timezone.utc).isoformat()
    meta["story_mode"] = config.story_mode.value
    meta["source_url"] = source_url or ""
    meta["run_id"] = run_id

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(meta, f, indent=2)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise PyReelError("metadata.json is empty or missing after write.")

    return meta


def _heuristic_metadata(story: str) -> dict:
    sentences = [s.strip() for s in story.replace("\n", " ").split(".") if s.strip()]

    first_sentence = sentences[0] if sentences else story[:80]
    if len(first_sentence) > 80:
        title = first_sentence[:80] + "..."
    else:
        title = first_sentence

    description = ". ".join(sentences[:2]) + ("." if sentences else "")
    if len(sentences) < 2:
        description = story[:200]

    hashtags = [
        "reddit",
        "story",
        "viral",
        "shortsvideo",
        "reels",
        "tiktok",
        "storytelling",
    ]

    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "platforms": ["tiktok", "reels", "shorts"],
    }
