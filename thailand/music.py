#!/usr/bin/env python3
"""Synthesise an original, royalty-free tropical-house backing track.

Everything here is generated from scratch (no samples), so the output has no
third-party copyright. 120 BPM, Am-F-C-G, marimba hook, pad, offbeat bass,
four-on-the-floor kick, claps and shaker.

Usage: python3 music.py OUT.wav [SECONDS]
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM          # 0.5 s
BAR = 4 * BEAT           # 2 s
rng = np.random.default_rng(7)

A4 = 440.0
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    """'A3' -> frequency."""
    pitch, octave = name[:-1], int(name[-1])
    midi = 12 * (octave + 1) + NOTE[pitch]
    return A4 * 2 ** ((midi - 69) / 12)


CHORDS = [  # one chord per bar: (bass root, pad voicing)
    ("A2", ["A3", "C4", "E4", "G4"]),   # Am7
    ("F2", ["F3", "A3", "C4", "E4"]),   # Fmaj7
    ("C3", ["G3", "C4", "E4", "G4"]),   # C
    ("G2", ["G3", "B3", "D4", "F#4"]),  # G (with a bright 7th)
]

# Two-bar marimba hooks in A minor pentatonic; (beat offset, note, length in beats)
HOOK_A = [(0, "E5", .5), (.5, "G5", .5), (1, "A5", 1), (2.5, "G5", .5), (3, "E5", 1),
          (4, "D5", .5), (4.5, "E5", .5), (5, "C5", 1), (6.5, "D5", .5), (7, "E5", 1)]
HOOK_B = [(0, "C5", .5), (.5, "E5", .5), (1, "G5", .5), (1.5, "A5", 1), (3, "G5", .5),
          (3.5, "E5", .5), (4, "D5", 1), (5.5, "E5", .5), (6, "G5", .5), (6.5, "E5", .5), (7, "D5", 1)]


def env_exp(n, decay):
    return np.exp(-np.arange(n) / (decay * SR))


def place(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


def marimba(f, dur):
    n = int((dur + 0.9) * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) * env_exp(n, 0.45)
           + 0.35 * np.sin(2 * np.pi * f * 3.93 * t) * env_exp(n, 0.07)
           + 0.12 * np.sin(2 * np.pi * f * 9.2 * t) * env_exp(n, 0.02))
    attack = np.minimum(1, t / 0.003)
    return sig * attack


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.12):  # slight detune for width
            for h, a in ((1, 1), (2, .3), (3, .12)):
                sig += a * np.sin(2 * np.pi * f * h * (1 + det / 100) * t + rng.uniform(0, 6.28))
    attack = np.minimum(1, t / 0.35)
    release = np.minimum(1, (dur - t) / 0.4)
    return sig * attack * np.clip(release, 0, 1) / (len(freqs) * 3)


def bass(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return sig * np.minimum(1, t / 0.008) * env_exp(n, 0.22)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 95 * np.exp(-t / 0.035)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * env_exp(n, 0.12)


def noise_hit(length, decay, hp=True):
    n = int(length * SR)
    x = rng.standard_normal(n)
    if hp:
        x = np.diff(x, prepend=0)  # crude high-pass
    return x * env_exp(n, decay)


def clap():
    sig = np.zeros(int(0.3 * SR))
    for k, d in enumerate((0, 0.011, 0.022)):  # three quick bursts
        place(sig, d, noise_hit(0.25, 0.012 if k < 2 else 0.07), 0.6)
    return sig


def reverb(x, seconds=1.3, mix=0.22):
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * env_exp(n, seconds / 5)
    ir[0] = 0
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-9)
    return (1 - mix) * x + mix * wet


def build(seconds):
    n = int(seconds * SR)
    L, R = np.zeros(n), np.zeros(n)
    melody, pads, drums, low = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    bars = int(np.ceil(seconds / BAR))
    end_groove = seconds - 2 * BAR  # last two bars: let the final chord ring

    for b in range(bars):
        t0 = b * BAR
        root, voicing = CHORDS[b % 4]
        final = t0 >= end_groove
        place(pads, t0, pad([hz(v) for v in voicing], BAR * (2 if final else 1) + 0.3), 0.55)
        if final:
            place(low, t0, bass(hz(root) / 2 * 2, BAR * 2), 0.6)
            place(melody, t0, marimba(hz("A5") if b % 2 == 0 else hz("E5"), 2), 0.5)
            continue
        intro = b < 4
        # bass on the off-beats (tropical bounce)
        if not intro:
            for k in range(4):
                place(low, t0 + k * BEAT + BEAT / 2, bass(hz(root), BEAT * 0.9), 0.75)
        # drums
        for k in range(4):
            if not intro or b >= 2:
                place(drums, t0 + k * BEAT, kick(), 0.9 if not intro else 0.5)
            if not intro and k in (1, 3):
                place(drums, t0 + k * BEAT, clap(), 0.24)
        for k in range(8 if intro else 16):
            step = BAR / (8 if intro else 16)
            accent = 1.0 if k % 2 else 0.55
            place(drums, t0 + k * step, noise_hit(0.05, 0.010), 0.055 * accent)
        # hook: two-bar phrases, alternate A/B every 8 bars
        if b % 2 == 0:
            hook = HOOK_A if (b // 8) % 2 == 0 else HOOK_B
            for off, note, ln in hook:
                place(melody, t0 + off * BEAT, marimba(hz(note), ln * BEAT), 0.42 if intro else 0.5)
                if not intro:  # octave-down doubling for body
                    place(melody, t0 + off * BEAT, marimba(hz(note) / 2, ln * BEAT), 0.15)

    melody = reverb(melody, 1.1, 0.28)
    pads = reverb(pads, 1.6, 0.35)
    # simple stereo image: melody slightly right with a short delay echo left
    delay = int(0.375 * SR)
    echo = np.zeros(n)
    echo[delay:] = melody[:-delay] * 0.28
    L += 0.85 * melody + echo + pads + low + drums
    R += melody + 0.6 * echo + pads + low + drums
    mix = np.stack([L, R], axis=1)
    # soft clip + normalise to -1 dBFS, fade in/out
    mix /= np.percentile(np.abs(mix), 99.9)  # peaks above this get gently rounded
    mix = np.tanh(mix * 0.9)
    mix /= np.max(np.abs(mix)) / 0.89
    fade_in, fade_out = int(0.5 * SR), int(2.5 * SR)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None] ** 1.5
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
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    save(out, build(seconds))
    print(f"wrote {out} ({seconds:.1f}s, {BPM} BPM)")
