import hashlib
import json
import os
from dataclasses import asdict

from .exceptions import PyReelError

ARTIFACT_MAP = {
    "story_fetch": "story_raw.txt",
    "story_sanitize": "story_clean.txt",
    "story_prepare": "story_final.txt",
    "tts_generate": "audio.wav",
    "whisper_align": "alignment.json",
    "broll_fetch": "broll_raw.mp4",
    "broll_crop": "broll_cropped.mp4",
    "video_compose": "final_video.mp4",
    "metadata_generate": "metadata.json",
}

_CHECKPOINT_FILE = ".checkpoint"


def _checkpoint_path(run_dir: str) -> str:
    return os.path.join(run_dir, _CHECKPOINT_FILE)


def load_checkpoint(run_dir: str) -> dict | None:
    path = _checkpoint_path(run_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def save_checkpoint(run_dir: str, stage: str) -> None:
    os.makedirs(run_dir, exist_ok=True)
    path = _checkpoint_path(run_dir)
    data = load_checkpoint(run_dir) or {
        "run_id": os.path.basename(run_dir),
        "completed_stages": [],
        "failed_stage": None,
        "config_hash": None,
    }
    if stage not in data["completed_stages"]:
        data["completed_stages"].append(stage)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def stage_complete(run_dir: str, stage: str) -> bool:
    data = load_checkpoint(run_dir)
    if data is None:
        return False
    if stage not in data.get("completed_stages", []):
        return False

    artifact = ARTIFACT_MAP.get(stage)
    if artifact is None:
        return True

    artifact_path = os.path.join(run_dir, artifact)
    if not os.path.exists(artifact_path):
        return False
    if os.path.getsize(artifact_path) == 0:
        return False
    return True


def clear_checkpoint(run_dir: str) -> None:
    path = _checkpoint_path(run_dir)
    if os.path.exists(path):
        os.remove(path)


def compute_config_hash(config) -> str:
    try:
        data = json.dumps(asdict(config), sort_keys=True, default=str)
    except Exception:
        data = str(config)
    return hashlib.sha256(data.encode()).hexdigest()


def init_checkpoint(run_dir: str, run_id: str, config) -> None:
    os.makedirs(run_dir, exist_ok=True)
    path = _checkpoint_path(run_dir)
    data = {
        "run_id": run_id,
        "completed_stages": [],
        "failed_stage": None,
        "config_hash": compute_config_hash(config),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
