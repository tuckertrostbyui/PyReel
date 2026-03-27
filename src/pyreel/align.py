import json
import os

from .config import PyReelConfig
from .exceptions import PyReelAlignError


def align_audio(audio_path: str, output_path: str, config: PyReelConfig) -> dict:
    try:
        import whisperx
    except ImportError as e:
        raise PyReelAlignError("whisperx is not installed.") from e

    try:
        audio = whisperx.load_audio(audio_path)

        model = whisperx.load_model(
            config.whisper_model,
            config.whisper_device,
            compute_type="int8",
        )

        result = model.transcribe(audio)

        language_code = result.get("language", "en")

        align_model, metadata = whisperx.load_align_model(
            language_code=language_code,
            device=config.whisper_device,
        )

        aligned = whisperx.align(
            result["segments"],
            align_model,
            metadata,
            audio,
            config.whisper_device,
            return_char_alignments=False,
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(aligned, f, indent=2)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise PyReelAlignError("alignment.json is empty or missing after write.")

        return aligned

    except PyReelAlignError:
        raise
    except Exception as e:
        raise PyReelAlignError(f"WhisperX alignment failed: {e}") from e
