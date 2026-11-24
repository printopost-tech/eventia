import sys, os, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = sys.argv[1]           # scratchpad
OUT = sys.argv[2]
PREVIEW = sys.argv[3] if len(sys.argv) > 3 else None
O = S + '/oasis'
SEG = O + '/seg_real'
W, H, FPS = 1080, 1920, 30
XF = 0.12   # near-hard cuts on the beat
F = S + '/fonts/'
def font(n, s): return ImageFont.truetype(F + n, s)

GOLD = (240, 200, 120, 255)
GOLD2 = (255, 226, 160, 255)
CREAM = (255, 244, 225, 255)
WHITE = (255, 255, 255, 255)
MAROON = (120, 16, 22, 255)

# ---------------- scenes ----------------
# seg: file in SEG, pos: horizontal crop position 0..1 (start,end) for slow pan
scenes = [
    dict(seg='dji_fly_20260505_213416', d=4.2, pos=(0.5, 0.5), cap='intro'),
    dict(seg='C0171', d=4.0, pos=(0.40, 0.55), cap='title'),
    dict(seg='C0163', d=3.4, pos=(0.50, 0.50), cap='dates'),
    dict(seg='dji_fly_20260505_173434', d=3.0, pos=(0.5, 0.5), ss=1.0, cap=('Celebrate in', 'Purulia')),
    dict(seg='C0033', d=2.6, pos=(0.35, 0.55)),
    dict(seg='C0060', d=2.8, pos=(0.45, 0.55), cap=('Cozy', 'Cottage Stays')),
    dict(seg='C0119', d=3.0, pos=(0.30, 0.45), cap='food'),
    dict(seg='C0126', d=2.4, pos=(0.45, 0.55), cap='food2'),
    dict(seg='dji_fly_20260505_214014', d=3.2, pos=(0.5, 0.5), cap=('31 DEC', 'Pool Party')),
    dict(seg='C0149', d=3.2, pos=(0.35, 0.55), cap=('31 DEC', 'DJ & Live Band')),
    dict(seg='C0165', d=3.4, pos=(0.60, 0.70), ss=8.0, cap=('31 DEC', 'Cake Cutting & Fireworks'), fw=True),
    dict(seg='C0083', d=3.2, pos=(0.30, 0.48), cap=('1 JAN', 'Tribal Dance')),
    dict(seg='C0133', d=3.2, pos=(0.40, 0.50), cap=('1 JAN', 'Chhau Performance')),
    dict(seg='C0157', d=2.6, pos=(0.45, 0.55)),
    dict(end=True, d=6.8, seg='C0165', ss=3.0, pos=(0.35, 0.45)),
]
t = 0
for s in scenes:
    s['t0s'] = t; s['t1s'] = t + s['d']; t += s['d'] - XF
# ---- beat-sync: scene starts land exactly on song beats ----
SONG_START = 35.97
BEATS = np.load(S + '/oasis/song/beats.npy') - SONG_START
BEATS = BEATS[BEATS >= -0.01]
BOUNDS = [0, 7, 14, 20, 24, 26, 30, 34, 38, 44, 48, 54, 60, 66, 70]   # beat index where each scene starts
assert len(BOUNDS) == len(scenes)
TOTAL = 44.0
for k, s in enumerate(scenes):
    s['t0s'] = 0.0 if k == 0 else float(BEATS[BOUNDS[k]])
    s['t1s'] = (float(BEATS[BOUNDS[k + 1]]) if k + 1 < len(scenes) else TOTAL) + XF
    s['d'] = s['t1s'] - s['t0s']
DROP = float(BEATS[14])
CUTS = [s['t0s'] for s in scenes[1:]]
print('drop at', DROP, 'end card at', scenes[-1]['t0s'])
print('total', TOTAL, flush=True)

