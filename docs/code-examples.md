# Code Examples

End-to-end examples for the most common PyReel workflows.
All examples assume `pip install pyreel` and system dependencies (FFmpeg, ImageMagick) installed.

---

## Basic Reddit Fetch

The simplest real-world invocation — fetch a random top post from a subreddit and render it over a local video file.

```python
import pyreel

config = pyreel.PyReelConfig(
    reddit_client_id="YOUR_CLIENT_ID",
    reddit_client_secret="YOUR_CLIENT_SECRET",
    story_mode=pyreel.StoryMode.FETCH,
    max_duration=60,
    broll_local_path="./data/broll/gameplay.mp4",
    output_dir="./output",
)

paths = pyreel.generate(subreddit="AmItheAsshole", config=config)
print(f"Video: {paths[0]}")
```

!!! tip "Auto-discovery"

    If `broll_local_path` is not set, PyReel looks for the first `.mp4` or `.mov` file
    in `./data/broll/` relative to where your script is run.

---

## Fetch a Specific Post by ID

Pass `post_id` to target a specific Reddit submission (the alphanumeric ID from the URL):

```python
paths = pyreel.generate(
    subreddit="tifu",
    post_id="abc123",   # from reddit.com/r/tifu/comments/abc123/...
    config=config,
)
```

---

## LLM Rewrite

Fetch a Reddit post and rewrite it with an LLM for better pacing, hooks, and social-media style.
Requires an LLM provider and API key.

```python
import pyreel

config = pyreel.PyReelConfig(
    reddit_client_id="YOUR_CLIENT_ID",
    reddit_client_secret="YOUR_CLIENT_SECRET",

    story_mode=pyreel.StoryMode.LLM_REWRITE,
    llm_provider="openai/gpt-4o",
    llm_api_key="sk-...",

    max_duration=60,
    broll_local_path="./data/broll/minecraft.mp4",
    output_dir="./output",
)

paths = pyreel.generate(subreddit="AmItheAsshole", config=config)
```

