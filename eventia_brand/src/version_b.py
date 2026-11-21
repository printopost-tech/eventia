"""Version B - 'Bold & Fast': beat-synced cuts (120 BPM), punch zooms, big bold type, teal/yellow brand accents."""
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from lib import *

OUT = sys.argv[1]; PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
BEAT = 0.5
f_black = lambda s: font('mont900.ttf', s)
f_xb = lambda s: font('mont800.ttf', s)
f_b = lambda s: font('mont700.ttf', s)
f_m = lambda s: font('mont500.ttf', s)
f_script = lambda s: font('vibes.ttf', s)

def cover(n, **k): return prep_cover(img(n), scale=1.18)

# ---------- timeline ----------
# 0.0-2.0  : 4 word hits  YOUR / DREAM / WEDDING / PLANNED BY  (each 0.5s, photos flash)
# 2.0-4.0  : logo hit on teal
# 4.0-15.0 : 11 services x 1.0s
# 15.0-18.0: events grid (6 tiles) building
# 18.0-21.0: 6 events x 0.5s flashes with label
# 21.0-25.5: WHY EVENTIA 3 statements x 1.5s
# 25.5-33.0: CTA
INTRO_WORDS = [('YOUR', 52), ('DREAM', 54), ('WEDDING', 56), ('PLANNED BY', 59)]
SERVICES = [
    ('Wedding Planning', '& execution', 56), ('Venue', 'hunting', 62), ('Decor', 'that wows', 54),
    ('Food & Menu', 'selection', 58), ('Photography', '& cinematography', 55), ('Entertainment', 'DJ • performers • dancers', 48),
    ('Makeup & Mehndi', 'bridal & guests • drape • hair', 46), ('E-Cards', 'design & printing', 79),
    ('Gifts & Hampers', 'curated favours', 76), ('Travel Logistics', 'for you & your guests', 61), ('Guest Management', '& budget planning', 52),
]
EVENTS = [('Haldi', 36), ('Mehndi & Alta', 44), ('Sangeet', 48), ('Wedding', 53), ('Destination', 62), ('Reception', 83)]
WHYS = [('PERSONAL TOUCH.', 'Professional accountability.'), ('LIKE FAMILY.', 'Seamless execution, end to end.'),
        ('BEST RATES.', 'Customised. Creative. Quality assured.')]
WHY_BG = [54, 84, 59]
TOTAL = 33.0

# prepare images
IM = {}
for n in set([w[1] for w in INTRO_WORDS] + [s[2] for s in SERVICES] + [e[1] for e in EVENTS] + WHY_BG + [24]):
    IM[n] = cover(n)
GRID_TILES = {n: ImageOps.fit(ImageOps.exif_transpose(img(n)).convert('RGB'), (330, 440), Image.LANCZOS) for _, n in EVENTS}

VIG = vignette(0.5)
def photo(n, p, punch=True, mode='zin', amt=0.06):
    fr = kenburns(IM[n], p, mode, amt)
    if punch:  # quick zoom-punch on the cut
        k = 1 - ease_out(p * 4)  # first 25% of the shot
        if k > 0:
            z = 1 + 0.10 * k
            fr = fr.transform((W, H), Image.AFFINE, (1 / z, 0, W * (1 - 1 / z) / 2, 0, 1 / z, H * (1 - 1 / z) / 2), Image.BILINEAR)
    return fr.convert('RGBA')

def darken(im, a):
    ov = Image.new('RGBA', (W, H), (0, 0, 0, int(255 * a))); im.alpha_composite(ov); return im

def teal_fill():
    return Image.new('RGBA', (W, H), TEAL_D + (255,))

def logo_card(h, bg=True):
    lg = LOGO.resize((int(LOGO.width * h / LOGO.height), h), Image.LANCZOS)
    px, py = int(h * .4), int(h * .3)
    out = Image.new('RGBA', (lg.width + 2 * px, lg.height + 2 * py), (0, 0, 0, 0))
    if bg: ImageDraw.Draw(out).rounded_rectangle((0, 0, out.width - 1, out.height - 1), int(h * .25), fill=TEAL_D + (200,))
    out.alpha_composite(lg, (px, py)); return out
LOGO_S = logo_card(52)

