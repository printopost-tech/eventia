#!/usr/bin/env python3
"""Build the ~60s Hic Et Ubique Thailand trip Reel (1080x1920, 9:16).

Usage: python3 build.py SRC_DIR OUT.mp4
SRC_DIR holds the client clips as c1.mp4 ... (see CLIPS below).
Steps: cut + grade each shot, crossfade them, lay timed captions and the
logo over the top, and score it with the original track from music.py.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "assets" / "fonts"
W, H, FPS = 1080, 1920, 30
XF = 0.5  # crossfade length

# client clip -> what it shows
CLIPS = {
    "c1": "group on the long-tail boat",
    "c2": "rainforest boardwalk and lagoons",
    "c4": "speedboat through the limestone karsts",
    "c5": "swimming at the Emerald Pool",
    "c8": "sunset parasailing (portrait via rotation metadata)",
}

# (clip, in-point, duration, speed)
SHOTS = [
    ("c4", 0.0, 4.5, 1),     # 0  karst cliff - opening title
    ("c4", 13.0, 3.5, 1),    # 1  spray + islands on the horizon
    ("c4", 60.0, 3.5, 1),    # 2  big karst
    ("c1", 11.0, 4.0, 1),    # 3  smiling close-ups
    ("c1", 16.0, 3.5, 1),    # 4
    ("c4", 28.0, 3.5, 1),    # 5  karst wall
    ("c4", 39.0, 3.5, 1),    # 6  karst range
    ("c4", 70.5, 3.0, 1),    # 7  splash under the cliff
    ("c2", 0.0, 3.0, 1),     # 8  forest stream
    ("c2", 19.0, 4.0, 1),    # 9  boardwalk
    ("c2", 34.5, 3.0, 1),    # 10 clear stream
    ("c2", 41.0, 3.0, 1),    # 11 lagoon under blue sky
    ("c5", 3.5, 3.0, 1),     # 12 Emerald Pool wide
    ("c5", 9.0, 2.6, 1),     # 13 couple waving (black frame at ~12s, stay clear)
    ("c5", 19.0, 3.0, 1),    # 14
    ("c5", 24.5, 4.3, 1),    # 15 arms up!
    ("c1", 6.0, 2.5, 1),     # 16 the whole group on the boat
    ("c1", 21.5, 3.0, 1),    # 17 group laughing
    ("c8", 0.0, 5.2, 0.6),   # 18 sunset, slowed - end card
]

RED = (224, 49, 55)
ORANGE = (247, 165, 52)
TEAL = (33, 182, 196)
WHITE = (255, 255, 255)
INK = (8, 20, 32)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def run(cmd):
    subprocess.run(cmd, check=True)


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True).stdout
    return float(out)


# --- graphics ----------------------------------------------------------------

def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def with_shadow(layer, blur=10, offset=(0, 5), strength=200):
    a = layer.getchannel("A")
    sh = Image.new("L", layer.size, 0)
    sh.paste(a, offset)
    sh = sh.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, v * strength // 128))
    out = Image.new("RGBA", layer.size, INK + (0,))
    out.putalpha(sh)
    out.alpha_composite(layer)
    return out


def text_centre(d, y, s, fnt, fill, cx=W // 2):
    d.text((cx, y), s, font=fnt, fill=fill, anchor="mt")
    bb = d.textbbox((cx, y), s, font=fnt, anchor="mt")
    return bb[3]


def wrap(d, s, fnt, max_w):
    words, lines, cur = s.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and d.textlength(trial, font=fnt) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    return lines + [cur]


def logo_card():
    """White rounded card with the client logo, top centre (persistent)."""
    logo = Image.open(HERE / "assets" / "logo.png").convert("RGBA")
    lw = 640
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    pad_x, pad_y = 22, 6
    cw, ch = lw + 2 * pad_x, logo.height + 2 * pad_y
    x0, y0 = (W - cw) // 2, 96
    layer = blank()
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=34, fill=(255, 255, 255, 240))
    card.alpha_composite(logo, (pad_x, pad_y))
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw - 1, ch - 1], radius=34, fill=255)
    card.putalpha(Image.composite(card.getchannel("A"), mask, mask))
    layer.alpha_composite(card, (x0, y0))
    return with_shadow(layer, blur=14, offset=(0, 6), strength=110)


def lower_scrim():
    """Soft dark gradient behind the caption area."""
    col = Image.new("L", (1, H), 0)
    for y in range(H):
        t = (y - 1050) / 350
        col.putpixel((0, y), round(150 * max(0.0, min(1.0, t)) ** 1.4) if y < 1750 else 150)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    layer.putalpha(col.resize((W, H)))
    return layer


def caption(kicker, text):
    """Lower-third: small coloured kicker chip + big white line(s)."""
    layer = blank()
    d = ImageDraw.Draw(layer)
    kf = font("Montserrat-ExtraBold.ttf", 34)
    tf = font("Montserrat-ExtraBold.ttf", 62)
    lines = wrap(d, text, tf, 820)
    if len(lines) == 2:  # balance the two lines so no word is left on its own
        words = text.split()
        lines = min(([" ".join(words[:k]), " ".join(words[k:])] for k in range(1, len(words))),
                    key=lambda ls: max(d.textlength(x, font=tf) for x in ls))
    y = 1520 - len(lines) * 82 - 70
    # kicker chip
    kw = d.textlength(kicker, font=kf) + 8 * len(kicker) * 0.3
    chip = [W // 2 - kw / 2 - 26, y, W // 2 + kw / 2 + 26, y + 58]
    d.rounded_rectangle(chip, radius=29, fill=RED + (255,))
    x = chip[0] + 26
    for ch in kicker:  # tracked caps
        d.text((x, y + 29), ch, font=kf, fill=WHITE + (255,), anchor="lm")
        x += d.textlength(ch, font=kf) + 2.4
    y += 80
    for line in lines:
        y = text_centre(d, y, line, tf, WHITE + (255,)) + 16
    # small sun-orange underline
    d.rounded_rectangle([W // 2 - 60, y + 6, W // 2 + 60, y + 14], radius=4, fill=ORANGE + (255,))
    return with_shadow(layer, blur=9, offset=(0, 4), strength=170)


def title_card():
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([-80, 640, W + 80, 1240], fill=150)
    layer = Image.new("RGBA", (W, H), INK + (255,))
    layer.putalpha(glow.filter(ImageFilter.GaussianBlur(90)))
    text = blank()
    d = ImageDraw.Draw(text)
    y = 760
    y = text_centre(d, y, "Unforgettable", font("Pacifico-Regular.ttf", 104), ORANGE + (255,)) + 4
    y = text_centre(d, y, "THAILAND", font("Montserrat-ExtraBold.ttf", 150), WHITE + (255,)) + 34
    sub = "A trip our travellers will never forget"
    text_centre(d, y, sub, font("Poppins-SemiBold.ttf", 44), WHITE + (255,))
    layer.alpha_composite(with_shadow(text, blur=12, offset=(0, 6), strength=200))
    return layer


def end_message():
    layer = blank()
    d = ImageDraw.Draw(layer)
    y = 560
    y = text_centre(d, y, "Thank you, travellers!", font("Pacifico-Regular.ttf", 84), ORANGE + (255,)) + 34
    body = font("Montserrat-ExtraBold.ttf", 60)
    for line in wrap(d, "Our guests thoroughly enjoyed every moment of their Thailand vacation with us.", body, 820):
        y = text_centre(d, y, line, body, WHITE + (255,)) + 18
    return with_shadow(layer, blur=12, offset=(0, 6), strength=210)


def end_cta():
    layer = blank()
    d = ImageDraw.Draw(layer)
    y = 1130
    y = text_centre(d, y, "For such bookings, call us", font("Poppins-SemiBold.ttf", 52), WHITE + (255,)) + 30
    # phone button
    pf = font("Montserrat-ExtraBold.ttf", 76)
    num = "+91 82409 97561"
    icon_f = ImageFont.truetype(str(HERE.parent / "reel" / "assets" / "fonts" / "MaterialSymbolsRounded-Filled.ttf"), 70)
    tw = d.textlength(num, font=pf)
    iw = 70
    bw = tw + iw + 24 + 2 * 46
    x0, x1 = W / 2 - bw / 2, W / 2 + bw / 2
    y1 = y + 128
    d.rounded_rectangle([x0, y, x1, y1], radius=64, fill=RED + (255,))
    d.rounded_rectangle([x0 + 6, y + 6, x1 - 6, y1 - 6], radius=58, outline=(255, 255, 255, 120), width=3)
    cy = (y + y1) / 2
    d.text((x0 + 46, cy), "call", font=icon_f, fill=WHITE + (255,), anchor="lm")
    d.text((x0 + 46 + iw + 24, cy), num, font=pf, fill=WHITE + (255,), anchor="lm")
    y = y1 + 36
    text_centre(d, y, "Hic Et Ubique  ·  Complete Tourism Solution", font("Poppins-Medium.ttf", 36),
                (255, 255, 255, 235))
    return with_shadow(layer, blur=12, offset=(0, 6), strength=200)


def end_scrim():
    col = Image.new("L", (1, H), 150)
    layer = Image.new("RGBA", (W, H), (10, 8, 20, 255))
    layer.putalpha(col.resize((W, H)))
    return layer


# --- edit --------------------------------------------------------------------

def timeline():
    """Start time of each shot on the output timeline, plus total length."""
    starts, t = [], 0.0
    for clip, tin, dur, speed in SHOTS:
        starts.append(t)
        t += dur / speed - XF
    return starts, t + XF


def cut_shots(src, work):
    paths = []
    for i, (clip, tin, dur, speed) in enumerate(SHOTS):
        out = work / f"shot{i:02d}.mp4"
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
              f"setsar=1,setpts=(PTS-STARTPTS)/{speed},fps={FPS},"
              "eq=saturation=1.14:contrast=1.04:brightness=0.01,unsharp=5:5:0.55,format=yuv420p")
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(tin), "-t", str(dur), "-i", str(src / f"{clip}.mp4"),
             "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "14", str(out)])
        paths.append(out)
    return paths


def main(src, out):
    src, out = Path(src), Path(out)
    work = out.parent / "work"
    work.mkdir(parents=True, exist_ok=True)
    starts, total = timeline()
    print(f"timeline {total:.2f}s over {len(SHOTS)} shots")

    # graphics: (png, t_in, t_out, slide)
    end_t = starts[-1]
    g = [
        (lower_scrim(), 0.0, end_t + XF, False),
        (title_card(), 0.4, starts[1] + 0.2, True),
        (caption("ISLAND HOPPING", "Speedboat rides past limestone cliffs"), starts[1] + 0.5, starts[3] + 0.2, True),
        (caption("ALL SMILES", "Happy travellers, happy memories"), starts[3] + 0.5, starts[5] + 0.2, True),
        (caption("KRABI", "Rainforest trails & hidden lagoons"), starts[8] + 0.5, starts[11] + 1.5, True),
        (caption("EMERALD POOL", "A dip in nature's own pool"), starts[12] + 0.5, starts[14] + 0.3, True),
        (caption("PURE JOY", "Every moment, thoroughly enjoyed"), starts[15] + 0.6, starts[18] + 0.2, True),
        (end_scrim(), end_t + 0.2, total, False),
        (end_message(), end_t + 0.6, total, True),
        (end_cta(), end_t + 2.6, total, True),
        (logo_card(), 0.0, total, False),  # last, so nothing dims it
    ]
    pngs = []
    for k, (img, t0, t1, slide) in enumerate(g):
        p = work / f"gfx{k:02d}.png"
        img.save(p)
        pngs.append((p, t0, t1, slide))

    shots = cut_shots(src, work)

    music = work / "music.wav"
    run([sys.executable, str(HERE / "music.py"), str(music), f"{total:.3f}"])
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(music), "-af",
                           "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    loud = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
            f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:linear=true")

    cmd = ["ffmpeg", "-v", "error", "-stats", "-y"]
    for s in shots:
        cmd += ["-i", str(s)]
    for p, *_ in pngs:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(p)]
    cmd += ["-i", str(music)]

    fc = []
    prev = "[0:v]"
    for i in range(1, len(shots)):
        lbl = f"[x{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={starts[i]:.3f}{lbl}")
        prev = lbl
    base = len(shots)
    for k, (p, t0, t1, slide) in enumerate(pngs):
        fi = 0.45
        fc.append(f"[{base + k}:v]format=rgba,fade=t=in:st={t0:.3f}:d={fi}:alpha=1,"
                  f"fade=t=out:st={max(t0, t1 - fi):.3f}:d={fi}:alpha=1[g{k}]")
        y = f"'40*max(0,1-(t-{t0:.3f})/0.6)'" if slide else "0"
        fc.append(f"{prev}[g{k}]overlay=x=0:y={y}:enable='between(t,{t0:.3f},{t1:.3f})'[o{k}]")
        prev = f"[o{k}]"
    fc.append(f"{prev}format=yuv420p[v]")
    fc.append(f"[{base + len(pngs)}:a]{loud},aresample=48000[a]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "8M", "-bufsize", "16M", "-profile:v", "high", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(out)]
    run(cmd)
    print(f"wrote {out} ({probe_duration(out):.2f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
