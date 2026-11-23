"""neuronade.ia identity prototype: intro 'dossier' + corner logo + outro '+1 neurone rafraichi' with sonic logo."""
import math, random, subprocess, os, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont

W, H, FPS = 1080, 1920, 30
OUT = '/home/claude/d003/brand_out'
CY = (70, 232, 238); LEM = (255, 222, 60); MINT = (150, 255, 230); WH = (240, 255, 250)
FD = '/usr/share/fonts/opentype/inter/Inter-'; MONOB = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'; MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
_fc = {}
def font(n, s):
    k = (n, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(MONOB if n == 'monob' else MONO if n == 'mono' else FD + n + '.otf', s)
    return _fc[k]
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def sm(x): x = clamp(x); return x * x * (3 - 2 * x)
def ramp(t, a, b): return sm((t - a) / (b - a))
def rgba(c, a): return (int(c[0]), int(c[1]), int(c[2]), int(clamp(a, 0, 255)))
def text(img, xy, s, f, col, a=1.0, anchor='mm', stroke=0):
    if a <= 0.01 or not s: return
    d = ImageDraw.Draw(img, 'RGBA'); x0, y0, x1, y1 = d.textbbox(xy, s, font=f, anchor=anchor, stroke_width=stroke)
    x0, y0, x1, y1 = int(x0) - 2, int(y0) - 2, int(x1) + 2, int(y1) + 2
    lay = Image.new('RGBA', (x1 - x0, y1 - y0)); ImageDraw.Draw(lay).text((xy[0] - x0, xy[1] - y0), s, font=f, fill=rgba(col, 255), anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a))); img.paste(lay, (x0, y0), lay)
def glow(img, g1=1.3, g2=1.1):
    w, h = img.size
    a = img.resize((w // 4, h // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((w, h), Image.BILINEAR).point(lambda v: min(255, int(v * g1)))
    b = img.resize((w // 10, h // 10), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4)).resize((w, h), Image.BILINEAR).point(lambda v: min(255, int(v * g2)))
    return ImageChops.screen(ImageChops.screen(img, a), b)
def bg_img():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.43) / (H * 0.7)) ** 2) * 1.6
    v = np.clip(1 - r, 0, 1)
    return Image.fromarray(np.stack([3 + 12 * v, 10 + 44 * v, 14 + 48 * v], 2).astype(np.uint8))
BG = bg_img()
rnd0 = random.Random(5)
NODES = [(rnd0.uniform(0, W), rnd0.uniform(0, H)) for _ in range(110)]
def network(d, t, a=1.0):
    for i, (x, y) in enumerate(NODES):
        x += 6 * math.sin(t * 0.7 + i); y += 6 * math.cos(t * 0.6 + i * 1.3)
        for (x2, y2) in NODES[i + 1:i + 8]:
            dd = math.hypot(x - x2, y - y2)
            if dd < 230: d.line([(x, y), (x2, y2)], fill=(40, 150, 160, int(60 * a * (1 - dd / 230))), width=2)
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(60, 190, 200, int(110 * a)))

