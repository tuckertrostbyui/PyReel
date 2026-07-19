# PyReel

Automate short-form vertical video creation for TikTok, Instagram Reels, and YouTube Shorts.

Given a Reddit post (or an LLM-generated story), PyReel:
- Sanitizes and optionally rewrites the text via LLM
- Converts it to speech using Microsoft Edge TTS
- Aligns word-level timestamps via WhisperX
- Sources b-roll footage from a local video file
- Crops footage to 9:16 portrait
- Burns karaoke-style word-by-word subtitles
- Outputs a fully rendered `.mp4` + structured metadata bundle

LLM features are opt-in and provider-agnostic via [LiteLLM](https://github.com/BerriAI/litellm).

---

## System Dependencies

Install before using PyReel:

**FFmpeg**
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: https://ffmpeg.org/download.html

**ImageMagick**
- macOS: `brew install imagemagick`
- Ubuntu/Debian: `sudo apt install imagemagick`
- Windows: https://imagemagick.org/script/download.php

---

## Installation

```bash
pip install git+https://github.com/tuckertrost/PyReel.git
```

Or with uv:
```bash
uv pip install git+https://github.com/tuckertrost/PyReel.git
```

---

## Quick Start

### Check dependencies first

```python
import pyreel

pyreel.check_dependencies()
```

### Basic usage (Reddit fetch + local b-roll)

```python
import pyreel

config = pyreel.PyReelConfig(
    reddit_client_id="your_client_id",
    reddit_client_secret="your_client_secret",
    story_mode=pyreel.StoryMode.FETCH,
    max_duration=60,
    broll_local_path="./data/broll/gameplay.mp4",
    subtitle_style=pyreel.SubtitleStyleConfig(
        style=pyreel.SubtitleStyle.BOLD_WHITE,
        font_size=80,
    ),
    output_dir="./my_videos",
)

output_paths = pyreel.generate(subreddit="AmItheAsshole", config=config)
print(f"Video ready: {output_paths[0]}")
```

### With LLM rewriting

```python
config = pyreel.PyReelConfig(
    reddit_client_id="...",
    reddit_client_secret="...",
    story_mode=pyreel.StoryMode.LLM_REWRITE,
    llm_provider="openai/gpt-4o",
    llm_api_key="sk-...",
    max_duration=60,
    broll_local_path="./data/broll/gameplay.mp4",
)
output_paths = pyreel.generate(subreddit="relationship_advice", config=config)
```

### Multi-part series

```python
config = pyreel.PyReelConfig(
    reddit_client_id="...",
    reddit_client_secret="...",
    story_mode=pyreel.StoryMode.LLM_REWRITE,
    series_mode=pyreel.SeriesMode.SPLIT,
    llm_provider="anthropic/claude-3-5-sonnet-20241022",
    llm_api_key="sk-ant-...",
    max_duration=60,
    broll_local_path="./data/broll/subway_surfers.mp4",
)
output_paths = pyreel.generate(subreddit="tifu", config=config)
for i, path in enumerate(output_paths, 1):
    print(f"Part {i}: {path}")
```

### Dry run (validate config without producing video)

```python
config = pyreel.PyReelConfig(dry_run=True, reddit_client_id="...", reddit_client_secret="...")
pyreel.generate(subreddit="AmItheAsshole", config=config)
# Prints validation report. No video generated.
```

---

## Output Structure

```
output/run_20260415_120000_aita-neighbour/
  final_video.mp4      <- always kept
  metadata.json        <- always kept
  story_final.txt      <- always kept
  run_config.json      <- always kept
  audio.wav            <- deleted if keep_artifacts=False
  alignment.json       <- deleted if keep_artifacts=False
  broll_raw.mp4        <- deleted if keep_artifacts=False
  broll_cropped.mp4    <- deleted if keep_artifacts=False
  story_raw.txt        <- deleted if keep_artifacts=False
  story_clean.txt      <- deleted if keep_artifacts=False
```

---

## Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Create a new "script" application
3. Note your `client_id` and `client_secret`
4. Pass them to `PyReelConfig`

---

## B-Roll

PyReel uses a local video file as b-roll. Point `broll_local_path` to any `.mp4` or `.mov` file:

```python
config = pyreel.PyReelConfig(
    broll_local_path="./data/broll/gameplay.mp4",
    ...
)
```

If `broll_local_path` is not set, PyReel auto-discovers the first `.mp4` or `.mov` in `./data/broll/` relative to the working directory.

---

## Resuming Interrupted Runs

PyReel uses a checkpoint system. If a run is interrupted, re-run with the same config and it will resume from the last completed stage — no re-processing already-completed steps.

---

## License

MIT — see [LICENSE](LICENSE)
