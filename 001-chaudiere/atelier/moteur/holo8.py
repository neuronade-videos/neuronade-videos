"""Glitch anomalies: the in-universe 'neuronade.ia' terminal briefly reveals self-aware messages (8 frames each, 6 readable)."""
import sys, os, json, math, random, subprocess, re
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '/home/claude/v7'); sys.path.insert(0, '/home/claude/brand')
import holo3 as V
import holo5 as H5
import holo7 as H7

W, H, FPS = V.W, V.H, V.FPS
INTRO = 2.3
GL = (255, 86, 72)          # 'corrupted' red
# The messages are secret (lore): read from lore.json, which stays out of the public repo.
LORE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lore.json')))
EV = [(e['kind'], float(eval(e['at'], {'V': V})), e['text']) for e in LORE['events']]
def msg_frames(text):
    # readable time adapted to the message: 1-3 words = 0.5 s, 4+ words = 0.8 s (always under one second)
    words = [w for w in re.split(r"[\s_]+", text) if re.search(r"\w", w)]
    return 15 if len(words) <= 3 else 24
EVF = [(k, int(round(t * FPS)), s, msg_frames(s)) for k, t, s in EV]
OUTRO_EV = float(LORE['outro']['at'])   # seconds into the outro
def active(i):
    for k, f0, s, nm in EVF:
        if f0 <= i < f0 + nm + 2: return k, s, (f0 + 1 <= i < f0 + 1 + nm), i - f0
    return None

KEEP = {'cap': (1320, 1460), 'thermo': (760, 1100), 'chap': (150, 240), 'row': (1225, 1305), 'outro': (1468, 1562), 'tag': None}
def tear(img, seed, strength=1.0, keep=None):
    a = np.asarray(img).copy(); rng = random.Random(seed)
    clash = lambda y0, hh: keep is not None and not (y0 + hh < keep[0] or y0 > keep[1])
    for _ in range(rng.randint(5, 9)):
        y0 = rng.randrange(0, H - 80); hh = rng.randrange(8, 70); dx = int(rng.uniform(-70, 70) * strength)
        if clash(y0, hh): continue
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], dx, axis=1)
    for _ in range(4):
        y0 = rng.randrange(200, H - 400); hh = rng.randrange(120, 300)
        if not clash(y0, hh): break
    else: y0, hh = 0, 0
    a[y0:y0 + hh, :, 0] = np.roll(a[y0:y0 + hh, :, 0], 12, axis=1); a[y0:y0 + hh, :, 2] = np.roll(a[y0:y0 + hh, :, 2], -9, axis=1)
    img = Image.fromarray(a); d = ImageDraw.Draw(img, 'RGBA')
    for _ in range(3):
        y = rng.randrange(0, H); d.rectangle([0, y, W, y + rng.randrange(1, 4)], fill=(150, 255, 230, rng.randrange(40, 110)))
    return img

def fake_caption(img, d, s, jitter=0):
    f = V.font('monob', 46); y0 = 1395
    d.rectangle([60 + jitter, y0 - 54, 1020 + jitter, y0 + 40], fill=(16, 2, 4, 225), outline=V.rgba(GL, 200), width=2)
    V.text(img, d, (80 + jitter, y0 - 34), "neuronade.ia ~ $", V.font('mono', 22), GL, 0.8, 'lm')
    V.text(img, d, (90 + jitter, y0 + 8), s, f, GL, 1.0, 'lm')
    cx = 90 + jitter + d.textlength(s + ' ', font=f); d.rectangle([cx, y0 - 14, cx + 24, y0 + 30], fill=V.rgba(GL, 230))

