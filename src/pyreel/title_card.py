import os
import sys
from typing import TYPE_CHECKING, Optional

from .exceptions import PyReelTitleCardError

if TYPE_CHECKING:
    from .config import PyReelConfig, TitleCardConfig

FRAME_W = 1080
FRAME_H = 1920
CARD_W = 860
PADDING = 30
CORNER = 20
AVATAR_D = 70


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_title_card_clip(
    title: str,
    author: str,
    config: "PyReelConfig",
    duration: Optional[float] = None,
) -> object:
    """Return a full-frame (1080x1920) RGBA moviepy ImageClip timed to [0, duration].

    The card is drawn on a transparent canvas so CompositeVideoClip alpha-composites
    it cleanly on top of the broll background.

    Args:
        duration: Explicit duration in seconds. If None, falls back to
                  config.title_card.duration. Pass the value returned by
                  calculate_title_duration() to sync the card with the TTS.
    """
    try:
        import numpy as np
        from moviepy import ImageClip
    except ImportError as e:
        raise PyReelTitleCardError("moviepy / numpy is required for title card rendering.") from e

    try:
        effective_duration = duration if duration is not None else config.title_card.duration
        pil_image = _draw_card_image(title, author, config.title_card)
        arr = np.array(pil_image)  # (1920, 1080, 4) RGBA uint8
        clip = ImageClip(arr).with_start(0).with_end(effective_duration)
        return clip
    except PyReelTitleCardError:
        raise
    except Exception as e:
        raise PyReelTitleCardError(f"Title card rendering failed: {e}") from e


def calculate_title_duration(title: str, alignment: dict) -> Optional[float]:
    """Return the timestamp (seconds) when the title finishes being spoken.

    Counts the words in `title` and finds the end time of the matching word
    in the alignment data. Returns None if the alignment doesn't have enough
    words (fall back to config.title_card.duration in that case).

    A small 0.4-second buffer is added so the card doesn't snap away at the
    exact instant the last title word ends.
    """
    if not title or not alignment:
        return None

    title_word_count = len(title.split())
    if title_word_count == 0:
        return None

    # Flatten all aligned words that have a valid end timestamp
    all_words = [
        w
        for seg in alignment.get("segments", [])
        for w in seg.get("words", [])
        if "end" in w
    ]

    if title_word_count > len(all_words):
        return None

    end_time = float(all_words[title_word_count - 1]["end"])
    return end_time + 0.4  # small trailing buffer


# ---------------------------------------------------------------------------
# Avatar image helper
# ---------------------------------------------------------------------------

