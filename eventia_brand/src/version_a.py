"""Version A - 'Elegant Story': brand teal + blush roses, soft Ken Burns, script chapter titles."""
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from lib import *

OUT = sys.argv[1]; PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
XF = 0.6
f_script = lambda s: font('vibes.ttf', s)
f_serif = lambda s: font('dmserif.ttf', s)
f_lora = lambda s: font('lora500.ttf', s)
f_sans = lambda s: font('mont500.ttf', s)
f_sansb = lambda s: font('mont600.ttf', s)

# ---------- static pieces ----------
def teal_bg():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    a = np.clip(r * 1.3, 0, 1)[..., None]
    c = np.array(TEAL, np.float32) * (1 - a) + np.array(TEAL_D, np.float32) * a
    # subtle paper texture from the pdf's background image
    tex = img(0).convert('L').resize((W, H)); tx = (np.asarray(tex, np.float32) - 128) / 128 * 6
    return Image.fromarray(np.clip(c + tx[..., None], 0, 255).astype(np.uint8)).convert('RGBA')
TEAL_BG = teal_bg()

def frame_border(lay, inset=60, col=(IVORY[0], IVORY[1], IVORY[2], 200), w=3):
    d = ImageDraw.Draw(lay)
    d.rectangle((inset, inset, W - inset, H - inset), outline=col, width=w)
    d.rectangle((inset + 14, inset + 14, W - inset - 14, H - inset - 14), outline=col[:3] + (110,), width=1)

def rose(scale, flip=False, rot=0):
    r = ROSE.resize((int(ROSE.width * scale), int(ROSE.height * scale)), Image.LANCZOS)
    if flip: r = ImageOps.mirror(r)
    if rot: r = r.rotate(rot, expand=True, resample=Image.BICUBIC)
    return r
ROSE_TR = rose(0.55); ROSE_BL = rose(0.5, flip=True, rot=180)
ROSE_SMALL = rose(0.30)
ROSE_TR_S = rose(0.36); ROSE_BL_S = rose(0.36, flip=True, rot=180)

