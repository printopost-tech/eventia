"""Festive, premium New Year track: piano + strings pad + sleigh bells + light beat, builds to a finale."""
import numpy as np, wave, sys
SR = 44100
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 42.0
N = int(SR * DUR)
rng = np.random.default_rng(11)
t_all = np.arange(N) / SR
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
BPM = 100
beat = 60 / BPM
bar = beat * 4
nbars = int(np.ceil(DUR / bar)) + 1
# C major: C  G/B  Am  F | C  G  F  G
chords = [
    [48, 55, 60, 64, 67, 72], [47, 55, 59, 62, 67, 71], [45, 52, 57, 60, 64, 69], [41, 53, 57, 60, 65, 69],
    [48, 55, 60, 64, 67, 72], [43, 55, 59, 62, 67, 71], [41, 53, 57, 60, 65, 69], [43, 55, 59, 62, 65, 71],
]
L = np.zeros(N); R = np.zeros(N)
def add(sig, start, pan=0.0, gain=1.0):
    i0 = int(start * SR)
    if i0 >= N or i0 < 0: return
    seg = sig[: N - i0] * gain
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    L[i0:i0 + len(seg)] += seg * l; R[i0:i0 + len(seg)] += seg * r
def lowpass(x, c):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / np.sqrt(1 + (f / c) ** 4)
    return np.fft.irfft(X, len(x))
def highpass(x, c):
    return x - lowpass(x, c)

# section intensity: intro (bars 0-1), verse (2-5), build (6-7), chorus (8-12), outro
def inten(b):
    if b < 2: return 0
    if b < 6: return 1
    if b < 8: return 2
    if b < nbars - 2: return 3
    return 4

# strings pad
def pad_note(freq, dur):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for det in (-0.1, 0.0, 0.09):
        f = freq * 2 ** (det / 12) * (1 + 0.002 * np.sin(2 * np.pi * 5 * t))
        s += 2 * ((np.cumsum(np.full(n, f)) / SR + rng.uniform()) % 1) - 1
    env = np.minimum(1, t / 0.6) * np.clip((dur - t) / 0.8, 0, 1)
    return s / 3 * env
pad = np.zeros(N)
for b in range(nbars):
    ch = chords[b % 8]; st = b * bar; i0 = int(st * SR)
    if i0 >= N: break
    g = [0.6, 0.8, 0.9, 1.1, 0.8][inten(b)]
    for m in ch[1:5]:
        sig = pad_note(midi(m), bar + 0.8) * g; seg = sig[: N - i0]; pad[i0:i0 + len(seg)] += seg
pad = lowpass(pad, 1400) * 0.05
L += pad; R += np.roll(pad, 500)

# bright piano
def piano(freq, dur=2.5, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for k, a in enumerate([1, 0.5, 0.25, 0.13, 0.07, 0.04], 1):
        s += a * np.sin(2 * np.pi * freq * k * (1 + 0.0004 * k * k) * t) * np.exp(-t * (1.6 + 1.1 * k))
    return s * np.minimum(1, t / 0.005) * vel * np.clip((dur - t) / 0.2, 0, 1)
pat = [2, 3, 4, 3, 5, 3, 4, 3]
for b in range(nbars):
    ch = chords[b % 8]; st = b * bar; I = inten(b)
    add(piano(midi(ch[0]), 3.0, 0.5), st, -0.2)
    if I == 0:
        for j in range(4): add(piano(midi(ch[2 + j % 3] + 12), 2.2, 0.28), st + j * beat, 0.2)
        continue
    for j, ix in enumerate(pat):
        if I == 4 and j > 3: break
        add(piano(midi(ch[ix] + 12), 2.0, 0.27 + 0.05 * (j % 2 == 0)), st + j * beat / 2, 0.3 * np.sin(j))
# melody in chorus
mel = [(0, 76, 1), (1, 79, 1), (2, 81, 1.5), (3.5, 79, 0.5),
       (4, 79, 1), (5, 77, 1), (6, 76, 2),
       (8, 76, 1), (9, 74, 1), (10, 72, 1.5), (11.5, 74, 0.5),
       (12, 76, 1), (13, 77, 1), (14, 79, 2)]
for b0 in (8, 12):
    for off, m, ln in mel:
        tt = b0 * bar + off * beat
        if tt < DUR - 2.5: add(piano(midi(m), 2.8, 0.45), tt, 0.05)

# sleigh bells (noise bursts, high-passed) on 8ths from verse
def jingle(dur=0.18):
    n = int(dur * SR); t = np.arange(n) / SR
    s = rng.normal(0, 1, n) * np.exp(-t * 28)
    for f in (5200, 6800, 8100): s += 0.6 * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t * 35)
    return s
