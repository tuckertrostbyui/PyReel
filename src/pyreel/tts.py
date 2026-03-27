import asyncio
import os
import subprocess
import tempfile

from .config import PyReelConfig
from .exceptions import PyReelTTSError


async def _async_generate(text: str, mp3_path: str, config: PyReelConfig) -> None:
    try:
        import edge_tts
    except ImportError as e:
        raise PyReelTTSError("edge-tts is not installed.") from e

    communicate = edge_tts.Communicate(
        text=text,
        voice=config.tts_voice,
        rate=config.tts_rate,
    )
    await communicate.save(mp3_path)


def generate_audio(text: str, output_path: str, config: PyReelConfig) -> str:
    mp3_fd, mp3_path = tempfile.mkstemp(suffix=".mp3")
    os.close(mp3_fd)

    try:
        asyncio.run(_async_generate(text, mp3_path, config))

        if not os.path.exists(mp3_path) or os.path.getsize(mp3_path) == 0:
            raise PyReelTTSError("edge-tts produced an empty or missing mp3 file.")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", mp3_path,
                "-ar", "16000",
                "-ac", "1",
                output_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise PyReelTTSError(
                f"ffmpeg conversion failed: {result.stderr}"
            )

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise PyReelTTSError("ffmpeg produced an empty or missing wav file.")

        return output_path

    except PyReelTTSError:
        raise
    except Exception as e:
        raise PyReelTTSError(f"TTS generation failed: {e}") from e
    finally:
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
