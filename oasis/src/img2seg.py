import sys, subprocess
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
src, out, mode, dur = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
W, H, FPS = 1080, 1920, 30
im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
sc = max(W * 1.12 / im.width, H * 1.06 / im.height)
im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
iw, ih = im.size
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-crf', '15', '-preset', 'fast', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
n = int(dur * FPS)
for i in range(n):
    e = i / (n - 1)
    base = min(iw / W, ih / H)
    if mode == 'zin':
        z = 1 + 0.10 * e; cw, ch = W * base / z, H * base / z; cx, cy = iw / 2, ih / 2
    else:
        cw, ch = W * base, H * base; span = iw - cw
        cx = cw / 2 + span * (0.15 + 0.7 * e); cy = ih / 2
    fr = im.transform((W, H), Image.AFFINE, (cw / W, 0, cx - cw / 2, 0, ch / H, cy - ch / 2), Image.BICUBIC)
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait(); print('ok', out)
