import logging
import os
from typing import Optional

from .config import PyReelConfig
from .exceptions import PyReelBrollError

logger = logging.getLogger(__name__)


def _find_default_broll_video() -> Optional[str]:
    """Scan ./data/broll/ relative to the current working directory for the
    first .mp4 or .mov file. Requires scripts to be run from the project root.
    Set broll_local_path explicitly for a path-independent alternative."""
    broll_dir = os.path.join(os.getcwd(), "data", "broll")
    if not os.path.isdir(broll_dir):
        return None
    for fname in sorted(os.listdir(broll_dir)):
        if fname.lower().endswith((".mp4", ".mov")):
            return os.path.join(broll_dir, fname)
    return None


def fetch_broll(run_dir: str, config: PyReelConfig) -> str:
    if config.broll_local_path:
        path = config.broll_local_path
    else:
        discovered = _find_default_broll_video()
        if not discovered:
            raise PyReelBrollError(
                "No broll video found. Either place a .mp4 or .mov file in "
                "./data/broll/, or set broll_local_path in PyReelConfig."
            )
        path = discovered

    if not os.path.exists(path):
        raise PyReelBrollError(f"broll_local_path does not exist: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in (".mp4", ".mov"):
        raise PyReelBrollError(
            f"B-roll video must be .mp4 or .mov, got: {ext}"
        )

    logger.info("Using b-roll video: %s", path)
    return path
