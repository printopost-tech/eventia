#!/usr/bin/env python3
"""Synthesise an original, royalty-free, soothing resort-ambience track (no samples).

72 BPM, D major: Dmaj7 - Bm7 - Gmaj7 - A(sus), a warm slow-attack pad, a
soft kalimba-style arpeggio, a gentle sub-bass note per bar and sparse high
chimes through a long reverb. No drums - it is meant to sit under footage of
a calm hilltop resort and end on a held, ringing chord.

Usage: python3 music.py OUT.wav [SECONDS]
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 72
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(5)

NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((12 * (octave + 1) + NOTE[pitch] - 69) / 12)


CHORDS = [  # (bass, pad voicing, arpeggio tones low->high)
    ("D2", ["D3", "F#3", "A3", "C#4", "E4"], ["D4", "A4", "C#5", "F#5", "A4", "E5", "C#5", "A4"]),
    ("B1", ["B2", "D3", "F#3", "A3", "D4"], ["B3", "F#4", "A4", "D5", "F#4", "B4", "A4", "F#4"]),
    ("G2", ["G2", "D3", "F#3", "B3", "D4"], ["G3", "D4", "F#4", "B4", "D5", "B4", "F#4", "D4"]),
    ("A2", ["A2", "E3", "G3", "B3", "E4"], ["A3", "E4", "G4", "B4", "E5", "B4", "G4", "E4"]),
]
CHIMES = ["F#5", "A5", "B5", "D6", "E6", "F#6"]


def env(n, decay):
    return np.exp(-np.arange(n) / (decay * SR))


def place(buf, t, sig, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += gain * sig[: j - i]


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for f in freqs:
        for det in (-0.18, 0.0, 0.18):
            for h, a in ((1, 1), (2, .25), (3, .08)):
                sig += a * np.sin(2 * np.pi * f * h * (1 + det / 100) * t + rng.uniform(0, 6.28))
    att = np.minimum(1, t / 1.3)
    rel = np.clip((dur - t) / 1.6, 0, 1)
    return sig * att * rel / (len(freqs) * 3.5)


def kalimba(f, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) * env(n, 0.55)
           + 0.28 * np.sin(2 * np.pi * f * 5.4 * t) * env(n, 0.05)
           + 0.08 * np.sin(2 * np.pi * f * 8.9 * t) * env(n, 0.02))
    return sig * np.minimum(1, t / 0.002)


def bass(f, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.15) * np.clip((dur - t) / 0.8, 0, 1)


def chime(f):
    n = int(3.2 * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * env(n, 0.5)
           + 0.2 * np.sin(2 * np.pi * f * 5.4 * t) * env(n, 0.25)) * env(n, 0.9)
    return sig * np.minimum(1, t / 0.003)


def reverb(x, seconds=3.0, mix=0.4):
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * env(n, seconds / 4.5)
    ir[0] = 0
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-9)
    return (1 - mix) * x + mix * wet


def build(seconds):
    n = int(seconds * SR)
    pads, arp, low, bells = (np.zeros(n) for _ in range(4))
    bars = int(np.ceil(seconds / BAR))
    last = bars - 1
    for b in range(bars):
        t0 = b * BAR
        bass_n, voicing, tones = CHORDS[b % 4]
        final = b == last
        place(pads, t0, pad([hz(v) for v in voicing], BAR * (2.2 if final else 1) + 1.0), 0.8)
        place(low, t0, bass(hz(bass_n), BAR * (2.2 if final else 1)), 0.7)
        if b >= 1 and not final:  # arpeggio enters after the first bar
            for k, tone in enumerate(tones):
                place(arp, t0 + k * BEAT / 2, kalimba(hz(tone)), 0.34 * (0.85 + 0.3 * rng.random()))
        if b >= 2 and not final:  # a couple of chimes per bar, off the grid
            for _ in range(2):
                place(bells, t0 + rng.uniform(0.2, BAR - 0.4), chime(hz(CHIMES[rng.integers(len(CHIMES))])), 0.1)
    place(arp, last * BAR, kalimba(hz("D5"), 3.0), 0.4)
    place(arp, last * BAR + BEAT, kalimba(hz("A5"), 3.0), 0.3)
    pads = reverb(pads, 3.2, 0.35)
    arp = reverb(arp, 2.4, 0.38)
    bells = reverb(bells, 3.5, 0.55)
    d = int(0.017 * SR)  # tiny Haas offset: widens the arpeggio and bells
    L = pads + arp + low + bells
    R = pads + np.concatenate([np.zeros(d), arp[:-d]]) + low + np.concatenate([np.zeros(d), bells[:-d]])
    mix = np.stack([L, R], axis=1)
    mix /= np.percentile(np.abs(mix), 99.9)
    mix = np.tanh(mix * 0.9)
    mix /= np.max(np.abs(mix)) / 0.85
    fi, fo = int(1.5 * SR), int(3.5 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None] ** 1.5
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
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    save(sys.argv[1], build(seconds))
    print(f"wrote {sys.argv[1]} ({seconds:.1f}s, {BPM} BPM)")
