"""Glitch anomalies: the in-universe 'neuronade.ia' terminal briefly reveals self-aware messages (8 frames each, 6 readable)."""
import sys, os, json, math, random, subprocess, re
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '/home/claude/d002')
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

KEEP = {'cap': (1320, 1460), 'hud': (322, 372), 'outro': (1468, 1562)}
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
    tw = ImageDraw.Draw(img).textlength(s + '  ', font=f)
    if tw > 900: f = V.font('monob', int(46 * 900 / tw))
    d.rectangle([60 + jitter, y0 - 54, 1020 + jitter, y0 + 40], fill=(16, 2, 4, 225), outline=V.rgba(GL, 200), width=2)
    V.text(img, d, (80 + jitter, y0 - 34), "neuronade.ia ~ $", V.font('mono', 22), GL, 0.8, 'lm')
    V.text(img, d, (90 + jitter, y0 + 8), s, f, GL, 1.0, 'lm')
    cx = 90 + jitter + d.textlength(s + ' ', font=f); d.rectangle([cx, y0 - 14, cx + 24, y0 + 30], fill=V.rgba(GL, 230))

class R8(H7.R7):
    _ev = None; _kz = None
    def frame(self, i):
        self._ev = active(i); self._kz = None
        img = super().frame(i)
        if self._ev:
            k, s, show, j = self._ev
            keep = (self._kz or KEEP.get(k)) if show else None
            img = tear(img, i * 7 + 3, 1.0 if show else 0.6, keep)
        return img
    def captions(self, img, d, t):
        e = self._ev
        if e and e[0] == 'cap' and e[2]: fake_caption(img, d, e[1], jitter=(6 if e[3] % 2 else -4)); return
        super().captions(img, d, t)
    def overlays3d(self, img, d, cam, t):
        e = self._ev
        if e and e[0] == 'thermo' and e[2]:
            sc, zc = cam.p1(np.array(V.TH) + (-3, 8, 0))
            if zc > 50:
                fs = int(V.clamp(22 * cam.F / zc, 8, 120)); V.text(img, d, (sc[0], sc[1]), e[1], V.font('Bold', fs), GL, 1.0, 'mm')
                self._kz = (sc[1] - fs, sc[1] + fs)
            return
        if e and e[0] == 'door' and e[2]:
            p = V.door_points_one(V.G.ANCH['door'][0], t); sc, zc = cam.p1(np.array(p) + (0, 60, 0))
            if zc > 50:
                f = V.font('monob', 40); s = e[1]; tw = d.textlength(s, font=f)
                x0 = V.clamp(sc[0] - tw / 2, 60, W - 80 - tw); y = V.clamp(sc[1], 420, 1200)
                d.rectangle([x0 - 20, y - 34, x0 + tw + 20, y + 34], fill=(16, 2, 4, 235), outline=V.rgba(GL, 200), width=2)
                V.text(img, d, (x0, y), s, f, GL, 1.0, 'lm'); self._kz = (y - 40, y + 40)
        super().overlays3d(img, d, cam, t)
    def hud(self, img, d, t):
        e = self._ev
        if e and e[0] == 'chap' and e[2]:
            n = max(x['p'] for x in V.SENTS if x['t0'] <= t + 0.4); old = V.CHAP[n]; V.CHAP[n] = e[1]
            try: super().hud(img, d, t)
            finally: V.CHAP[n] = old
            self._kz = (150, 240); return
        super().hud(img, d, t)
        if e and e[0] == 'hud' and e[2]:
            lab, val = e[1].split(' : ', 1)
            text_x = 70
            V.text(img, d, (text_x, 336), lab, V.font('mono', 20), GL, 0.9, 'lm')
            V.text(img, d, (text_x + 118, 338), val, V.font('monob', 30), GL, 1.0, 'lm')

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
    return k, encode('/home/claude/d002/seg/seg_%03d.mp4' % k, (r.frame(i) for i in range(f0, f1)))

if __name__ == '__main__':
    import time
    os.makedirs('/home/claude/d002/prev', exist_ok=True); os.makedirs('/home/claude/d002/seg', exist_ok=True)
    if sys.argv[1] == 'preview':
        r = R8()
        for k, f0, s, nm in EVF:
            r.frame(f0 + 3).save('/home/claude/d002/prev/g_%d.png' % f0); print(k, round(f0 / FPS, 2), flush=True)
        outro8(OUTRO_EV + 3 / FPS).save('/home/claude/d002/prev/g_outro.png')
    elif sys.argv[1] == 'frames':
        r = R8()
        for ts in sys.argv[2:]:
            t0 = time.time(); r.frame(int(float(ts) * FPS)).save('/home/claude/d002/prev/f_%s.png' % ts); print(ts, round(time.time() - t0, 2), flush=True)
    else:
        times = [INTRO + f0 / FPS for k, f0, s, nm in EVF] + [INTRO + V.NF / FPS + OUTRO_EV]
        durs = [(nm + 2) / FPS for k, f0, s, nm in EVF] + [(msg_frames(LORE['outro']['text']) + 2) / FPS]
        os.makedirs('/home/claude/d002/audio', exist_ok=True)
        json.dump(dict(times=times, durs=durs), open('/home/claude/d002/audio/glitch_times.json', 'w'))
        print('times', [round(x, 2) for x in times], flush=True)
        allk = [k for k in range((V.NF + 149) // 150) if not os.path.exists('/home/claude/d002/seg/seg_%03d.mp4' % k)]
        from multiprocessing import Pool
        with Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 2) as p:
            for res in p.imap_unordered(render_seg, allk): print(res, flush=True)
        import brand as B
        if not os.path.exists('/home/claude/d002/seg/z_outro.mp4'):
            print('outro', encode('/home/claude/d002/seg/z_outro.mp4', (outro8(i / FPS) for i in range(int(round(B.OUTRO * FPS))))), flush=True)
