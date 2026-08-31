"""Build the link preview card and the favicon out of the pieces themselves.

    python make-share-card.py /path/to/artwall-gallery

Writes share-card.png (1200x630, what Slack and the rest show) and
favicon.png / apple-touch-icon.png.
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MONO = "/System/Library/Fonts/SFNSMono.ttf"
CARD = (1200, 630)
CELL = 120
EYEBROW = "JETBRAINS  ×  ADEPTASK  ×  AQUION"
TITLE = "PyCon AU 2026 Code Art Wall"
SUB = ("Every piece here was written in Python and rendered from that code. "
       "Click one to read it.")
SUB_MAX = 1060      # the widest the line may run before it is broken in two


def stills(gallery: Path) -> list[Path]:
    """One image per piece: the still for an animated one, the piece itself
    for a static one."""
    media = gallery / "media"
    out = []
    for f in sorted(media.iterdir()):
        if f.name.endswith(".poster.jpg"):
            out.append(f)
        elif f.suffix == ".png":
            out.append(f)
    return out


def montage(images: list[Path], size: tuple[int, int]) -> Image.Image:
    cols = -(-size[0] // CELL)
    rows = -(-size[1] // CELL) + 1
    sheet = Image.new("RGB", (cols * CELL, rows * CELL), (0, 0, 0))
    picks = list(images)
    # Deterministic, so rebuilding the card does not reshuffle the artwork.
    random.Random(2026).shuffle(picks)
    for i in range(cols * rows):
        src = picks[i % len(picks)]
        try:
            tile = Image.open(src).convert("RGB")
        except Exception:
            continue
        tile.thumbnail((CELL, CELL), Image.LANCZOS)
        cell = Image.new("RGB", (CELL, CELL), (16, 16, 20))
        cell.paste(tile, ((CELL - tile.width) // 2, (CELL - tile.height) // 2))
        sheet.paste(cell, ((i % cols) * CELL, (i // cols) * CELL))
    # Centre-crop to the card, so the montage is not cut off at one edge only.
    left = (sheet.width - size[0]) // 2
    top = (sheet.height - size[1]) // 2
    return sheet.crop((left, top, left + size[0], top + size[1]))


def font(px: int):
    try:
        return ImageFont.truetype(MONO, px)
    except OSError:
        return ImageFont.load_default()


def centred(draw, y, text, f, fill):
    w = draw.textbbox((0, 0), text, font=f)[2]
    draw.text(((CARD[0] - w) // 2, y), text, font=f, fill=fill)


def wrapped(draw, text, f, limit):
    """Break on whole words at `limit` pixels. The card is a fixed size and
    the text is not, so a line that outgrows it has to fold rather than run
    off the edge."""
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=f)[2] > limit and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def share_card(gallery: Path) -> Path:
    card = montage(stills(gallery), CARD)
    # A scrim, or the artwork wins and the words are unreadable at the size
    # Slack actually renders this.
    scrim = Image.new("RGBA", CARD, (0, 0, 0, 170))
    card = Image.alpha_composite(card.convert("RGBA"), scrim)
    # Darker still behind the words themselves.
    band = Image.new("RGBA", CARD, (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle([0, 195, CARD[0], 435], fill=(0, 0, 0, 130))
    card = Image.alpha_composite(card, band).convert("RGB")

    draw = ImageDraw.Draw(card)
    centred(draw, 228, EYEBROW, font(23), (163, 152, 255))
    centred(draw, 281, TITLE, font(54), (255, 255, 255))
    # The one purple rule, as on the pages.
    draw.rectangle([CARD[0] // 2 - 46, 346, CARD[0] // 2 + 46, 349],
                   fill=(107, 87, 255))
    sub = font(23)
    for i, line in enumerate(wrapped(draw, SUB, sub, SUB_MAX)):
        centred(draw, 372 + i * 33, line, sub, (198, 198, 206))

    out = gallery / "share-card.png"
    card.save(out, "PNG", optimize=True)
    return out


def favicon(gallery: Path) -> list[Path]:
    """A 4x4 of pieces reduced to their average colour: a wall of art, at
    sixteen pixels."""
    picks = list(stills(gallery))
    random.Random(7).shuffle(picks)
    swatch = Image.new("RGB", (4, 4), (0, 0, 0))
    for i in range(16):
        try:
            im = Image.open(picks[i % len(picks)]).convert("RGB")
        except Exception:
            continue
        swatch.putpixel((i % 4, i // 4), im.resize((1, 1), Image.LANCZOS).getpixel((0, 0)))
    written = []
    for name, px in (("favicon.png", 256), ("apple-touch-icon.png", 180)):
        out = gallery / name
        swatch.resize((px, px), Image.NEAREST).save(out, "PNG", optimize=True)
        written.append(out)
    return written


if __name__ == "__main__":
    g = Path(sys.argv[1])
    card = share_card(g)
    print(f"{card.name}  {card.stat().st_size / 1024:.0f} KB  {Image.open(card).size}")
    for f in favicon(g):
        print(f"{f.name}  {f.stat().st_size / 1024:.0f} KB  {Image.open(f).size}")
