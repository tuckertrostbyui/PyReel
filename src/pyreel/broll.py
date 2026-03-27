import logging
import os
from datetime import datetime, timezone
from typing import Optional

from .config import BrollSource, PyReelConfig
from .exceptions import PyReelBrollError

logger = logging.getLogger(__name__)


def _write_attribution(
    run_dir: str,
    run_id: str,
    source: str,
    url: str,
    title: str,
    author: str,
) -> None:
    path = os.path.join(run_dir, "broll_sources.txt")
    ts = datetime.now(timezone.utc).isoformat()
    content = (
        f"PyReel B-Roll Attribution Log\n"
        f"Run: {run_id}\n"
        f"Generated: {ts}\n"
        f"\n"
        f"Source: {source}\n"
        f"URL: {url}\n"
        f"Title: {title}\n"
        f"Channel/Author: {author}\n"
        f"\n"
        f"DISCLAIMER: The user is solely responsible for ensuring they have the right\n"
        f"to use any downloaded content. yt-dlp footage from YouTube may be subject\n"
        f"to copyright. PyReel assumes no liability for copyright infringement.\n"
        f"Pexels and Pixabay content is used under their respective free licenses.\n"
    )
    with open(path, "w") as f:
        f.write(content)


def fetch_ytdlp(keyword: str, output_path: str, config: PyReelConfig, run_dir: str) -> str:
    try:
        import yt_dlp
    except ImportError as e:
        raise PyReelBrollError("yt-dlp is not installed.") from e

    query = f"{keyword} no commentary"
    search_query = f"ytsearch{config.broll_candidates}:{query}"

    ydl_opts_info = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
        except Exception as e:
            raise PyReelBrollError(f"yt-dlp search failed: {e}") from e

    entries = info.get("entries", [])
    if not entries:
        raise PyReelBrollError("yt-dlp returned no search results.")

    valid = []
    for entry in entries:
        if not entry:
            continue
        if entry.get("availability") in ("private", "needs_auth"):
            continue
        if entry.get("age_limit", 0) > 0:
            continue
        duration = entry.get("duration") or 0
        if duration < config.broll_min_duration:
            continue
        valid.append(entry)

    valid.sort(key=lambda e: e.get("view_count") or 0, reverse=True)

    last_error = None
    for entry in valid:
        video_id = entry.get("id") or entry.get("url", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_title = entry.get("title", "N/A")
        video_author = entry.get("uploader") or entry.get("channel", "N/A")

        try:
            ydl_opts_dl = {
                "quiet": True,
                "no_warnings": True,
                "outtmpl": output_path,
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "merge_output_format": "mp4",
            }

            with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                ydl.download([video_url])

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                _write_attribution(
                    run_dir=run_dir,
                    run_id=os.path.basename(run_dir),
                    source="yt-dlp",
                    url=video_url,
                    title=video_title,
                    author=video_author,
                )
                return output_path

        except Exception as e:
            last_error = e
            logger.warning(f"yt-dlp download failed for {video_url}: {e}")
            continue

    raise PyReelBrollError(
        f"All yt-dlp candidates failed. Last error: {last_error}"
    )


def fetch_pexels(keyword: str, output_path: str, config: PyReelConfig, run_dir: str) -> str:
    if not config.pexels_api_key:
        raise PyReelBrollError("pexels_api_key is required for BrollSource.PEXELS.")

    try:
        import requests
    except ImportError as e:
        raise PyReelBrollError("requests is not installed.") from e

    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": config.pexels_api_key},
            params={"query": keyword, "per_page": 5, "orientation": "landscape"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise PyReelBrollError(f"Pexels API request failed: {e}") from e

    videos = data.get("videos", [])
    if not videos:
        raise PyReelBrollError(f"Pexels returned no videos for keyword: {keyword}")

    video = videos[0]
    files = video.get("video_files", [])
    if not files:
        raise PyReelBrollError("Pexels video has no downloadable files.")

    best = max(files, key=lambda f: f.get("width", 0) * f.get("height", 0))
    download_url = best.get("link")
    if not download_url:
        raise PyReelBrollError("Pexels video file has no download link.")

    video_title = f"Pexels video {video.get('id', 'N/A')}"
    video_author = video.get("user", {}).get("name", "N/A")

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with requests.get(download_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        raise PyReelBrollError(f"Pexels download failed: {e}") from e

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise PyReelBrollError("Pexels download produced empty file.")

    _write_attribution(
        run_dir=run_dir,
        run_id=os.path.basename(run_dir),
        source="pexels",
        url=download_url,
        title=video_title,
        author=video_author,
    )
    return output_path


def fetch_pixabay(keyword: str, output_path: str, config: PyReelConfig, run_dir: str) -> str:
    if not config.pixabay_api_key:
        raise PyReelBrollError("pixabay_api_key is required for BrollSource.PIXABAY.")

    try:
        import requests
    except ImportError as e:
        raise PyReelBrollError("requests is not installed.") from e

    try:
        resp = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": config.pixabay_api_key,
                "q": keyword,
                "per_page": 5,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise PyReelBrollError(f"Pixabay API request failed: {e}") from e

    hits = data.get("hits", [])
    if not hits:
        raise PyReelBrollError(f"Pixabay returned no videos for keyword: {keyword}")

    hit = hits[0]
    videos = hit.get("videos", {})
    large = videos.get("large", {})
    download_url = large.get("url")
    if not download_url:
        medium = videos.get("medium", {})
        download_url = medium.get("url")
    if not download_url:
        raise PyReelBrollError("Pixabay video has no large/medium download URL.")

    video_title = f"Pixabay video {hit.get('id', 'N/A')}"
    video_author = hit.get("user", "N/A")

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with requests.get(download_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        raise PyReelBrollError(f"Pixabay download failed: {e}") from e

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise PyReelBrollError("Pixabay download produced empty file.")

    _write_attribution(
        run_dir=run_dir,
        run_id=os.path.basename(run_dir),
        source="pixabay",
        url=download_url,
        title=video_title,
        author=video_author,
    )
    return output_path


def fetch_local(config: PyReelConfig, run_dir: str) -> str:
    if not config.broll_local_path:
        raise PyReelBrollError("broll_local_path is required for BrollSource.LOCAL.")

    path = config.broll_local_path
    if not os.path.exists(path):
        raise PyReelBrollError(f"broll_local_path does not exist: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in (".mp4", ".mov"):
        raise PyReelBrollError(
            f"broll_local_path must be .mp4 or .mov, got: {ext}"
        )

    _write_attribution(
        run_dir=run_dir,
        run_id=os.path.basename(run_dir),
        source="local",
        url=f"local file: {path}",
        title="N/A",
        author="N/A",
    )
    return path


def fetch_broll(keyword: str, run_dir: str, config: PyReelConfig) -> str:
    output_path = os.path.join(run_dir, "broll_raw.mp4")

    if config.broll_source == BrollSource.LOCAL:
        return fetch_local(config, run_dir)

    if config.broll_source == BrollSource.YTDLP:
        try:
            return fetch_ytdlp(keyword, output_path, config, run_dir)
        except PyReelBrollError as e:
            logger.warning(f"yt-dlp failed, trying Pexels: {e}")

        if config.pexels_api_key:
            try:
                return fetch_pexels(keyword, output_path, config, run_dir)
            except PyReelBrollError as e:
                logger.warning(f"Pexels failed, trying Pixabay: {e}")

        if config.pixabay_api_key:
            try:
                return fetch_pixabay(keyword, output_path, config, run_dir)
            except PyReelBrollError as e:
                logger.warning(f"Pixabay failed: {e}")

        raise PyReelBrollError(
            "All b-roll sources exhausted (yt-dlp, Pexels, Pixabay). "
            "Provide API keys or use BrollSource.LOCAL."
        )

    if config.broll_source == BrollSource.PEXELS:
        try:
            return fetch_pexels(keyword, output_path, config, run_dir)
        except PyReelBrollError as e:
            logger.warning(f"Pexels failed, trying Pixabay: {e}")

        if config.pixabay_api_key:
            try:
                return fetch_pixabay(keyword, output_path, config, run_dir)
            except PyReelBrollError as e:
                logger.warning(f"Pixabay failed: {e}")

        raise PyReelBrollError("Pexels (and Pixabay fallback) failed.")

    if config.broll_source == BrollSource.PIXABAY:
        return fetch_pixabay(keyword, output_path, config, run_dir)

    raise PyReelBrollError(f"Unknown broll_source: {config.broll_source}")
