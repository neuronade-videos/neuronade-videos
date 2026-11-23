"""Premium version: photoreal Blender inserts at key moments, on top of the hologram renderer (holo3)."""
import sys, os, json, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
sys.path.insert(0, '/home/claude/d003')
import holo3 as V

W, H, FPS = V.W, V.H, V.FPS
B3 = '/home/claude/d003/b3d'
FOCUS_Y = {}
SC = {'front': 1.25, 'igniter': 1.25}
T_IGNSHOT = V.Sx(0, 2) - 0.15
HERO = [  # (t0, t1, shot, zoom0, zoom1, focus anchor)
    (0.0, T_IGNSHOT, 'front', 1.0, 1.12, 'glass'),
    (T_IGNSHOT, V.T_REW, 'igniter', 1.0, 1.15, 'igniter'),
    (V.Sx(9, 1) - 0.25, V.DUR + 1, 'front', 1.12, 1.0, 'display'),
]
for h in HERO[2:]:
    V.CHANGES.append(h[0])
    if h[1] < V.DUR: V.CHANGES.append(h[1])
def hero_at(t):
    for h in HERO:
        if h[0] <= t < h[1]: return h
    return None

def make_grain(k):
    rng = np.random.default_rng(k); g = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
    return Image.fromarray(np.clip(128 + g * 9, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).convert('RGB')
def make_vign():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    v = np.clip(1.08 - 0.42 * r ** 2.2, 0.45, 1.0); return Image.fromarray((np.stack([v] * 3, 2) * 255).astype(np.uint8))

class R4(V.Renderer):
    def __init__(self):
        super().__init__(); self.stills = {}; self.anch = {}; self.grain = [make_grain(k) for k in range(6)]; self.vign = make_vign()
        g = np.ones((H, W, 3), np.float32); ramp_ = np.clip(np.arange(H) / 420.0, 0, 1) ** 0.8; g *= (0.35 + 0.65 * ramp_)[:, None, None]
        self.topgrad = Image.fromarray((g * 255).astype(np.uint8))
    def still(self, shot):
        if shot not in self.stills:
            im = Image.open('%s/final_%s.png' % (B3, shot)).convert('RGB')
            # premium bloom on highlights
            small = im.resize((im.width // 6, im.height // 6), Image.BILINEAR)
            bright = small.point(lambda v: max(0, v - 150) * 2.2).filter(ImageFilter.GaussianBlur(6)).resize(im.size, Image.BILINEAR)
            im = ImageChops.screen(im, bright)
            self.stills[shot] = im
            self.anch[shot] = json.load(open('%s/anch_%s.json' % (B3, shot)))
        return self.stills[shot], self.anch[shot]

    def frame(self, i):
        t = i / FPS; h = hero_at(t)
        if not h: return super().frame(i)
        t0, t1, shot, z0, z1, fk = h
        im, an = self.still(shot); s = SC[shot]; Ws, Hs = im.size
        u = V.sm((t - t0) / max(0.1, (min(t1, V.DUR) - t0)))
        z = z0 + (z1 - z0) * u
        fx, fy = an[fk][0] * s, an[fk][1] * s
        cw, ch = Ws / z, Hs / z
        k = (z - 1) / max(1e-6, (max(z0, z1) - 1)) * 0.75 if max(z0, z1) > 1 else 0
        cx = Ws / 2 + (fx - Ws / 2) * k; cy = Hs / 2 + (fy - Hs / 2) * k
        x0 = min(max(cx - cw / 2, 0), Ws - cw); y0 = min(max(cy - ch / 2, 0), Hs - ch)
        if shot in FOCUS_Y: y0 = min(max(fy - FOCUS_Y[shot] * ch / H, 0), Hs - ch)
        frame = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
        def P(key):
            a = an[key]; return ((a[0] * s - x0) * W / cw, (a[1] * s - y0) * H / ch)
        sc = W / cw * s  # px per output unit
        ov = Image.new('RGB', (W, H)); d = ImageDraw.Draw(ov, 'RGBA')
        if shot == 'front':
            # warm air rising from the top grille + flicker of the flame through the glass
            (gx, gy) = P('grille'); (fx_, fy_) = P('flame')
            wl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dw = ImageDraw.Draw(wl, 'RGBA')
            for kk in range(7):
                x = gx + (kk - 3) * 38 * sc
                for j in range(2):
                    ph = (t * 0.35 + kk * 0.17 + j * 0.5) % 1.0
                    pts = [(x + 10 * sc * math.sin(m * 0.6 - t * 3 + kk), gy - 260 * sc * (ph + m * 0.02)) for m in range(12)]
                    dw.line(pts, fill=(255, 170, 110, int(70 * math.sin(math.pi * ph))), width=5)
            frame = Image.alpha_composite(frame.convert('RGBA'), wl.filter(ImageFilter.GaussianBlur(3))).convert('RGB')
            fl = 0.5 + 0.5 * math.sin(t * 9.0) * math.sin(t * 5.3 + 1)
            r = 140 * sc; d.ellipse([fx_ - r, fy_ - r * 1.6, fx_ + r, fy_ + r * 0.8], fill=(255, 120, 40, int(30 + 25 * fl)))
        if shot == 'igniter':
            # the "hair dryer" : hot air streaming over the red igniter tip onto the pellets
            (ix, iy) = P('igniter'); (px_, py_) = P('pot'); hk = V.ramp(t, t0, t0 + 0.4)
            rng = random.Random(7)
            for kk in range(46):
                u = (t * 0.9 * (0.7 + 0.6 * rng.random()) + rng.random()) % 1.0
                sx, sy = ix + rng.uniform(-30, 30) * sc, iy - 220 * sc
                x = sx + (px_ + rng.uniform(-150, 150) * sc - sx) * u; y = sy + (py_ + 40 * sc - sy) * u
                col = V.mix((255, 210, 150), (255, 90, 30), u); r = (4 + 5 * u) * sc
                d.ellipse([x - r, y - r, x + r, y + r], fill=V.rgba(col, 220 * hk * math.sin(math.pi * u)))
            gl = 0.75 + 0.25 * math.sin(t * 6)
            r = 70 * sc; d.ellipse([ix - r, iy - r, ix + r, iy + r], fill=(255, 60, 10, int(70 * gl * hk)))
        frame = ImageChops.screen(frame, ov)
        # film look: vignette + grain
        frame = ImageChops.multiply(frame, self.vign)
        frame = ImageChops.multiply(frame, self.topgrad)
        frame = ImageChops.overlay(frame, self.grain[i % 6]) if hasattr(ImageChops, 'overlay') else frame
        frame = self.post_fx(frame, t, i)
        d1 = ImageDraw.Draw(frame, 'RGBA')
        # labels on photoreal shots
        LB = {'igniter': [(t0 + 0.4, t1, 'igniter', "Bougie d'allumage", True, 'r')]}.get(shot, []) if t0 < 20 else []
        for e in LB:
            self.label2d(frame, d1, P(e[2]), e[3], t, e[0], e[1], e[4], e[5], *(e[6:]))
        self.hud(frame, d1, t)
        self.captions(frame, d1, t)
        return frame

    def label2d(self, img, d, s, txt_, t, t0, t1, hot, side, dy=-60):
        a = V.win(t, t0, t1, 0.3)
        if a <= 0.01: return
        S_ = V.SAFE; f = V.font('SemiBold', 34); tw = d.textlength(txt_, font=f)
        right = side == 'r'; grow = V.ramp(t, t0, t0 + 0.3)
        ex = s[0] + (66 if right else -66); ey = V.clamp(s[1] + dy, S_['y0'], S_['y1']); hx = ex + (32 if right else -32)
        if right and hx + 12 + tw > S_['x1']: hx = S_['x1'] - 12 - tw; ex = min(ex, hx - 10)
        if not right and hx - 12 - tw < S_['x0']: hx = S_['x0'] + 12 + tw; ex = max(ex, hx + 10)
        col = V.FOCUS if hot else (140, 236, 255)
        d.ellipse([s[0] - 9, s[1] - 9, s[0] + 9, s[1] + 9], outline=V.rgba(col, 255 * a), width=3)
        d.ellipse([s[0] - 3.5, s[1] - 3.5, s[0] + 3.5, s[1] + 3.5], fill=V.rgba(col, 255 * a))
        d.line([s[0], s[1], s[0] + (ex - s[0]) * grow, s[1] + (ey - s[1]) * grow], fill=V.rgba(col, 240 * a), width=3)
        if grow > 0.6:
            d.line([ex, ey, hx, ey], fill=V.rgba(col, 240 * a), width=3)
            tx = hx + 12 if right else hx - 12
            V.text(img, d, (tx, ey), txt_, f, (255, 255, 255), a * V.ramp(t, t0 + 0.15, t0 + 0.5), 'lm' if right else 'rm', 4)

def render_seg(args):
    idx, f0, f1 = args
    r = R4(); out = '/home/claude/d003/seg/seg_%03d' % idx
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(FPS), '-f', 'mp4', out + '.tmp.mp4']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1): p.stdin.write(r.frame(i).tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.rename(out + '.tmp.mp4', out + '.mp4')
    return idx, rc

if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        r = R4(); os.makedirs('/home/claude/d003/prev', exist_ok=True)
        for ts in sys.argv[2:]:
            r.frame(int(float(ts) * FPS)).save('/home/claude/d003/prev/p_%s.png' % ts); print(ts, flush=True)
    elif sys.argv[1] == 'segs':
        SEG = 150; need = set()
        for h in HERO:
            a, b = max(0, h[0] - 0.6), min(V.DUR, h[1] + 0.6)
            for k in range(int(a * FPS) // SEG, int(b * FPS) // SEG + 1): need.add(k)
        print(sorted(need))
    else:
        from multiprocessing import Pool
        SEG = 150; need = set()
        for h in HERO:
            a, b = max(0, h[0] - 0.6), min(V.DUR, h[1] + 0.6)
            for k in range(int(a * FPS) // SEG, min(int(b * FPS) // SEG, (V.NF - 1) // SEG) + 1): need.add(k)
        segs = [(k, k * SEG, min(V.NF, (k + 1) * SEG)) for k in sorted(need)]
        segs = [s for s in segs if not os.path.exists('/home/claude/d003/seg/seg_%03d.mp4' % s[0])]
        with Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 2) as p:
            for res in p.imap_unordered(render_seg, segs): print(res, flush=True)