# ---------- animated glass (drawn at 2x then reduced) ----------
def glass(fill, neuron_y, neuron_a, t, splash=0.0, size=880, ring=True):
    S = 2; M = size * S; img = Image.new('RGB', (M, M)); d = ImageDraw.Draw(img, 'RGBA'); rnd = random.Random(4)
    cx = M / 2; top_y = 0.27 * M; bot_y = 0.83 * M; rt = 0.232 * M; rb = 0.186 * M; k = 0.20
    def ell(y, r): return [cx - r, y - r * k, cx + r, y + r * k]
    def ring_pts(y, r, a0, a1, n=80): return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), y + r * k * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    L = lambda a, b, u: a + (b - a) * u
    if fill > 0.01:
        u0 = 1 - 0.82 * fill; ly = L(top_y, bot_y, u0) + 6 * math.sin(t * 9) * splash; lr = L(rt, rb, u0)
        d.polygon(ring_pts(ly, lr, math.pi, 2 * math.pi) + ring_pts(bot_y - 0.012 * M, rb - 6, 0, math.pi), fill=(255, 196, 30, 105))
        d.ellipse(ell(ly, lr), fill=(255, 225, 80, 110), outline=LEM + (255,), width=5)
        for q in (0.75, 0.5): d.ellipse(ell(ly, lr * q), outline=LEM + (120,), width=3)
        for j in range(int(26 * fill)):
            uu = (rnd.random() + t * 0.35 * (0.5 + rnd.random())) % 1.0; y = L(bot_y - 30, ly + 30, uu); r_ = L(rb, lr, uu) - 40
            x = cx + rnd.uniform(-r_, r_); s_ = rnd.uniform(6, 14); d.ellipse([x - s_, y - s_, x + s_, y + s_], outline=(255, 245, 190, 200), width=3)
    else: ly = bot_y
    # neuron
    if neuron_a > 0.01:
        nx, ny = cx + 0.015 * M, neuron_y * M; nr = random.Random(9)
        def branch(x, y, ang, length, w, depth):
            pts = [(x, y)]; a = ang
            for i in range(8):
                a += nr.uniform(-0.35, 0.35); x += math.cos(a) * length / 8; y += math.sin(a) * length / 8 * 0.85; pts.append((x, y))
            d.line(pts, fill=(20, 140, 160, int(200 * neuron_a)), width=max(4, int(w * 2.2)), joint='curve')
            d.line(pts, fill=(150, 250, 255, int(255 * neuron_a)), width=max(2, int(w * 0.9)), joint='curve')
            if depth > 0:
                for s_ in (-1, 1): branch(x, y, a + s_ * nr.uniform(0.35, 0.8), length * 0.62, w * 0.65, depth - 1)
            else: d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(170, 255, 255, int(255 * neuron_a)))
        for i in range(7):
            a = 2 * math.pi * i / 7 + nr.uniform(-0.25, 0.25); branch(nx + math.cos(a) * 80, ny + math.sin(a) * 68, a, nr.uniform(150, 210), 17, 2)
        d.ellipse([nx - 100, ny - 88, nx + 100, ny + 88], fill=(20, 140, 160, int(255 * neuron_a)))
        d.ellipse([nx - 88, ny - 76, nx + 88, ny + 76], fill=(90, 225, 240, int(255 * neuron_a)), outline=(220, 255, 255, int(255 * neuron_a)), width=7)
        d.ellipse([nx - 36, ny - 30, nx + 36, ny + 30], fill=(255, 240, 150, int(255 * neuron_a)))
    # splash droplets
    if splash > 0.01:
        for i in range(18):
            a = math.pi * (0.1 + 0.8 * i / 17); v = 0.6 + 0.4 * random.Random(i).random(); q = 1 - splash
            x = cx + math.cos(a) * 260 * q * v * (1 if i % 2 else -1); y = ly - math.sin(a) * 420 * q * v + 600 * q * q
            s_ = 10 * splash + 4; d.ellipse([x - s_, y - s_, x + s_, y + s_], fill=LEM + (int(255 * splash),))
    # glass wireframe
    for j in range(9):
        u = j / 8; y = L(top_y, bot_y, u); r = L(rt, rb, u)
        d.line(ring_pts(y, r, math.pi, 2 * math.pi), fill=CY + (70,), width=3)
        d.line(ring_pts(y, r, 0, math.pi), fill=CY + (200 if j in (0, 8) else 120,), width=6 if j in (0, 8) else 3)
    for i in range(16):
        a = 2 * math.pi * i / 16; front = math.sin(a) > 0
        d.line([(cx + rt * math.cos(a), top_y + rt * k * math.sin(a)), (cx + rb * math.cos(a), bot_y + rb * k * math.sin(a))], fill=CY + (190 if front else 60,), width=4 if front else 2)
    d.ellipse(ell(top_y, rt), outline=CY + (255,), width=8); d.ellipse(ell(bot_y, rb), outline=CY + (230,), width=6)
    # lemon + straw (appear with fill)
    la = clamp(fill * 1.5)
    if la > 0:
        lx, ly2, lr2 = cx + rt * 0.78, top_y - 0.035 * M, 0.088 * M
        d.ellipse([lx - lr2, ly2 - lr2, lx + lr2, ly2 + lr2], fill=(255, 215, 50, int(60 * la)), outline=LEM + (int(255 * la),), width=10)
        for i in range(10):
            a = 2 * math.pi * i / 10; d.line([(lx, ly2), (lx + lr2 * 0.8 * math.cos(a), ly2 + lr2 * 0.8 * math.sin(a))], fill=LEM + (int(220 * la),), width=5)
        sx0, sy0 = cx - 0.07 * M, bot_y - 0.12 * M; sx1, sy1 = cx - 0.15 * M, top_y - 0.20 * M
        for q in range(10):
            u0, u1 = q / 10, (q + 1) / 10; col = LEM if q % 2 else CY
            d.line([(L(sx0, sx1, u0), L(sy0, sy1, u0)), (L(sx0, sx1, u1), L(sy0, sy1, u1))], fill=col + (int(235 * la),), width=22)
    if ring:
        R = 0.455 * M; rot = t * 25
        for a0 in range(0, 360, 30): d.arc([cx - R, M / 2 - R, cx + R, M / 2 + R], a0 + 4 + rot, a0 + 22 + rot, fill=CY + (150,), width=6)
    return img.reduce(S)

