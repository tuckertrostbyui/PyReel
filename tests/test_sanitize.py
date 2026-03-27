import pytest
from unittest.mock import patch, MagicMock

from pyreel.config import PyReelConfig
from pyreel.sanitize import sanitize_text, _strip_reddit_formatting


class TestStripRedditFormatting:
    def test_markdown_link_stripped(self):
        text = "Check out [this post](https://reddit.com/r/foo/bar)"
        result = _strip_reddit_formatting(text)
        assert "this post" in result
        assert "https://" not in result
        assert "[" not in result

    def test_bare_url_removed(self):
        text = "Visit https://example.com for more info"
        result = _strip_reddit_formatting(text)
        assert "https://" not in result
        assert "for more info" in result

    def test_blockquote_marker_removed_text_preserved(self):
        text = "> This is a quote\nNormal text"
        result = _strip_reddit_formatting(text)
        assert ">" not in result
        assert "This is a quote" in result
        assert "Normal text" in result

    def test_bold_asterisks_removed(self):
        text = "This is **bold** text"
        result = _strip_reddit_formatting(text)
        assert "**" not in result
        assert "bold" in result

    def test_italic_asterisks_removed(self):
        text = "This is *italic* text"
        result = _strip_reddit_formatting(text)
        assert "*" not in result
        assert "italic" in result

    def test_strikethrough_removed_text_preserved(self):
        text = "This is ~~strikethrough~~ text"
        result = _strip_reddit_formatting(text)
        assert "~~" not in result
        assert "strikethrough" in result

    def test_subreddit_reference_removed(self):
        text = "I posted in r/AmItheAsshole yesterday"
        result = _strip_reddit_formatting(text)
        assert "r/AmItheAsshole" not in result
        assert "I posted in" in result

    def test_username_reference_removed(self):
        text = "Thanks to u/someuser for the help"
        result = _strip_reddit_formatting(text)
        assert "u/someuser" not in result
        assert "Thanks to" in result

    def test_whitespace_normalized(self):
        text = "word1    word2\n\n\n\nword3"
        result = _strip_reddit_formatting(text)
        assert "    " not in result
        assert "\n\n\n" not in result


class TestSanitizeText:
    def setup_method(self):
        self.config = PyReelConfig(nsfw_filter=False)
        self.config_nsfw = PyReelConfig(nsfw_filter=True)

    def test_markdown_link_in_full_pipeline(self):
        text = "I saw [something crazy](https://example.com) happen today."
        result = sanitize_text(text, self.config)
        assert "https://" not in result
        assert "something crazy" in result

    def test_reddit_formatting_stripped(self):
        text = "**Bold** and *italic* and r/subreddit and u/user"
        result = sanitize_text(text, self.config)
        assert "**" not in result
        assert "r/subreddit" not in result
        assert "u/user" not in result

    def test_nsfw_filter_calls_profanity_censor(self):
        text = "This is clean text."
        with patch("better_profanity.profanity.censor", return_value="This is clean text.") as mock_censor:
            with patch("better_profanity.profanity.load_censor_words"):
                result = sanitize_text(text, self.config_nsfw)
        mock_censor.assert_called_once()

    def test_nsfw_filter_disabled_does_not_censor(self):
        text = "Some text here."
        with patch("better_profanity.profanity.censor") as mock_censor:
            result = sanitize_text(text, self.config)
        mock_censor.assert_not_called()

    def test_profanity_replaced_not_deleted(self):
        from better_profanity import profanity
        text = "This is a test sentence."
        with patch("better_profanity.profanity.censor", return_value="This is a **** sentence.") as mock_censor:
            with patch("better_profanity.profanity.load_censor_words"):
                result = sanitize_text(text, self.config_nsfw)
        assert result == "This is a **** sentence."

    def test_empty_string(self):
        result = sanitize_text("", self.config)
        assert isinstance(result, str)

    def test_plain_text_unchanged_structure(self):
        text = "I went to the store today and bought some groceries."
        result = sanitize_text(text, self.config)
        assert "store" in result
        assert "groceries" in result
