"""Upbeat modern pop-house groove, 120 BPM (beat = 0.5s) for Version B."""
import numpy as np, wave, sys
SR = 44100
DUR = float(sys.argv[2])
N = int(SR * DUR); t_all = np.arange(N) / SR
rng = np.random.default_rng(21)
BPM = 120; beat = 0.5; bar = 2.0
def midi(m): return 440 * 2 ** ((m - 69) / 12)
L = np.zeros(N); R = np.zeros(N)
def add(sig, st, pan=0.0, g=1.0):
    i0 = int(st * SR)
    if i0 >= N or i0 < 0: return
    seg = sig[:N - i0] * g
    L[i0:i0 + len(seg)] += seg * np.cos((pan + 1) * np.pi / 4); R[i0:i0 + len(seg)] += seg * np.sin((pan + 1) * np.pi / 4)
def lp(x, c):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / np.sqrt(1 + (f / c) ** 4); return np.fft.irfft(X, len(x))
def hp(x, c): return x - lp(x, c)
# A minor-ish uplifting: Am F C G  (vi IV I V)
prog = [[57, 60, 64], [53, 57, 60], [48, 55, 60, 64], [55, 59, 62]]
roots = [45, 41, 48, 43]
nb = int(np.ceil(DUR / bar)) + 1
def sec(b):
    tt = b * bar
    if tt < 2: return 'intro'          # 0-2 s: build hits
    if tt >= DUR - 4: return 'outro'
    return 'main'
def kick():
    n = int(0.3 * SR); t = np.arange(n) / SR; f = 45 + 110 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10) * 1.0
def clap():
    n = int(0.22 * SR); t = np.arange(n) / SR
    return hp(rng.normal(0, 1, n), 1200) * (np.exp(-t * 22) + 0.6 * np.exp(-((t - .01) * 300) ** 2))
def hat(op=False):
    n = int((0.18 if op else 0.05) * SR); t = np.arange(n) / SR
    return hp(rng.normal(0, 1, n), 7000) * np.exp(-t * (14 if op else 70))
def pluck(f, dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(a * np.sign(np.sin(2 * np.pi * f * k * t)) * np.exp(-t * (9 + 4 * k)) for k, a in ((1, 1), (2, .3)))
    return lp(s * np.minimum(1, t / .003), 3500)
def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return s * np.minimum(1, t / .01) * np.clip((dur - t) / .05, 0, 1)
def padn(fs, dur):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in fs:
        for d in (-.08, .08): s += 2 * ((t * f * 2 ** (d / 12) + rng.uniform()) % 1) - 1
    return lp(s, 1800) * np.minimum(1, t / .3) * np.clip((dur - t) / .4, 0, 1)
for b in range(nb):
    st = b * bar; c = prog[b % 4]; rt = roots[b % 4]; s = sec(b)
    if st >= DUR: break
    add(padn([midi(m) for m in c], bar + .3), st, 0, 0.022 if s != 'intro' else 0.03)
    for q in range(4):
        tq = st + q * beat
        if s == 'main':
            add(kick(), tq, 0, 0.55);
            if q in (1, 3): add(clap(), tq, 0, 0.16)
            add(hat(), tq + beat / 2, 0.3, 0.06); add(hat(True), tq + beat / 2, -0.3, 0.025)
            add(bass(midi(rt - 12), beat / 2 - .02), tq + beat / 2, 0, 0.32)
        elif s == 'intro':
            add(kick(), tq, 0, 0.5)   # 4 hits on the intro word flashes
        else:  # outro: half-time
            if q in (0, 2): add(kick(), tq, 0, 0.45)
            if q == 2: add(clap(), tq, 0, 0.12)
    if s != 'intro':
        arp = [c[0], c[1], c[2], c[1] + 12 if len(c) < 4 else c[3], c[2] + 12, c[1] + 12, c[2], c[1]]
        for j, m in enumerate(arp):
            add(pluck(midi(m + 12)), st + j * beat / 2, 0.35 * (1 if j % 2 else -1), 0.07)
# riser into main + impact
n = int(2 * SR); t = np.arange(n) / SR
add(hp(rng.normal(0, 1, n), 2500) * (t / t[-1]) ** 2 * 0.03, 0)
add(lp(rng.normal(0, 1, int(1.5 * SR)), 150) * np.exp(-np.arange(int(1.5 * SR)) / SR * 3) * 0.5, 2.0)
def rev(x, sd):
    r = np.random.default_rng(sd); n = int(1.2 * SR); t = np.arange(n) / SR
    ir = lp(r.normal(0, 1, n) * np.exp(-t * 5), 6000); ir /= np.sqrt((ir ** 2).sum()); m = len(x) + n
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
L2 = L + rev(L, 1) * .2; R2 = R + rev(R, 2) * .2
env = np.minimum(1, t_all / .05) * np.clip((DUR - t_all) / 1.8, 0, 1); L2 *= env; R2 *= env
mx = max(abs(L2).max(), abs(R2).max()); L2 = np.tanh(L2 / mx * 1.5) * .9; R2 = np.tanh(R2 / mx * 1.5) * .9
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.stack([L2, R2], 1) * 32767).astype(np.int16).tobytes())
print('ok')
