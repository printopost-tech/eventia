"""Shared helpers for the Eventia reels."""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

E = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(E)
FD = S + '/fonts/'
W, H, FPS = 1080, 1920, 30

TEAL = (31, 72, 80)
TEAL_D = (18, 46, 52)
TEAL_L = (58, 168, 160)
BLUSH = (236, 170, 170)
IVORY = (253, 248, 238)
GOLD = (226, 190, 120)
WHITE = (255, 255, 255)
INK = (34, 52, 58)
YELLOW = (250, 214, 60)

PHONE = '+91 74390 12840'

def font(name, size): return ImageFont.truetype(FD + name, size)

def img(n):
    """load extracted pdf image by its number, e.g. 56 -> i-010-056.*"""
    for f in os.listdir(E + '/img'):
        if f.split('-')[2].split('.')[0] == f'{n:03d}':
            return Image.open(E + '/img/' + f)
    raise KeyError(n)

def with_mask(n_img, n_mask):
    im = img(n_img).convert('RGB'); m = img(n_mask).convert('L')
    out = im.convert('RGBA'); out.putalpha(m)
    return out.crop(out.getbbox())

LOGO = with_mask(5, 6)
ROSE = with_mask(1, 2)

def prep_cover(im, scale=1.12, sharpen=True):
    im = ImageOps.exif_transpose(im).convert('RGB')
    sc = max(W * scale / im.width, H * scale / im.height)
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    if sharpen: im = im.filter(ImageFilter.UnsharpMask(2, 60, 2))
    im = ImageEnhance.Contrast(im).enhance(1.05)
    return ImageEnhance.Color(im).enhance(1.06)

def kenburns(im, p, mode='zin', amount=0.08, focus=(0.5, 0.5)):
    """im is a cover-prepared image; p 0..1"""
    iw, ih = im.size
    base = min(iw / W, ih / H)
    if mode == 'zin': z = 1 + amount * p
    elif mode == 'zout': z = 1 + amount * (1 - p)
    else: z = 1.0
    cw, ch = W * base / z, H * base / z
    fx, fy = focus
    cx = np.clip(iw * fx, cw / 2, iw - cw / 2); cy = np.clip(ih * fy, ch / 2, ih - ch / 2)
    if mode in ('panL', 'panR'):
        span = iw - cw; d = 1 if mode == 'panR' else -1
        cx = iw / 2 + d * min(span * 0.45, iw * 0.2) * (p - 0.5)
    return im.transform((W, H), Image.AFFINE, (cw / W, 0, cx - cw / 2, 0, ch / H, cy - ch / 2), Image.BICUBIC)

def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def ease_out(x):
    x = min(1.0, max(0.0, x)); return 1 - (1 - x) ** 3
def ease_back(x):
    x = min(1.0, max(0.0, x)); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def alpha(im, a):
    if a >= 1: return im
    c = im.copy(); c.putalpha(c.split()[3].point(lambda v: int(v * max(0, a)))); return c

def text_layer(text, fnt, fill, shadow=True, blur=10, sh_alpha=170, stroke=0, stroke_fill=None, spacing=0):
    """returns tight RGBA image of text with soft shadow"""
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    bb = d.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    pad = 40
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    o = (pad - bb[0], pad - bb[1])
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((o[0] + 2, o[1] + 4), text, font=fnt, fill=(0, 0, 0, sh_alpha), stroke_width=stroke)
        lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(lay).text(o, text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return lay

def paste_center(base, lay, cx, cy, a=1.0, scale=1.0):
    if scale != 1.0:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BICUBIC)
    base.alpha_composite(alpha(lay, a), (int(cx - lay.width / 2), int(cy - lay.height / 2)))

def radial_backdrop(cy, rx=620, ry=280, a=150, cx=W / 2):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    b = np.zeros((H, W, 4), np.uint8); b[..., 3] = (np.clip(1 - r, 0, 1) ** 1.4 * a).astype(np.uint8)
    return Image.fromarray(b, 'RGBA')

def vertical_grad(h, a_top, a_bot, col=(0, 0, 0)):
    g = np.zeros((h, W, 4), np.uint8); g[..., :3] = col
    g[..., 3] = np.linspace(a_top, a_bot, h).astype(np.uint8)[:, None]
    return Image.fromarray(g, 'RGBA')

def icon_phone(d, x, y, s, col):
    d.rounded_rectangle((x + s * .22, y, x + s * .78, y + s * 1.2), s * .14, fill=col)
    d.rounded_rectangle((x + s * .30, y + s * .14, x + s * .70, y + s * .95), s * .04, fill=(0, 0, 0, 0))

def icon_chat(d, x, y, s, col):
    d.rounded_rectangle((x, y, x + s * 1.2, y + s * 0.85), s * .22, fill=col)
    d.polygon([(x + s * .25, y + s * .75), (x + s * .55, y + s * .75), (x + s * .2, y + s * 1.1)], fill=col)
    for k in range(3):
        cx = x + s * (0.33 + k * 0.27); d.ellipse((cx - s * .07, y + s * .36, cx + s * .07, y + s * .5), fill=(0, 0, 0, 0))

def vignette(strength=0.4):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return np.clip(1 - strength * np.clip(r - 0.5, 0, 1) ** 1.4, 0, 1)[..., None].astype(np.float32)

def encode(render, total, music, out):
    nfr = int(round(total * FPS))
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-i', music, '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p',
                          '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for i in range(nfr):
        p.stdin.write(render(i / FPS).convert('RGB').tobytes())
        if i % 150 == 0: print(i, '/', nfr, flush=True)
    p.stdin.close(); p.wait(); print('done', p.returncode)
