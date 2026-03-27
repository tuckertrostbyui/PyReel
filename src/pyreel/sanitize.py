import re

from .config import PyReelConfig
from .exceptions import PyReelError


def sanitize_text(text: str, config: PyReelConfig) -> str:
    text = _strip_reddit_formatting(text)
    text = _strip_markdown(text)
    if config.nsfw_filter:
        text = _filter_nsfw(text)
    return text


def _strip_reddit_formatting(text: str) -> str:
    # [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove bare URLs
    text = re.sub(
        r'https?://\S+',
        '',
        text
    )

    # Remove > blockquote markers (keep text)
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)

    # Remove **bold** asterisks
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # Remove *italic* asterisks
    text = re.sub(r'\*(.+?)\*', r'\1', text)

    # Remove ~~strikethrough~~
    text = re.sub(r'~~(.+?)~~', r'\1', text)

    # Remove r/subredditname references
    text = re.sub(r'r/\w+', '', text)

    # Remove u/username references
    text = re.sub(r'u/\w+', '', text)

    # Normalize whitespace and newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    return text


def _strip_markdown(text: str) -> str:
    try:
        from markdown_it import MarkdownIt
        md = MarkdownIt()
        tokens = md.parse(text)
        plain = _extract_text_from_tokens(tokens)
        if plain.strip():
            return plain.strip()
    except Exception:
        pass
    return text


def _extract_text_from_tokens(tokens) -> str:
    parts = []
    for token in tokens:
        if token.type == "inline" and token.children:
            for child in token.children:
                if child.type == "text" or child.type == "softbreak":
                    parts.append(child.content if child.type == "text" else " ")
        elif token.children:
            parts.append(_extract_text_from_tokens(token.children))
    return " ".join(p for p in parts if p.strip())


def _filter_nsfw(text: str) -> str:
    try:
        from better_profanity import profanity
        profanity.load_censor_words()
        return profanity.censor(text)
    except Exception:
        return text