def logo_badge(h, pill=False):
    lg = LOGO.resize((int(LOGO.width * h / LOGO.height), h), Image.LANCZOS)
    padx, pady = (int(h * .45), int(h * .32)) if pill else (30, 30)
    bw, bh = lg.width + 2 * padx, lg.height + 2 * pady
    out = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    if pill:
        ImageDraw.Draw(out).rounded_rectangle((0, 0, bw - 1, bh - 1), bh // 2, fill=TEAL_D + (190,), outline=CREAM + (120,), width=2)
    else:
        sh = Image.new('RGBA', out.size, (0, 0, 0, 0)); sh.alpha_composite(Image.merge('RGBA', (*Image.new('RGB', lg.size, 0).split(), lg.split()[3])), (padx, pady + 3))
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(lg, (padx, pady))
    return out
LOGO_SMALL = logo_badge(52, pill=True)
LOGO_POS = (W - LOGO_SMALL.width - 20, 100)

def contact_strip():
    hgt = 170
    bar = vertical_grad(hgt, 0, 0, TEAL_D)
    g = np.asarray(bar).copy(); g[..., 3] = (np.sin(np.linspace(0, np.pi, hgt)) ** .6 * 190).astype(np.uint8)[:, None]
    bar = Image.fromarray(g, 'RGBA'); d = ImageDraw.Draw(bar)
    fn = f_sansb(44); txt = PHONE; tw = d.textlength(txt, font=fn); x = (W - tw - 56) / 2
    ic = Image.new('RGBA', (60, 70), (0, 0, 0, 0)); icon_phone(ImageDraw.Draw(ic), 6, 6, 42, BLUSH + (255,))
    bar.alpha_composite(ic, (int(x - 6), 52)); d.text((x + 54, 50), txt, font=fn, fill=WHITE + (255,))
    d.text((W / 2, 128), 'Call  •  WhatsApp  •  DM us', font=f_sans(28), fill=(255, 235, 230, 220), anchor='mm')
    return bar
STRIP = contact_strip(); STRIP_Y = 1480

# ---------- scenes ----------
# kinds: 'intro', 'photo', 'services', 'why', 'cta'
P = lambda n, **k: dict(kind='photo', n=n, **k)
scenes = [
    dict(kind='intro', d=4.4),
    P(24, d=3.6, mo='zin', l1='Picture-perfect events', l2='with guaranteed client satisfaction', style='serif'),
    P(53, d=3.4, mo='zout', l1='End-to-end planners', l2='& logistical support partners', style='serif'),
    P(38, d=2.9, mo='zin', chap='Haldi', focus=(.5, .45)),
    P(43, d=2.9, mo='zin', chap='Mehndi & Alta'),
    P(50, d=2.9, mo='panR', chap='Sangeet'),
    P(56, d=2.9, mo='zin', chap='Wedding'),
    P(55, d=2.6, mo='zout', focus=(.5, .4)),
    P(61, d=2.9, mo='zin', chap='Destination Wedding'),
    P(84, d=2.9, mo='zin', chap='Reception'),
    P(76, d=2.7, mo='panL', chap='Gifts, Hampers & Favours'),
    dict(kind='services', d=5.6, title='Our Services', items=[
        'Wedding planning & execution', 'Venue hunting', 'Decor', 'Food & menu selection',
        'Photography & cinematography', 'Entertainment – DJ & performers',
        'Bridal & guest makeup, mehndi']),
    dict(kind='services', d=5.0, title='…and much more', items=[
        'E-card designing & printing', 'Gifts & hampers', 'Travel logistics',
        'Customised stationery', 'Guest management', 'Budget planning']),
    dict(kind='why', d=4.6),
    dict(kind='cta', d=6.0),
]
t = 0
for s in scenes:
    s['t0'] = t; s['t1'] = t + s['d']; t += s['d'] - XF
TOTAL = scenes[-1]['t1']
print('total', TOTAL)

for s in scenes:
    if s['kind'] == 'photo':
        s['im'] = prep_cover(img(s['n']))

# precomputed text layers
def chap_layer(s):
    return text_layer(s['chap'], f_script(150 if len(s['chap']) < 14 else 112), WHITE + (255,), blur=12, sh_alpha=200)
for s in scenes:
    if s.get('chap'): s['L'] = chap_layer(s)
    if s.get('l1'):
        s['L1'] = text_layer(s['l1'], f_serif(84 if len(s['l1']) < 22 else 74), WHITE + (255,), blur=12, sh_alpha=200)
        s['L2'] = text_layer(s['l2'], f_lora(44), (255, 228, 222, 255), blur=8, sh_alpha=200)
EYEBROW = text_layer('OUR CELEBRATIONS', f_sansb(30), BLUSH + (255,), blur=6)
BACK = radial_backdrop(880, 640, 300, 150)
VIG = vignette(0.45)

def card_services(s, p, tt):
    """ivory card with rose, staggered bullet list"""
    lay = TEAL_BG.copy()
    frame_border(lay)
    cx0, cy0, cx1, cy1 = 110, 400, W - 110, 1440
    cin = ease_out((tt - s['t0']) / 0.7)
    card = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((cx0, cy0 + 16, cx1, cy1 + 16), 28, fill=(0, 0, 0, 120))
    card.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    d.rounded_rectangle((cx0, cy0, cx1, cy1), 28, fill=IVORY + (255,))
    d.rounded_rectangle((cx0 + 18, cy0 + 18, cx1 - 18, cy1 - 18), 20, outline=TEAL + (160,), width=2)
    d.text((W / 2, cy0 + 120), s['title'], font=f_serif(88), fill=TEAL + (255,), anchor='mm')
    d.line((W / 2 - 90, cy0 + 190, W / 2 + 90, cy0 + 190), fill=BLUSH + (255,), width=4)
    lay.alpha_composite(alpha(card, cin), (0, int((1 - cin) * 60)))
    n = len(s['items']); fn = f_lora(42 if n > 6 else 46)
    y = cy0 + 270; step = (cy1 - 90 - y) / n
    for i, it in enumerate(s['items']):
        a = ease_out((tt - s['t0'] - 0.5 - i * 0.28) / 0.45)
        if a <= 0: continue
        row = Image.new('RGBA', (W, 120), (0, 0, 0, 0)); rd = ImageDraw.Draw(row)
        rd.ellipse((cx0 + 70, 42, cx0 + 94, 66), fill=BLUSH + (255,))
        # wrap long lines
        words = it.split(' '); lines = ['']
        for w_ in words:
            if rd.textlength(lines[-1] + ' ' + w_, font=fn) > cx1 - cx0 - 200: lines.append(w_)
            else: lines[-1] = (lines[-1] + ' ' + w_).strip()
        for k, ln in enumerate(lines[:2]):
            rd.text((cx0 + 120, 54 + k * 50), ln, font=fn if k == 0 else fn, fill=INK + (255,), anchor='lm')
        lay.alpha_composite(alpha(row, a), (int((1 - a) * -40), int(y + i * step - 40)))
    # roses
    rin = ease_out((tt - s['t0']) / 1.0)
    lay.alpha_composite(alpha(ROSE_TR_S, rin), (W - ROSE_TR_S.width + 90 + int((1 - rin) * 80), 10))
    lay.alpha_composite(alpha(ROSE_BL_S, rin), (-90 - int((1 - rin) * 80), 1360))
    return lay

WHY = [('A personal touch', 'with professional accountability'),
       ('Like an extension of your family', 'seamless execution, start to finish'),
       ('Best rates & full customisation', 'creativity, quality assurance & client support')]
def card_why(s, tt):
    lay = TEAL_BG.copy(); frame_border(lay)
    a = ease_out((tt - s['t0']) / .6)
    paste_center(lay, text_layer('Why choose', f_lora(52), (255, 228, 222, 255)), W / 2, 420, a)
    paste_center(lay, text_layer('Eventia', f_script(190), WHITE + (255,), blur=12), W / 2, 560, a)
    for i, (h1, h2) in enumerate(WHY):
        b = ease_out((tt - s['t0'] - .5 - i * .45) / .5)
        if b <= 0: continue
        y = 790 + i * 210
        row = Image.new('RGBA', (W, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
        d.rounded_rectangle((120, 10, W - 120, 180), 26, fill=(255, 255, 255, 26), outline=BLUSH + (200,), width=2)
        d.ellipse((160, 65, 210, 115), fill=BLUSH + (255,))
        d.line((172, 92, 182, 102), fill=TEAL + (255,), width=5); d.line((182, 102, 199, 80), fill=TEAL + (255,), width=5)
        d.text((240, 72), h1, font=f_serif(50), fill=WHITE + (255,), anchor='lm')
        d.text((240, 128), h2, font=f_lora(34), fill=(255, 228, 222, 235), anchor='lm')
        lay.alpha_composite(alpha(row, b), (0, int(y + (1 - b) * 40)))
    lay.alpha_composite(alpha(ROSE_TR_S, a), (W - ROSE_TR_S.width + 100, 0))
    lay.alpha_composite(alpha(ROSE_BL_S, a), (-100, 1440))
    return lay

def scene_intro(s, tt):
    lay = TEAL_BG.copy(); p = tt - s['t0']
    frame_border(lay)
    ra = ease_out(p / 1.4)
    r1 = ROSE_TR.resize((int(ROSE_TR.width * (0.85 + .15 * ra)), int(ROSE_TR.height * (0.85 + .15 * ra))))
    lay.alpha_composite(alpha(r1, ra), (W - r1.width + 60 + int((1 - ra) * 120), 40 - int((1 - ra) * 80)))
    r2 = ROSE_BL
    lay.alpha_composite(alpha(r2, ra), (-80 - int((1 - ra) * 120), H - r2.height + 40 + int((1 - ra) * 80)))
    # ivory medallion with logo
    la = ease_back((p - 0.4) / 0.9)
    if la > 0:
        med = Image.new('RGBA', (760, 760), (0, 0, 0, 0)); d = ImageDraw.Draw(med)
        d.ellipse((20, 20, 740, 740), fill=TEAL_D + (255,)); d.ellipse((44, 44, 716, 716), outline=CREAM + (150,), width=3)
        lg = LOGO.resize((440, int(440 * LOGO.height / LOGO.width)), Image.LANCZOS)
        lg = LOGO.resize((600, int(600 * LOGO.height / LOGO.width)), Image.LANCZOS)
        med.alpha_composite(lg, ((760 - lg.width) // 2, 270))
        d.line((270, 500, 490, 500), fill=BLUSH + (220,), width=2)
        d.text((380, 575), 'Wedding Planner', font=f_script(78), fill=BLUSH + (255,), anchor='mm')
        sh = Image.new('RGBA', (820, 820), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((50, 66, 770, 786), fill=(0, 0, 0, 120))
        paste_center(lay, sh.filter(ImageFilter.GaussianBlur(20)), W / 2, 830, min(1, la))
        paste_center(lay, med, W / 2, 820, min(1, la * 1.4), scale=0.6 + 0.4 * la)
    ta = ease_out((p - 1.6) / 0.8)
    if ta > 0:
        paste_center(lay, text_layer('Make your wedding moment', f_lora(48), (255, 236, 230, 255)), W / 2, 1300 + (1 - ta) * 30, ta)
        paste_center(lay, text_layer('unforgettable with us', f_script(110), WHITE + (255,), blur=12), W / 2, 1400 + (1 - ta) * 30, ta)
    return lay

def scene_photo(s, tt):
    p = (tt - s['t0']) / s['d']
    base = kenburns(s['im'], p, s.get('mo', 'zin'), 0.09, s.get('focus', (.5, .5))).convert('RGBA')
    a0 = s['t0'] + 0.3; a1 = s['t1'] - XF
    a = ease((tt - a0) / .6) * ease((a1 + .2 - tt) / .4)
    if a > 0:
        base.alpha_composite(alpha(BACK, a))
        dy = (1 - ease_out((tt - a0) / .8)) * 30
        if s.get('chap'):
            if s['n'] in (38, 43):  # first chapters get eyebrow
                paste_center(base, EYEBROW, W / 2, 760 + dy, a)
            paste_center(base, s['L'], W / 2, 880 + dy, a)
            d = ImageDraw.Draw(base)
            w_ = 120 * ease_out((tt - a0 - .3) / .6)
            d.line((W / 2 - w_, 1000 + dy, W / 2 + w_, 1000 + dy), fill=BLUSH + (int(255 * a),), width=3)
        if s.get('l1'):
            paste_center(base, s['L1'], W / 2, 850 + dy, a)
            paste_center(base, s['L2'], W / 2, 945 + dy, ease((tt - a0 - .35) / .6) * ease((a1 + .2 - tt) / .4))
    return base

def scene_cta(s, tt):
    lay = TEAL_BG.copy(); frame_border(lay); p = tt - s['t0']
    a = ease_out(p / .7)
    lay.alpha_composite(alpha(ROSE_TR_S, a), (W - ROSE_TR_S.width + 110, -10 - int((1 - a) * 60)))
    lay.alpha_composite(alpha(ROSE_BL_S, a), (-100, H - ROSE_BL_S.height + 60 + int((1 - a) * 60)))
    paste_center(lay, logo_badge(165), W / 2, 500, a, scale=.9 + .1 * a)
    b = ease_out((p - .4) / .7)
    paste_center(lay, text_layer("Let's plan your", f_lora(56), (255, 228, 222, 255)), W / 2, 760 + (1 - b) * 30, b)
    paste_center(lay, text_layer('Dream Wedding', f_script(170), WHITE + (255,), blur=12), W / 2, 890 + (1 - b) * 30, b)
    c = ease_back((p - .9) / .7)
    if c > 0:
        pw, ph = 760, 130
        pill = Image.new('RGBA', (pw + 60, ph + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(pill)
        sh = Image.new('RGBA', pill.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + pw, 40 + ph), ph // 2, fill=(0, 0, 0, 120))
        pill.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
        d.rounded_rectangle((30, 30, 30 + pw, 30 + ph), ph // 2, fill=IVORY + (255,))
        fn = f_sansb(58); tw = d.textlength(PHONE, font=fn); x = 30 + (pw - tw - 62) / 2
        icon_phone(d, x, 30 + 34, 52, TEAL + (255,)); d.text((x + 64, 30 + ph / 2), PHONE, font=fn, fill=TEAL + (255,), anchor='lm')
        paste_center(lay, pill, W / 2, 1120, min(1, c), scale=.85 + .15 * min(1, c))
    e = ease_out((p - 1.4) / .7)
    if e > 0:
        paste_center(lay, text_layer('Call  or  WhatsApp us today', f_sans(38), WHITE + (240,), blur=6), W / 2, 1250, e)
        chat = Image.new('RGBA', (560, 110), (0, 0, 0, 0)); d = ImageDraw.Draw(chat)
        d.rounded_rectangle((0, 0, 560, 100), 50, outline=BLUSH + (255,), width=3)
        icon_chat(d, 52, 26, 46, BLUSH + (255,))
        d.text((320, 50), 'DM us to book', font=f_sansb(40), fill=BLUSH + (255,), anchor='mm')
        paste_center(lay, chat, W / 2, 1390, e)
        paste_center(lay, text_layer('EVENTIA  •  Event Management  •  Wedding Planner', f_sans(28), (255, 236, 230, 200), blur=4), W / 2, 1560, e)
    return lay

RENDER = {'intro': scene_intro, 'photo': scene_photo, 'services': lambda s, tt: card_services(s, 0, tt),
          'why': card_why, 'cta': scene_cta}

def render(tt):
    act = [s for s in scenes if s['t0'] <= tt < s['t1']]
    out = None
    for s in act:
        fr = RENDER[s['kind']](s, tt).convert('RGB')
        if out is None: out = fr
        else: out = Image.blend(out, fr, ease((tt - s['t0']) / XF))
    arr = np.asarray(out).astype(np.float32) * VIG
    img_ = Image.fromarray(arr.astype(np.uint8)).convert('RGBA')
    # small logo + contact strip on photo scenes
    def photo_w(tt):
        w = 0
        for s in act:
            if s['kind'] == 'photo':
                w = max(w, min(ease((tt - s['t0']) / XF) if s is not act[0] else 1, ease((s['t1'] - tt) / XF) if s is act[0] and len(act) > 1 else 1))
        return w
    pw = photo_w(tt)
    if pw > 0:
        img_.alpha_composite(alpha(LOGO_SMALL, pw), LOGO_POS)
        img_.alpha_composite(alpha(STRIP, pw), (0, STRIP_Y))
    return img_

if PREVIEW:
    for tt in [float(x) for x in PREVIEW.split(',')]:
        render(tt).convert('RGB').save(f'{OUT}_{tt:05.1f}.jpg', quality=88)
    sys.exit()
encode(render, TOTAL, os.path.dirname(os.path.abspath(__file__)) + '/music_a.wav', OUT)