!!! note "Provider-agnostic"

    `llm_provider` follows the [LiteLLM](https://docs.litellm.ai/docs/providers) naming convention.
    Examples: `"openai/gpt-4o"`, `"anthropic/claude-3-5-sonnet-20241022"`, `"gemini/gemini-1.5-pro"`.

---

## LLM-Generated Story (no Reddit)

Generate a completely original story from a prompt — no Reddit credentials needed.

```python
import pyreel

config = pyreel.PyReelConfig(
    story_mode=pyreel.StoryMode.LLM_WRITE,
    llm_provider="anthropic/claude-3-5-sonnet-20241022",
    llm_api_key="sk-ant-...",

    max_duration=45,
    broll_local_path="./data/broll/city.mp4",
    output_dir="./output",
)

paths = pyreel.generate(
    prompt="Write a dramatic AITA story about a wedding cake disaster",
    config=config,
)
```

---

## Subtitle Styles

PyReel supports four karaoke subtitle styles. Use `SubtitleStyleConfig` to pick and customize one.

=== "BOLD_WHITE"

    ```python
    import pyreel

    config = pyreel.PyReelConfig(
        ...,
        subtitle_style=pyreel.SubtitleStyleConfig(
            style=pyreel.SubtitleStyle.BOLD_WHITE,
            font_size=80,
            active_color="white",
            inactive_color="#888888",
            outline_color="black",
            outline_width=3,
            position=("center", 1350),
        ),
    )
    ```

=== "HIGHLIGHT"

    ```python
    config = pyreel.PyReelConfig(
        ...,
        subtitle_style=pyreel.SubtitleStyleConfig(
            style=pyreel.SubtitleStyle.HIGHLIGHT,
            font_size=72,
            active_color="yellow",
            inactive_color="white",
        ),
    )
    ```

=== "ALLCAPS"

    ```python
    config = pyreel.PyReelConfig(
        ...,
        subtitle_style=pyreel.SubtitleStyleConfig(
            style=pyreel.SubtitleStyle.ALLCAPS,
            font_size=80,
            active_color="white",
        ),
    )
    ```

=== "ROLLING"

    ```python
    config = pyreel.PyReelConfig(
        ...,
        subtitle_style=pyreel.SubtitleStyleConfig(
            style=pyreel.SubtitleStyle.ROLLING,
            font_size=68,
            active_color="white",
            inactive_color="#666666",
        ),
    )
    ```

---

## Title Card Customization

The Reddit-style title card is shown at the start of each video. Customize it with `TitleCardConfig`.

```python
import pyreel

config = pyreel.PyReelConfig(
    ...,
    title_card=pyreel.TitleCardConfig(
        enabled=True,
        username="u/throwaway_legal",
        avatar_color="#0079D3",     # Reddit blue
        emoji_row="😱🔥💔",
        vote_count="47.2k",
        duration=5.0,
        card_position="bottom",
        show_verified=False,
    ),
)
```

Use a custom avatar image instead of the colored circle:

```python
title_card=pyreel.TitleCardConfig(
    avatar_image="./assets/avatar.png",
    username="StoryTime",
),
```

Disable the title card entirely:

```python
title_card=pyreel.TitleCardConfig(enabled=False),
```

---

## Multi-Part Series

For long Reddit posts that exceed `max_duration`, use `SeriesMode.SPLIT` to automatically split the
story into parts using an LLM and produce one video per part.

```python
import pyreel

config = pyreel.PyReelConfig(
    reddit_client_id="YOUR_CLIENT_ID",
    reddit_client_secret="YOUR_CLIENT_SECRET",

    story_mode=pyreel.StoryMode.LLM_REWRITE,
    series_mode=pyreel.SeriesMode.SPLIT,

    llm_provider="openai/gpt-4o",
    llm_api_key="sk-...",

    max_duration=60,
    broll_local_path="./data/broll/subway_surfers.mp4",
    output_dir="./output",
)

paths = pyreel.generate(subreddit="tifu", config=config)

for i, path in enumerate(paths, 1):
    print(f"Part {i}: {path}")
```

!!! note

    `SeriesMode.SPLIT` requires an LLM provider — the split is performed by the LLM.
    It cannot be used with `StoryMode.FETCH` alone.

---

## Custom Crop

Override the default center-crop with a specific pixel origin:

```python
import pyreel

config = pyreel.PyReelConfig(
    ...,
    crop=pyreel.CropConfig(
        strategy=pyreel.CropStrategy.CUSTOM,
        custom_x=420,   # left edge of the 1080px wide crop window
        custom_y=0,     # top edge
    ),
)
```

The output crop window is always 1080×1920 pixels; `custom_x` and `custom_y` set the top-left origin.

---

## Multi-Account Post History

When running multiple themed accounts, use `history_file` to prevent the same Reddit post from appearing twice. PyReel automatically skips already-used posts and records each new post after a successful run.

```python
# accounts/amitheasshole/generate.py
import pyreel

config = pyreel.PyReelConfig(
    reddit_client_id="YOUR_CLIENT_ID",
    reddit_client_secret="YOUR_CLIENT_SECRET",
    story_mode=pyreel.StoryMode.LLM_REWRITE,
    llm_provider="openai/gpt-4o",
    llm_api_key="sk-...",
    history_file="./history.json",   # one file per account folder
    max_duration=60,
    broll_local_path="./data/broll/gameplay.mp4",
    output_dir="./output",
)

paths = pyreel.generate(subreddit="AmItheAsshole", config=config)
# history.json is created on first run and updated after each successful video
```

!!! tip "One history file per account"

    Keep each account's `history.json` inside its own folder. Posts used for your
    AITA account are tracked separately from your spooky-stories account.

### Inspecting history

```python
import pyreel

history = pyreel.load_history("./accounts/amitheasshole/history.json")

print(f"{len(history.used_ids)} posts used so far")

# Check if a specific post is already in history
if history.contains("abc123"):
    print("Already used")
```

### Resetting history

```python
import pyreel

# Clear all entries — posts can be reused after this
pyreel.clear_history("./accounts/amitheasshole/history.json")
```

### Handling exhausted history

When all 25 hot posts in a subreddit are already in history, `generate()` raises `PyReelHistoryError`:

```python
import pyreel

try:
    paths = pyreel.generate(subreddit="AmItheAsshole", config=config)
except pyreel.PyReelHistoryError:
    print("Ran out of new posts — try again later or clear the history.")
```

---

## Dry Run

Validate dependencies and configuration without producing any video:

```python
import pyreel

config = pyreel.PyReelConfig(
    reddit_client_id="YOUR_CLIENT_ID",
    reddit_client_secret="YOUR_CLIENT_SECRET",
    broll_local_path="./data/broll/gameplay.mp4",
    dry_run=True,
)

result = pyreel.generate(subreddit="AmItheAsshole", config=config)
# result is []
# PyReel logs: [PyReel dry_run] Dependencies OK. Run directory: ./output/run_...
```

Use `dry_run=True` in CI/CD or before a production run to confirm the environment is correctly configured.

---

## Pipeline Stage Diagram

```mermaid
graph LR
    A[deps_check] --> B[story_fetch]
    B --> C[story_sanitize]
    C --> D[story_prepare]
    D --> E[tts_generate]
    E --> F[whisper_align]
    F --> G[broll_fetch]
    G --> H[broll_crop]
    H --> I[subtitles_render]
    I --> J[title_card_render]
    J --> K[video_compose]
    K --> L[metadata_generate]
    L --> M[output_finalize]
```

PyReel's checkpoint system records each completed stage to a `.checkpoint` file in the run directory.
If a run is interrupted at any stage, re-running with the same config resumes automatically from where it left off.