# ---------------- video readers ----------------
class Reader:
    def __init__(self, s):
        D = s['d'] + 0.2
        p0, p1 = s['pos']
        path = f"{SEG}/{s['seg']}.mp4"
        vf = (f"fps={FPS},scale=-2:{H}:flags=lanczos,"
              f"crop={W}:{H}:'(iw-{W})*({p0}+({p1}-{p0})*t/{D})':0,"
              f"eq=contrast=1.06:saturation=1.12:gamma=0.98,unsharp=5:5:0.6")
        if s.get('end'):
            vf += ",gblur=sigma=14,eq=brightness=-0.18"
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(s.get('ss', 0)), '-i', path, '-t', str(D),
                                   '-vf', vf, '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  stdout=subprocess.PIPE, bufsize=W * H * 3 * 4)
        self.last = None
    def next(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.last = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        return self.last if self.last is not None else np.zeros((H, W, 3), np.uint8)

# ---------------- graphics helpers ----------------
def shadow_text(lay, xy, text, fnt, fill, anchor='mm', blur=10, alpha=180, glow=None):
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 2, xy[1] + 4), text, font=fnt, fill=(0, 0, 0, alpha), anchor=anchor)
    sh = sh.filter(ImageFilter.GaussianBlur(blur)); lay.alpha_composite(sh)
    if glow:
        g = Image.new('RGBA', lay.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text(xy, text, font=fnt, fill=glow, anchor=anchor)
        lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(lay).text(xy, text, font=fnt, fill=fill, anchor=anchor)

def gold_text(lay, xy, text, fnt, anchor='mm', blur=10):
    """text with vertical gold gradient"""
    m = Image.new('L', lay.size, 0)
    ImageDraw.Draw(m).text(xy, text, font=fnt, fill=255, anchor=anchor)
    bb = m.getbbox()
    if not bb: return
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0)); sh.putalpha(m.point(lambda v: v * 0.75))
    sh = Image.merge('RGBA', (*Image.new('RGB', lay.size, 0).split(), sh.split()[3]))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)), (2, 5))
    grad = np.zeros((H, W, 3), np.float32)
    y0, y1 = bb[1], bb[3]
    yy = np.clip((np.arange(H) - y0) / max(1, y1 - y0), 0, 1)[:, None]
    top = np.array([255, 238, 190]); mid = np.array([236, 190, 105]); bot = np.array([200, 145, 60])
    col = np.where(yy[..., None] < 0.5, top + (mid - top) * (yy[..., None] * 2), mid + (bot - mid) * ((yy[..., None] - 0.5) * 2))
    grad[:] = col[:, 0, :][:, None, :]
    g = Image.fromarray(grad.astype(np.uint8), 'RGB').convert('RGBA'); g.putalpha(m)
    lay.alpha_composite(g)

def backdrop(lay, cy, rx=640, ry=300, a=150):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    g = (np.clip(1 - r, 0, 1) ** 1.4 * a).astype(np.uint8)
    b = np.zeros((H, W, 4), np.uint8); b[..., 3] = g
    lay.alpha_composite(Image.fromarray(b, 'RGBA'))

def ornament(d, cx, y, w=150, col=GOLD):
    d.line((cx - w, y, cx - 18, y), fill=col, width=3)
    d.line((cx + 18, y, cx + w, y), fill=col, width=3)
    d.polygon([(cx, y - 9), (cx + 9, y), (cx, y + 9), (cx - 9, y)], fill=col)

def ribbon(lay, cx, cy, text, fnt, pw=None, ph=120):
    d = ImageDraw.Draw(lay)
    tw = d.textlength(text, font=fnt); pw = pw or tw + 140
    x0, x1, y0, y1 = cx - pw / 2, cx + pw / 2, cy - ph / 2, cy + ph / 2
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 10, x1, y1 + 10), 18, fill=(0, 0, 0, 150))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    pts = [(x0 - 30, cy), (x0, y0), (x1, y0), (x1 + 30, cy), (x1, y1), (x0, y1)]
    d.polygon(pts, fill=GOLD)
    inner = [(x0 - 18, cy), (x0 + 6, y0 + 8), (x1 - 6, y0 + 8), (x1 + 18, cy), (x1 - 6, y1 - 8), (x0 + 6, y1 - 8)]
    d.polygon(inner, fill=(128, 18, 24, 255))
    # subtle top highlight
    hl = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).polygon([(x0 + 6, y0 + 8), (x1 - 6, y0 + 8), (x1 + 4, cy - 10), (x0 - 4, cy - 10)], fill=(255, 255, 255, 28))
    lay.alpha_composite(hl)
    shadow_text(lay, (cx, cy + 2), text, fnt, CREAM, blur=4, alpha=120)