J = np.zeros(N)
for b in range(2, nbars):
    I = inten(b)
    if I == 4: continue
    for j in range(8):
        tt = b * bar + j * beat / 2
        i0 = int(tt * SR)
        if i0 >= N: break
        sig = jingle() * (0.5 if j % 2 else 0.8) * (0.6 if I == 1 else 1); seg = sig[: N - i0]; J[i0:i0 + len(seg)] += seg
J = highpass(J, 3500) * 0.02
L += J * 0.8; R += np.roll(J, 300) * 1.0

# soft beat: kick on 1 & 3 (build/chorus), clap on 2 & 4 (chorus)
def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
def clap():
    n = int(0.25 * SR); t = np.arange(n) / SR
    return highpass(rng.normal(0, 1, n), 900) * (np.exp(-t * 25) + 0.5 * np.exp(-((t - 0.012) * 400) ** 2))
for b in range(nbars):
    I = inten(b)
    for q in range(4):
        tt = b * bar + q * beat
        if I >= 2 and I < 4 and q in (0, 2): add(kick(), tt, 0, 0.32 if I == 3 else 0.2)
        if I == 3 and q in (1, 3): add(clap(), tt, 0, 0.07)
# riser + impact into chorus
cs = 8 * bar
n = int(2 * bar * SR); t = np.arange(n) / SR
riser = highpass(rng.normal(0, 1, n), 2000) * (t / t[-1]) ** 2 * 0.028
add(riser, cs - 2 * bar, 0)
imp = lowpass(rng.normal(0, 1, int(2.5 * SR)), 200) * np.exp(-np.arange(int(2.5 * SR)) / SR * 2.5) * 0.4
add(imp + kick()[:1].sum() * 0, cs, 0); add(kick(), cs, 0, 0.5)

# celesta sparkles
def bell(freq, dur=3.0, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2*np.pi*freq*t) + 0.4*np.sin(2*np.pi*freq*2.76*t)*np.exp(-t*4)
    return s * np.exp(-t * 2) * np.minimum(1, t / 0.002) * vel
for b in range(0, nbars):
    ch = chords[b % 8]
    for k in range(2):
        add(bell(midi(ch[rng.integers(2, 6)] + 24), 3, 0.06), b * bar + rng.choice([1, 2, 3, 3.5]) * beat, rng.uniform(-.8, .8))

def reverb(x, seed):
    r = np.random.default_rng(seed); n = int(2.2 * SR); t = np.arange(n) / SR
    ir = lowpass(r.normal(0, 1, n) * np.exp(-t * 2.8), 6000); ir /= np.sqrt((ir ** 2).sum())
    m = len(x) + n
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
L2 = L * 0.78 + reverb(L, 1) * 0.35; R2 = R * 0.78 + reverb(R, 2) * 0.35
env = np.minimum(1, t_all / 0.8) * np.clip((DUR - t_all) / 2.5, 0, 1)
L2 *= env; R2 *= env
mx = max(np.abs(L2).max(), np.abs(R2).max())
L2 = np.tanh(L2 / mx * 1.2) * 0.88; R2 = np.tanh(R2 / mx * 1.2) * 0.88
out = (np.stack([L2, R2], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print('ok', DUR, 'chorus at', cs)
