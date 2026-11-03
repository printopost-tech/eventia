#!/usr/bin/env python3
"""Render the transparent 1080x1920 overlay states for the Eventia Pujo promo Reel.

States (one PNG each, swapped in on hard cuts by build.py):
  title.png   logo + "Durga Puja" + "It's not just a Festival, it's our Emotion 🥹"
  help_1..3   logo + "How Eventia can help you" + one benefit card (1/3, 2/3, 3/3)
  cta.png     end card: headline, "Reach out to us for such packages", BOOK NOW, phone

Usage: python3 overlays.py OUT_DIR
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "reel" / "assets" / "fonts"
LOGO = HERE.parent / "reel" / "assets" / "image1.png"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

W, H = 1080, 1920
CX = W // 2
# Reels UI: keep text out of the top ~120px status/header and the bottom
# ~300px caption/buttons, and away from the right-hand action rail.
SAFE_BOTTOM = H - 300

CRIMSON = (139, 14, 28)
MAROON_DARK = (70, 4, 12)
GOLD = (201, 162, 75)
GOLD_LIGHT = (240, 214, 140)
SAFFRON = (247, 186, 22)      # the reference's flat golden-yellow title
CREAM = (255, 244, 220)
WHITE = (255, 255, 255)
SHADOW = (8, 6, 20)

PHONE = "+91 74390 12840"
BENEFITS = [
    ("directions_bus", "Pickup & drop", "included, so you just enjoy"),
    ("temple_hindu", "Handpicked pandals", "one smooth, curated trail"),
    ("restaurant", "Rajbari visit", "+ traditional Mahabhog lunch"),
]


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def icon_font(size):
    return font("MaterialSymbolsRounded-Filled.ttf", size)


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def gradient(size, top, bottom):
    w, h = size
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        col.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return col.resize((w, h))


def commit(canvas, lay, blur=6, offset=(0, 3), strength=2.2):
    """Composite a layer with a soft dark drop shadow (keeps text legible on busy footage)."""
    a = lay.getchannel("A")
    sh = Image.new("L", canvas.size, 0)
    sh.paste(a, offset)
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * strength)))
    shadow = Image.new("RGBA", canvas.size, SHADOW + (0,))
    shadow.putalpha(sh)
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(lay)


def scrim(canvas, stops):
    """Black overlay whose alpha follows (y, alpha) keypoints, smoothstepped."""
    col = Image.new("L", (1, H), 0)
    for y in range(H):
        for (y0, a0), (y1, a1) in zip(stops, stops[1:]):
            if y0 <= y <= y1:
                t = (y - y0) / max(y1 - y0, 1)
                t = t * t * (3 - 2 * t)
                col.putpixel((0, y), round(255 * (a0 + (a1 - a0) * t)))
                break
    band = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    band.putalpha(col.resize((W, H)))
    canvas.alpha_composite(band)


def gold_fill(lay, top=CREAM, bottom=GOLD_LIGHT):
    box = lay.getbbox()
    g = gradient((box[2] - box[0], box[3] - box[1]), top, bottom).convert("RGBA")
    g.putalpha(lay.crop(box).getchannel("A"))
    out = layer()
    out.paste(g, box[:2])
    return out


def cap_height(fnt):
    return -fnt.getbbox("H", anchor="ls")[1]


def text_c(canvas, y, s, fnt, fill, grad=None, blur=6, tracking=0):
    """Centred line with cap-top at y. Returns baseline."""
    lay = layer()
    d = ImageDraw.Draw(lay)
    base = y + cap_height(fnt)
    if tracking:
        ws = [d.textlength(c, font=fnt) for c in s]
        x = CX - (sum(ws) + tracking * (len(s) - 1)) / 2
        for c, cw in zip(s, ws):
            d.text((x, base), c, font=fnt, fill=fill, anchor="ls")
            x += cw + tracking
    else:
        d.text((CX, base), s, font=fnt, fill=fill, anchor="ms")
    if grad:
        lay = gold_fill(lay, *grad)
    commit(canvas, lay, blur=blur)
    return base


def emoji(size_px):
    """Noto Color Emoji only renders at 109px; draw there and scale down."""
    f = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10, 10), "\U0001F979", font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((size_px, round(im.height * size_px / im.width)), Image.LANCZOS)


def logo(canvas, y, width):
    img = Image.open(LOGO).convert("RGBA")
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    lay = layer()
    lay.paste(img, (CX - width // 2, y))
    commit(canvas, lay, blur=8, offset=(0, 2), strength=3)
    return y + img.height


def top_block(canvas, heading):
    """Shared top band: scrim, logo, then either the title pair or the help heading."""
    scrim(canvas, [(0, 0.62), (430, 0.38), (620, 0.0), (H, 0.0)])
    y = logo(canvas, 130, 300)
    if heading == "title":
        base = text_c(canvas, y + 26, "Durga Puja", font("PlayfairDisplay-ExtraBold.ttf", 96), SAFFRON, blur=7)
        # subtitle + emoji on one centred line
        fnt = font("Lora-Bold.ttf", 42)
        s = "It’s not just a Festival, it’s our Emotion"
        em = emoji(46)
        lay = layer()
        d = ImageDraw.Draw(lay)
        tw = d.textlength(s, font=fnt)
        gap = 12
        x0 = CX - (tw + gap + em.width) / 2
        b2 = base + 30 + cap_height(fnt)
        d.text((x0, b2), s, font=fnt, fill=WHITE, anchor="ls")
        commit(canvas, lay, blur=5)
        canvas.alpha_composite(em, (round(x0 + tw + gap), round(b2 - cap_height(fnt) - 6)))
    else:
        base = text_c(canvas, y + 30, "How Eventia", font("PlayfairDisplay-ExtraBold.ttf", 88), SAFFRON, blur=7)
        text_c(canvas, base + 22, "can help you", font("PlayfairDisplay-Bold.ttf", 64), WHITE, blur=6)


def card(canvas, y, icon, title, sub, step):
    """Maroon glass card with gold border: big icon, title, sub-line and a step counter."""
    x0, x1 = 90, W - 90
    h = 210
    y1 = y + h
    body = gradient((x1 - x0, h), CRIMSON, MAROON_DARK).convert("RGBA")
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, h - 1], radius=36, fill=228)
    body.putalpha(mask)
    lay = layer()
    lay.paste(body, (x0, y))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0, y, x1, y1], radius=36, outline=GOLD + (255,), width=4)
    # icon disc
    cxi, cyi, r = x0 + 115, y + h // 2, 70
    d.ellipse([cxi - r, cyi - r, cxi + r, cyi + r], fill=GOLD_LIGHT + (255,))
    ic = icon_font(84)
    d.text((cxi, cyi), icon, font=ic, fill=MAROON_DARK + (255,), anchor="mm")
    tf = font("Lora-Bold.ttf", 58)
    sf = font("Lora-Medium.ttf", 38)
    tx = x0 + 225
    d.text((tx, y + 92), title, font=tf, fill=CREAM + (255,), anchor="ls")
    d.text((tx, y + 152), sub, font=sf, fill=GOLD_LIGHT + (255,), anchor="ls")
    # step dots
    for k in range(3):
        cx = tx + 6 + k * 30
        cy = y + 186
        rr = 7
        fill = (GOLD_LIGHT + (255,)) if k == step else (GOLD + (110,))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=fill)
    commit(canvas, lay, blur=14, offset=(0, 8), strength=1.6)


def pill(canvas, y, text, fnt, fill_top, fill_bottom, text_fill, icon=None, pad_x=56, pad_y=30, outline=GOLD):
    lay = layer()
    d = ImageDraw.Draw(lay)
    capw = cap_height(fnt)
    ic = icon_font(round(capw * 1.5)) if icon else None
    iw = d.textlength(icon, font=ic) + 18 if icon else 0
    tw = iw + d.textlength(text, font=fnt)
    x0, x1 = round(CX - tw / 2 - pad_x), round(CX + tw / 2 + pad_x)
    y1 = y + capw + 2 * pad_y
    body = gradient((x1 - x0, y1 - y), fill_top, fill_bottom).convert("RGBA")
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=(y1 - y) // 2, fill=255)
    body.putalpha(mask)
    lay.paste(body, (x0, y))
    if outline:
        d.rounded_rectangle([x0, y, x1, y1], radius=(y1 - y) // 2, outline=outline + (255,), width=4)
    x = CX - tw / 2
    if icon:
        d.text((x, (y + y1) / 2), icon, font=ic, fill=text_fill + (255,), anchor="lm")
        x += iw
    d.text((x, y + pad_y + capw), text, font=fnt, fill=text_fill + (255,), anchor="ls")
    commit(canvas, lay, blur=14, offset=(0, 8), strength=1.6)
    return y1


def cta(canvas):
    scrim(canvas, [(0, 0.55), (420, 0.2), (700, 0.0), (980, 0.0), (1250, 0.62), (H, 0.86)])
    logo(canvas, 130, 300)
    # Success-story end card: a general Eventia tagline, not tied to Durga Puja.
    yb = pill(canvas, 990, "SUCCESS STORY", font("Cinzel-Bold.ttf", 34), CRIMSON, MAROON_DARK,
              GOLD_LIGHT, icon="verified", pad_x=40, pad_y=20, outline=GOLD)
    base = text_c(canvas, yb + 36, "Another Successful Event", font("PlayfairDisplay-ExtraBold.ttf", 72),
                  CREAM, grad=(CREAM, GOLD_LIGHT), blur=7)
    base = text_c(canvas, base + 26, "by Eventia", font("PlayfairDisplay-ExtraBold.ttf", 72), SAFFRON, blur=7)
    base = text_c(canvas, base + 30, "Planning your next event? Let’s make it a success.",
                  font("Lora-SemiBold.ttf", 38), WHITE, blur=5)
    yb = pill(canvas, base + 46, "BOOK A CALL", font("Cinzel-Bold.ttf", 56), SAFFRON, (226, 150, 10),
              MAROON_DARK, icon="event_available", outline=GOLD_LIGHT)
    yp = pill(canvas, yb + 34, PHONE, font("Lora-Bold.ttf", 56), CRIMSON, MAROON_DARK, CREAM,
              icon="call", outline=GOLD)
    text_c(canvas, yp + 30, "EVENTIA  •  KOLKATA", font("Cinzel-SemiBold.ttf", 32), GOLD_LIGHT, tracking=4, blur=4)


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    c = layer(); top_block(c, "title"); c.save(out / "title.png")
    for i, (icon, title, sub) in enumerate(BENEFITS):
        c = layer()
        top_block(c, "help")
        scrim(c, [(0, 0), (1150, 0), (1380, 0.45), (1620, 0.45), (1800, 0)])
        card(c, 1330, icon, title, sub, i)
        c.save(out / f"help_{i + 1}.png")
    c = layer(); cta(c); c.save(out / "cta.png")
    print("overlays ->", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "overlays")
