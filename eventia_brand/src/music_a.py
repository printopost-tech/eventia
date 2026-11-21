import numpy as np, wave, sys
SR = 44100
DUR = float(sys.argv[2])
N = int(SR * DUR)
rng = np.random.default_rng(19)
t_all = np.arange(N) / SR

def midi(m): return 440.0 * 2 ** ((m + 3 - 69) / 12)

BPM = 78
beat = 60 / BPM          # 0.833s
bar = beat * 4           # 3.33s
# progression (2 bars each would be long; use 1 bar each), key of D major
# Dmaj9, Bm7, Gmaj7, A6sus -> repeat
chords = [
    [50, 57, 62, 64, 66, 69],   # D maj9
    [47, 54, 59, 62, 66, 69],   # Bm7
    [43, 50, 55, 59, 62, 66],   # Gmaj7
    [45, 52, 57, 62, 64, 69],   # Asus/add9
]
nbars = int(np.ceil(DUR / bar)) + 1

L = np.zeros(N); R = np.zeros(N)

def add(sig, start, pan=0.0, gain=1.0):
    i0 = int(start * SR)
    if i0 >= N: return
    seg = sig[: N - i0] * gain
    l = np.cos((pan + 1) * np.pi / 4); r = np.sin((pan + 1) * np.pi / 4)
    L[i0:i0 + len(seg)] += seg * l
    R[i0:i0 + len(seg)] += seg * r

def lowpass(x, cutoff):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))

# ---- warm pad (detuned saws, low-passed, slow attack) ----
def pad_note(freq, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for det in (-0.12, 0.0, 0.11):
        f = freq * 2 ** (det / 12)
        ph = rng.uniform(0, 1)
        s += 2 * ((t * f + ph) % 1) - 1
    s /= 3
    att, rel = 1.2, 1.6
    env = np.minimum(1, t / att) * np.clip((dur - t) / rel, 0, 1)
    return s * env

pad = np.zeros(N)
for b in range(nbars):
    ch = chords[b % 4]
    st = b * bar
    for m in ch[1:5]:
        sig = pad_note(midi(m), bar + 1.4)
        i0 = int(st * SR); seg = sig[: max(0, N - i0)]
        pad[i0:i0 + len(seg)] += seg
pad = lowpass(pad, 900) * 0.055
add(pad, 0, 0, 1)  # mono centre; widen with delay below
R[int(0.013*SR):] += pad[: N - int(0.013*SR)] * 0.25

# ---- soft felt piano ----
def piano(freq, dur=3.5, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for k, a in enumerate([1, 0.45, 0.22, 0.12, 0.06, 0.03], start=1):
        fk = freq * k * (1 + 0.0004 * k * k)
        s += a * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.2 + 0.9 * k))
    att = np.minimum(1, t / 0.008)
    hammer = np.convolve(rng.normal(0, 1, n), np.ones(24)/24, "same") * np.exp(-t * 60) * 0.008
    return (s * att + hammer) * vel * np.clip((dur - t) / 0.3, 0, 1)

# arpeggio pattern in 8th notes; intensity builds after intro
pattern = [0, 2, 3, 4, 3, 2, 5, 3]  # indices into chord
for b in range(nbars):
    ch = chords[b % 4]
    st = b * bar
    # bass note on beat 1 (from bar 1)
    add(piano(midi(ch[0] - 12 + 12), 4.0, 0.55), st, -0.15)
    if b == 0:
        # sparse intro: just a few notes
        for j, idx in enumerate([3, 4, 5]):
            add(piano(midi(ch[idx] + 12), 3.0, 0.32), st + j * beat * 1.3, 0.2)
        continue
    for j, idx in enumerate(pattern):
        if b >= nbars - 2 and j > 3:  # thin out at the end
            break
        v = 0.30 + 0.06 * (j % 2 == 0)
        if b >= 4: v *= 1.12
        add(piano(midi(ch[idx] + 12), 2.8, v), st + j * beat / 2, 0.25 * np.sin(j))

# ---- melody (upper piano), enters bar 4 ----
mel = {  # bar: [(beat offset, midi, len)]
    4: [(0, 78, 1.5), (1.5, 76, 0.5), (2, 74, 2)],
    5: [(0, 73, 1), (1, 74, 1), (2, 76, 2)],
    6: [(0, 74, 1.5), (1.5, 71, 0.5), (2, 74, 2)],
    7: [(0, 76, 3), (3, 73, 1)],
    8: [(0, 78, 1.5), (1.5, 81, 0.5), (2, 78, 1), (3, 76, 1)],
    9: [(0, 73, 1), (1, 74, 1), (2, 78, 2)],
    10: [(0, 79, 1.5), (1.5, 78, 0.5), (2, 74, 2)],
    11: [(0, 76, 2), (2, 73, 2)],
    12: [(0, 74, 4)],
}
for b, notes in mel.items():
    for off, m, ln in notes:
        add(piano(midi(m), 3.5, 0.42), b * bar + off * beat, 0.05)

# ---- winter bells / celesta sparkles ----
def bell(freq, dur=4.0, vel=1.0):
    n = int(dur * SR); t = np.arange(n) / SR
    s = (np.sin(2*np.pi*freq*t) + 0.5*np.sin(2*np.pi*freq*2.76*t)*np.exp(-t*3)
         + 0.25*np.sin(2*np.pi*freq*5.4*t)*np.exp(-t*6))
    return s * np.exp(-t * 1.4) * np.minimum(1, t / 0.003) * vel
for b in range(1, nbars - 1):
    ch = chords[b % 4]
    for k in range(3):
        m = ch[rng.integers(2, 6)] + 24
        tt = b * bar + rng.choice([0.5, 1.5, 2.5, 3.5]) * beat + k * 0.05
        add(bell(midi(m), 4, 0.07), tt, rng.uniform(-0.8, 0.8))

# ---- airy wind/noise texture (wintry) ----
noise = rng.normal(0, 1, N)
wind = lowpass(noise, 600) - lowpass(noise, 200)
wmod = 0.5 + 0.5 * np.sin(2 * np.pi * t_all / 11.0)
wind *= 0.012 * wmod
L += wind; R += np.roll(wind, 3000)

# ---- reverb (FFT convolution with decaying noise) ----
def reverb(x, seed):
    r = np.random.default_rng(seed)
    n = int(2.8 * SR); t = np.arange(n) / SR
    ir = r.normal(0, 1, n) * np.exp(-t * 2.3)
    ir = lowpass(np.concatenate([ir, np.zeros(len(x))]), 5000)[:n]
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return y
L2 = L * 0.7 + reverb(L, 1) * 0.45
R2 = R * 0.7 + reverb(R, 2) * 0.45

# fades
fi = np.minimum(1, t_all / 1.5)
fo = np.clip((DUR - t_all) / 3.0, 0, 1)
env = fi * fo
L2 *= env; R2 *= env
mx = max(np.abs(L2).max(), np.abs(R2).max())
L2 = np.tanh(L2 / mx * 1.1) * 0.85; R2 = np.tanh(R2 / mx * 1.1) * 0.85
out = (np.stack([L2, R2], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print("ok")
