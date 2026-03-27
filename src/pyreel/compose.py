import os

from .config import PyReelConfig
from .exceptions import PyReelComposeError

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920


def compose_video(
    broll_path: str,
    audio_path: str,
    subtitle_clips: list,
    output_path: str,
    config: PyReelConfig,
) -> str:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
        import moviepy.video.fx.all as vfx
    except ImportError as e:
        raise PyReelComposeError("moviepy is not installed.") from e

    try:
        audio = AudioFileClip(audio_path)
        audio_duration = audio.duration

        broll = VideoFileClip(broll_path)
        broll_duration = broll.duration

        if broll_duration < audio_duration:
            broll = broll.fx(vfx.loop, duration=audio_duration)
        else:
            broll = broll.subclipped(0, audio_duration)

        broll = broll.with_audio(audio)

        all_clips = [broll] + list(subtitle_clips)
        final = CompositeVideoClip(all_clips, size=(TARGET_WIDTH, TARGET_HEIGHT))
        final = final.with_duration(audio_duration)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="medium",
            bitrate="4000k",
            logger=None,
        )

        audio.close()
        broll.close()
        final.close()

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise PyReelComposeError("Compose produced empty or missing output file.")

        return output_path

    except PyReelComposeError:
        raise
    except Exception as e:
        raise PyReelComposeError(f"Video composition failed: {e}") from e
