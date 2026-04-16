# API Reference

Complete public API for PyReel v0.1.0. All symbols are importable directly from the `pyreel` namespace:

```python
import pyreel
```

---

## `generate()`

```python
pyreel.generate(
    subreddit: str | None = None,
    post_id:   str | None = None,
    prompt:    str | None = None,
    config:    PyReelConfig | None = None,
) -> list[str]
```

The main entry point. Runs the full PyReel pipeline and returns a list of absolute paths to the rendered `.mp4` file(s).

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `subreddit` | `str \| None` | Subreddit name (without `r/`). Required when `story_mode=StoryMode.FETCH`. |
| `post_id` | `str \| None` | Specific Reddit post ID (the alphanumeric string from the URL). If omitted with `StoryMode.FETCH`, a random top self-post is fetched from the subreddit. |
| `prompt` | `str \| None` | Text prompt passed to the LLM when `story_mode=StoryMode.LLM_WRITE`, or seed text for `LLM_SUMMARIZE`. |
| `config` | `PyReelConfig \| None` | Configuration object. If `None`, a default `PyReelConfig()` is used. |

### Returns

`list[str]` — File paths to rendered `.mp4` files. Contains one path in `SeriesMode.SINGLE` and one path per part in `SeriesMode.SPLIT`. Returns an empty list when `config.dry_run=True`.

### Raises

| Exception | When |
|-----------|------|
| `PyReelPipelineError` | Any pipeline stage fails. The stage name and root cause are included in the message. |
| `PyReelConfigError` | Invalid or incompatible config values detected before the pipeline starts. |
| `PyReelDepsError` | FFmpeg, ImageMagick, or Python version requirements not met. |

---

## `check_dependencies()`

```python
pyreel.check_dependencies(
    config: PyReelConfig | None = None,
) -> dict
```

Validates that all system and credential dependencies are available. Safe to call before `generate()` as a preflight check.

**Checks performed:**

- FFmpeg is on `PATH`
- ImageMagick `convert` is on `PATH`
- Python >= 3.11
- If `config.story_mode=StoryMode.FETCH`: Reddit credentials present
- If `config` uses an LLM mode: `llm_provider` and `llm_api_key` present
- If `config.broll_local_path` is set: path exists on disk

### Returns

`dict` with keys:

- `"passed"` (`bool`) — `True` if all checks pass.
- `"issues"` (`list[str]`) — Empty on success; human-readable failure descriptions on failure.

### Raises

`PyReelDepsError` — Raised (not just returned) if any check fails.

---

## `PyReelConfig`

The main configuration dataclass. All fields are optional with sensible defaults.

```python
config = pyreel.PyReelConfig(
    story_mode=pyreel.StoryMode.FETCH,
    reddit_client_id="...",
    reddit_client_secret="...",
    broll_local_path="./data/broll/gameplay.mp4",
)
```

### Story Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `story_mode` | `StoryMode` | `StoryMode.FETCH` | How the story text is acquired and processed. See [`StoryMode`](#storymode). |
| `series_mode` | `SeriesMode` | `SeriesMode.SINGLE` | Whether to produce one video or split a long story into multiple parts. See [`SeriesMode`](#seriesmode). |
| `min_duration` | `int \| None` | `None` | Minimum target video duration in seconds. Used as the lower word-count bound for LLM prompts. |
| `max_duration` | `int` | `60` | Maximum target video duration in seconds. Controls TTS pacing and LLM word-count targeting. |

### Reddit Fields

Required when `story_mode=StoryMode.FETCH`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `reddit_client_id` | `str \| None` | `None` | Reddit API client ID. Get one at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps). |
| `reddit_client_secret` | `str \| None` | `None` | Reddit API client secret. |
| `reddit_user_agent` | `str` | `"pyreel/0.1.0"` | User agent string sent with Reddit API requests. |

### LLM Fields

Required when `story_mode` is `LLM_REWRITE`, `LLM_WRITE`, or `LLM_SUMMARIZE`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `llm_provider` | `str \| None` | `None` | LiteLLM provider string, e.g. `"openai/gpt-4o"`, `"anthropic/claude-3-5-sonnet-20241022"`. |
| `llm_api_key` | `str \| None` | `None` | API key for the chosen LLM provider. |