def chip(lay, x, y, text, fnt):
    d = ImageDraw.Draw(lay); tw = d.textlength(text, font=fnt)
    d.rounded_rectangle((x, y, x + tw + 56, y + 70), 35, fill=(128, 18, 24, 240), outline=GOLD, width=3)
    d.text((x + 28 + tw / 2, y + 36), text, font=fnt, fill=GOLD2, anchor='mm')
    return tw + 56

# logo
logo_raw = Image.open(os.path.join(S, '..', 'images', '2.png')).convert('RGBA')
logo_raw = logo_raw.crop(logo_raw.getbbox())
def logo(h):
    w = int(logo_raw.width * h / logo_raw.height)
    im = logo_raw.resize((w * 2, h * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 80, 0)).resize((w, h), Image.LANCZOS)
    return im
def logo_with_shadow(h, sh_a=200):
    lg = logo(h); pad = 30
    out = Image.new('RGBA', (lg.width + 2 * pad, lg.height + 2 * pad), (0, 0, 0, 0))
    a = lg.split()[3].point(lambda v: int(v * sh_a / 255))
    sh = Image.new('RGBA', lg.size, (0, 0, 0, 255)); sh.putalpha(a)
    tmp = Image.new('RGBA', out.size, (0, 0, 0, 0)); tmp.alpha_composite(sh, (pad, pad + 3))
    out.alpha_composite(tmp.filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(tmp.filter(ImageFilter.GaussianBlur(3)))
    out.alpha_composite(lg, (pad, pad))
    return out
LOGO_SMALL = logo_with_shadow(190)
LOGO_POS = (W - LOGO_SMALL.width - 18, 105)

PHONE = '+91 99039 89950'
PLACE = 'Purulia, West Bengal'
WEB = 'thedivineoasisresort.com'

def icon_phone(d, x, y, s, col):
    d.rounded_rectangle((x + s * .22, y, x + s * .78, y + s * 1.2), s * .14, fill=col)
    d.rounded_rectangle((x + s * .30, y + s * .14, x + s * .70, y + s * .95), s * .04, fill=(0, 0, 0, 0))
def icon_pin(d, x, y, s, col):
    d.ellipse((x, y, x + s, y + s), fill=col)
    d.polygon([(x + s * .08, y + s * .62), (x + s * .92, y + s * .62), (x + s / 2, y + s * 1.38)], fill=col)
    d.ellipse((x + s * .32, y + s * .3, x + s * .68, y + s * .66), fill=(0, 0, 0, 0))

def contact_bar():
    hgt = 230
    g = np.zeros((hgt, W, 4), np.uint8)
    g[..., 3] = (np.sin(np.linspace(0, np.pi, hgt)) ** 0.7 * 175).astype(np.uint8)[:, None]
    bar = Image.fromarray(g, 'RGBA'); d = ImageDraw.Draw(bar)
    fn = font('mont600.ttf', 46); fa = font('mont500.ttf', 34)
    tw = d.textlength(PHONE, font=fn); x = (W - tw - 54) / 2
    ic = Image.new('RGBA', (60, 70), (0, 0, 0, 0)); icon_phone(ImageDraw.Draw(ic), 6, 6, 44, GOLD)
    bar.alpha_composite(ic, (int(x - 6), 46)); d.text((x + 54, 44), PHONE, font=fn, fill=WHITE)
    line = f'{PLACE}   •   {WEB}'
    tw = d.textlength(line, font=fa); x = (W - tw - 40) / 2
    ic = Image.new('RGBA', (40, 50), (0, 0, 0, 0)); icon_pin(ImageDraw.Draw(ic), 6, 4, 26, GOLD)
    bar.alpha_composite(ic, (int(x - 4), 122)); d.text((x + 40, 122), line, font=fa, fill=(255, 255, 255, 235))
    return bar
BAR = contact_bar(); BAR_Y = 1450

# caption layers
def make_cap(c):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if c == 'intro':
        backdrop(lay, 820, 600, 430, 165)
        big = logo_with_shadow(470)
        lay.alpha_composite(big, ((W - big.width) // 2, 560))
        shadow_text(lay, (W / 2, 1180), 'PRESENTS', font('cinzel600.ttf', 40), GOLD2, blur=6)
    elif c == 'title':
        backdrop(lay, 860, 700, 420, 170)
        gold_text(lay, (W / 2, 700), 'Christmas &', font('pf_bolditalic.ttf', 130))
        gold_text(lay, (W / 2, 850), 'New Year', font('pf_bolditalic.ttf', 150))
        gold_text(lay, (W / 2, 1000), 'Celebration', font('pf_bolditalic.ttf', 130))
        ornament(d, W / 2, 1110, 220)
        shadow_text(lay, (W / 2, 1170), 'AT THE DIVINE OASIS RESORT', font('cinzel600.ttf', 38), CREAM, blur=6)
    elif c == 'dates':
        backdrop(lay, 860, 650, 300, 150)
        shadow_text(lay, (W / 2, 730), 'JOIN US ON', font('cinzel600.ttf', 44), GOLD2, blur=6)
        ribbon(lay, W / 2, 860, '31 Dec – 1 Jan', font('pf_semibold.ttf', 84), pw=640, ph=140)
        shadow_text(lay, (W / 2, 1010), 'Two nights of celebration', font('pf_italic.ttf', 50), CREAM)
    elif c in ('food', 'food2'):
        backdrop(lay, 860, 680, 300, 165)
        shadow_text(lay, (W / 2, 730), 'ALL MEALS INCLUDED', font('cinzel600.ttf', 40), GOLD2, blur=6)
        shadow_text(lay, (W / 2, 840), 'Breakfast • Snack • Dinner', font('pf_semibold.ttf', 68), WHITE, blur=10)
        fn = font('pf_italic.ttf', 52); tw = d.textlength('Lunch à la carte', font=fn)
        d.rounded_rectangle((W / 2 - tw / 2 - 40, 920, W / 2 + tw / 2 + 40, 1010), 45, fill=(246, 222, 170, 245))
        d.text((W / 2, 963), 'Lunch à la carte', font=fn, fill=(70, 30, 10, 255), anchor='mm')
    else:
        l1, l2 = c
        backdrop(lay, 860, 640, 270, 160)
        if l1 in ('31 DEC', '1 JAN'):
            fnc = font('cinzel700.ttf', 42); tw = ImageDraw.Draw(lay).textlength(l1, font=fnc) + 56
            chip(lay, int(W / 2 - tw / 2), 740, l1, fnc)
            fs = 120 if len(l2) < 14 else (96 if len(l2) < 20 else 82)
            gold_text(lay, (W / 2, 900), l2, font('pf_bolditalic.ttf', fs))
            ornament(d, W / 2, 990, 150)
        else:
            shadow_text(lay, (W / 2, 790), l1.upper(), font('cinzel600.ttf', 44), GOLD2, blur=6)
            gold_text(lay, (W / 2, 900), l2, font('pf_bolditalic.ttf', 120))
            ornament(d, W / 2, 990, 150)
    return lay
for s in scenes:
    if s.get('cap'): s['caplay'] = make_cap(s['cap'])

def end_layer():
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    big = logo_with_shadow(380)
    lay.alpha_composite(big, ((W - big.width) // 2, 230))
    gold_text(lay, (W / 2, 760), 'Book Your', font('pf_bolditalic.ttf', 110))
    gold_text(lay, (W / 2, 880), 'Celebration', font('pf_bolditalic.ttf', 120))
    shadow_text(lay, (W / 2, 975), 'CHRISTMAS & NEW YEAR  •  31 DEC – 1 JAN', font('cinzel600.ttf', 32), CREAM, blur=6)
    # phone pill
    pw, ph, py = 740, 124, 1045
    sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(((W - pw) / 2, py + 10, (W + pw) / 2, py + ph + 10), ph / 2, fill=(0, 0, 0, 160))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    d.rounded_rectangle(((W - pw) / 2, py, (W + pw) / 2, py + ph), ph / 2, fill=GOLD)
    d.rounded_rectangle(((W - pw) / 2 + 6, py + 6, (W + pw) / 2 - 6, py + ph - 6), ph / 2, outline=(255, 240, 200, 255), width=2)
    fn = font('mont600.ttf', 56); tw = d.textlength(PHONE, font=fn); x = (W - tw - 62) / 2
    ic = Image.new('RGBA', (70, 80), (0, 0, 0, 0)); icon_phone(ImageDraw.Draw(ic), 6, 6, 52, (90, 20, 20, 255))
    lay.alpha_composite(ic, (int(x - 8), py + 26))
    d.text((x + 62, py + ph / 2), PHONE, font=fn, fill=(90, 20, 20, 255), anchor='lm')
    shadow_text(lay, (W / 2, py + ph + 52), 'Call now to reserve your stay', font('mont500.ttf', 34), WHITE, blur=6)
    ic = Image.new('RGBA', (60, 70), (0, 0, 0, 0)); icon_pin(ImageDraw.Draw(ic), 8, 4, 40, GOLD)
    lay.alpha_composite(ic, (W // 2 - 30, 1290))
    shadow_text(lay, (W / 2, 1395), 'The Divine Oasis Resort', font('pf_semibold.ttf', 50), WHITE)
    shadow_text(lay, (W / 2, 1460), 'Purulia, West Bengal', font('pf_italic.ttf', 46), GOLD2)
    shadow_text(lay, (W / 2, 1540), WEB, font('mont500.ttf', 36), CREAM, blur=6)
    return lay
END = end_layer()

# ---------------- fireworks ----------------
rs = np.random.default_rng(5)
PALETTE = [(255, 210, 120), (255, 90, 90), (255, 250, 235), (255, 160, 60), (255, 120, 200), (140, 200, 255)]
def make_bursts(t0, t1, n, ymin=250, ymax=800):
    out = []
    for i in range(n):
        out.append(dict(t=rs.uniform(t0, t1), x=rs.uniform(150, W - 150), y=rs.uniform(ymin, ymax),
                        col=PALETTE[rs.integers(len(PALETTE))], n=int(rs.integers(70, 120)),
                        sp=rs.uniform(260, 420), ang=rs.uniform(0, 2 * np.pi, 130), spd=rs.uniform(0.55, 1.0, 130)))
    return out
fw_scene = [s for s in scenes if s.get('fw')][0]
BURSTS = make_bursts(fw_scene['t0s'] + 0.1, fw_scene['t1s'] - 0.8, 6, 200, 650) + \
         make_bursts(scenes[-1]['t0s'] + 0.2, TOTAL - 1.5, 9, 150, 560)
LIFE = 1.8
def fireworks(tt):
    act = [b for b in BURSTS if 0 <= tt - b['t'] < LIFE]
    if not act: return None
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for b in act:
        a = tt - b['t']; fade = (1 - a / LIFE) ** 1.5
        for k in range(b['n']):
            v = b['sp'] * b['spd'][k]; drag = (1 - np.exp(-a * 2.2)) / 2.2
            for tr in (0.0, 0.06, 0.12):  # trail
                aa = max(0, a - tr); dd = (1 - np.exp(-aa * 2.2)) / 2.2
                x = b['x'] + np.cos(b['ang'][k]) * v * dd
                y = b['y'] + np.sin(b['ang'][k]) * v * dd + 90 * aa * aa
                r = (3.2 - tr * 15) * (0.6 + 0.4 * fade)
                al = int(255 * fade * (1 - tr * 5))
                if al > 0 and r > 0.4:
                    d.ellipse((x - r, y - r, x + r, y + r), fill=(*b['col'], al))
        if a < 0.15:  # flash
            r = 60 * (1 - a / 0.15) + 10
            d.ellipse((b['x'] - r, b['y'] - r, b['x'] + r, b['y'] + r), fill=(255, 240, 210, int(160 * (1 - a / 0.15))))
    glow = lay.filter(ImageFilter.GaussianBlur(6))
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.alpha_composite(glow); out.alpha_composite(glow); out.alpha_composite(lay)
    return out

# golden bokeh sparkles drifting (subtle, premium)
NB = 45
bx = rs.uniform(0, W, NB); by = rs.uniform(0, H, NB); bs = rs.uniform(3, 9, NB); bv = rs.uniform(15, 45, NB); bp = rs.uniform(0, 6.28, NB)
def sparkles(tt):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i in range(NB):
        y = (by[i] - bv[i] * tt) % H; x = bx[i] + 20 * np.sin(tt * 0.6 + bp[i])
        tw = 0.5 + 0.5 * np.sin(tt * 2.5 + bp[i] * 3)
        r = bs[i]; d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 215, 140, int(70 + 90 * tw)))
    return lay.filter(ImageFilter.GaussianBlur(2.5))

# vignette
yy, xx = np.mgrid[0:H, 0:W]
rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIG = np.clip(1 - 0.42 * np.clip(rr - 0.5, 0, 1) ** 1.4, 0, 1)[..., None].astype(np.float32)

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def with_alpha(im, a):
    c = im.copy(); c.putalpha(c.split()[3].point(lambda v: int(v * a))); return c

def render_frame(tt, readers):
    act = [s for s in scenes if s['t0s'] <= tt < s['t1s']]
    base = None
    for s in act:
        rd = readers.get(id(s))
        if rd is None: rd = readers[id(s)] = Reader(s)
        fr = rd.next().astype(np.float32)
        if base is None: base = fr
        else:
            a = ease((tt - s['t0s']) / XF); base = base * (1 - a) + fr * a
    # close finished readers
    for s in scenes:
        if tt >= s['t1s'] and readers.get(id(s)):
            readers[id(s)].p.kill(); readers[id(s)] = False
    img = Image.fromarray(np.clip(base * VIG, 0, 255).astype(np.uint8))
    # zoom-punch on every cut after the drop
    last_cut = max([c for c in CUTS if c <= tt], default=None)
    if last_cut is not None and last_cut >= DROP - 0.01 and act[-1] is not scenes[-1]:
        k = 1 - ease((tt - last_cut) / 0.28)
        if k > 0:
            z = 1 + (0.09 if abs(last_cut - DROP) < 0.02 else 0.05) * k
            img = img.transform((W, H), Image.AFFINE, (1 / z, 0, W * (1 - 1 / z) / 2, 0, 1 / z, H * (1 - 1 / z) / 2), Image.BILINEAR)
    img = img.convert('RGBA')
    # white flash on the drop
    fl = 0.55 * (1 - ease((tt - DROP) / 0.35)) if DROP <= tt < DROP + 0.35 else 0
    if fl > 0: img.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * fl))))
    fw = fireworks(tt)
    if fw is not None: img.alpha_composite(fw)
    for s in act:
        if 'caplay' in s:
            a0 = s['t0s'] + 0.08; a1 = s['t1s'] - XF
            a = ease((tt - a0) / 0.3) * ease((a1 - tt) / 0.22)
            if s['cap'] == 'food2': a = ease((a1 - tt) / 0.22)  # continuous with previous
            if s['cap'] == 'food': a = ease((tt - a0) / 0.3)
            if a > 0:
                dy = int((1 - ease((tt - a0) / 0.35)) * 30)
                img.alpha_composite(with_alpha(s['caplay'], a), (0, dy))
    e = scenes[-1]; ea = ease((tt - e['t0s'] - 0.1) / 0.7)
    intro = scenes[0]
    la = ease((tt - intro['t1s'] + XF) / 0.6) * (1 - ea)   # small logo after intro
    if la > 0: img.alpha_composite(with_alpha(LOGO_SMALL, la), LOGO_POS)
    ba = ease((tt - 1.5) / 0.7) * (1 - ea)
    if ba > 0: img.alpha_composite(with_alpha(BAR, ba), (0, BAR_Y))
    if ea > 0: img.alpha_composite(with_alpha(END, ea), (0, int((1 - ea) * 40)))
    return img.convert('RGB')

if PREVIEW:
    times = [float(x) for x in PREVIEW.split(',')]
    for tt in times:
        readers = {}
        # fast-forward readers for the active scenes
        for s in scenes:
            if s['t0s'] <= tt < s['t1s']:
                r = readers[id(s)] = Reader(s)
                for _ in range(int((tt - s['t0s']) * FPS)): r.next()
        render_frame(tt, readers).save(f'{OUT}_{tt:05.1f}.jpg', quality=88)
        for r in readers.values():
            if r: r.p.kill()
    sys.exit()

nfr = int(round(TOTAL * FPS))
proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                         '-i', '-', '-i', O + '/music.wav', '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                         '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', OUT],
                        stdin=subprocess.PIPE)
readers = {}
for i in range(nfr):
    proc.stdin.write(render_frame(i / FPS, readers).tobytes())
    if i % 150 == 0: print(i, flush=True)
proc.stdin.close(); proc.wait(); print('done', proc.returncode)
