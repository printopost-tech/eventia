#!/usr/bin/env python3
"""Render the static North Kolkata Pujo Trail overlay as a transparent PNG.

Usage: python3 make_overlay.py [WIDTH HEIGHT] [OUT.png]
Defaults to 1080x1920 (standard Reel). Layout is designed on a 1080x1920
canvas and scaled for other sizes, so the safe zones still hold.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "assets" / "fonts"
LOGO = HERE / "assets" / "image1.png"

W, H = 1080, 1920
# Instagram Reels safe zones (on the 1080x1920 design canvas). The bottom
# limit is 270px rather than the conservative 380px so the info block sits
# low and leaves the idols visible; the logo is deliberately placed in the
# top band, above the clip's own "Durga puja" caption (y ~165-310).
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT, MARGIN = 250, 270, 130, 60
SAFE = (MARGIN, SAFE_TOP, W - SAFE_RIGHT, H - SAFE_BOTTOM)  # x0, y0, x1, y1
TOP_BAND_OK = {"logo"}  # elements allowed above SAFE_TOP
CX = W // 2  # shares the centre line of the clip's baked-in caption

CRIMSON = (139, 14, 28)
MAROON_DARK = (88, 6, 16)
GOLD = (201, 162, 75)
GOLD_LIGHT = (240, 214, 140)
CREAM = (255, 244, 220)
NAVY = (10, 16, 42)

STOPS = ["Santosh Mitra Square", "College Square", "Chaltabagan", "Kashi Bose Lane",
         "Nalin Sarkar Street", "Ahiritola", "Kumartuli Park", "Bagbazar", "Sovabazar Rajbari"]

placed = []  # bounding boxes of every element, for the safe-zone check


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def icon_font(size):
    return font("MaterialSymbolsRounded-Filled.ttf", size)


def new_layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def vertical_gradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        grad.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return grad.resize((w, h))


def commit(canvas, layer, name, blur=8, offset=(0, 4), track=True):
    """Composite a layer over the canvas with a soft navy drop shadow."""
    alpha = layer.getchannel("A")
    sh_alpha = Image.new("L", canvas.size, 0)
    sh_alpha.paste(alpha, offset)
    sh_alpha = sh_alpha.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, v * 2))
    shadow = Image.new("RGBA", canvas.size, NAVY + (0,))
    shadow.putalpha(sh_alpha)
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(layer)
    if track:
        placed.append((name, layer.getbbox()))
    return layer.getbbox()


def ink_height(fnt, s="Hg"):
    bb = fnt.getbbox(s, anchor="ls")
    return -bb[1], bb[3]  # ascent above baseline, descent below


def draw_runs(d, x, baseline, runs):
    """Draw [(text, font, fill), ...] left to right on one shared baseline."""
    for s, fnt, fill in runs:
        d.text((x, baseline), s, font=fnt, fill=fill, anchor="ls")
        x += d.textlength(s, font=fnt)
    return x


def runs_width(d, runs):
    return sum(d.textlength(s, font=f) for s, f, _ in runs)


def gold_fill(layer, top=CREAM, bottom=GOLD_LIGHT):
    """Replace the colour of everything on a layer with a vertical gradient."""
    box = layer.getbbox()
    grad = vertical_gradient((box[2] - box[0], box[3] - box[1]), top, bottom).convert("RGBA")
    grad.putalpha(layer.crop(box).getchannel("A"))
    out = new_layer()
    out.paste(grad, box[:2])
    return out


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


# --- elements ----------------------------------------------------------------

def logo(canvas, y, width):
    img = Image.open(LOGO).convert("RGBA")
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    layer = new_layer()
    layer.paste(img, (CX - width // 2, y))
    commit(canvas, layer, "logo", blur=6, offset=(0, 2))
    return y + img.height


def centred_text(canvas, y, s, fnt, fill, name=None, tracking=0, gradient=None, blur=8):
    """Centred single line with its cap-top at y; returns the baseline y."""
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    asc, _ = ink_height(fnt, "H")
    base = y + asc
    if tracking:
        widths = [d.textlength(c, font=fnt) for c in s]
        x = CX - (sum(widths) + tracking * (len(s) - 1)) / 2
        for c, cw in zip(s, widths):
            d.text((x, base), c, font=fnt, fill=fill, anchor="ls")
            x += cw + tracking
    else:
        d.text((CX, base), s, font=fnt, fill=fill, anchor="ms")
    if gradient:
        layer = gold_fill(layer, *gradient)
    commit(canvas, layer, name or s, blur=blur)
    return base


def flourish(canvas, y, half_gap, length, name):
    """Pair of tapering gold rules either side of a centred gap, with end dots."""
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    for sign in (-1, 1):
        x_in, x_out = CX + sign * half_gap, CX + sign * (half_gap + length)
        steps = 40
        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            a = round(255 * (1 - t0) ** 0.6)
            d.line([(x_in + (x_out - x_in) * t0, y), (x_in + (x_out - x_in) * t1, y)],
                   fill=GOLD + (a,), width=3)
        d.polygon([(x_in, y - 7), (x_in + sign * 7, y), (x_in, y + 7), (x_in - sign * 7, y)],
                  fill=GOLD_LIGHT + (255,))
    commit(canvas, layer, name, blur=3, offset=(0, 1))


def date_chip(canvas, y):
    """Rounded maroon chip: [calendar] 17th October  ◆  [clock] 8 AM – 3 PM."""
    fnt = font("Lora-SemiBold.ttf", 44)
    ic = icon_font(50)
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    asc, desc = ink_height(fnt, "H")
    pad_x, pad_y, gap_icon, gap_mid = 40, 24, 14, 54
    parts = [("calendar_month", "17th October"), ("schedule", "8 AM – 3 PM")]
    widths = [d.textlength(i, font=ic) + gap_icon + d.textlength(t, font=fnt) for i, t in parts]
    inner = sum(widths) + gap_mid
    x0, x1 = round(CX - inner / 2 - pad_x), round(CX + inner / 2 + pad_x)
    y0, y1 = y, y + asc + 2 * pad_y
    r = (y1 - y0) // 2
    body = vertical_gradient((x1 - x0, y1 - y0), CRIMSON, MAROON_DARK).convert("RGBA")
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=r, fill=225)
    body.putalpha(mask)
    layer.paste(body, (x0, y0))
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=GOLD + (255,), width=3)
    base = y0 + pad_y + asc
    x = x0 + pad_x
    for k, (icon, label) in enumerate(parts):
        ib = d.textbbox((0, 0), icon, font=ic)
        d.text((x, (y0 + y1) / 2 - (ib[1] + ib[3]) / 2), icon, font=ic, fill=GOLD_LIGHT + (255,))
        x += d.textlength(icon, font=ic) + gap_icon
        d.text((x, base), label, font=fnt, fill=CREAM + (255,), anchor="ls")
        x += d.textlength(label, font=fnt)
        if k == 0:
            cx, cy = x + gap_mid / 2, (y0 + y1) / 2
            d.polygon([(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)], fill=GOLD + (255,))
            x += gap_mid
    commit(canvas, layer, "date chip", blur=12, offset=(0, 6))
    return y1


def wrap_stops(d, fnt, max_w, sep=" • "):
    """Split the stops (in route order) into the fewest, most even lines that fit."""
    width = lambda group: d.textlength(sep.join(group), font=fnt)
    n = len(STOPS)
    for k in range(1, n + 1):
        best = None

        def splits(start, parts):
            if parts == 1:
                yield [STOPS[start:]]
                return
            for end in range(start + 1, n - parts + 2):
                for rest in splits(end, parts - 1):
                    yield [STOPS[start:end]] + rest

        for lines in splits(0, k):
            widest = max(width(g) for g in lines)
            if widest <= max_w and (best is None or widest < best[0]):
                best = (widest, lines)
        if best:
            return best[1]


def info_card(canvas, y0, x0=132, x1=948):
    """Framed card: two icon rows (pandals / pickup), then the list of stops."""
    head = font("Lora-SemiBold.ttf", 42)
    body = font("Lora-Medium.ttf", 40)
    stop_f = font("Lora-Medium.ttf", 30)
    ic = icon_font(58)
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    pad, icon_w, icon_gap = 34, 58, 22
    text_x = x0 + pad + icon_w + icon_gap

    rows = [("temple_hindu", "9 Pandals + Mahabhog Lunch", "at Sovabazar Rajbari"),
            ("directions_subway", "Pickup & Drop:", "Kalighat Metro & Esplanade Metro")]
    h_asc, _ = ink_height(head, "H")
    b_asc, b_desc = ink_height(body, "Hg")
    line_gap = 14
    row_h = h_asc + line_gap + b_asc + b_desc
    s_asc, s_desc = ink_height(stop_f, "Hg")
    stop_lines = wrap_stops(d, stop_f, (x1 - x0) - 2 * pad)
    stop_lh = s_asc + s_desc + 10

    y = y0 + pad
    content = []
    for icon, l1, l2 in rows:
        content.append(("row", y, icon, l1, l2))
        y += row_h + 26
    divider_y = y + 4
    y = divider_y + 30
    stops_top = y
    y += len(stop_lines) * stop_lh - 10
    y1 = y + pad - 6

    # card body: translucent maroon-to-navy with double gold frame
    body_img = vertical_gradient((x1 - x0, y1 - y0), (60, 6, 14), (14, 10, 30)).convert("RGBA")
    mask = Image.new("L", body_img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body_img.width - 1, body_img.height - 1], radius=30, fill=170)
    body_img.putalpha(mask)
    layer.paste(body_img, (x0, y0))
    d.rounded_rectangle([x0, y0, x1, y1], radius=30, outline=GOLD + (255,), width=3)
    d.rounded_rectangle([x0 + 9, y0 + 9, x1 - 9, y1 - 9], radius=22, outline=GOLD + (90,), width=1)

    for _, ry, icon, l1, l2 in content:
        ib = d.textbbox((0, 0), icon, font=ic)
        d.text((x0 + pad + (icon_w - (ib[2] - ib[0])) / 2 - ib[0], ry + row_h / 2 - (ib[1] + ib[3]) / 2),
               icon, font=ic, fill=GOLD_LIGHT + (255,))
        d.text((text_x, ry + h_asc), l1, font=head, fill=GOLD_LIGHT + (255,), anchor="ls")
        d.text((text_x, ry + h_asc + line_gap + b_asc), l2, font=body, fill=CREAM + (255,), anchor="ls")

    # divider with a location pin, then the stops
    pin = icon_font(40)
    pb = d.textbbox((0, 0), "location_on", font=pin)
    d.text((CX - (pb[0] + pb[2]) / 2, divider_y - (pb[1] + pb[3]) / 2), "location_on", font=pin,
           fill=GOLD_LIGHT + (255,))
    for sign in (-1, 1):
        d.line([(CX + sign * 36, divider_y), (CX + sign * ((x1 - x0) / 2 - pad - 10), divider_y)],
               fill=GOLD + (150,), width=2)
    sep = " • "
    for i, line in enumerate(stop_lines):
        base = stops_top + s_asc + i * stop_lh
        runs = []
        for j, stop in enumerate(line):
            if j:
                runs.append((sep, stop_f, GOLD + (255,)))
            runs.append((stop, stop_f, CREAM + (240,)))
        draw_runs(d, CX - runs_width(d, runs) / 2, base, runs)

    commit(canvas, layer, "info card", blur=14, offset=(0, 6))
    return y1


def price_pill(canvas, y):
    """Maroon pill: small 'Rs', big '3199', small 'only' on one baseline."""
    small = font("PlayfairDisplay-Bold.ttf", 46)
    big = font("PlayfairDisplay-ExtraBold.ttf", 84)
    runs = [("Rs ", small, GOLD_LIGHT + (255,)), ("3199", big, GOLD_LIGHT + (255,)),
            (" only", small, GOLD_LIGHT + (255,))]
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    asc, _ = ink_height(big, "3199")
    tw = runs_width(d, runs)
    pad_x, pad_y = 60, 20
    x0, x1 = round(CX - tw / 2 - pad_x), round(CX + tw / 2 + pad_x)
    y1 = y + asc + 2 * pad_y
    r = (y1 - y) // 2
    body = vertical_gradient((x1 - x0, y1 - y), CRIMSON, MAROON_DARK).convert("RGBA")
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=r, fill=255)
    body.putalpha(mask)
    layer.paste(body, (x0, y))
    d.rounded_rectangle([x0, y, x1, y1], radius=r, outline=GOLD + (255,), width=4)
    d.rounded_rectangle([x0 + 8, y + 8, x1 - 8, y1 - 8], radius=r - 8, outline=GOLD + (110,), width=2)
    draw_runs(d, CX - tw / 2, y + pad_y + asc, runs)
    commit(canvas, layer, "price", blur=12, offset=(0, 6))
    return y1


def phone_line(canvas, y):
    """Gold call badge + large cream number (grouped 74390 12840)."""
    fnt = font("Lora-Bold.ttf", 80)
    number = "74390 12840"
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    asc, _ = ink_height(fnt, "7")
    badge, gap = 82, 22
    total = badge + gap + d.textlength(number, font=fnt)
    x = CX - total / 2
    by = y + asc / 2 - badge / 2
    d.ellipse([x, by, x + badge, by + badge], fill=GOLD_LIGHT + (255,), outline=GOLD + (255,), width=3)
    ic = icon_font(52)
    ib = d.textbbox((0, 0), "call", font=ic)
    d.text((x + badge / 2 - (ib[0] + ib[2]) / 2, by + badge / 2 - (ib[1] + ib[3]) / 2), "call",
           font=ic, fill=MAROON_DARK + (255,))
    d.text((x + badge + gap, y + asc), number, font=fnt, fill=CREAM + (255,), anchor="ls")
    commit(canvas, layer, "phone", blur=10, offset=(0, 4))
    return y + asc


def build():
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Readability scrims (55% black at their darkest). The top one eases off
    # over the clip's own caption so that keeps its original look.
    scrim(c, [(0, 0.55), (140, 0.5), (185, 0.12), (300, 0.12), (360, 0.5),
              (720, 0.5), (860, 0.0), (860, 0.0), (1000, 0.55), (H, 0.55)])

    # --- Top block -------------------------------------------------------
    logo(c, 60, width=290)
    y = centred_text(c, 352, "A CURATED HERITAGE EXPERIENCE", font("Cinzel-Bold.ttf", 34),
                     GOLD_LIGHT + (255,), tracking=4, blur=5)
    title = font("PlayfairDisplay-ExtraBold.ttf", 124)
    y = centred_text(c, y + 34, "North Kolkata", title, (255, 255, 255, 255), gradient=(CREAM, GOLD_LIGHT))
    y = centred_text(c, y + 46, "Pujo Trail", title, (255, 255, 255, 255), gradient=(GOLD_LIGHT, GOLD))
    flourish(c, y + 42, 40, 230, "flourish")
    date_chip(c, y + 74)

    # --- Lower block (sits low so the idols stay visible) -----------------
    y = info_card(c, 940)
    y = price_pill(c, y + 24)
    y = centred_text(c, y + 22, "Limited seats, book now!", font("Lora-SemiBold.ttf", 42),
                     GOLD_LIGHT + (255,))
    phone_line(c, y + 22)
    return c


def check_layout():
    ok = True
    for name, (x0, y0, x1, y1) in placed:
        top = 0 if name in TOP_BAND_OK else SAFE[1]
        bad = x0 < SAFE[0] or y0 < top or x1 > SAFE[2] or y1 > SAFE[3]
        ok &= not bad
        print(f"{'FAIL' if bad else 'ok  '} {name!r:34} x {x0}-{x1}  y {y0}-{y1}")
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
    if not check_layout():
        sys.exit("overlay violates safe zones or has overlapping elements")
    if (tw, th) != (W, H):
        img = img.resize((tw, th), Image.LANCZOS)
    img.save(out)
    print(f"wrote {out} ({tw}x{th})")