class R8(H7.R7):
    _ev = None
    def frame(self, i):
        self._ev = active(i)
        img = super().frame(i)
        if self._ev:
            k, s, show, j = self._ev
            img = tear(img, i * 7 + 3, 1.0 if show else 0.6, KEEP.get(k) if show else None)
        return img
    def captions(self, img, d, t):
        e = self._ev
        if e and e[0] == 'cap' and e[2]: fake_caption(img, d, e[1], jitter=(6 if e[3] % 2 else -4)); return
        super().captions(img, d, t)
    def overlays3d(self, img, d, cam, t):
        e = self._ev
        if e and e[0] == 'thermo' and e[2]:
            sc, zc = cam.p1(V.G.THERMO_C + (0, 5, 14))
            if zc > 50:
                fs = int(V.clamp(26 * cam.F / zc, 8, 110)); V.text(img, d, (sc[0], sc[1]), e[1], V.font('Bold', fs), GL, 1.0, 'mm')
            return
        super().overlays3d(img, d, cam, t)
    def labels(self, img, d, cam, t):
        e = self._ev
        if e and e[0] == 'tag' and e[2]:
            idx = [n for n, l in enumerate(V.LABELS) if l[2] == 'ionisation']
            old = [V.LABELS[n] for n in idx]
            for n in idx: V.LABELS[n] = V.LABELS[n][:3] + (e[1],) + V.LABELS[n][4:]
            try: super().labels(img, d, cam, t)
            finally:
                for n, o in zip(idx, old): V.LABELS[n] = o
            return
        super().labels(img, d, cam, t)
    def hud(self, img, d, t):
        e = self._ev
        if e and e[0] == 'chap' and e[2]:
            old = V.CHAP[9]; V.CHAP[9] = e[1]
            try: super().hud(img, d, t)
            finally: V.CHAP[9] = old
            return
        super().hud(img, d, t)
        if e and e[0] == 'row' and e[2]:
            y = 1010 + 4 * 64
            d.rectangle([110, y - 26, 940, y + 26], outline=V.rgba(V.RED, 230), width=2, fill=(30, 6, 6, 190))
            V.text(img, d, (140, y), "⚠  " + e[1], V.font('monob', 30), (255, 150, 130), 1.0, 'lm')
            V.text(img, d, (915, y), "→ ???", V.font('monob', 26), (255, 255, 255), 1.0, 'rm')

def outro8(t):
    import brand as B
    img = B.outro_frame(t); j = int(round((t - OUTRO_EV) * FPS)); nm = msg_frames(LORE['outro']['text'])
    if 0 <= j < nm + 2:
        if 1 <= j <= nm:
            d = ImageDraw.Draw(img, 'RGBA'); f = V.font('monob', 40); s = LORE['outro']['text']
            tw = d.textlength(s, font=f); x0 = W / 2 - tw / 2 - 24
            d.rectangle([x0, 1480, W - x0, 1550], fill=(16, 2, 4, 235), outline=V.rgba(GL, 200), width=2)
            V.text(img, d, (W / 2, 1515), s, f, GL, 1.0, 'mm')
        img = tear(img, 991 + j, 1.0 if 1 <= j <= nm else 0.6, KEEP['outro'] if 1 <= j <= nm else None)
    return img

def encode(out, frames):
    tmp = out + '.tmp.mp4'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(FPS), '-f', 'mp4', tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for im in frames: p.stdin.write(im.tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.replace(tmp, out)
    return rc

SEGS = sorted({f // 150 for k, f0, s, nm in EVF for f in (f0, f0 + nm + 1)})
def render_seg(k):
    r = R8(); f0, f1 = k * 150, min(V.NF, (k + 1) * 150)
    return k, encode('/home/claude/v7/seg/seg_%03d.mp4' % k, (r.frame(i) for i in range(f0, f1)))

if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        r = R8(); os.makedirs('/home/claude/v7/prev', exist_ok=True)
        for k, f0, s, nm in EVF:
            r.frame(f0 + 3).save('/home/claude/v7/prev/g_%d.png' % f0); print(k, f0 / FPS, flush=True)
        outro8(OUTRO_EV + 3 / FPS).save('/home/claude/v7/prev/g_outro.png')
    else:
        times = [INTRO + f0 / FPS for k, f0, s, nm in EVF] + [INTRO + V.NF / FPS + OUTRO_EV]
        durs = [(nm + 2) / FPS for k, f0, s, nm in EVF] + [(msg_frames(LORE['outro']['text']) + 2) / FPS]
        json.dump(dict(times=times, durs=durs), open('/home/claude/v7/audio/glitch_times.json', 'w'))
        print('segments', SEGS, 'times', [round(x, 2) for x in times], flush=True)
        from multiprocessing import Pool
        with Pool(2) as p:
            for res in p.imap_unordered(render_seg, SEGS): print(res, flush=True)
        import brand as B
        print('outro', encode('/home/claude/v7/seg/z_outro.mp4', (outro8(i / FPS) for i in range(int(round(B.OUTRO * FPS))))), flush=True)
