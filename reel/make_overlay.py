#!/usr/bin/env python3
"""Render the static North Kolkata Pujo Trail overlay as a transparent PNG.

Usage: python3 make_overlay.py [WIDTH HEIGHT] [OUT.png]
Defaults to 1080x1920 (standard Reel). Layout is designed on a 1080x1920
canvas and scaled for other sizes, so Instagram safe zones still hold.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "assets" / "fonts"
LOGO = HERE / "assets" / "image1.png"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

W, H = 1080, 1920
# Instagram Reels safe zones (on the 1080x1920 design canvas)
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT, MARGIN = 250, 380, 130, 60
SAFE = (MARGIN, SAFE_TOP, W - SAFE_RIGHT, H - SAFE_BOTTOM)  # x0, y0, x1, y1
CX = (SAFE[0] + SAFE[2]) // 2  # horizontal centre of the usable area

CRIMSON = (139, 14, 28)
MAROON_DARK = (92, 8, 18)
GOLD = (201, 162, 75)
GOLD_LIGHT = (240, 214, 140)
CREAM = (255, 244, 220)
NAVY = (10, 16, 42)

placed = []  # bounding boxes of every element, for the safe-zone check


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def vertical_gradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        grad.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return grad.resize((w, h))


def shadowed(canvas, layer, blur=10, offset=(0, 4), strength=230):
    """Composite an RGBA layer with a soft navy drop shadow underneath."""
    alpha = layer.getchannel("A")
    shadow = Image.new("RGBA", canvas.size, NAVY + (0,))
    sh_alpha = Image.new("L", canvas.size, 0)
    sh_alpha.paste(alpha, offset)
    sh_alpha = sh_alpha.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, v * strength // 255 * 2))
    shadow.putalpha(sh_alpha)
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(layer)


def text(canvas, y, s, fnt, fill, spacing=0, shadow_blur=8, gradient=None):
    """Draw centred text with its top at y; returns the bottom y of the ink."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if spacing:  # manual letter-spacing for small caps
        widths = [d.textlength(c, font=fnt) for c in s]
        total = sum(widths) + spacing * (len(s) - 1)
        x = CX - total / 2
        top = d.textbbox((0, 0), s, font=fnt)[1]
        for c, cw in zip(s, widths):
            d.text((x, y - top), c, font=fnt, fill=fill)
            x += cw + spacing
    else:
        bb = d.textbbox((0, 0), s, font=fnt)
        d.text((CX - (bb[0] + bb[2]) / 2, y - bb[1]), s, font=fnt, fill=fill)
    if gradient:
        box = layer.getbbox()
        grad = vertical_gradient((box[2] - box[0], box[3] - box[1]), *gradient).convert("RGBA")
        grad.putalpha(layer.crop(box).getchannel("A"))
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        layer.paste(grad, box[:2])
    box = layer.getbbox()
    placed.append((s, box))
    shadowed(canvas, layer, blur=shadow_blur)
    return box[3]


def ornament(canvas, y, half=150):
    """Thin gold rule with a centre diamond."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.line([(CX - half, y), (CX - 16, y)], fill=GOLD + (255,), width=3)
    d.line([(CX + 16, y), (CX + half, y)], fill=GOLD + (255,), width=3)
    d.polygon([(CX, y - 9), (CX + 9, y), (CX, y + 9), (CX - 9, y)], fill=GOLD_LIGHT + (255,))
    placed.append(("ornament", layer.getbbox()))
    shadowed(canvas, layer, blur=4, offset=(0, 2))


def logo(canvas, y, width=250):
    img = Image.open(LOGO).convert("RGBA")
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(img, (CX - width // 2, y))
    placed.append(("logo", layer.getbbox()))
    shadowed(canvas, layer, blur=6, offset=(0, 2))
    return y + img.height


def price_pill(canvas, y, s, fnt):
    probe = ImageDraw.Draw(canvas)
    bb = probe.textbbox((0, 0), s, font=fnt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad_x, pad_y = 54, 18
    x0, x1 = CX - tw // 2 - pad_x, CX + tw // 2 + pad_x
    y0, y1 = y, y + th + 2 * pad_y
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = (y1 - y0) // 2
    body = vertical_gradient((x1 - x0, y1 - y0), CRIMSON, MAROON_DARK).convert("RGBA")
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=r, fill=255)
    body.putalpha(mask)
    layer.paste(body, (x0, y0))
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=GOLD + (255,), width=4)
    d.rounded_rectangle([x0 + 9, y0 + 9, x1 - 9, y1 - 9], radius=r - 9, outline=GOLD + (120,), width=2)
    d.text((CX - (bb[0] + bb[2]) / 2, y0 + pad_y - bb[1]), s, font=fnt, fill=GOLD_LIGHT + (255,))
    placed.append((s, layer.getbbox()))
    shadowed(canvas, layer, blur=12, offset=(0, 6))
    return y1


def phone_line(canvas, y, number, fnt):
    """Phone emoji (Noto Color Emoji, scaled from its 109px bitmap) + bold number."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bb = d.textbbox((0, 0), number, font=fnt)
    th = bb[3] - bb[1]
    icon_size = round(th * 1.25)
    gap = 22
    emoji = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(emoji).text((0, 0), "\U0001F4DE", font=ImageFont.truetype(EMOJI_FONT, 109), embedded_color=True)
    # the receiver glyph is dark, so sit it on a gold badge to keep it visible
    inner = round(icon_size * 0.66)
    emoji = emoji.crop(emoji.getbbox()).resize((inner, inner), Image.LANCZOS)
    total = icon_size + gap + (bb[2] - bb[0])
    x = CX - total // 2
    iy = y + (th - icon_size) // 2
    d.ellipse([x, iy, x + icon_size, iy + icon_size], fill=GOLD_LIGHT + (255,), outline=GOLD + (255,), width=4)
    off = (icon_size - inner) // 2
    layer.paste(emoji, (x + off, iy + off), emoji)
    d.text((x + icon_size + gap - bb[0], y - bb[1]), number, font=fnt, fill=CREAM + (255,))
    placed.append((number, layer.getbbox()))
    shadowed(canvas, layer, blur=10, offset=(0, 4))
    return y + th


