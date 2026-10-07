#!/usr/bin/env python3
"""Render the static two-trail (North + South Kolkata) overlay as a transparent PNG.

Usage: python3 make_overlay_both.py [WIDTH HEIGHT] [OUT.png]
Designed on a 1080x1920 canvas and scaled for other sizes. Reuses the fonts,
colours and drawing helpers of make_overlay.py so both Reels match.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import make_overlay as base
from make_overlay import (CREAM, CRIMSON, GOLD, GOLD_LIGHT, MAROON_DARK, H, W, commit, draw_runs,
                          font, gold_fill, ink_height, new_layer, runs_width, vertical_gradient)

HERE = Path(__file__).resolve().parent
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

# Instagram Reels safe zones on the 1080x1920 design canvas.
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT, MARGIN = 250, 380, 130, 60
SAFE = (MARGIN, SAFE_TOP, W - SAFE_RIGHT, H - SAFE_BOTTOM)  # 60, 250, 950, 1540
CX = (SAFE[0] + SAFE[2]) // 2  # centre of the usable width (505)
CARD_X0, CARD_X1, CARD_H, CARD_PAD = SAFE[0], SAFE[2] - 1, 330, 26

TRAILS = [
    ("North Kolkata Pujo Trail", "17th October", "9 Pandals + Mahabhog Lunch",
     [["Santosh Mitra Square", "College Square"], ["Kumartuli Park", "Sovabazar Rajbari"]]),
    ("South Kolkata Pujo Trail", "18th October", "12 Pandals + Lunch Included",
     [["Chetla Agrani", "66 Palli"], ["Singhi Park", "Bosepukur Sitala Mandir"]]),
]


def fit(name, size, text, max_w, floor):
    """Largest font size <= size at which text fits max_w (never below floor)."""
    while size > floor and font(name, size).getlength(text) > max_w:
        size -= 1
    f = font(name, size)
    if f.getlength(text) > max_w:
        sys.exit(f"{text!r} does not fit {max_w}px even at {floor}px")
    return f


def centred(canvas, y, s, fnt, fill, name, tracking=0, gradient=None, blur=8):
    """Centred line (on CX) with its cap-top at y; returns the baseline."""
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    asc, _ = ink_height(fnt, "H")
    baseline = y + asc
    widths = [d.textlength(c, font=fnt) for c in s] if tracking else None
    if tracking:
        x = CX - (sum(widths) + tracking * (len(s) - 1)) / 2
        for c, cw in zip(s, widths):
            d.text((x, baseline), c, font=fnt, fill=fill, anchor="ls")
            x += cw + tracking
    else:
        d.text((CX, baseline), s, font=fnt, fill=fill, anchor="ms")
    if gradient:
        layer = gold_fill(layer, *gradient)
    commit(canvas, layer, name, blur=blur)
    return baseline


def tapered_rules(d, y, half_gap, length, alpha=255, width=2):
    for sign in (-1, 1):
        x_in, x_out = CX + sign * half_gap, CX + sign * (half_gap + length)
        steps = 40
        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            a = round(alpha * (1 - t0) ** 0.6)
            d.line([(x_in + (x_out - x_in) * t0, y), (x_in + (x_out - x_in) * t1, y)],
                   fill=GOLD + (a,), width=width)


def header(canvas, y):
    fnt = font("Cinzel-Bold.ttf", 40)
    baseline = centred(canvas, y, "EVENTIA PUJO TRAILS", fnt, GOLD_LIGHT + (255,), "header",
                       tracking=6, blur=5)
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    rule_y = baseline + 22
    tapered_rules(d, rule_y, 14, 190)
    d.polygon([(CX, rule_y - 7), (CX + 7, rule_y), (CX, rule_y + 7), (CX - 7, rule_y)],
              fill=GOLD_LIGHT + (255,))
    commit(canvas, layer, "header rule", blur=3, offset=(0, 1))
    return rule_y + 8


def trail_card(canvas, y0, title, date, pandals, stop_lines):
    title_f = font("PlayfairDisplay-Bold.ttf", 64)
    inner_w = CARD_X1 - CARD_X0 - 2 * CARD_PAD
    sep = " • "
    info_f = fit("Lora-SemiBold.ttf", 42, date + sep + pandals, inner_w, 38)
    stop_f = font("Lora-Medium.ttf", 34)
    y1 = y0 + CARD_H

    layer = new_layer()
    d = ImageDraw.Draw(layer)
    # Panel: dark maroon at ~65% opacity, thin gold frame + faint inner hairline.
    body = vertical_gradient((CARD_X1 - CARD_X0, CARD_H), (72, 6, 16), (40, 4, 12)).convert("RGBA")
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], radius=28, fill=166)
    body.putalpha(mask)
    layer.paste(body, (CARD_X0, y0))
    d.rounded_rectangle([CARD_X0, y0, CARD_X1, y1], radius=28, outline=GOLD + (255,), width=3)
    d.rounded_rectangle([CARD_X0 + 8, y0 + 8, CARD_X1 - 8, y1 - 8], radius=21, outline=GOLD + (80,), width=1)

    # Vertical rhythm: title, info line, short rule, two lines of stops.
    t_asc, t_desc = ink_height(title_f, "Hg")
    i_asc, _ = ink_height(info_f, "H")
    s_asc, s_desc = ink_height(stop_f, "Hg")
    stop_lh = s_asc + s_desc + 8
    content_h = t_asc + t_desc + 14 + i_asc + 34 + len(stop_lines) * stop_lh - 8
    y = y0 + (CARD_H - content_h) / 2

    title_layer = new_layer()
    ImageDraw.Draw(title_layer).text((CX, y + t_asc), title, font=title_f, fill=(255, 255, 255, 255),
                                     anchor="ms")
    title_layer = gold_fill(title_layer, GOLD_LIGHT, GOLD)
    y += t_asc + t_desc + 14

    runs = [(date, info_f, CREAM + (255,)), (sep, info_f, GOLD + (255,)), (pandals, info_f, CREAM + (255,))]
    draw_runs(d, CX - runs_width(d, runs) / 2, y + i_asc, runs)
    y += i_asc + 17
    tapered_rules(d, y, 6, 150, alpha=170)
    y += 17

    for i, line in enumerate(stop_lines):
        runs = []
        for j, stop in enumerate(line):
            if j:
                runs.append((sep, stop_f, GOLD + (255,)))
            runs.append((stop, stop_f, CREAM + (235,)))
        draw_runs(d, CX - runs_width(d, runs) / 2, y + s_asc + i * stop_lh, runs)

    layer.alpha_composite(title_layer)
    commit(canvas, layer, title, blur=14, offset=(0, 6))
    return y1


def ampersand(canvas, y_mid):
    fnt = font("PlayfairDisplay-Bold.ttf", 46)
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    bb = d.textbbox((0, 0), "&", font=fnt)
    d.text((CX - (bb[0] + bb[2]) / 2, y_mid - (bb[1] + bb[3]) / 2), "&", font=fnt, fill=GOLD_LIGHT + (255,))
    tapered_rules(d, y_mid, 30, 170)
    commit(canvas, layer, "ampersand", blur=4, offset=(0, 1))


def price_pill(canvas, y):
    """Maroon ribbon: 'Rs 3199 only' with a small '(each trail)'."""
    small = font("PlayfairDisplay-Bold.ttf", 46)
    big = font("PlayfairDisplay-ExtraBold.ttf", 84)
    note = font("Lora-SemiBold.ttf", 32)
    runs = [("Rs ", small, GOLD_LIGHT + (255,)), ("3199", big, GOLD_LIGHT + (255,)),
            (" only ", small, GOLD_LIGHT + (255,)), ("(each trail)", note, CREAM + (230,))]
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    asc, _ = ink_height(big, "3199")
    tw = runs_width(d, runs)
    pad_x, pad_y = 54, 20
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


def phone_emoji(size):
    """📞 from Noto Color Emoji (bitmap font, only renders at 109px) scaled to size."""
    f = ImageFont.truetype(EMOJI_FONT, 109)
    img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10, 10), "\U0001F4DE", font=f, embedded_color=True)
    img = img.crop(img.getbbox())
    return img.resize((round(img.width * size / img.height), size), Image.LANCZOS)


def phone_line(canvas, y):
    fnt = font("Lora-Bold.ttf", 80)
    number = "74390 12840"
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    asc, _ = ink_height(fnt, "7")
    badge, gap = 84, 22
    icon = phone_emoji(56)
    total = badge + gap + d.textlength(number, font=fnt)
    x = CX - total / 2
    by = y + asc / 2 - badge / 2
    # Gold disc behind the emoji: the dark receiver glyph alone gets lost on maroon.
    d.ellipse([x, by, x + badge, by + badge], fill=GOLD_LIGHT + (255,), outline=GOLD + (255,), width=3)
    layer.alpha_composite(icon, (round(x + badge / 2 - icon.width / 2), round(by + badge / 2 - icon.height / 2)))
    d.text((x + badge + gap, y + asc), number, font=fnt, fill=CREAM + (255,), anchor="ls")
    commit(canvas, layer, "phone", blur=10, offset=(0, 4))
    return y + asc


def build():
    base.placed.clear()
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # Soft scrim behind the whole block (max 42% black), fading out above and
    # below so the footage stays visible.
    base.scrim(c, [(0, 0.0), (300, 0.0), (420, 0.38), (1380, 0.42), (1600, 0.0), (H, 0.0)])

    y = header(c, 332)
    y = trail_card(c, y + 26, *TRAILS[0])
    gap = 56
    ampersand(c, y + gap // 2)
    y = trail_card(c, y + gap, *TRAILS[1])

    line = "8 AM – 3 PM • Pickup & Drop: Kalighat & Esplanade Metro"
    f = fit("Lora-SemiBold.ttf", 36, line, SAFE[2] - SAFE[0], 30)
    layer = new_layer()
    d = ImageDraw.Draw(layer)
    parts = line.split(" • ")
    runs = [(parts[0], f, CREAM + (255,)), (" • ", f, GOLD + (255,)), (parts[1], f, CREAM + (255,))]
    asc, _ = ink_height(f, "H")
    draw_runs(d, CX - runs_width(d, runs) / 2, y + 30 + asc, runs)
    commit(c, layer, "time + pickup", blur=6)
    y = y + 30 + asc

    y = price_pill(c, y + 30)
    y = phone_line(c, y + 38)
    centred(c, y + 36, "Limited seats, book now!", font("Lora-SemiBold.ttf", 36), GOLD_LIGHT + (255,),
            "limited seats")
    return c


def check_layout():
    ok = True
    for name, (x0, y0, x1, y1) in base.placed:
        bad = x0 < SAFE[0] or y0 < SAFE[1] or x1 > SAFE[2] or y1 > SAFE[3]
        ok &= not bad
        print(f"{'FAIL' if bad else 'ok  '} {name!r:30} x {x0}-{x1}  y {y0}-{y1}")
    for i, (n1, a) in enumerate(base.placed):
        for n2, b in base.placed[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                ok = False
                print(f"OVERLAP {n1!r} / {n2!r}")
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    out = Path(args.pop() if args and args[-1].endswith(".png") else HERE / "overlay-both-trails.png")
    tw, th = (int(args[0]), int(args[1])) if len(args) >= 2 else (W, H)
    img = build()
    if not check_layout():
        sys.exit("overlay violates safe zones or has overlapping elements")
    if (tw, th) != (W, H):
        img = img.resize((tw, th), Image.LANCZOS)
    img.save(out)
    print(f"wrote {out} ({tw}x{th})")