def _paste_circular_image(canvas, image_path: str, x: int, y: int, diameter: int) -> None:
    """Load `image_path`, center-crop to a square, apply a circular mask, and
    paste the result onto `canvas` at pixel position (x, y)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return

    try:
        src = Image.open(image_path).convert("RGBA")
    except Exception:
        return  # Silently skip if the image can't be opened

    # Center-crop to square
    w, h = src.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    src = src.crop((left, top, left + side, top + side))

    # Resize to avatar diameter
    src = src.resize((diameter, diameter), Image.LANCZOS)

    # Build a circular mask
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (diameter, diameter)], fill=255)

    # Apply mask so only the circle is opaque
    src.putalpha(mask)

    # Paste onto the main canvas (the src already has alpha from the mask)
    canvas.paste(src, (x, y), src)


# ---------------------------------------------------------------------------
# Verified badge helper
# ---------------------------------------------------------------------------

def _paste_verified_badge(canvas, x: int, y: int, size: int) -> None:
    """Paste the bundled verified_check.png badge at (x, y) scaled to `size` px."""
    try:
        from importlib.resources import files
        from PIL import Image
        badge_path = files("pyreel").joinpath("assets/verified_check.png")
        badge = Image.open(badge_path).convert("RGBA")
        badge = badge.resize((size, size), Image.LANCZOS)
        canvas.paste(badge, (x, y), badge)
    except Exception:
        pass  # Silently skip if asset is unavailable


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def _draw_card_image(title: str, author: str, tc_cfg: "TitleCardConfig"):
    """Draw the Reddit-style card on a transparent 1080x1920 RGBA canvas."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as e:
        raise PyReelTitleCardError("Pillow is required for title card rendering. Install with: pip install pillow>=8.2.0") from e

    # ---- fonts -------------------------------------------------------
    font_title = _resolve_font(tc_cfg.font, 44)
    font_username = _resolve_font(tc_cfg.font, 26)
    font_engagement = _resolve_font(tc_cfg.font, 24)
    font_avatar = _resolve_font(tc_cfg.font, 30)
    font_emoji = _resolve_emoji_font(36) or _resolve_font(tc_cfg.font, 36)
    font_emoji_sm = _resolve_emoji_font(24) or font_engagement

    # ---- measure title height ----------------------------------------
    # We need card_h before we can draw, so measure text on a scratch surface.
    scratch = Image.new("RGBA", (CARD_W, 200), (0, 0, 0, 0))
    scratch_draw = ImageDraw.Draw(scratch)

    title_lines = _wrap_text(scratch_draw, title, font_title, CARD_W - 2 * PADDING)
    title_line_h = 56
    title_block_h = max(len(title_lines), 1) * title_line_h

    show_emoji = bool(tc_cfg.emoji_row)
    emoji_block_h = 50 if show_emoji else 0

    # header: avatar + username row
    header_h = AVATAR_D + 20          # avatar diameter + gap below
    engagement_h = 44
    card_h = (
        PADDING
        + header_h
        + emoji_block_h
        + 16
        + title_block_h
        + 20
        + engagement_h
        + PADDING
    )

    # ---- position card -----------------------------------------------
    card_x = (FRAME_W - CARD_W) // 2  # 110
    pos = (tc_cfg.card_position or "bottom").lower()
    if pos == "center":
        card_y = (FRAME_H - card_h) // 2
    elif pos == "top":
        card_y = 120
    else:  # "bottom"
        card_y = FRAME_H - card_h - 120

    # ---- main canvas -------------------------------------------------
    img = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ---- card background (white rounded rect) -------------------------
    draw.rounded_rectangle(
        [(card_x, card_y), (card_x + CARD_W, card_y + card_h)],
        radius=CORNER,
        fill=(255, 255, 255, 245),
    )

    # ---- avatar circle -----------------------------------------------
    ax = card_x + PADDING
    ay = card_y + PADDING
    avatar_color_rgb = _hex_to_rgb(tc_cfg.avatar_color)

    if tc_cfg.avatar_image:
        _paste_circular_image(img, tc_cfg.avatar_image, ax, ay, AVATAR_D)
    else:
        draw.ellipse([(ax, ay), (ax + AVATAR_D, ay + AVATAR_D)], fill=(*avatar_color_rgb, 255))
        # avatar initial
        initial = (author[0].upper() if author else "A")
        try:
            bbox = draw.textbbox((0, 0), initial, font=font_avatar)
            iw = bbox[2] - bbox[0]
            ih = bbox[3] - bbox[1]
        except Exception:
            iw, ih = 18, 24
        draw.text(
            (ax + (AVATAR_D - iw) // 2, ay + (AVATAR_D - ih) // 2),
            initial,
            font=font_avatar,
            fill=(255, 255, 255, 255),
        )

    # ---- username text -----------------------------------------------
    ux = ax + AVATAR_D + 14
    uy = card_y + PADDING + (AVATAR_D - 26) // 2  # vertically center in avatar height
    display_name = author if author else "Anonymous"
    draw.text((ux, uy), display_name, font=font_username, fill=(30, 30, 30, 255))

    # measure username width for checkmark placement
    try:
        ubbox = draw.textbbox((ux, uy), display_name, font=font_username)
        utext_w = ubbox[2] - ubbox[0]
    except Exception:
        utext_w = len(display_name) * 14

    # ---- verified checkmark -----------------------------------------
    if tc_cfg.show_verified:
        vx = ux + utext_w + 8
        vy = uy + 2
        vd = 26
        _paste_verified_badge(img, vx, vy, vd)

    # ---- emoji row ---------------------------------------------------
    cur_y = card_y + PADDING + header_h
    if show_emoji:
        try:
            # embedded_color=True reads color from the font's own color tables.
            # Do NOT pass fill here — it overrides the embedded color and causes boxes.
            draw.text(
                (card_x + PADDING, cur_y),
                tc_cfg.emoji_row,
                font=font_emoji,
                embedded_color=True,
            )
        except Exception:
            pass  # Silently skip if emoji rendering fails on this system
        cur_y += emoji_block_h

    cur_y += 16  # gap before title

    # ---- title text --------------------------------------------------
    for line in title_lines:
        draw.text(
            (card_x + PADDING, cur_y),
            line,
            font=font_title,
            fill=(20, 20, 20, 255),
        )
        cur_y += title_line_h

    # ---- engagement row (❤️ likes  💬 comments  ↗️ share) ----------
    eng_y = card_y + card_h - PADDING - engagement_h
    eng_x = card_x + PADDING
    # Each tuple: (emoji, label text)
    eng_items = [
        ("\u2764\ufe0f", tc_cfg.vote_count),   # ❤️
        ("\U0001f4ac", tc_cfg.vote_count),      # 💬
        ("\u2197\ufe0f", "Share"),              # ↗️
    ]
    for emoji_ch, label in eng_items:
        try:
            draw.text((eng_x, eng_y + 6), emoji_ch, font=font_emoji_sm, embedded_color=True)
        except Exception:
            pass
        eng_x += 28  # fixed width slot for emoji at ~20-24px bitmap
        draw.text((eng_x, eng_y + 10), label, font=font_engagement, fill=(100, 100, 100, 255))
        try:
            lbbox = draw.textbbox((eng_x, eng_y + 10), label, font=font_engagement)
            eng_x += int(lbbox[2] - lbbox[0]) + 22
        except Exception:
            eng_x += len(label) * 13 + 22

    return img


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _wrap_text(draw, text: str, font, max_width: int) -> list:
    """Word-wrap `text` to fit within `max_width` pixels. Returns list of lines."""
    if not text:
        return [""]

    words = text.split()
    lines = []
    current = ""

    for word in words:
        candidate = (current + " " + word).strip()
        try:
            w = draw.textlength(candidate, font=font)
        except Exception:
            w = len(candidate) * 24  # rough fallback
        if w <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines if lines else [""]


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _resolve_font(font_path: Optional[str], size: int):
    """Return a Pillow FreeTypeFont. Falls back through system paths to load_default()."""
    try:
        from PIL import ImageFont
    except ImportError:
        raise PyReelTitleCardError("Pillow is required for title card rendering.")

    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    # Try system sans-serif fonts
    candidates = []
    if sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    elif sys.platform.startswith("linux"):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    elif sys.platform == "win32":
        candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    return ImageFont.load_default()


def _resolve_emoji_font(size: int):
    """Try to load a color emoji font. Returns None if unavailable.

    Apple Color Emoji is a bitmap font with fixed SBIX sizes (20, 32, 40, 48,
    64, 96, 160). We snap to 40 on macOS to guarantee a clean bitmap match.
    """
    try:
        from PIL import ImageFont
    except ImportError:
        return None

    if sys.platform == "darwin":
        # Snap to the nearest supported SBIX bitmap size
        supported = [20, 32, 40, 48, 64, 96, 160]
        snap_size = min(supported, key=lambda s: abs(s - size))
        path = "/System/Library/Fonts/Apple Color Emoji.ttc"
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, snap_size, index=0)
            except Exception:
                return None

    elif sys.platform.startswith("linux"):
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/usr/share/fonts/noto/NotoColorEmoji.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue

    elif sys.platform == "win32":
        path = "C:/Windows/Fonts/seguiemj.ttf"
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                return None

    return None


# ---------------------------------------------------------------------------
# Color helper
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert '#RRGGBB' to (R, G, B) int tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (255, 69, 0)  # fallback Reddit orange
