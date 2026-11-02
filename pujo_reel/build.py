#!/usr/bin/env python3
"""Cut the Eventia Durga Puja promo Reel (1080x1920, 30 fps, 21.3 s).

Edit style follows the reference: hard cuts on the beat, flash-montage
sections (4-frame shots) alternating with slow hero shots, a fixed top text
block, then a "How Eventia can help you" section and a Book-now end card.

Usage: python3 build.py CLIPS_DIR OUT.mp4 [WORK_DIR]
CLIPS_DIR holds the original VID_20261016_*.mp4 files from the client's Drive.
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
BEAT = 16   # frames; 112.5 BPM at 30 fps (see music.py)
BAR = 64

# short ids -> source files (all shot 16 Oct 2026 on the North Kolkata trail)
SRC = {
    "street": "084143104", "redgate": "105713545", "pyramid": "105934844", "bus": "110604620",
    "walk": "113656156", "mud": "113954560", "busin": "120133492", "gate": "122534661",
    "mondrian": "122624838", "temple_walk": "125021591", "temple": "125151748",
    "facade": "125223116", "bagbazar": "125235120", "chandelier": "125303844",
    "crowd": "134146316", "rajbari_yard": "135442891", "rajbari": "135458844",
    "rb_idol": "140543266", "hall": "140849258", "rb_inside": "140912888",
    "lunch_hall": "143053271", "lunch": "143143485",
}

# Edit decision list: (section, shot id, source start seconds, length in frames)
FLASH = 4
EDL = []


def add(section, shots, frames):
    for sid, t in shots:
        EDL.append((section, sid, t, frames))


# bars 0-1: flash montage, 32 x 4 frames
add("title", [
    ("bagbazar", 20), ("pyramid", 3.5), ("chandelier", 2), ("mondrian", 47), ("temple_walk", 20),
    ("street", 41), ("rb_idol", 8), ("rajbari", 3), ("temple", 3), ("redgate", 1),
    ("mud", 26.5), ("rajbari_yard", 8), ("hall", 6), ("crowd", 4), ("rb_inside", 15),
    ("facade", 3), ("gate", 12), ("walk", 1), ("mondrian", 20), ("lunch", 2),
    ("pyramid", 5.5), ("bagbazar", 9), ("street", 30), ("bus", 3), ("temple_walk", 32),
    ("chandelier", 4.5), ("rajbari", 7), ("lunch_hall", 1), ("mondrian", 26), ("mud", 27.5),
    ("rajbari_yard", 4), ("rb_idol", 9.5),
], FLASH)
# bar 2: four slow hero shots, one per beat
add("title", [("temple", 3.0), ("pyramid", 4.0), ("chandelier", 2.5), ("rajbari_yard", 8.5)], BEAT)
# bars 3-5: how Eventia helps, two half-bar shots per benefit
add("help_1", [("bus", 1.0), ("busin", 1.5)], BAR // 2)
add("help_2", [("facade", 0.5), ("mondrian", 30.0)], BAR // 2)
add("help_3", [("rajbari", 2.0), ("lunch", 3.0)], BAR // 2)
# bar 6: second flash montage, 16 x 4 frames
add("title", [
    ("mud", 27), ("street", 42), ("mondrian", 46), ("hall", 7), ("pyramid", 6), ("facade", 4),
    ("rb_inside", 5), ("bagbazar", 22), ("redgate", 3), ("temple_walk", 36), ("rb_idol", 7),
    ("chandelier", 3), ("rajbari_yard", 9.5), ("temple", 6), ("mondrian", 13), ("rajbari", 5),
], FLASH)
# bars 7-9: end card over the two best idol shots
add("cta", [("bagbazar", 18.0), ("rb_idol", 6.0)], BAR * 3 // 2)

# Warm, punchy grade: lift contrast/saturation, warm mids, a touch of sharpening.
GRADE = ("eq=contrast=1.10:saturation=1.38:gamma=0.96,"
         "colorbalance=rm=0.05:gm=0.0:bm=-0.05:rh=0.03:bh=-0.04,"
         "unsharp=5:5:0.6:5:5:0.0,"
         "vignette=PI/6")


def cut(args):
    i, (section, sid, t, frames), clips, work = args
    out = work / f"seg_{i:03d}.mp4"
    src = clips / f"VID_20261016_{SRC[sid]}.mp4"
    vf = (f"fps={FPS},scale=1080:1920:force_original_aspect_ratio=increase,"
          f"crop=1080:1920,setsar=1,{GRADE},format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src),
                    "-frames:v", str(frames), "-an", "-vf", vf,
                    "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-r", str(FPS), str(out)],
                   check=True)
    return out


def main(clips, out, work):
    clips, out, work = Path(clips), Path(out), Path(work)
    work.mkdir(parents=True, exist_ok=True)
    total = sum(e[3] for e in EDL)
    print(f"{len(EDL)} shots, {total} frames = {total / FPS:.2f}s")

    with ThreadPoolExecutor(4) as ex:
        segs = list(ex.map(cut, [(i, e, clips, work) for i, e in enumerate(EDL)]))
    (work / "concat.txt").write_text("".join(f"file '{s}'\n" for s in segs))

    ov = work / "overlays"
    subprocess.run([sys.executable, str(HERE / "overlays.py"), str(ov)], check=True)
    music = work / "music.wav"
    subprocess.run([sys.executable, str(HERE / "music.py"), str(music), f"{total / FPS:.3f}"], check=True)

    # overlay windows in frames, from the EDL's contiguous sections
    windows, f = [], 0
    for section, _, _, n in EDL:
        if windows and windows[-1][0] == section and windows[-1][2] == f:
            windows[-1][2] = f + n
        else:
            windows.append([section, f, f + n])
        f += n
    inputs = []
    for section, _, _ in windows:  # one still input per window (a stream can't feed two overlays)
        inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(ov / f"{section}.png")]
    names = windows
    chain, last = [], "[0:v]"
    for k, (section, a, b) in enumerate(windows):
        tag = f"[v{k}]"
        chain.append(f"{last}[{k + 1}:v]overlay=0:0:shortest=1:enable='between(n,{a},{b - 1})'{tag}")
        last = tag
    chain.append(f"{last}format=yuv420p[vout]")

    cmd = (["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "concat.txt")]
           + inputs + ["-i", str(music), "-filter_complex", ";".join(chain),
                       "-map", "[vout]", "-map", f"{len(names) + 1}:a",
                       "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-profile:v", "high",
                       "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-shortest",
                       "-movflags", "+faststart", str(out)])
    subprocess.run(cmd, check=True)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "work")