def label_block(title, sub, tt_in):
    """big bold title with yellow underline bar + teal tag for sub, slides from left"""
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a = ease_out(tt_in / 0.25)
    fn = f_black(108 if len(title) <= 12 else 88 if len(title) <= 15 else 80)
    x = 70 - (1 - a) * 120
    # title
    tl = text_layer(title.upper(), fn, WHITE + (255,), blur=14, sh_alpha=200)
    lay.alpha_composite(alpha(tl, a), (int(x - 40), 1080 - 40))
    tw = d.textlength(title.upper(), font=fn)
    bw = tw * ease_out((tt_in - 0.08) / 0.3)
    d.rectangle((x, 1222, x + bw, 1238), fill=YELLOW + (255,))
    b = ease_out((tt_in - 0.12) / 0.25)
    if b > 0:
        fs = f_b(40); sw = d.textlength(sub.upper(), font=fs)
        tag = Image.new('RGBA', (int(sw + 50), 74), (0, 0, 0, 0)); td = ImageDraw.Draw(tag)
        td.rectangle((0, 0, tag.width, 74), fill=TEAL_L + (240,))
        td.text((25, 37), sub.upper(), font=fs, fill=WHITE + (255,), anchor='lm')
        lay.alpha_composite(alpha(tag, b), (int(70 - (1 - b) * 80), 1262))
    return lay

def counter(i, n):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((70, 1000), f'{i + 1:02d}', font=f_xb(44), fill=YELLOW + (255,), anchor='ls')
    d.text((140, 1000), f'/ {n:02d}  SERVICES', font=f_b(30), fill=(255, 255, 255, 220), anchor='ls')
    return lay

def bottom_bar():
    bar = vertical_grad(200, 0, 210, TEAL_D); d = ImageDraw.Draw(bar)
    fn = f_xb(44); tw = d.textlength(PHONE, font=fn); x = (W - tw - 56) / 2
    icon_phone(d, x, 100, 40, YELLOW + (255,)); d.text((x + 56, 124), PHONE, font=fn, fill=WHITE + (255,), anchor='lm')
    return bar
BAR = bottom_bar()

def flash(img_, a):
    if a > 0: img_.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * a))))

