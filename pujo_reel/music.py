#!/usr/bin/env python3
"""Synthesise an original, royalty-free dhak + kashor Pujo beat (no samples).

112.5 BPM so that one 16th note is exactly 4 video frames at 30 fps
(beat = 16 frames, bar = 64 frames) and every cut in build.py lands on the grid.

Sections follow the edit (bar = 2.1333 s):
  bars 0-1  full dhak groove + kashor        (fast flash montage)
  bar  2    big hits on each beat, drone     (slow hero shots)
  bars 3-5  groove + flute melody            ("How Eventia can help you")
  bar  6    16th-note dhak roll, crescendo   (second fast montage)
  bars 7-9  gong hit, drone + melody, fade   (CTA end card)

Usage: python3 music.py OUT.wav [SECONDS] [v1|tour]
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 112.5
BEAT = 60 / BPM
STEP = BEAT / 4
BAR = 4 * BEAT
rng = np.random.default_rng(11)


def env(n, decay):
    return np.exp(-np.arange(n) / (decay * SR))


def place(buf, t, sig, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def dhak_low(pitch=1.0):
    """Big barrel drum: pitch-dropping membrane + skin slap."""
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = (78 + 90 * np.exp(-t / 0.03)) * pitch
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.17)
    body += 0.35 * np.sin(2 * np.pi * np.cumsum(f * 1.52) / SR) * env(n, 0.07)
    slap = rng.standard_normal(n) * env(n, 0.012)
    return np.tanh(1.6 * (body + 0.25 * slap))


def dhak_high(pitch=1.0):
    """Thin stick on the high head: tight tone + crack."""
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 330 * pitch * t) * env(n, 0.04)
    crack = np.diff(rng.standard_normal(n + 1)) * env(n, 0.008)
    return 0.7 * tone + 0.35 * crack


def kashor(decay=0.35):
    """Bell-metal plate struck with a stick: inharmonic partials."""
    n = int((decay * 3) * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for f, a, d in ((612, 1, 1), (1287, .7, .8), (1934, .5, .6), (2771, .35, .45), (3913, .25, .3)):
        sig += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * env(n, decay * d)
    sig += 0.3 * np.diff(rng.standard_normal(n + 1)) * env(n, 0.01)
    return sig * 0.35


def gong(seconds=3.5):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for f, a in ((98, 1), (147.5, .6), (231, .45), (318, .3), (452, .2)):
        sig += a * np.sin(2 * np.pi * f * (1 + 0.004 * np.sin(2 * np.pi * 3 * t)) * t) * env(n, seconds / 3)
    return sig * np.minimum(1, t / 0.01) * 0.5


def drone(dur, root=146.83):  # D3 - harmonium-ish sa-pa drone
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for f, a in ((root, 1), (root * 1.5, .55), (root * 2, .45)):
        for h in range(1, 7):
            sig += a / h * np.sin(2 * np.pi * f * h * (1 + rng.uniform(-.001, .001)) * t + rng.uniform(0, 6))
    sig = lowpass(sig, 1400)
    att = np.minimum(1, t / 0.4)
    rel = np.clip((dur - t) / 0.8, 0, 1)
    return sig * att * rel / 6


def flute(f, dur):
    n = int((dur + 0.25) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t / 0.25)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    sig = np.sin(ph) + 0.18 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    sig += 0.04 * lowpass(rng.standard_normal(n), 3000)  # breath
    a = np.minimum(1, t / 0.05)
    r = np.clip((dur + 0.25 - t) / 0.25, 0, 1)
    return sig * a * r


def reverb(x, seconds=1.4, mix=0.25):
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * env(n, seconds / 5)
    ir[0] = 0
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-9)
    return (1 - mix) * x + mix * wet


# D major-pentatonic-ish (Bhupali: Sa Re Ga Pa Dha) around D4
SA = 293.66
SW = {"S": 1, "R": 9 / 8, "G": 5 / 4, "P": 3 / 2, "D": 5 / 3, "S'": 2, "R'": 9 / 4, "G'": 5 / 2}
# (step offset within a 2-bar phrase, swara, length in steps)
PHRASE_A = [(0, "G", 2), (2, "P", 2), (4, "D", 4), (8, "S'", 6), (14, "D", 2),
            (16, "P", 4), (20, "G", 2), (22, "R", 2), (24, "G", 8)]
PHRASE_B = [(0, "P", 2), (2, "D", 2), (4, "S'", 4), (8, "R'", 4), (12, "S'", 4),
            (16, "D", 3), (19, "P", 1), (20, "G", 4), (24, "S", 8)]

# 16-step dhak groove: L = low, h = high tap, H = accented high, . = rest
GROOVE = "L.hLh.LhL.hLH.hh"
ROLL = "LhhhLhhhLhhhLHHH"


def build(seconds):
    n = int(seconds * SR)
    drums, metal, tonal, fx = (np.zeros(n) for _ in range(4))

    def groove(b, pattern, gain=1.0):
        t0 = b * BAR
        for k, c in enumerate(pattern):
            t = t0 + k * STEP
            if c == "L":
                place(drums, t, dhak_low(), 0.95 * gain)
            elif c == "h":
                place(drums, t, dhak_high(), 0.32 * gain * (0.8 + 0.4 * rng.random()))
            elif c == "H":
                place(drums, t, dhak_high(1.05), 0.55 * gain)
        for k in range(4):  # kashor on the off-beats
            place(metal, t0 + k * BEAT + BEAT / 2, kashor(0.22), 0.55 * gain)

    def melody(b0, phrase, gain=0.32):
        for off, sw, ln in phrase:
            place(tonal, b0 * BAR + off * STEP, flute(SA * SW[sw], ln * STEP), gain)

    # bars 0-1: full groove, opening hit
    place(fx, 0, gong(2.5), 0.55)
    groove(0, GROOVE)
    groove(1, GROOVE[:12] + "LHLH")
    # bar 2: four big hits for the four hero shots
    for k in range(4):
        place(drums, 2 * BAR + k * BEAT, dhak_low(0.9), 1.0)
        place(drums, 2 * BAR + k * BEAT, dhak_low(1.3), 0.5)
        place(metal, 2 * BAR + k * BEAT, kashor(0.5), 0.5)
    place(tonal, 2 * BAR, drone(BAR * 4 + 0.6), 0.5)
    # bars 3-5: lighter groove under the flute
    for b in (3, 4, 5):
        groove(b, GROOVE, 0.7)
    melody(3, PHRASE_A)
    melody(5, PHRASE_B[:8])
    # bar 6: roll crescendo
    for k, c in enumerate(ROLL):
        g = 0.55 + 0.6 * k / 15
        t = 6 * BAR + k * STEP
        place(drums, t, dhak_low() if c == "L" else dhak_high(1 + 0.02 * (k % 4)), g * (0.95 if c == "L" else 0.6))
        place(metal, t, kashor(0.12), 0.25 * g)
    # bars 7-9: gong + drone + melody, sparse dhak, fade
    place(fx, 7 * BAR, gong(4.5), 0.8)
    place(drums, 7 * BAR, dhak_low(0.85), 1.1)
    place(tonal, 7 * BAR, drone(max(0.5, seconds - 7 * BAR)), 0.55)
    melody(7, PHRASE_B, 0.34)
    for b in (7, 8):
        for k in (0, 6, 8, 11):
            place(drums, b * BAR + k * STEP, dhak_low(), 0.55)
        for k in range(4):
            place(metal, b * BAR + k * BEAT + BEAT / 2, kashor(0.22), 0.35)
    place(drums, 9 * BAR, dhak_low(0.85), 0.9)
    place(fx, 9 * BAR, gong(3.0), 0.5)

    tonal = reverb(tonal, 1.6, 0.3)
    metal = reverb(metal, 1.0, 0.2)
    drums = reverb(drums, 0.8, 0.12)
    d = int(0.012 * SR)  # tiny Haas offset for width on metal/flute
    L = drums + metal + 0.9 * tonal + fx
    R = drums + np.concatenate([np.zeros(d), metal[:-d]]) + np.concatenate([np.zeros(d), tonal[:-d]]) + fx
    mix = np.stack([L, R], axis=1)
    mix /= np.percentile(np.abs(mix), 99.9)
    mix = np.tanh(mix * 0.95)
    mix /= np.max(np.abs(mix)) / 0.89
    fi, fo = int(0.02 * SR), int(2.0 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return mix


def build_tour(seconds, chapter_bars=(2, 4, 6, 9, 11), end_bar=13):
    """Longer, calmer arrangement for the tour-story cut (V2).

    bars 0-1 full groove (hook montage); then a lighter groove with flute
    phrases, a big hit + kashor accent on each chapter change; from end_bar
    the gong / drone / melody outro, fading out.
    """
    n = int(seconds * SR)
    drums, metal, tonal, fx = (np.zeros(n) for _ in range(4))

    def groove(b, pattern, gain=1.0):
        t0 = b * BAR
        for k, c in enumerate(pattern):
            t = t0 + k * STEP
            if c == "L":
                place(drums, t, dhak_low(), 0.95 * gain)
            elif c == "h":
                place(drums, t, dhak_high(), 0.32 * gain * (0.8 + 0.4 * rng.random()))
            elif c == "H":
                place(drums, t, dhak_high(1.05), 0.55 * gain)
        for k in range(4):
            place(metal, t0 + k * BEAT + BEAT / 2, kashor(0.22), 0.55 * gain)

    def melody(b0, phrase, gain=0.3):
        for off, sw, ln in phrase:
            place(tonal, b0 * BAR + off * STEP, flute(SA * SW[sw], ln * STEP), gain)

    place(fx, 0, gong(2.5), 0.55)
    groove(0, GROOVE)
    groove(1, GROOVE[:12] + "LHLH")
    place(tonal, 2 * BAR, drone((end_bar - 2) * BAR + 0.6), 0.4)
    for b in range(2, end_bar):
        groove(b, GROOVE, 0.6)
        if b in chapter_bars:
            place(drums, b * BAR, dhak_low(0.9), 1.0)
            place(metal, b * BAR, kashor(0.5), 0.45)
    phrases = [PHRASE_A, PHRASE_B]
    for k, b in enumerate(range(2, end_bar - 1, 2)):
        melody(b, phrases[k % 2])
    for k, c in enumerate(ROLL):  # roll into the outro
        g = 0.4 + 0.5 * k / 15
        t = (end_bar - 1) * BAR + k * STEP
        place(drums, t, dhak_low() if c == "L" else dhak_high(1 + 0.02 * (k % 4)), g * (0.9 if c == "L" else 0.55))
    place(fx, end_bar * BAR, gong(4.5), 0.8)
    place(drums, end_bar * BAR, dhak_low(0.85), 1.1)
    place(tonal, end_bar * BAR, drone(max(0.5, seconds - end_bar * BAR)), 0.55)
    melody(end_bar, PHRASE_B, 0.34)
    for b in range(end_bar, int(seconds / BAR)):
        for k in (0, 6, 8, 11):
            place(drums, b * BAR + k * STEP, dhak_low(), 0.5)
        for k in range(4):
            place(metal, b * BAR + k * BEAT + BEAT / 2, kashor(0.22), 0.3)
    return master(drums, metal, tonal, fx)


def master(drums, metal, tonal, fx):
    tonal = reverb(tonal, 1.6, 0.3)
    metal = reverb(metal, 1.0, 0.2)
    drums = reverb(drums, 0.8, 0.12)
    d = int(0.012 * SR)
    L = drums + metal + 0.9 * tonal + fx
    R = drums + np.concatenate([np.zeros(d), metal[:-d]]) + np.concatenate([np.zeros(d), tonal[:-d]]) + fx
    mix = np.stack([L, R], axis=1)
    mix /= np.percentile(np.abs(mix), 99.9)
    mix = np.tanh(mix * 0.95)
    mix /= np.max(np.abs(mix)) / 0.89
    fi, fo = int(0.02 * SR), int(2.0 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return mix


def save(path, mix):
    pcm = (mix * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    out = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 10 * BAR
    variant = sys.argv[3] if len(sys.argv) > 3 else "v1"
    save(out, build_tour(seconds) if variant == "tour" else build(seconds))
    print(f"wrote {out} ({seconds:.2f}s, {BPM} BPM)")
