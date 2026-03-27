# PyReel Roadmap

## v0.1.0 (Current)

- Reddit post fetching and text sanitization
- Edge TTS speech synthesis
- WhisperX word-level alignment
- B-roll fetching (yt-dlp, Pexels, Pixabay, local)
- 9:16 portrait crop
- Karaoke-style subtitle styles (BOLD_WHITE, HIGHLIGHT, ALLCAPS, ROLLING)
- MoviePy video composition
- LLM rewrite/summarize/split/write via LiteLLM (opt-in)
- Checkpoint-based resumable pipeline
- Metadata bundle output

---

## v2 Features (NOT in v1 — planned for future releases)

The following features are explicitly **not implemented** in v0.1.0. They are documented here for roadmap planning only.

### 1. Post Deduplication Tracking
SQLite database at `~/.pyreel/history.db` logging `post_id`, `subreddit`, `timestamp`, `output_path`, `run_id` per `account_id`. `generate()` will accept an optional `account_id: str` parameter. Already-used posts will be skipped automatically to prevent duplicate content.

### 2. Auto-Posting
- **YouTube Shorts** via YouTube Data API v3
- **Instagram Reels** via Meta Graph API (requires Business/Creator account)
- **TikTok** via browser automation + cookies (documented as experimental and fragile)

### 3. Background Music Layer
Pixabay music API integration. Fixed volume mixing via FFmpeg `amix` filter. Configurable `music_volume` float `0.0–1.0`.

### 4. Automatic Audio Ducking
Reduce music volume when narration is active via FFmpeg `sidechaincompress` filter.

### 5. Smart Crop
OpenCV motion/activity detection to find the most visually active frame region for crop centering — replacing the static CENTER strategy.

### 6. ElevenLabs TTS
Premium voice option with native word-level timestamps, removing the need for the WhisperX alignment pass entirely.

### 7. Video Series Scheduler
Given a subreddit list and posting schedule, auto-queue generation on a cron-style schedule.
