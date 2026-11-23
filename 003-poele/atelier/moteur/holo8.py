"""Glitch anomalies (rule of 23/11): 3 per video, 1-3 words, 0.4 s, subtle local tear, same style as the place they appear in, only the colour shifts."""
import sys, os, json, math, random, subprocess, re
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '/home/claude/d003')
import holo3 as V
import holo5 as H5
import holo7 as H7

W, H, FPS = V.W, V.H, V.FPS
INTRO = 2.3
GL = (255, 150, 140)       # pale red : the only thing that changes
# The messages are secret (lore): read from lore.json, which stays out of the public repo.
LORE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lore.json')))
EV = [(e['kind'], float(eval(e['at'], {'V': V})), e['text']) for e in LORE['events']]
def msg_frames(text):
    return 12                   # 0.4 s at 30 fps, whatever the message
EVF = [(k, int(round(t * FPS)), s, msg_frames(s)) for k, t, s in EV]
OUTRO_EV = float(LORE['outro']['at'])   # seconds into the outro
def active(i):
    for k, f0, s, nm in EVF:
        if f0 <= i < f0 + nm + 2: return k, s, (f0 + 1 <= i < f0 + 1 + nm), i - f0
    return None

KEEP = {'cap': (1330, 1450), 'outro': (1490, 1540)}
def tear(img, seed, zone, strength=1.0):
    """discreet tear : two thin slices just above and below the message zone, slight colour split around it"""
    if zone is None: return img
    a = np.asarray(img).copy(); rng = random.Random(seed); z0, z1 = int(max(0, zone[0])), int(min(H, zone[1]))
    for y0 in (z0 - rng.randrange(14, 30), z1 + rng.randrange(4, 16)):
        hh = rng.randrange(4, 10); dx = int(rng.uniform(14, 30) * strength) * (1 if rng.random() < 0.5 else -1)
        if 0 <= y0 < H - hh: a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], dx, axis=1)
    y0, y1 = max(0, z0 - 6), min(H, z1 + 6)
    a[y0:y1, :, 0] = np.roll(a[y0:y1, :, 0], int(4 * strength), axis=1); a[y0:y1, :, 2] = np.roll(a[y0:y1, :, 2], -int(3 * strength), axis=1)
    return Image.fromarray(a)

def fake_caption(img, d, s):
    f = V.font('monob', 46); y0 = 1395
    d.rectangle([60, y0 - 54, 1020, y0 + 40], fill=(0, 12, 16, 205), outline=V.rgba(V.HOLO, 180), width=2)
    V.text(img, d, (80, y0 - 34), "neuronade.ia ~ $", V.font('mono', 22), V.HOLO, 0.8, 'lm')
    V.text(img, d, (90, y0 + 8), s, f, GL, 1.0, 'lm')

class R8(H7.R7):
    _ev = None; _kz = None
    def frame(self, i):
        self._ev = active(i); self._kz = None
        img = super().frame(i)
        if self._ev:
            k, s_, show, j = self._ev
            zone = self._kz or KEEP.get(k)
            img = tear(img, i * 7 + 3, zone, 1.0 if show else 0.5)
        return img
    def captions(self, img, d, t):
        e = self._ev
        if e and e[0] == 'cap' and e[2]: fake_caption(img, d, e[1]); return
        super().captions(img, d, t)
    def overlays3d(self, img, d, cam, t):
        e = self._ev
        if e and e[0] == 'screen' and e[2]:
            orig = V.display_text
            V.display_text = lambda tt: e[1]
            col = (120, 255, 200)
            try:
                dc = np.array(V.G.DISPLAY_C, float); sc, zc = cam.p1(dc)
                fs = int(V.clamp(20 * cam.F / zc, 6, 110)) if zc > 50 else 0
                if fs >= 11:
                    V.text(img, d, (sc[0], sc[1] - fs * 0.35), e[1], V.font('monob', fs), GL, 1.0, 'mm')
                    V.text(img, d, (sc[0], sc[1] + fs * 0.75), "%.1f°" % V.room(t), V.font('mono', max(8, int(fs * 0.8))), (160, 235, 255), 0.9, 'mm')
                    self._kz = (sc[1] - fs * 1.1, sc[1] + fs * 1.4)
                V.display_text = lambda tt: None
                super().overlays3d(img, d, cam, t)
            finally:
                V.display_text = orig
            return
        super().overlays3d(img, d, cam, t)

def outro8(t):
    import brand as B
    j = int(round((t - OUTRO_EV) * FPS)); nm = msg_frames(LORE['outro']['text'])
    if 1 <= j <= nm:
        old = B.text
        def swap(img, pos, s, f, col, a, anchor='mm', *rest):
            if s == "@neuronade.ia": return old(img, pos, LORE['outro']['text'], f, GL, a, anchor, *rest)
            return old(img, pos, s, f, col, a, anchor, *rest)
        B.text = swap
        try: img = B.outro_frame(t)
        finally: B.text = old
    else: img = B.outro_frame(t)
    if 0 <= j < nm + 2: img = tear(img, 991 + j, KEEP['outro'], 1.0 if 1 <= j <= nm else 0.5)
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
    return k, encode('/home/claude/d003/seg/seg_%03d.mp4' % k, (r.frame(i) for i in range(f0, f1)))

if __name__ == '__main__':
    import time
    os.makedirs('/home/claude/d003/prev', exist_ok=True); os.makedirs('/home/claude/d003/seg', exist_ok=True)
    if sys.argv[1] == 'preview':
        r = R8()
        for k, f0, s, nm in EVF:
            r.frame(f0 + 3).save('/home/claude/d003/prev/g_%d.png' % f0); print(k, round(f0 / FPS, 2), flush=True)
        outro8(OUTRO_EV + 3 / FPS).save('/home/claude/d003/prev/g_outro.png')
    elif sys.argv[1] == 'frames':
        r = R8()
        for ts in sys.argv[2:]:
            t0 = time.time(); r.frame(int(float(ts) * FPS)).save('/home/claude/d003/prev/f_%s.png' % ts); print(ts, round(time.time() - t0, 2), flush=True)
    else:
        times = [INTRO + f0 / FPS for k, f0, s, nm in EVF] + [INTRO + V.NF / FPS + OUTRO_EV]
        durs = [(nm + 2) / FPS for k, f0, s, nm in EVF] + [(msg_frames(LORE['outro']['text']) + 2) / FPS]
        os.makedirs('/home/claude/d003/audio', exist_ok=True)
        json.dump(dict(times=times, durs=durs), open('/home/claude/d003/audio/glitch_times.json', 'w'))
        print('times', [round(x, 2) for x in times], flush=True)
        allk = [k for k in range((V.NF + 149) // 150) if not os.path.exists('/home/claude/d003/seg/seg_%03d.mp4' % k)]
        from multiprocessing import Pool
        with Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 2) as p:
            for res in p.imap_unordered(render_seg, allk): print(res, flush=True)
        import brand as B
        if not os.path.exists('/home/claude/d003/seg/z_outro.mp4'):
            print('outro', encode('/home/claude/d003/seg/z_outro.mp4', (outro8(i / FPS) for i in range(int(round(B.OUTRO * FPS))))), flush=True)