def gradient_band(canvas, y0, y1, peak, fade_in, fade_out):
    """Black band: transparent -> peak alpha over fade_in px, hold, -> 0 over fade_out px."""
    a = Image.new("L", (1, canvas.height), 0)
    for y in range(max(0, y0), min(canvas.height, y1)):
        t = 1.0
        if y < y0 + fade_in:
            t = (y - y0) / fade_in
        elif y > y1 - fade_out:
            t = (y1 - y) / fade_out
        t = t * t * (3 - 2 * t)  # smoothstep
        a.putpixel((0, y), round(255 * peak * t))
    band = Image.new("RGBA", canvas.size, (0, 0, 0, 255))
    band.putalpha(a.resize(canvas.size))
    canvas.alpha_composite(band)


def build():
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Readability scrims (55% black at their darkest)
    gradient_band(c, 300, 860, 0.55, 90, 280)  # starts below the clip's own caption
    gradient_band(c, 800, H + 1, 0.55, 200, 1)

    # --- Top block -------------------------------------------------------
    y = logo(c, 340, width=290)  # clears the baked-in "Durga puja" caption (y~165-310)
    y = text(c, y + 22, "A CURATED HERITAGE EXPERIENCE", font("Cinzel-Bold.ttf", 40),
             GOLD + (255,), spacing=1, shadow_blur=5)
    title = font("PlayfairDisplay-ExtraBold.ttf", 118)
    y = text(c, y + 30, "North Kolkata", title, (255, 255, 255, 255), gradient=(CREAM, GOLD_LIGHT))
    y = text(c, y + 34, "Pujo Trail", title, (255, 255, 255, 255), gradient=(GOLD_LIGHT, GOLD))
    ornament(c, y + 36)

    # --- Lower block -----------------------------------------------------
    body = font("Lora-Medium.ttf", 44)
    body_b = font("Lora-SemiBold.ttf", 46)
    y = text(c, 940, "17th October  |  8 AM – 3 PM", body_b, GOLD_LIGHT + (255,))
    y = text(c, y + 22, "9 Pandals + Mahabhog Lunch", body, CREAM + (255,))
    y = text(c, y + 12, "at Sovabazar Rajbari", body, CREAM + (255,))
    y = text(c, y + 22, "Pickup & Drop:", body, CREAM + (255,))
    y = text(c, y + 12, "Kalighat Metro & Esplanade Metro", body, CREAM + (255,))
    y = price_pill(c, y + 26, "Rs 3199 only", font("PlayfairDisplay-ExtraBold.ttf", 74))
    y = text(c, y + 22, "Limited seats, book now!", font("Lora-SemiBold.ttf", 46), GOLD_LIGHT + (255,))
    phone_line(c, y + 22, "7439012840", font("Lora-Bold.ttf", 80))
    return c


def check_safe_zones():
    ok = True
    for name, (x0, y0, x1, y1) in placed:
        bad = x0 < SAFE[0] or y0 < SAFE[1] or x1 > SAFE[2] or y1 > SAFE[3]
        ok &= not bad
        print(f"{'FAIL' if bad else 'ok  '} {name!r:40} x {x0}-{x1}  y {y0}-{y1}")
    for i, (n1, a) in enumerate(placed):
        for n2, b in placed[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                ok = False
                print(f"OVERLAP {n1!r} / {n2!r}")
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    out = Path(args.pop() if args and args[-1].endswith(".png") else HERE / "overlay.png")
    tw, th = (int(args[0]), int(args[1])) if len(args) >= 2 else (W, H)
    img = build()
    if not check_safe_zones():
        sys.exit("overlay violates safe zones or has overlapping elements")
    if (tw, th) != (W, H):
        img = img.resize((tw, th), Image.LANCZOS)
    img.save(out)
    print(f"wrote {out} ({tw}x{th})")
