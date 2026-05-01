class PyReelError(Exception):
    pass


class PyReelPipelineError(PyReelError):
    pass


class PyReelConfigError(PyReelError):
    pass


class PyReelDepsError(PyReelError):
    pass


class PyReelRedditError(PyReelError):
    pass


class PyReelLLMError(PyReelError):
    pass


class PyReelTTSError(PyReelError):
    pass


class PyReelAlignError(PyReelError):
    pass


class PyReelBrollError(PyReelError):
    pass


class PyReelCropError(PyReelError):
    pass


class PyReelSubtitleError(PyReelError):
    pass


class PyReelComposeError(PyReelError):
    pass


class PyReelTitleCardError(PyReelError):
    pass


class PyReelHistoryError(PyReelError):
    pass


class PyReelStoryReadyError(PyReelError):
    """Raised when stop_after_story=True; signals the story is ready for voiceover recording."""
    def __init__(self, story_path: str, run_dir: str):
        self.story_path = story_path
        self.run_dir = run_dir
        super().__init__(
            f"Story ready at: {story_path}\n"
            f"Record your voiceover, then re-run with:\n"
            f"  voiceover_audio='<your_file>'\n"
            f"  run_dir='{run_dir}'"
        )