### TTS Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tts_voice` | `str` | `"en-US-GuyNeural"` | Microsoft Edge TTS voice name. Any voice from the `edge-tts` voice list is valid. |
| `tts_rate` | `str` | `"+0%"` | TTS speaking rate modifier, e.g. `"+10%"` for faster, `"-10%"` for slower. |

### WhisperX Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `whisper_model` | `str` | `"base"` | WhisperX model size: `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large"`. Larger = more accurate, slower. |
| `whisper_device` | `str` | `"cpu"` | Inference device: `"cpu"` or `"cuda"`. |

### B-roll Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `broll_local_path` | `str \| None` | `None` | Path to a `.mp4` or `.mov` file to use as b-roll background footage. If `None`, PyReel auto-discovers the first `.mp4`/`.mov` in `./data/broll/` relative to the working directory. |

### Video Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `crop` | `CropConfig` | `CropConfig()` | Portrait crop configuration. See [`CropConfig`](#cropconfig). |
| `subtitle_style` | `SubtitleStyleConfig` | `SubtitleStyleConfig()` | Subtitle appearance configuration. See [`SubtitleStyleConfig`](#subtitlestyleconfig). |
| `burn_subtitles` | `bool` | `True` | Whether to burn karaoke subtitles into the video. |
| `title_card` | `TitleCardConfig` | `TitleCardConfig()` | Title card overlay configuration. See [`TitleCardConfig`](#titlecardconfig). |

### Output Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output_dir` | `str` | `"./output"` | Directory where run folders are created. Created automatically if it does not exist. |
| `keep_artifacts` | `bool` | `False` | If `True`, intermediate files (audio.wav, alignment.json, etc.) are kept after the run completes. |
| `nsfw_filter` | `bool` | `True` | Apply profanity/NSFW filter to story text during sanitization. |
| `dry_run` | `bool` | `False` | If `True`, validates dependencies and config only — no video is produced. Returns `[]`. |

---

## `SubtitleStyleConfig`

Controls the visual appearance of karaoke-style subtitles burned into the video.

```python
pyreel.SubtitleStyleConfig(
    style=pyreel.SubtitleStyle.BOLD_WHITE,
    font_size=80,
    active_color="white",
    inactive_color="#888888",
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `style` | `SubtitleStyle` | `SubtitleStyle.BOLD_WHITE` | The subtitle rendering style. See [`SubtitleStyle`](#subtitlestyle). |
| `font` | `str \| None` | `None` | Path to a `.ttf` font file. `None` uses the bundled Anton-Regular font. |
| `font_size` | `int` | `80` | Font size in pixels. |
| `active_color` | `str` | `"white"` | Color of the currently-spoken word. Accepts color names or hex strings. |
| `inactive_color` | `str` | `"#888888"` | Color of surrounding words (not active). |
| `outline_color` | `str` | `"black"` | Drop shadow / outline color. |
| `outline_width` | `int` | `3` | Outline thickness in pixels. |
| `position` | `str \| tuple` | `("center", 1350)` | Subtitle position. A string (`"center"`) or an `(x, y)` pixel tuple passed to MoviePy `with_position()`. |

---

## `CropConfig`

Controls how footage is cropped to 9:16 portrait (1080×1920).

```python
pyreel.CropConfig(
    strategy=pyreel.CropStrategy.CENTER,
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strategy` | `CropStrategy` | `CropStrategy.CENTER` | Crop strategy. See [`CropStrategy`](#cropstrategy). |
| `custom_x` | `int \| None` | `None` | Left-edge pixel of the 1080px crop window. Used only when `strategy=CropStrategy.CUSTOM`. |
| `custom_y` | `int \| None` | `None` | Top-edge pixel of the 1920px crop window. Used only when `strategy=CropStrategy.CUSTOM`. |

---

## `TitleCardConfig`

Controls the Reddit-style title card overlay shown at the start of each video.

```python
pyreel.TitleCardConfig(
    enabled=True,
    username="u/throwaway",
    avatar_color="#FF4500",
    card_position="bottom",
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | Show the title card. Set to `False` to skip it entirely. |
| `username` | `str \| None` | `None` | Display username. `None` uses the Reddit post author; falls back to `"Anonymous"`. |
| `avatar_color` | `str` | `"#FF4500"` | Avatar background color (Reddit orange by default). Ignored when `avatar_image` is set. |
| `avatar_image` | `str \| None` | `None` | Path to a custom image file for the avatar. Center-cropped to a circle. |
| `emoji_row` | `str` | `"🎭😱💔🤯🌟😤🔥"` | Emoji row shown below the username. Set to `""` to hide. |
| `vote_count` | `str` | `"99+"` | Upvote count displayed on the card. |
| `duration` | `float` | `5.0` | Seconds the title card is visible. Automatically overridden when alignment data can compute the exact title speech duration. |
| `font` | `str \| None` | `None` | Path to a `.ttf` font file. `None` auto-detects a system sans-serif font. |
| `show_verified` | `bool` | `True` | Show the Reddit verified badge next to the username. |
| `card_position` | `str` | `"bottom"` | Vertical position of the card: `"bottom"`, `"center"`, or `"top"`. |

---

## Enums

### `StoryMode`

Controls how the story text is acquired and processed.

| Value | Description |
|-------|-------------|
| `StoryMode.FETCH` | Fetch a post from Reddit via PRAW. Requires Reddit credentials. |
| `StoryMode.LLM_REWRITE` | Fetch a Reddit post, then rewrite it with an LLM for social-media pacing and hooks. Requires Reddit credentials and LLM config. |
| `StoryMode.LLM_WRITE` | Generate a completely original story from a `prompt` using an LLM. No Reddit credentials needed. |
| `StoryMode.LLM_SUMMARIZE` | Fetch a Reddit post and summarize it to fit within `max_duration`. Requires Reddit credentials and LLM config. |

### `SeriesMode`

| Value | Description |
|-------|-------------|
| `SeriesMode.SINGLE` | Produce one video. |
| `SeriesMode.SPLIT` | Use an LLM to split the story into natural cliffhanger parts and produce one video per part. Requires an LLM provider. |

### `SubtitleStyle`

| Value | Description |
|-------|-------------|
| `SubtitleStyle.BOLD_WHITE` | Bold white text with a black outline. The active word is bright white; surrounding words are dimmed. |
| `SubtitleStyle.HIGHLIGHT` | Active word is highlighted with a colored background box. |
| `SubtitleStyle.ALLCAPS` | All subtitle text is rendered in uppercase with a shadow effect. |
| `SubtitleStyle.ROLLING` | Pairs of consecutive words shown together, rolling forward as the narration progresses. |

### `CropStrategy`

| Value | Description |
|-------|-------------|
| `CropStrategy.CENTER` | Center-crop the footage to 1080×1920. Best for most landscape videos. |
| `CropStrategy.CUSTOM` | Crop from a specific pixel coordinate. Set `CropConfig.custom_x` and `custom_y`. |

---

## Exceptions

All PyReel exceptions inherit from `PyReelError`.

```
PyReelError
├── PyReelPipelineError   # A pipeline stage failed (wraps the stage-level cause)
├── PyReelConfigError     # Invalid or incompatible configuration
├── PyReelDepsError       # Missing system dependency (FFmpeg, ImageMagick, Python version)
├── PyReelRedditError     # Reddit API fetch failed (auth error, no suitable posts)
├── PyReelLLMError        # LLM call failed (rate limit, bad key, provider error)
├── PyReelTTSError        # Edge TTS synthesis failed
├── PyReelAlignError      # WhisperX alignment failed
├── PyReelBrollError      # B-roll file not found or unreadable
├── PyReelCropError       # Portrait crop failed
├── PyReelSubtitleError   # Subtitle rendering failed
├── PyReelComposeError    # MoviePy video composition failed
└── PyReelTitleCardError  # Title card rendering failed
```

Catch `PyReelError` to handle all pipeline failures in one `except` clause, or catch specific subclasses for targeted recovery.

```python
import pyreel

try:
    paths = pyreel.generate(subreddit="AmItheAsshole", config=config)
except pyreel.PyReelDepsError as e:
    print(f"Missing dependency: {e}")
except pyreel.PyReelRedditError as e:
    print(f"Reddit fetch failed: {e}")
except pyreel.PyReelError as e:
    print(f"Pipeline error: {e}")
```
