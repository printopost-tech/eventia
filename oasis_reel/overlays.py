#!/usr/bin/env python3
"""Transparent 1080x1920 overlays for The Divine Oasis Resort reel.

  cap_<i>.png   bottom caption for shot i (cap_0 also carries the logo at the top)
  end.png       end card: logo + tagline, address, BOOK YOUR STAY, phone

Brand look follows the client's own Diwali ad: deep forest green + gold on cream.

Usage: python3 overlays.py OUT_DIR
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "reel" / "assets" / "fonts"
LOGO = HERE / "assets" / "logo.png"

W, H = 1080, 1920
CX = W // 2
GREEN = (16, 66, 46)
GREEN_DARK = (7, 36, 25)
GOLD = (212, 175, 90)
GOLD_LIGHT = (243, 220, 150)
CREAM = (255, 247, 228)
SHADOW = (4, 14, 9)

PHONE = "+91 99039 89950"
ADDRESS = "Hilltop, Ajodhya · Purulia · West Bengal"

CAPTIONS = [
    "Escape to the hills of Purulia",
    "Splash into the blue",
    "Folk music & dance on the lawn",
    "Feasts, shared together",
    "When the evening lights up",
    "Purulia Chhau under the stars",
    "Live music nights",
    "Dance the night away",
]


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def gradient(size, top, bottom):
    w, h = size
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        col.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return col.resize((w, h))


def commit(canvas, lay, blur=8, offset=(0, 4), strength=2.4):
    a = lay.getchannel("A")
    sh = Image.new("L", canvas.size, 0)
    sh.paste(a, offset)
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * strength)))
    shadow = Image.new("RGBA", canvas.size, SHADOW + (0,))
    shadow.putalpha(sh)
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(lay)


def scrim(canvas, stops):
    col = Image.new("L", (1, H), 0)
    for y in range(H):
        for (y0, a0), (y1, a1) in zip(stops, stops[1:]):
            if y0 <= y <= y1:
                t = (y - y0) / max(y1 - y0, 1)
                t = t * t * (3 - 2 * t)
                col.putpixel((0, y), round(255 * (a0 + (a1 - a0) * t)))
                break
    band = Image.new("RGBA", (W, H), (3, 14, 9, 255))
    band.putalpha(col.resize((W, H)))
    canvas.alpha_composite(band)


def cap_h(fnt):
    return -fnt.getbbox("H", anchor="ls")[1]


def text_c(canvas, y, s, fnt, fill, blur=8, tracking=0):
    lay = layer()
    d = ImageDraw.Draw(lay)
    base = y + cap_h(fnt)
    if tracking:
        ws = [d.textlength(c, font=fnt) for c in s]
        x = CX - (sum(ws) + tracking * (len(s) - 1)) / 2
        for c, cw in zip(s, ws):
            d.text((x, base), c, font=fnt, fill=fill, anchor="ls")
            x += cw + tracking
    else:
        d.text((CX, base), s, font=fnt, fill=fill, anchor="ms")
    commit(canvas, lay, blur=blur)
    return base


def logo(canvas, y, width):
    """The supplied logo is tiny (~99x156 px of white artwork), so upscale only its
    alpha and re-threshold it: edges stay crisp instead of going soft."""
    img = Image.open(LOGO).convert("RGBA")
    img = img.crop(img.getbbox())
    size = (width, round(img.height * width / img.width))
    a = img.getchannel("A").resize(size, Image.LANCZOS)
    a = a.point(lambda v: 0 if v < 80 else 255 if v > 175 else round((v - 80) * 255 / 95))
    a = a.filter(ImageFilter.GaussianBlur(0.8))
    white = Image.new("RGBA", size, CREAM + (0,))
    white.putalpha(a)
    lay = layer()
    lay.paste(white, (CX - width // 2, y))
    commit(canvas, lay, blur=10, offset=(0, 3), strength=3)
    return y + size[1]


def diamond_rule(canvas, y, half=170):
    lay = layer()
    d = ImageDraw.Draw(lay)
    for sign in (-1, 1):
        steps = 40
        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            a = round(255 * (1 - t0) ** 0.7)
            d.line([(CX + sign * (16 + half * t0), y), (CX + sign * (16 + half * t1), y)],
                   fill=GOLD + (a,), width=3)
    d.polygon([(CX, y - 8), (CX + 8, y), (CX, y + 8), (CX - 8, y)], fill=GOLD_LIGHT + (255,))
    commit(canvas, lay, blur=3, offset=(0, 1))


def caption(text, with_logo=False):
    c = layer()
    scrim(c, [(0, 0.45 if with_logo else 0.0), (460, 0.0 if with_logo else 0.0), (1330, 0.0), (1560, 0.55), (H, 0.75)])
    if with_logo:
        logo(c, 150, 210)
    diamond_rule(c, 1478)
    text_c(c, 1512, text, font("PlayfairDisplay-Bold.ttf", 62), CREAM, blur=9)
    return c


def pill(canvas, y, text, fnt, top, bottom, text_fill, icon, outline, pad_x=58, pad_y=30):
    lay = layer()
    d = ImageDraw.Draw(lay)
    capw = cap_h(fnt)
    ic = font("MaterialSymbolsRounded-Filled.ttf", round(capw * 1.5))
    iw = d.textlength(icon, font=ic) + 18
    tw = iw + d.textlength(text, font=fnt)
    x0, x1 = round(CX - tw / 2 - pad_x), round(CX + tw / 2 + pad_x)
    y1 = y + capw + 2 * pad_y
    body = gradient((x1 - x0, y1 - y), top, bottom).convert("RGBA")
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=(y1 - y) // 2, fill=255)
    body.putalpha(mask)
    lay.paste(body, (x0, y))
    d.rounded_rectangle([x0, y, x1, y1], radius=(y1 - y) // 2, outline=outline + (255,), width=4)
    x = CX - tw / 2
    d.text((x, (y + y1) / 2), icon, font=ic, fill=text_fill + (255,), anchor="lm")
    d.text((x + iw, y + pad_y + capw), text, font=fnt, fill=text_fill + (255,), anchor="ls")
    commit(canvas, lay, blur=14, offset=(0, 8), strength=1.6)
    return y1


def end_card():
    c = layer()
    scrim(c, [(0, 0.82), (500, 0.82), (1500, 0.82), (H, 0.9)])
    # soft green wash so the card reads as the brand colour over any footage
    wash = Image.new("RGBA", (W, H), GREEN_DARK + (120,))
    c.alpha_composite(wash)
    y = logo(c, 250, 340)
    diamond_rule(c, y + 60, half=210)
    text_c(c, y + 100, "Your hilltop escape in Purulia", font("PlayfairDisplay-Bold.ttf", 46), CREAM, blur=8)
    yb = pill(c, 1050, "BOOK YOUR STAY", font("Cinzel-Bold.ttf", 58), GOLD_LIGHT, GOLD, GREEN_DARK,
              "event_available", GOLD_LIGHT)
    yp = pill(c, yb + 36, PHONE, font("Lora-Bold.ttf", 58), GREEN, GREEN_DARK, CREAM, "call", GOLD)
    # address with a pin icon
    lay = layer()
    d = ImageDraw.Draw(lay)
    af = font("Lora-SemiBold.ttf", 38)
    ic = font("MaterialSymbolsRounded-Filled.ttf", 54)
    iw = d.textlength("location_on", font=ic) + 12
    tw = iw + d.textlength(ADDRESS, font=af)
    x = CX - tw / 2
    ya = yp + 70
    d.text((x, ya + 14), "location_on", font=ic, fill=GOLD_LIGHT + (255,), anchor="lm")
    d.text((x + iw, ya + 14 + cap_h(af) / 2), ADDRESS, font=af, fill=CREAM + (255,), anchor="ls")
    commit(c, lay, blur=6)
    return c


def main(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(CAPTIONS):
        caption(text, with_logo=(i == 0)).save(out / f"cap_{i}.png")
    end_card().save(out / "end.png")
    print("overlays ->", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "overlays")
