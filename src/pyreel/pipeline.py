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
from .config import PyReelConfig, SeriesMode, StoryMode
from .exceptions import PyReelHistoryError, PyReelPipelineError, PyReelRedditError

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
    title_meta: dict = {}
    if not stage_complete(run_dir, "story_fetch"):
        try:
            if config.story_mode in (StoryMode.FETCH, StoryMode.LLM_REWRITE, StoryMode.LLM_SUMMARIZE):
                _exclude: set = set()
                if config.history_file and not post_id:
                    from .history import PostHistory as _PostHistory
                    _exclude = _PostHistory(config.history_file).used_ids

                try:
                    post = reddit.fetch_post(subreddit or "", post_id, config, exclude_ids=_exclude)
                except PyReelRedditError as e:
                    if _exclude:
                        raise PyReelHistoryError(
                            f"No new posts found in r/{subreddit} — all available posts have "
                            f"already been used. History file: {config.history_file}"
                        ) from e
                    raise

                story = post["title"] + "\n\n" + post["body"]
                source_url = post["url"]
                title_meta = {"title": post["title"], "author": post.get("author", "")}

                fetched_post_path = os.path.join(run_dir, "fetched_post.json")
                with open(fetched_post_path, "w") as _fp:
                    json.dump(post, _fp, indent=2)
            elif config.story_mode == StoryMode.LLM_WRITE:
                from . import llm as llm_mod
                story = llm_mod.write_story(prompt or "", config)
                first_line = story.split("\n")[0].strip()[:200]
                title_meta = {"title": first_line, "author": ""}
            else:
                story = story or ""
                first_line = story.split("\n")[0].strip()[:200]
                title_meta = {"title": first_line, "author": ""}

            raw_path = os.path.join(run_dir, "story_raw.txt")
            with open(raw_path, "w") as f:
                f.write(story or "")

            title_meta_path = os.path.join(run_dir, "title_meta.json")
            with open(title_meta_path, "w") as f:
                json.dump(title_meta, f, indent=2)

            save_checkpoint(run_dir, "story_fetch")
        except (PyReelPipelineError, PyReelHistoryError):
            raise
        except Exception as e:
            logger.error(f"[pipeline] Stage story_fetch failed: {e}")
            raise PyReelPipelineError(f"Stage story_fetch failed: {e}") from e
    else:
        raw_path = os.path.join(run_dir, "story_raw.txt")
        with open(raw_path) as f:
            story = f.read()
        title_meta_path = os.path.join(run_dir, "title_meta.json")
        if os.path.exists(title_meta_path):
            with open(title_meta_path) as f:
                title_meta = json.load(f)
        else:
            title_meta = {"title": story.split("\n")[0].strip()[:200], "author": ""}

    # Stage 3: story_sanitize
    if not stage_complete(run_dir, "story_sanitize"):
        try:
            clean = sanitize.sanitize_text(story or "", config)
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
                final_story = llm_mod.rewrite_with_hook(clean, config)
            elif config.story_mode == StoryMode.LLM_SUMMARIZE:
                final_story = llm_mod.summarize_to_fit(clean, config)
            else:
                final_story = clean

            final_path = os.path.join(run_dir, "story_final.txt")
            with open(final_path, "w") as f:
                f.write(final_story)
            if config.story_mode == StoryMode.LLM_REWRITE:
                hook_line = final_story.split("\n\n", 1)[0].strip()
                if hook_line:
                    title_meta["title"] = hook_line
                    with open(title_meta_path, "w") as f:
                        json.dump(title_meta, f, indent=2)
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
        if config.story_mode == StoryMode.LLM_REWRITE:
            hook_line = final_story.split("\n\n", 1)[0].strip()
            if hook_line:
                title_meta["title"] = hook_line
                with open(title_meta_path, "w") as f:
                    json.dump(title_meta, f, indent=2)

    # Stage 5: tts_generate
    audio_path = os.path.join(run_dir, "audio.wav")
    if not stage_complete(run_dir, "tts_generate"):
        try:
            tts.generate_audio(final_story, audio_path, config)
        except PyReelPipelineError:
            raise
        except Exception as e:
            raise PyReelPipelineError(f"Stage tts_generate failed: {e}") from e
        save_checkpoint(run_dir, "tts_generate")

    # Stage 6: whisper_align
    alignment_path = os.path.join(run_dir, "alignment.json")
    if not stage_complete(run_dir, "whisper_align"):
        try:
            alignment = align.align_audio(audio_path, alignment_path, config)
        except PyReelPipelineError:
            raise
        except Exception as e:
            raise PyReelPipelineError(f"Stage whisper_align failed: {e}") from e
        save_checkpoint(run_dir, "whisper_align")
    else:
        with open(alignment_path) as f:
            alignment = json.load(f)

    # Stage 7: broll_fetch
    broll_raw_path = os.path.join(run_dir, "broll_raw.mp4")
    if not stage_complete(run_dir, "broll_fetch"):
        try:
            broll_raw_path = broll.fetch_broll(run_dir, config)
        except PyReelPipelineError:
            raise
        except Exception as e:
            raise PyReelPipelineError(f"Stage broll_fetch failed: {e}") from e
        save_checkpoint(run_dir, "broll_fetch")

    # Stage 8: broll_crop
    broll_cropped_path = os.path.join(run_dir, "broll_cropped.mp4")
    if not stage_complete(run_dir, "broll_crop"):
        try:
            crop.crop_to_portrait(broll_raw_path, broll_cropped_path, config)
        except PyReelPipelineError:
            raise
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
            except PyReelPipelineError:
                raise
            except Exception as e:
                raise PyReelPipelineError(f"Stage subtitles_render failed: {e}") from e
        save_checkpoint(run_dir, "subtitles_render")

    # Stage 9.5: title_card_render
    # Rebuild the clip whenever video_compose hasn't run yet (clip is in-memory, no artifact).
    if config.title_card.enabled and not stage_complete(run_dir, "video_compose"):
        try:
            from . import title_card as title_card_mod
            _tc_title = title_meta.get("title", "")
            _tc_author = (
                config.title_card.username
                or title_meta.get("author", "")
                or "Anonymous"
            )
            # Calculate how long the title takes to be read from the alignment.
            # Falls back to config.title_card.duration if alignment is insufficient.
            tc_duration = (
                title_card_mod.calculate_title_duration(_tc_title, alignment)
                or config.title_card.duration
            )
            # Only show subtitles for the story body — suppress clips that start
            # during the title card phase.
            story_subtitle_clips = [c for c in subtitle_clips if c.start >= tc_duration]
            tc_clip = title_card_mod.build_title_card_clip(
                _tc_title, _tc_author, config, duration=tc_duration
            )
            subtitle_clips = [tc_clip] + story_subtitle_clips
        except PyReelPipelineError:
            raise
        except Exception as e:
            raise PyReelPipelineError(f"Stage title_card_render failed: {e}") from e
        if not stage_complete(run_dir, "title_card_render"):
            save_checkpoint(run_dir, "title_card_render")

    # Stage 10: video_compose
    final_video_path = os.path.join(run_dir, "final_video.mp4")
    if not stage_complete(run_dir, "video_compose"):
        try:
            compose.compose_video(broll_cropped_path, audio_path, subtitle_clips, final_video_path, config)
        except PyReelPipelineError:
            raise
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
        except PyReelPipelineError:
            raise
        except Exception as e:
            raise PyReelPipelineError(f"Stage metadata_generate failed: {e}") from e
        save_checkpoint(run_dir, "metadata_generate")

    # Stage 12: output_finalize
    if not stage_complete(run_dir, "output_finalize"):
        if not config.keep_artifacts:
            _cleanup_artifacts(run_dir)

        if config.history_file:
            fetched_post_path = os.path.join(run_dir, "fetched_post.json")
            if os.path.exists(fetched_post_path):
                from .history import PostHistory as _PostHistory
                with open(fetched_post_path) as _fp:
                    _post = json.load(_fp)
                _PostHistory(config.history_file).record(
                    post_id=_post["id"],
                    title=_post["title"],
                    url=_post["url"],
                    run_id=run_id,
                )

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
            _split_exclude: set = set()
            if config.history_file and not post_id:
                from .history import PostHistory as _PostHistory
                _split_exclude = _PostHistory(config.history_file).used_ids

            try:
                post = reddit_mod.fetch_post(subreddit or "", post_id, config, exclude_ids=_split_exclude)
            except PyReelRedditError as e:
                if _split_exclude:
                    raise PyReelHistoryError(
                        f"No new posts found in r/{subreddit} — all available posts have "
                        f"already been used. History file: {config.history_file}"
                    ) from e
                raise

            story = post["title"] + "\n\n" + post["body"]
            source_url = post["url"]
            split_title_meta = {"title": post["title"], "author": post.get("author", "")}

            _split_fetched_path = os.path.join(run_dir, "fetched_post.json")
            with open(_split_fetched_path, "w") as _fp:
                json.dump(post, _fp, indent=2)
        elif config.story_mode == StoryMode.LLM_WRITE:
            story = llm_mod.write_story(prompt or "", config)
            source_url = ""
            first_line = story.split("\n")[0].strip()[:200]
            split_title_meta = {"title": first_line, "author": ""}
        else:
            story = prompt or ""
            source_url = ""
            first_line = story.split("\n")[0].strip()[:200]
            split_title_meta = {"title": first_line, "author": ""}

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

            with open(os.path.join(part_dir, "title_meta.json"), "w") as f:
                json.dump(split_title_meta, f, indent=2)

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

        if config.history_file:
            _split_fetched_path = os.path.join(run_dir, "fetched_post.json")
            if os.path.exists(_split_fetched_path):
                from .history import PostHistory as _PostHistory
                with open(_split_fetched_path) as _fp:
                    _post = json.load(_fp)
                _PostHistory(config.history_file).record(
                    post_id=_post["id"],
                    title=_post["title"],
                    url=_post["url"],
                    run_id=run_id,
                )

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
