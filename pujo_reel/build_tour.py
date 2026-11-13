#!/usr/bin/env python3
"""V2 "tour story" cut of the Eventia Durga Puja Reel (1080x1920, 30 fps, ~34 s).

Client feedback on V1: show that it was a *tour* - bus travel, the guide,
and the photos from the day - at a slower pace. Structure (bar = 64 frames):

  bars 0-1   hook montage, 8-frame cuts (half the V1 speed)   title
  bars 2-3   Meet & board                                    ch_1
  bars 4-5   On the road (bus clips, snack round)            ch_2
  bars 6-8   Guided pandal hopping                           ch_3
  bars 9-10  Rajbari & Mahabhog                              ch_4
  bars 11-12 Memories made (group photos)                    ch_5
  bars 13-15 success-story end card over the group photo     cta

Photos get a slow Ken Burns push-in: portrait shots fill the frame; landscape
group shots sit as a framed print over a blurred copy of themselves so nobody
is cropped out.

Usage: python3 build_tour.py CLIPS_DIR NEW_DIR OUT.mp4 [WORK_DIR]
  CLIPS_DIR  original VID_20261016_*.mp4 files
  NEW_DIR    the WhatsApp exports (IMG-20261103-WA*.jpg, VID-20261103-WA*.mp4)
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from build import FPS, GRADE, SRC

HERE = Path(__file__).resolve().parent
BAR, BEAT, HALF = 64, 16, 32
W, H = 1080, 1920

# clip ids: V1 names (SRC) plus the bus videos from the WhatsApp batch
WA_VID = {"bus_ride": "0064", "bus_ride2": "0062", "bus_ride3": "0058"}

EDL = []  # (section, kind, ref, start_or_mode, frames)


def clip(section, ref, t, frames):
    EDL.append((section, "clip", ref, t, frames))


def photo(section, num, frames, mode="cover", y=None):
    EDL.append((section, "photo", num, (mode, y), frames))


# bars 0-1: hook, alternating idol photos and pandal clips
for p, (c, t) in zip(["0042", "0080", "0029", "0041", "0032", "0040", "0019", "0079"],
                     [("bagbazar", 20), ("pyramid", 4), ("chandelier", 2), ("mondrian", 47),
                      ("rb_idol", 8), ("facade", 3), ("temple_walk", 20), ("rajbari_yard", 8.5)]):
    photo("title", p, 8)
    clip("title", c, t, 8)
# bars 2-3: meet & board
photo("ch_1", "0018", HALF)
photo("ch_1", "0015", HALF)
clip("ch_1", "bus", 1.0, HALF)
photo("ch_1", "0057", HALF)
# bars 4-5: on the road
clip("ch_2", "bus_ride", 2.5, HALF)
clip("ch_2", "busin", 1.5, HALF)
clip("ch_2", "bus_ride2", 4.0, HALF)
clip("ch_2", "bus_ride", 6.0, HALF)   # host walking the aisle with snacks
# bars 6-8: guided pandal hopping (pink-shirt tour lead walking the group in)
clip("ch_3", "gate", 2.0, HALF)
clip("ch_3", "mondrian", 8.0, HALF)
for p in ("0042", "0080", "0029", "0041"):
    photo("ch_3", p, BEAT)
clip("ch_3", "temple", 3.0, HALF)
clip("ch_3", "bagbazar", 19.0, HALF)
# bars 9-10: Rajbari & Mahabhog
clip("ch_4", "rajbari", 2.0, HALF)
clip("ch_4", "rb_inside", 8.0, HALF)
clip("ch_4", "lunch", 3.0, HALF)
clip("ch_4", "hall", 4.0, HALF)
# bars 11-12: memories
photo("ch_5", "0073", HALF, "print", 880)
photo("ch_5", "0089", HALF)
photo("ch_5", "0082", HALF, "print", 880)
photo("ch_5", "0074", HALF)
# bars 13-15: success card over the whole group
photo("cta", "0075", BAR * 3, "print", 640)


def src_path(ref, clips, new):
    if ref in WA_VID:
        return new / f"VID-20261103-WA{WA_VID[ref]}.mp4"
    return clips / f"VID_20261016_{SRC[ref]}.mp4"


def still(num, mode, y, new, out):
    """Compose a 1080x1920 still (2x supersampled for a smooth zoom)."""
    im = ImageOps.exif_transpose(Image.open(new / f"IMG-20261103-WA{num}.jpg")).convert("RGB")
    S = 2
    cw, ch = W * S, H * S
    if mode == "cover":
        canvas = ImageOps.fit(im, (cw, ch), Image.LANCZOS)
    else:  # framed print over a blurred, darkened copy
        bg = ImageOps.fit(im, (cw // 8, ch // 8), Image.LANCZOS).filter(ImageFilter.GaussianBlur(6))
        bg = ImageEnhance.Brightness(bg.resize((cw, ch), Image.LANCZOS)).enhance(0.55)
        pw = int(960 * S)
        ph = round(im.height * pw / im.width)
        pic = im.resize((pw, ph), Image.LANCZOS)
        border = 18 * S
        framed = Image.new("RGB", (pw + 2 * border, ph + 2 * border), (255, 248, 232))
        framed.paste(pic, (border, border))
        framed = framed.rotate(-1.5, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0))
        mask = Image.new("L", (pw + 2 * border, ph + 2 * border), 255).rotate(
            -1.5, resample=Image.BICUBIC, expand=True, fillcolor=0)
        x = (cw - framed.width) // 2
        yy = (y or 900) * S - framed.height // 2
        shadow = Image.new("L", (cw, ch), 0)
        shadow.paste(mask, (x + 10 * S, yy + 16 * S))
        shadow = shadow.filter(ImageFilter.GaussianBlur(18 * S))
        bg.paste((0, 0, 0), (0, 0), shadow.point(lambda v: int(v * 0.7)))
        bg.paste(framed, (x, yy), mask)
        canvas = bg
    canvas.save(out, quality=95)


def render(args):
    i, (section, kind, ref, arg, frames), clips, new, work = args
    out = work / f"seg_{i:03d}.mp4"
    tail = f"setsar=1,{GRADE},format=yuv420p"
    if kind == "clip":
        vf = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{tail}"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{arg:.3f}", "-i", str(src_path(ref, clips, new)),
               "-frames:v", str(frames), "-an", "-vf", vf]
    else:
        mode, y = arg
        img = work / f"still_{i:03d}.jpg"
        still(ref, mode, y, new, img)
        # slow push-in: ~6% over a 32-frame shot, scaled so short and long shots move at similar speed
        rate = 0.0019 if frames <= HALF else 0.0006
        vf = (f"zoompan=z='1+{rate}*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s={W}x{H}:fps={FPS},"
              # photos are already phone-processed: gentler grade than the video clips
              "eq=contrast=1.05:saturation=1.12,colorbalance=rm=0.03:bm=-0.03,format=yuv420p")
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(img), "-frames:v", str(frames), "-vf", vf]
    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "12", "-r", str(FPS), str(out)]
    subprocess.run(cmd, check=True)
    return out


def main(clips, new, out, work):
    clips, new, out, work = Path(clips), Path(new), Path(out), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    total = sum(e[4] for e in EDL)
    print(f"{len(EDL)} shots, {total} frames = {total / FPS:.2f}s")
    with ThreadPoolExecutor(4) as ex:
        segs = list(ex.map(render, [(i, e, clips, new, work) for i, e in enumerate(EDL)]))
    (work / "concat.txt").write_text("".join(f"file '{s}'\n" for s in segs))

    ov = work / "overlays"
    subprocess.run([sys.executable, str(HERE / "overlays.py"), str(ov), "tour"], check=True)
    music = work / "music.wav"
    subprocess.run([sys.executable, str(HERE / "music.py"), str(music), f"{total / FPS:.3f}", "tour"], check=True)

    windows, f = [], 0
    for section, *_, n in EDL:
        if windows and windows[-1][0] == section and windows[-1][2] == f:
            windows[-1][2] = f + n
        else:
            windows.append([section, f, f + n])
        f += n
    inputs, chain, last = [], [], "[0:v]"
    for k, (section, a, b) in enumerate(windows):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(ov / f"{section}.png")]
        chain.append(f"{last}[{k + 1}:v]overlay=0:0:shortest=1:enable='between(n,{a},{b - 1})'[v{k}]")
        last = f"[v{k}]"
    chain.append(f"{last}format=yuv420p[vout]")
    cmd = (["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "concat.txt")]
           + inputs + ["-i", str(music), "-filter_complex", ";".join(chain),
                       "-map", "[vout]", "-map", f"{len(windows) + 1}:a",
                       "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-profile:v", "high",
                       "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-shortest",
                       "-movflags", "+faststart", str(out)])
    subprocess.run(cmd, check=True)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "work_tour")