# ---------- static logo (photo de profil v2) for intro + watermark ----------
LOGO = Image.open('/home/claude/b3d/logo_holo2.png').convert('RGB')
def logo_disc(size):
    im = LOGO.resize((size, size), Image.LANCZOS).convert('RGBA'); m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255); im.putalpha(m); return im

INTRO = 2.3; MID = 2.4; OUTRO = 5.6
def intro_frame(t):
    img = BG.copy(); d = ImageDraw.Draw(img, 'RGBA'); network(d, t, ramp(t, 0, 0.6))
    # terminal command typing
    cmd = "neuronade.ia ~ $ ouvrir DOSSIER_#003"; n = int(len(cmd) * ramp(t, 0.1, 0.85))
    a_term = 1 - ramp(t, 1.05, 1.3)
    if a_term > 0:
        d.rectangle([90, 900, 990, 990], fill=(0, 12, 16, int(210 * a_term)), outline=rgba(CY, 200 * a_term), width=2)
        text(img, (120, 945), cmd[:n] + ('█' if int(t * 8) % 2 == 0 else ''), font('monob', 38), MINT, a_term, 'lm')
    img = glow(img, 1.2, 1.05); d = ImageDraw.Draw(img, 'RGBA')
    # logo pop with flash at 1.05s
    if t >= 1.0:
        u = (t - 1.0) / 0.35; sc = 0.4 + 0.75 * sm(u) - 0.15 * sm((u - 1) * 1.5) if u < 2.2 else 1.0
        sz = int(560 * sc); lg = logo_disc(max(10, sz)); img.paste(lg, (W // 2 - sz // 2, 760 - sz // 2), lg)
        f = 1 - ramp(t, 1.02, 1.35)
        if f > 0: img = ImageChops.screen(img, Image.new('RGB', (W, H), tuple(int(v * 0.55 * f) for v in (180, 255, 240))))
        text(img, (W / 2, 1150), "DOSSIER #003", font('monob', 56), LEM, ramp(t, 1.35, 1.6), 'mm')
        text(img, (W / 2, 1235), "LE POÊLE À GRANULÉS", font('Black', 76), WH, ramp(t, 1.5, 1.75), 'mm', 6)
    # exit scan wipe
    if t > INTRO - 0.35:
        y = int(H * ramp(t, INTRO - 0.35, INTRO)); d = ImageDraw.Draw(img, 'RGBA')
        d.rectangle([0, 0, W, y], fill=(0, 0, 0, 255)); d.rectangle([0, y - 6, W, y + 6], fill=rgba(CY, 255))
    return img

MID_SRC = '/home/claude/v5/chaudiere_finale.mp4'
def mid_frames():
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', '30.0', '-t', str(MID), '-i', MID_SRC, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    n = len(raw) // (W * H * 3)
    for i in range(n):
        t = i / FPS; img = Image.frombytes('RGB', (W, H), raw[i * W * H * 3:(i + 1) * W * H * 3])
        # corner watermark (top-right), gentle pulse
        sz = 96; lg = logo_disc(sz); pul = 0.85 + 0.15 * math.sin(t * 3)
        lg.putalpha(lg.getchannel('A').point(lambda v: int(v * pul))); img.paste(lg, (W - 60 - sz, 340), lg)
        d = ImageDraw.Draw(img, 'RGBA'); d.rectangle([0, 1640, W, 1740], fill=(0, 0, 0, 200))
        text(img, (W / 2, 1690), "↗ logo signature en coin de vidéo", font('Bold', 40), LEM, 1.0, 'mm')
        yield img

def outro_frame(t):
    img = BG.copy(); d = ImageDraw.Draw(img, 'RGBA'); network(d, t + 5, 1.0)
    fill = ramp(t, 0.2, 1.7)
    drop_t0, drop_t1 = 1.75, 2.25
    if t < drop_t0: ny, na = 0.02, ramp(t, 1.2, 1.6)
    elif t < drop_t1: ny, na = 0.02 + (0.36 - 0.02) * ((t - drop_t0) / (drop_t1 - drop_t0)) ** 2, 1.0
    else: ny, na = 0.36 + 0.012 * math.sin((t - drop_t1) * 4) * math.exp(-(t - drop_t1) * 1.5), 1.0
    splash = 1 - ramp(t, drop_t1, drop_t1 + 0.6) if t >= drop_t1 else 0
    g = glass(fill, ny, na, t, splash); gw = g.width
    img.paste(g, (W // 2 - gw // 2, 820 - gw // 2), Image.eval(g.convert('L'), lambda v: min(255, v * 3)))
    # counter
    if t > 2.3:
        a = ramp(t, 2.3, 2.6); val = '003' if t > 2.75 else ('002' if int(t * 20) % 2 else '003')
        text(img, (W / 2, 1330), "NEURONES RAFRAÎCHIS : " + val, font('monob', 46), LEM, a, 'mm')
        b = ramp(t, 2.75, 3.05)
        if b > 0: text(img, (W / 2 + 330, 1270), "+1", font('Black', 64), MINT, b * (1 - ramp(t, 4.2, 4.8)), 'mm', 5)
    text(img, (W / 2, 1430), "Neurone rafraîchi. À la prochaine dose.", font('Bold', 44), WH, ramp(t, 3.2, 3.6), 'mm', 4)
    text(img, (W / 2, 1515), "@neuronade.ia", font('monob', 40), CY, ramp(t, 3.6, 4.0), 'mm')
    return glow(img, 1.15, 1.05)

# ---------- sound ----------
SR = 44100
def sonic(total):
    N = int(total * SR); out = np.zeros(N); rng = np.random.default_rng(3)
    def put(t, sig, g):
        i0 = int(t * SR); i1 = min(N, i0 + len(sig)); out[i0:i1] += g * sig[:i1 - i0]
    def bell(f, dur, dec):
        x = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(2 * np.pi * 2.01 * f * x) + 0.15 * np.sin(2 * np.pi * 3.0 * f * x)) * np.exp(-x * dec) * np.minimum(1, x / 0.004)
    def fizz(dur):
        L = int(dur * SR); nz = rng.standard_normal(L); F = np.fft.rfft(nz); fr = np.fft.rfftfreq(L, 1 / SR); F *= (fr > 5000) * (fr < 14000)
        w = np.fft.irfft(F, L); w /= np.abs(w).max(); crack = (rng.random(L) < 0.004) * rng.uniform(0.3, 1, L)
        return (w * 0.35 + crack) * np.linspace(0, 1, L) ** 1.5
    def bloop(f0=650, f1=140, dur=0.28):
        x = np.arange(int(dur * SR)) / SR; f = f1 + (f0 - f1) * np.exp(-x * 18)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9)
    def sub(dur=0.9):
        x = np.arange(int(dur * SR)) / SR; return np.sin(2 * np.pi * (60 - 18 * x) * x) * np.exp(-x * 4)
    def ticks(t0, t1, step=0.045):
        t = t0
        while t < t1:
            L = int(0.012 * SR); x = np.arange(L) / SR; put(t, np.sin(2 * np.pi * 2600 * x) * np.exp(-x * 400), 0.08); t += step
    # signature motif: fizz rise -> pop -> D5 A5 F#6 (bright, fresh)
    def signature(t0, final=False):
        put(t0 - 0.6, fizz(0.6), 0.5); put(t0, bloop(900, 300, 0.12), 0.5); put(t0, sub(), 0.6)
        notes = [587.3, 880.0, 1480.0] if not final else [587.3, 880.0, 1174.7, 1480.0]
        for i, f in enumerate(notes): put(t0 + 0.07 + i * 0.11, bell(f, 1.6, 3.2 if i < len(notes) - 1 else 1.8), 0.32)
    ticks(0.1, 0.85)
    signature(1.02)
    put(INTRO - 0.35, np.convolve(rng.standard_normal(int(0.35 * SR)), np.ones(40) / 40, 'same') * np.linspace(1, 0, int(0.35 * SR)), 0.25)
    o = INTRO + MID
    # pour/fill sound
    L = int(1.5 * SR); nz = rng.standard_normal(L); F = np.fft.rfft(nz); fr = np.fft.rfftfreq(L, 1 / SR); F *= np.exp(-((np.log(fr + 1) - np.log(1800)) ** 2) / 0.6)
    pour = np.fft.irfft(F, L); pour /= np.abs(pour).max(); put(o + 0.2, pour * np.sin(np.linspace(0, np.pi, L)) * (0.8 + 0.2 * np.sin(np.arange(L) / SR * 2 * np.pi * 9)), 0.22)
    put(o + 2.25, bloop(), 0.7)            # plouf
    put(o + 2.25, fizz(0.5)[::-1], 0.25)
    signature(o + 2.8, final=True)
    # soft pad bed
    x = np.arange(N) / SR; pad = sum(np.sin(2 * np.pi * f * x + p) for f, p in ((146.8, 0), (220.0, 1), (293.7, 2), (370.0, 3))) * 0.04
    pad *= np.clip(x / 0.8, 0, 1) * np.clip((total - x) / 1.0, 0, 1)
    out += pad
    out = out / np.abs(out).max() * 0.9
    with wave.open(OUT + '/sonic.wav', 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((out * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    total = INTRO + MID + OUTRO
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '20', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', OUT + '/v.mp4'], stdin=subprocess.PIPE)
    for i in range(int(INTRO * FPS)): p.stdin.write(intro_frame(i / FPS).tobytes())
    for im in mid_frames(): p.stdin.write(im.tobytes())
    for i in range(int(OUTRO * FPS)): p.stdin.write(outro_frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    sonic(total)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', OUT + '/v.mp4', '-i', OUT + '/sonic.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-af', 'loudnorm=I=-15:TP=-1.5', '-shortest', '-movflags', '+faststart', OUT + '/prototype_identite_neuronade.mp4'])
    print('ok', total)
