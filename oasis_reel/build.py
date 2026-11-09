#!/usr/bin/env python3
"""Cut the 30 s The Divine Oasis Resort brand reel (1080x1920, 30 fps).

Day -> night story of the resort with guests enjoying it, soft cross-dissolves
(it is a calm, soothing piece), caption per shot, then a brand end card over
the lantern-lit restaurant. 8 shots x 2.7 s + a 8.4 s finale (3.0 s of footage,
then 5.4 s of end card). Landscape footage is cropped to 9:16 with a slow
sideways drift; the two phone clips are natively vertical.

Usage: python3 build.py SRC_DIR OUT.mp4 [WORK_DIR]
  SRC_DIR holds the originals: C0082.MP4 C0083.MP4 C0119.MP4 C0163.MP4 C0133.MP4
          C0236.MP4 C0256.MP4 C0171.MP4 VID20251109152146.mp4
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
SHOT = 81          # 2.7 s of visible footage per shot
XF = 12            # 0.4 s cross-dissolve
TOTAL = 900        # 30.0 s
W, H = 1080, 1920

DAY = ("hqdn3d=1.5:1.5:3:3,eq=contrast=1.06:saturation=1.18:gamma=0.98,"
       "colorbalance=rm=0.03:bm=-0.03,unsharp=5:5:0.5:5:5:0.0")
NIGHT = ("hqdn3d=3:3:5:5,eq=contrast=1.05:saturation=1.12:gamma=1.14:brightness=0.015,"
         "unsharp=5:5:0.45:5:5:0.0")

# (file, start s, crop-centre x at start, at end (0..1 of width), grade, vertical?)
SHOTS = [
    ("VID20251109152146.mp4", 1.5, 0.5, 0.5, DAY, True),    # golden-hour pond, bridge, cottages
    ("C0082.MP4", 2.0, 0.42, 0.50, DAY, False),             # water -> pool reveal
    ("C0083.MP4", 2.0, 0.40, 0.40, DAY, False),             # folk dancers + dhol on the lawn
    ("C0119.MP4", 1.0, 0.30, 0.34, DAY, False),             # buffet, guests
    ("C0163.MP4", 2.0, 0.19, 0.44, NIGHT, False),           # lit entrance sign -> angel statue
    ("C0133.MP4", 12.0, 0.50, 0.50, NIGHT, False),          # Chhau dancer
    ("C0236.MP4", 2.0, 0.55, 0.55, NIGHT, False),           # live band
    ("C0256.MP4", 3.0, 0.42, 0.42, NIGHT, False),           # guests dancing
    ("C0171.MP4", 0.0, 0.50, 0.50, NIGHT, False),           # lantern ceiling -> restaurant (finale)
]
LENGTHS = [SHOT + XF] * 8 + [TOTAL + XF * 8 - (SHOT + XF) * 8]  # finale absorbs the rest


def segment(args):
    i, (name, t0, c0, c1, grade, vertical), frames, src, work = args
    out = work / f"seg_{i}.mp4"
    if vertical:
        # 10% zoom, anchored to the top: drops the phone's own watermark along the bottom edge
        geo = f"scale={int(W * 1.1)}:{int(H * 1.1)}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-ow)/2:0"
    else:
        geo = (f"crop=w=ih*9/16:h=ih:x='(iw-ow)*({c0}+({c1}-{c0})*n/{frames})':y=0,"
               f"scale={W}:{H}:flags=lanczos")
    vf = f"fps={FPS},{geo},{grade},setsar=1,format=yuv420p"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(src / name),
                    "-frames:v", str(frames), "-an", "-vf", vf,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-r", str(FPS), str(out)], check=True)
    return out


def main(src, out, work):
    src, out, work = Path(src), Path(out), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(3) as ex:
        segs = list(ex.map(segment, [(i, s, LENGTHS[i], src, work) for i, s in enumerate(SHOTS)]))

    ov = work / "overlays"
    subprocess.run([sys.executable, str(HERE / "overlays.py"), str(ov)], check=True)
    music = work / "music.wav"
    subprocess.run([sys.executable, str(HERE / "music.py"), str(music), f"{TOTAL / FPS:.3f}"], check=True)

    inputs = []
    for s in segs:
        inputs += ["-i", str(s)]
    chain, acc_len, last = [], LENGTHS[0], "[0:v]"
    for k in range(1, len(segs)):
        off = (acc_len - XF) / FPS
        chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={XF / FPS}:offset={off:.4f}[x{k}]")
        last, acc_len = f"[x{k}]", acc_len + LENGTHS[k] - XF
    assert acc_len == TOTAL, (acc_len, TOTAL)

    # overlays: caption i fades in/out inside shot i; end card fades in 3.0 s into the finale
    idx = len(segs)
    wins = []
    for i in range(8):
        s = i * SHOT / FPS
        wins.append((f"cap_{i}.png", s + 0.35, s + SHOT / FPS - 0.1, True))
    fin = 8 * SHOT / FPS
    wins.append(("end.png", fin + 3.0, TOTAL / FPS, False))
    for k, (png, a, b, fade_out) in enumerate(wins):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{b - a + 1:.3f}", "-i", str(ov / png)]
        dur = b - a
        f = f"[{idx + k}:v]format=rgba,fade=t=in:st=0:d=0.45:alpha=1"
        if fade_out:
            f += f",fade=t=out:st={dur - 0.45:.3f}:d=0.45:alpha=1"
        f += f",setpts=PTS+{a:.3f}/TB[o{k}]"
        chain.append(f)
        chain.append(f"{last}[o{k}]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})':eof_action=pass[v{k}]")
        last = f"[v{k}]"
    chain.append(f"{last}format=yuv420p[vout]")

    a_idx = idx + len(wins)
    cmd = (["ffmpeg", "-nostdin", "-v", "error", "-y"] + inputs + ["-i", str(music),
           "-filter_complex", ";".join(chain),
           "-map", "[vout]", "-map", f"{a_idx}:a", "-af", "loudnorm=I=-14:TP=-1.0:LRA=7",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL / FPS:.3f}",
           "-movflags", "+faststart", str(out)])
    subprocess.run(cmd, check=True)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "work")
