# PyReel

Automate short-form vertical video creation for TikTok, Instagram Reels, and YouTube Shorts.

Given a Reddit post (or an LLM-generated story), PyReel:
- Sanitizes and optionally rewrites the text via LLM
- Converts it to speech using Microsoft Edge TTS
- Aligns word-level timestamps via WhisperX
- Downloads b-roll footage (YouTube via yt-dlp, or Pexels/Pixabay as fallback)
- Crops footage to 9:16 portrait
- Burns karaoke-style word-by-word subtitles
- Outputs a fully rendered `.mp4` + structured metadata bundle ready for upload

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
pip install pyreel
```

Or with uv:
```bash
uv add pyreel
```

---

## Quick Start

### Check dependencies first

```python
import pyreel

pyreel.check_dependencies()
```

### Basic usage (Reddit fetch + yt-dlp b-roll)

```python
import pyreel

pyreel.check_dependencies()

config = pyreel.PyReelConfig(
    reddit_client_id="your_client_id",
    reddit_client_secret="your_client_secret",
    story_mode=pyreel.StoryMode.FETCH,
    max_duration=60,
    broll_source=pyreel.BrollSource.YTDLP,
    broll_keyword="minecraft parkour no commentary",
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
    broll_source=pyreel.BrollSource.PEXELS,
    pexels_api_key="your_pexels_key",
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
    broll_source=pyreel.BrollSource.YTDLP,
    broll_keyword="subway surfers gameplay",
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
output/run_20240325_143022_aita-neighbour/
  final_video.mp4      <- always kept
  metadata.json        <- always kept
  story_final.txt      <- always kept
  broll_sources.txt    <- always kept
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

## B-Roll Sources

| Source | Config | Notes |
|--------|--------|-------|
| `BrollSource.YTDLP` | `broll_keyword` | Downloads from YouTube. See Legal Notice. |
| `BrollSource.PEXELS` | `pexels_api_key` | Free license, attribution in broll_sources.txt |
| `BrollSource.PIXABAY` | `pixabay_api_key` | Free license, attribution in broll_sources.txt |
| `BrollSource.LOCAL` | `broll_local_path` | Your own video file (.mp4 or .mov) |

PyReel tries sources in order: yt-dlp -> Pexels -> Pixabay. If all fail, raises `PyReelBrollError`.

---

## Legal Notice

**You are solely responsible for ensuring you have the right to use any downloaded content.**

- **YouTube / yt-dlp**: Content downloaded via yt-dlp from YouTube may be subject to copyright. Check the video's license before use. Many creators do not permit redistribution. PyReel assumes no liability for copyright infringement. Review YouTube's Terms of Service and the creator's license before publishing any video.
- **Pexels**: Content is used under the [Pexels License](https://www.pexels.com/license/). Attribution is written to `broll_sources.txt` automatically.
- **Pixabay**: Content is used under the [Pixabay License](https://pixabay.com/service/license/). Attribution is written to `broll_sources.txt` automatically.

PyReel writes a `broll_sources.txt` file on every run regardless of source. Review it before publishing any content.

---

## Resuming Interrupted Runs

PyReel uses a checkpoint system. If a run is interrupted, re-run with the same config and it will resume from the last completed stage — no re-downloading b-roll or re-rendering already-completed steps.

---

## License

MIT — see [LICENSE](LICENSE)