def render(tt):
    # ---- intro word hits
    if tt < 2.0:
        i = int(tt / BEAT); p = (tt - i * BEAT) / BEAT
        word, n = INTRO_WORDS[i]
        fr = darken(photo(n, p, True, 'zin', 0.05), 0.45)
        fn = f_black(170 if len(word) <= 7 else 120)
        sc = 1.25 - 0.25 * ease_out(p * 3)
        paste_center(fr, text_layer(word, fn, WHITE + (255,), blur=16, sh_alpha=220), W / 2, H / 2 - 40, 1, sc)
        flash(fr, 0.6 * (1 - ease_out(p * 6)) if i == 0 else 0.35 * (1 - ease_out(p * 6)))
        return fr
    # ---- logo hit
    if tt < 4.0:
        p = (tt - 2.0) / 2.0
        fr = teal_fill()
        # expanding rings
        d = ImageDraw.Draw(fr)
        for k in range(3):
            r = (p * 2.2 - k * 0.35)
            if r > 0:
                rr = 200 + r * 700; aa = int(120 * max(0, 1 - r))
                d.ellipse((W / 2 - rr, 820 - rr, W / 2 + rr, 820 + rr), outline=TEAL_L + (aa,), width=6)
        s = ease_back(p * 2.4)
        lg = LOGO.resize((780, int(780 * LOGO.height / LOGO.width)), Image.LANCZOS)
        card = Image.new('RGBA', (900, 420), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((0, 0, 899, 419), 40, fill=TEAL + (255,), outline=CREAM + (200,), width=4)
        cd.rounded_rectangle((16, 16, 883, 403), 30, outline=YELLOW + (160,), width=2)
        card.alpha_composite(lg, ((900 - lg.width) // 2, (420 - lg.height) // 2))
        paste_center(fr, card, W / 2, 820, min(1, p * 5), max(0.05, s))
        b = ease_out((p - 0.35) / 0.3)
        paste_center(fr, text_layer('EVENT MANAGEMENT  •  WEDDING PLANNER', f_b(36), YELLOW + (255,), blur=6), W / 2, 1270 + (1 - b) * 30, b)
        paste_center(fr, text_layer('Make your wedding moment unforgettable', f_m(38), WHITE + (230,), blur=6), W / 2, 1340 + (1 - b) * 30, ease_out((p - .5) / .3))
        flash(fr, 0.7 * (1 - ease_out(p * 8)))
        return fr
    # ---- services
    if tt < 15.0:
        i = int(tt - 4.0); p = (tt - 4.0 - i)
        title, sub, n = SERVICES[i]
        fr = photo(n, p, True, 'zin' if i % 2 == 0 else 'zout', 0.07)
        fr.alpha_composite(vertical_grad(H, 0, 0))
        fr.alpha_composite(alpha(radial_backdrop(1180, 900, 380, 170, cx=300), 1))
        if i == 0:
            paste_center(fr, text_layer('WHAT WE DO', f_xb(60), YELLOW + (255,), blur=10), W / 2, 330, ease_out((tt - 4) / .3))
        fr.alpha_composite(counter(i, len(SERVICES)))
        fr.alpha_composite(label_block(title, sub, p))
        fr.alpha_composite(LOGO_S, (W - LOGO_S.width - 40, 110))
        fr.alpha_composite(BAR, (0, 1500))
        flash(fr, 0.25 * (1 - ease_out(p * 8)))
        return fr
    # ---- events grid build
    if tt < 18.0:
        p = (tt - 15.0)
        fr = teal_fill()
        paste_center(fr, text_layer('EVERY CELEBRATION', f_black(78), WHITE + (255,)), W / 2, 230, ease_out(p / .3))
        paste_center(fr, text_layer('beautifully done', f_script(110), YELLOW + (255,)), W / 2, 330, ease_out((p - .2) / .3))
        for k, (name, n) in enumerate(EVENTS):
            a = ease_back((p - 0.25 - k * BEAT / 2) / 0.35)
            if a <= 0: continue
            col, row = k % 3, k // 3
            cx = 190 + col * 350; cy = 720 + row * 480
            tile = GRID_TILES[n].copy().convert('RGBA')
            m = Image.new('L', tile.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, tile.width - 1, tile.height - 1), 30, fill=255)
            g = vertical_grad(tile.height, 0, 0); tile.alpha_composite(Image.fromarray(np.dstack([np.zeros((tile.height, tile.width, 3), np.uint8), np.linspace(0, 200, tile.height).astype(np.uint8)[:, None].repeat(tile.width, 1)]), 'RGBA'))
            ImageDraw.Draw(tile).text((tile.width / 2, tile.height - 45), name.upper(), font=f_xb(30 if len(name) > 10 else 34), fill=WHITE + (255,), anchor='mm')
            tile.putalpha(m)
            paste_center(fr, tile, cx, cy, min(1, a * 2), min(1.05, a))
        fr.alpha_composite(BAR, (0, 1500))
        return fr
    # ---- event flashes
    if tt < 21.0:
        i = int((tt - 18.0) / BEAT); p = (tt - 18.0 - i * BEAT) / BEAT
        name, n = EVENTS[i]
        fr = photo(n, p, True, 'zin', 0.05)
        fr.alpha_composite(radial_backdrop(H / 2, 700, 300, 150))
        paste_center(fr, text_layer(name, f_script(170 if len(name) < 10 else 140), WHITE + (255,), blur=14, sh_alpha=220), W / 2, H / 2 - 40, 1, 1.15 - .15 * ease_out(p * 3))
        fr.alpha_composite(LOGO_S, (W - LOGO_S.width - 40, 110)); fr.alpha_composite(BAR, (0, 1500))
        flash(fr, 0.3 * (1 - ease_out(p * 8)))
        return fr
    # ---- why
    if tt < 25.5:
        i = int((tt - 21.0) / 1.5); p = (tt - 21.0 - i * 1.5) / 1.5
        big, small = WHYS[i]
        fr = darken(photo(WHY_BG[i], p, True, 'zin', 0.05), 0.55)
        if i == 0: paste_center(fr, text_layer('WHY EVENTIA?', f_xb(56), YELLOW + (255,)), W / 2, 560, 1)
        sl = ease_out(p * 3.5)
        tl = text_layer(big, f_black(112 if len(big) < 14 else 96), WHITE + (255,), blur=14, sh_alpha=220)
        fr.alpha_composite(alpha(tl, sl), (int((W - tl.width) / 2 + (1 - sl) * 200), 760))
        d = ImageDraw.Draw(fr); bw = 300 * ease_out((p - .15) * 4)
        d.rectangle((W / 2 - bw / 2, 930, W / 2 + bw / 2, 944), fill=YELLOW + (255,))
        paste_center(fr, text_layer(small, f_b(44), WHITE + (240,), blur=8), W / 2, 1010, ease_out((p - .2) * 4))
        fr.alpha_composite(LOGO_S, (W - LOGO_S.width - 40, 110)); fr.alpha_composite(BAR, (0, 1500))
        flash(fr, 0.3 * (1 - ease_out(p * 10)))
        return fr
    # ---- CTA
    p = tt - 25.5
    fr = teal_fill(); d = ImageDraw.Draw(fr)
    # diagonal yellow stripe sweep
    sw = ease_out(p / .5)
    d.polygon([(-200 + sw * 0, 1460), (W * sw + 200, 1300), (W * sw + 200, 1360), (-200, 1520)], fill=TEAL_L + (255,))
    paste_center(fr, logo_card(120, bg=False), W / 2, 380, ease_out(p / .4), .8 + .2 * ease_back(p / .5))
    for k, (w_, y) in enumerate([("LET'S PLAN", 690), ('YOUR BIG DAY.', 820)]):
        a = ease_out((p - .3 - k * .25) / .35)
        tl = text_layer(w_, f_black(118 if k == 0 else 106), (WHITE if k == 0 else YELLOW) + (255,), blur=10)
        fr.alpha_composite(alpha(tl, a), (int((W - tl.width) / 2 - (1 - a) * 150), int(y - tl.height / 2)))
    c = ease_back((p - .9) / .45)
    if c > 0:
        pw, ph = 820, 150
        pill = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle((0, 0, pw - 1, ph - 1), 26, fill=YELLOW + (255,))
        fn = f_black(66); tw = pd.textlength(PHONE, font=fn); x = (pw - tw - 70) / 2
        icon_phone(pd, x, 40, 58, TEAL_D + (255,)); pd.text((x + 72, ph / 2), PHONE, font=fn, fill=TEAL_D + (255,), anchor='lm')
        # pulse
        pulse = 1 + 0.03 * np.sin(max(0, p - 1.4) * 2 * np.pi / 1.0) if p > 1.4 else 1
        paste_center(fr, pill, W / 2, 1050, min(1, c * 2), min(1.0, c) * pulse)
    e = ease_out((p - 1.4) / .4)
    if e > 0:
        row = Image.new('RGBA', (W, 120), (0, 0, 0, 0)); rd = ImageDraw.Draw(row)
        items = [('CALL', icon_phone), ('WHATSAPP', icon_chat), ('DM US', icon_chat)]
        fl = f_xb(38); ws = [rd.textlength(l, font=fl) + 62 for l, _ in items]; gap = 70
        x = (W - sum(ws) - gap * 2) / 2
        for (lab, ic), w_ in zip(items, ws):
            ic(rd, x, 38, 40, YELLOW + (255,)); rd.text((x + 62, 60), lab, font=fl, fill=WHITE + (255,), anchor='lm'); x += w_ + gap
        fr.alpha_composite(alpha(row, e), (0, int(1190 + (1 - e) * 30)))
        paste_center(fr, text_layer('Weddings  •  Haldi  •  Mehndi  •  Sangeet  •  Destination  •  Reception', f_m(30), (255, 255, 255, 210), blur=4), W / 2, 1600, e)
    flash(fr, 0.6 * (1 - ease_out(p * 6)))
    return fr

def final(tt):
    fr = render(tt)
    arr = np.asarray(fr.convert('RGB')).astype(np.float32) * VIG
    return Image.fromarray(arr.astype(np.uint8))

if PREVIEW:
    for tt in [float(x) for x in PREVIEW.split(',')]:
        final(tt).save(f'{OUT}_{tt:05.1f}.jpg', quality=88)
    sys.exit()
encode(final, TOTAL, os.path.dirname(os.path.abspath(__file__)) + '/music_b.wav', OUT)
