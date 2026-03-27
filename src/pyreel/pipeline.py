import dataclasses
import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Optional

from slugify import slugify

from .checkpoint import (
    ARTIFACT_MAP,
    init_checkpoint,
    save_checkpoint,
    stage_complete,
)
from .config import BrollSource, PyReelConfig, SeriesMode, StoryMode
from .exceptions import PyReelPipelineError

logger = logging.getLogger(__name__)


class _EnumEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


def _write_run_config(run_dir: str, config: PyReelConfig) -> None:
    path = os.path.join(run_dir, "run_config.json")
    data = dataclasses.asdict(config)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=_EnumEncoder)


def _make_run_dir(config: PyReelConfig, title: str = "run") -> tuple[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(title, max_length=40) or "story"
    run_id = f"run_{timestamp}_{slug}"
    run_dir = os.path.join(config.output_dir, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir, run_id


def _run_stage(run_dir: str, stage_name: str, fn, *args, **kwargs):
    if stage_complete(run_dir, stage_name):
        logger.info(f"[checkpoint] Skipping already-complete stage: {stage_name}")
        artifact = ARTIFACT_MAP.get(stage_name)
        if artifact:
            artifact_path = os.path.join(run_dir, artifact)
            if os.path.exists(artifact_path):
                return _load_artifact(artifact_path)
        return None

    logger.info(f"[pipeline] Running stage: {stage_name}")
    try:
        result = fn(*args, **kwargs)
    except PyReelPipelineError:
        raise
    except Exception as e:
        logger.error(f"[pipeline] Stage {stage_name} failed: {e}")
        raise PyReelPipelineError(f"Stage {stage_name} failed: {e}") from e

    save_checkpoint(run_dir, stage_name)
    return result


def _load_artifact(path: str):
    if path.endswith(".json"):
        with open(path) as f:
            return json.load(f)
    elif path.endswith(".txt"):
        with open(path) as f:
            return f.read()
    return path


def _run_single(
    subreddit: Optional[str],
    post_id: Optional[str],
    prompt: Optional[str],
    story: Optional[str],
    run_dir: str,
    run_id: str,
    config: PyReelConfig,
    source_url: str = "",
) -> str:
    from . import align, broll, compose, crop, metadata, reddit, sanitize, subtitles, tts

    # Stage 2: story_fetch
    if not stage_complete(run_dir, "story_fetch"):
        try:
            if config.story_mode == StoryMode.FETCH:
                post = reddit.fetch_post(subreddit, post_id, config)
                story = post["title"] + "\n\n" + post["body"]
                source_url = post["url"]
            elif config.story_mode == StoryMode.LLM_WRITE:
                from . import llm as llm_mod
                story = llm_mod.write_story(prompt or "", config)
            else:
                story = story or ""

            raw_path = os.path.join(run_dir, "story_raw.txt")
            with open(raw_path, "w") as f:
                f.write(story)
            save_checkpoint(run_dir, "story_fetch")
        except PyReelPipelineError:
            raise
        except Exception as e:
            logger.error(f"[pipeline] Stage story_fetch failed: {e}")
            raise PyReelPipelineError(f"Stage story_fetch failed: {e}") from e
    else:
        raw_path = os.path.join(run_dir, "story_raw.txt")
        with open(raw_path) as f:
            story = f.read()

    # Stage 3: story_sanitize
    if not stage_complete(run_dir, "story_sanitize"):
        try:
            clean = sanitize.sanitize_text(story, config)
            clean_path = os.path.join(run_dir, "story_clean.txt")
            with open(clean_path, "w") as f:
                f.write(clean)
            save_checkpoint(run_dir, "story_sanitize")
        except PyReelPipelineError:
            raise
        except Exception as e:
            logger.error(f"[pipeline] Stage story_sanitize failed: {e}")
            raise PyReelPipelineError(f"Stage story_sanitize failed: {e}") from e
    else:
        clean_path = os.path.join(run_dir, "story_clean.txt")
        with open(clean_path) as f:
            clean = f.read()

    # Stage 4: story_prepare
    if not stage_complete(run_dir, "story_prepare"):
        try:
            from . import llm as llm_mod
            if config.story_mode == StoryMode.LLM_REWRITE:
                final_story = llm_mod.rewrite_for_social(clean, config)
            elif config.story_mode == StoryMode.LLM_SUMMARIZE:
                final_story = llm_mod.summarize_to_fit(clean, config)
            else:
                final_story = clean

            final_path = os.path.join(run_dir, "story_final.txt")
            with open(final_path, "w") as f:
                f.write(final_story)
            save_checkpoint(run_dir, "story_prepare")
        except PyReelPipelineError:
            raise
        except Exception as e:
            logger.error(f"[pipeline] Stage story_prepare failed: {e}")
            raise PyReelPipelineError(f"Stage story_prepare failed: {e}") from e
    else:
        final_path = os.path.join(run_dir, "story_final.txt")
        with open(final_path) as f:
            final_story = f.read()

    # Stage 5: tts_generate
    audio_path = os.path.join(run_dir, "audio.wav")
    if not stage_complete(run_dir, "tts_generate"):
        try:
            tts.generate_audio(final_story, audio_path, config)
        except Exception as e:
            raise PyReelPipelineError(f"Stage tts_generate failed: {e}") from e
        save_checkpoint(run_dir, "tts_generate")

    # Stage 6: whisper_align
    alignment_path = os.path.join(run_dir, "alignment.json")
    if not stage_complete(run_dir, "whisper_align"):
        try:
            alignment = align.align_audio(audio_path, alignment_path, config)
        except Exception as e:
            raise PyReelPipelineError(f"Stage whisper_align failed: {e}") from e
        save_checkpoint(run_dir, "whisper_align")
    else:
        with open(alignment_path) as f:
            alignment = json.load(f)

    # Stage 7: broll_fetch
    broll_keyword = config.broll_keyword or final_story[:50]
    broll_raw_path = os.path.join(run_dir, "broll_raw.mp4")
    if not stage_complete(run_dir, "broll_fetch"):
        try:
            broll_result = broll.fetch_broll(broll_keyword, run_dir, config)
        except Exception as e:
            raise PyReelPipelineError(f"Stage broll_fetch failed: {e}") from e
        if config.broll_source == BrollSource.LOCAL:
            broll_raw_path = broll_result
        save_checkpoint(run_dir, "broll_fetch")

    # Stage 8: broll_crop
    broll_cropped_path = os.path.join(run_dir, "broll_cropped.mp4")
    if not stage_complete(run_dir, "broll_crop"):
        try:
            crop.crop_to_portrait(broll_raw_path, broll_cropped_path, config)
        except Exception as e:
            raise PyReelPipelineError(f"Stage broll_crop failed: {e}") from e
        save_checkpoint(run_dir, "broll_crop")

    # Stage 9: subtitles_render
    subtitle_clips = []
    if not stage_complete(run_dir, "subtitles_render"):
        if config.burn_subtitles:
            try:
                from moviepy.audio.io.AudioFileClip import AudioFileClip
                audio_clip = AudioFileClip(audio_path)
                video_duration = audio_clip.duration
                audio_clip.close()
                subtitle_clips = subtitles.build_subtitle_clips(alignment, video_duration, config)
            except Exception as e:
                raise PyReelPipelineError(f"Stage subtitles_render failed: {e}") from e
        save_checkpoint(run_dir, "subtitles_render")

    # Stage 10: video_compose
    final_video_path = os.path.join(run_dir, "final_video.mp4")
    if not stage_complete(run_dir, "video_compose"):
        try:
            compose.compose_video(broll_cropped_path, audio_path, subtitle_clips, final_video_path, config)
        except Exception as e:
            raise PyReelPipelineError(f"Stage video_compose failed: {e}") from e
        save_checkpoint(run_dir, "video_compose")

    # Stage 11: metadata_generate
    metadata_path = os.path.join(run_dir, "metadata.json")
    if not stage_complete(run_dir, "metadata_generate"):
        try:
            title = final_story.split(".")[0][:80]
            metadata.generate_metadata(
                story=final_story,
                title=title,
                run_id=run_id,
                config=config,
                source_url=source_url,
                output_path=metadata_path,
            )
        except Exception as e:
            raise PyReelPipelineError(f"Stage metadata_generate failed: {e}") from e
        save_checkpoint(run_dir, "metadata_generate")

    # Stage 12: output_finalize
    if not stage_complete(run_dir, "output_finalize"):
        if not config.keep_artifacts:
            _cleanup_artifacts(run_dir)
        save_checkpoint(run_dir, "output_finalize")

    return final_video_path


def _cleanup_artifacts(run_dir: str) -> None:
    to_delete = [
        "audio.wav",
        "alignment.json",
        "broll_raw.mp4",
        "broll_cropped.mp4",
        "story_raw.txt",
        "story_clean.txt",
        ".checkpoint",
    ]
    for name in to_delete:
        path = os.path.join(run_dir, name)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning(f"Could not delete artifact {name}: {e}")


def run_pipeline(
    subreddit: Optional[str] = None,
    post_id: Optional[str] = None,
    prompt: Optional[str] = None,
    config: Optional[PyReelConfig] = None,
) -> list[str]:
    if config is None:
        config = PyReelConfig()

    from . import deps
    from .subtitles import check_and_patch_imagemagick

    # Stage 1: deps_check
    title_for_dir = subreddit or prompt or "story"
    run_dir, run_id = _make_run_dir(config, title_for_dir)
    init_checkpoint(run_dir, run_id, config)

    try:
        deps.check_dependencies(config)
    except Exception as e:
        raise PyReelPipelineError(f"Stage deps_check failed: {e}") from e

    check_and_patch_imagemagick()
    save_checkpoint(run_dir, "deps_check")

    if config.dry_run:
        print(f"[PyReel dry_run] Dependencies OK. Run directory: {run_dir}")
        print("[PyReel dry_run] Skipping all processing stages.")
        return []

    _write_run_config(run_dir, config)

    # SPLIT mode
    if config.series_mode == SeriesMode.SPLIT:
        from . import llm as llm_mod, reddit as reddit_mod, sanitize as sanitize_mod

        # Fetch and sanitize first
        if config.story_mode == StoryMode.FETCH:
            post = reddit_mod.fetch_post(subreddit, post_id, config)
            story = post["title"] + "\n\n" + post["body"]
            source_url = post["url"]
        elif config.story_mode == StoryMode.LLM_WRITE:
            story = llm_mod.write_story(prompt or "", config)
            source_url = ""
        else:
            story = prompt or ""
            source_url = ""

        clean = sanitize_mod.sanitize_text(story, config)
        parts = llm_mod.split_into_parts(clean, config)

        output_paths = []
        for i, part in enumerate(parts, 1):
            part_dir = os.path.join(run_dir, f"part_{i}")
            os.makedirs(part_dir, exist_ok=True)
            init_checkpoint(part_dir, f"{run_id}_part_{i}", config)

            raw_path = os.path.join(part_dir, "story_raw.txt")
            with open(raw_path, "w") as f:
                f.write(part)
            save_checkpoint(part_dir, "story_fetch")

            clean_path = os.path.join(part_dir, "story_clean.txt")
            with open(clean_path, "w") as f:
                f.write(part)
            save_checkpoint(part_dir, "story_sanitize")

            video_path = _run_single(
                subreddit=subreddit,
                post_id=post_id,
                prompt=prompt,
                story=part,
                run_dir=part_dir,
                run_id=f"{run_id}_part_{i}",
                config=config,
                source_url=source_url,
            )
            output_paths.append(video_path)

        return output_paths

    # SINGLE mode
    video_path = _run_single(
        subreddit=subreddit,
        post_id=post_id,
        prompt=prompt,
        story=prompt if config.story_mode == StoryMode.LLM_WRITE else None,
        run_dir=run_dir,
        run_id=run_id,
        config=config,
    )
    return [video_path]
