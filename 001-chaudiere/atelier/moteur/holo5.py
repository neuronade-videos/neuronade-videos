"""v5: terminal-style captions (style 3) + targeting-bracket component tags, on top of holo4 (photoreal inserts)."""
import sys, os, re, math, subprocess
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '/home/claude/v7')
import holo3 as V
import holo4 as H4

W, H, FPS = V.W, V.H, V.FPS
MINT = (150, 255, 230)
GROUPS = {'exchanger': ('exchanger', 'coil'), 'burner': ('burner',), 'fan': ('fan',), 'gasvalve': ('gasvalve',), 'pump': ('pump',),
          'board': ('board',), 'flue': ('flue',), 'vessel': ('vessel',), 'phx': ('phx',), 'valve3': ('valve3',), 'siphon': ('siphon',),
          'gauge': ('gauge',), 'ignition': ('ignition',), 'ionisation': ('ionisation',), 'thermostat': ('thermostat',), 'radiator': ('radiator',),
          'flowmeter': ('flowmeter',), 'safety': ('safety',), 'venturi': ('venturi',), 'tap': ('tap',), 'limiter': ('limiter',)}
GIDX = {}
for k, p in enumerate(V.POLYS): GIDX.setdefault(p['group'], []).append(k)
def group_pts(key):
    ids = [k for g in GROUPS.get(key, ()) for k in GIDX.get(g, [])]
    if not ids: return None
    return np.concatenate([V.POLYS[k]['pts'] for k in ids])
GP = {k: group_pts(k) for k in GROUPS}

def wrap(d, s, f, maxw):
    ws = s.split(' '); lines = []; cur = ''
    for w in ws:
        tr = (cur + ' ' + w).strip()
        if d.textlength(tr, font=f) <= maxw: cur = tr
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

LABEL_MODE = 'B'   # 'A' = no tags, 'B' = targeting brackets
# overview: one component at a time (until the next one is named)
_ov = sorted([l for l in V.LABELS if V.P(1) <= l[0] < V.P(2)], key=lambda l: l[0])
_new = []
for i_, l in enumerate(_ov):
    t1_ = _ov[i_ + 1][0] - 0.05 if i_ + 1 < len(_ov) else V.P(2) - 0.3
    _new.append((l[0], t1_) + tuple(l[2:]))
V.LABELS[:] = [l for l in V.LABELS if not (V.P(1) <= l[0] < V.P(2))] + _new
OVERVIEW = _new
_orig_focus = V.scene_focus
def _focus(t):
    if V.P(1) <= t < V.P(2):
        for l in OVERVIEW:
            if l[0] <= t < l[1] + 0.05: return set(GROUPS.get(l[2], ())), 0.5
    return _orig_focus(t)
V.scene_focus = _focus

def tag(img, d, box, txt, t, t0, t1, hot, taken=None):
    """targeting brackets around box (x0,y0,x1,y1) + terminal tag"""
    a = V.win(t, t0, t1, 0.25)
    if a <= 0.01: return
    x0, y0, x1, y1 = box; S_ = V.SAFE
    if x1 < S_['x0'] or x0 > W - 20 or y1 < S_['y0'] - 40 or y0 > S_['y1'] + 40: return
    g = V.sm((t - t0) / 0.3); pad = 18 + 60 * (1 - g)
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
    col = V.FOCUS if hot else MINT
    L = max(16, min(44, (x1 - x0) * 0.22, (y1 - y0) * 0.22))
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([cx, cy + L * sy, cx, cy, cx + L * sx, cy], fill=V.rgba(col, 235 * a), width=3)
    # tag above the box (or below if no room)
    f = V.font('monob', 30); s = '> ' + txt.upper().replace(' ', '_')
    n = max(2, int(len(s) * V.ramp(t, t0 + 0.15, t0 + 0.6)))
    vis = s[:n]; tw = d.textlength(s, font=f)
    tx = min(max(x0, S_['x0']), S_['x1'] - tw - 20); ty = y0 - 30
    if ty < S_['y0']: ty = y1 + 30
    ty = min(max(ty, S_['y0']), S_['y1'])
    if taken is not None:
        for (ax0, ay0, ax1, ay1) in taken:
            if not (tx + tw + 30 < ax0 or tx - 8 > ax1 or ty + 22 < ay0 or ty - 22 > ay1): ty = ay1 + 26
        taken.append((tx - 8, ty - 22, tx + tw + 30, ty + 22))
    d.rectangle([tx - 8, ty - 22, tx + tw + 30, ty + 22], fill=(0, 10, 14, int(205 * a)), outline=V.rgba(col, 160 * a), width=1)
    V.text(img, d, (tx, ty), vis, f, col, a, 'lm')
    if n < len(s) or int(t * 3) % 2 == 0:
        cx = tx + d.textlength(vis, font=f) + 3; d.rectangle([cx, ty - 15, cx + 15, ty + 15], fill=V.rgba(col, 220 * a))

class R5(H4.R4):
    # ---------- terminal captions ----------
    def captions(self, img, d, t):
        chunk = None
        for c in V.CAPS:
            if c['t0'] - 0.05 <= t < c['t1']: chunk = c; break
        if not chunk: return
        full = ' '.join(w['w'] for w in chunk['words'])
        span = max(0.1, chunk['words'][-1]['t1'] - chunk['t0'])
        n = int(len(full) * min(1, (t - chunk['t0']) / span * 1.1))
        f = V.font('monob', 46); lines = wrap(d, full, f, 840)
        y0 = 1395 - (len(lines) - 1) * 31
        d.rectangle([60, y0 - 54, 1020, y0 + (len(lines) - 1) * 62 + 40], fill=(0, 12, 16, 205), outline=V.rgba(V.HOLO, 180), width=2)
        V.text(img, d, (80, y0 - 34), "neuronade.ia ~ $", V.font('mono', 22), V.HOLO, 0.8, 'lm')
        k = 0
        for j, ln in enumerate(lines):
            vis = ln[:max(0, min(len(ln), n - k))]; k += len(ln) + 1
            yy = y0 + 8 + j * 62
            # keyword colouring: draw word by word
            x = 90; ws = vis.split(' ')
            for wi, w in enumerate(ws):
                base = re.sub(r"[^\wÀ-ÿ']", '', w.lower())
                col = V.KEYC.get(base) or MINT
                V.text(img, d, (x, yy), w, f, col, 1.0, 'lm'); x += d.textlength(w + ' ', font=f)
            if len(vis) < len(ln) or j == len(lines) - 1:
                if len(vis) < len(ln) or int(t * 3) % 2 == 0:
                    cx = 90 + d.textlength(vis, font=f) + 4; d.rectangle([cx, yy - 22, cx + 24, yy + 22], fill=(150, 255, 230, 230))
                break
    # ---------- component tags (hologram frames) ----------
    def labels(self, img, d, cam, t):
        if LABEL_MODE == 'A': return
        taken = []
        for (t0, t1, key, txt, hot, side) in sorted(V.LABELS, key=lambda l: l[0]):
            if V.win(t, t0, t1, 0.25) <= 0.01: continue
            txt_ = txt or (V.G.ANCH[key][1] if key in V.G.ANCH else '')
            if isinstance(key, str) and GP.get(key) is not None:
                s, z = cam.proj(GP[key])
                if (z < 50).any(): continue
                box = (s[:, 0].min(), s[:, 1].min(), s[:, 0].max(), s[:, 1].max())
                if box[2] - box[0] > W * 0.95 or box[3] - box[1] > H * 0.6:   # component fills the frame: tag its anchor only
                    a_, z_ = cam.p1(V.G.ANCH[key][0]); box = (a_[0] - 40, a_[1] - 40, a_[0] + 40, a_[1] + 40)
            else:
                p = V.G.ANCH[key][0] if key in V.G.ANCH else key
                a_, z_ = cam.p1(p)
                if z_ < 50: continue
                box = (a_[0] - 34, a_[1] - 34, a_[0] + 34, a_[1] + 34)
            tag(img, d, box, txt_, t, t0, t1, hot, taken)
    # ---------- tags on photoreal frames ----------
    def label2d(self, img, d, s, txt_, t, t0, t1, hot, side, dy=-60):
        if LABEL_MODE == 'A': return
        tag(img, d, (s[0] - 40, s[1] - 40, s[0] + 40, s[1] + 40), txt_, t, t0, t1, hot)

def render_seg(args):
    idx, f0, f1 = args
    r = R5(); out = '/home/claude/v7/seg/seg_%03d' % idx
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(FPS), '-f', 'mp4', out + '.tmp.mp4']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1): p.stdin.write(r.frame(i).tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.rename(out + '.tmp.mp4', out + '.mp4')
    return idx, rc

if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        global_mode = sys.argv[2]; LABEL_MODE = global_mode
        r = R5(); os.makedirs('/home/claude/v7/prev', exist_ok=True)
        for ts in sys.argv[3:]:
            r.frame(int(float(ts) * FPS)).save('/home/claude/v7/prev/%s_%s.png' % (global_mode, ts)); print(ts, flush=True)
    else:
        from multiprocessing import Pool
        os.makedirs('/home/claude/v7/seg', exist_ok=True); SEG = 150
        segs = [(k, k * SEG, min(V.NF, (k + 1) * SEG)) for k in range((V.NF + SEG - 1) // SEG)]
        segs = [s for s in segs if not os.path.exists('/home/claude/v7/seg/seg_%03d.mp4' % s[0])]
        with Pool(2) as p:
            for res in p.imap_unordered(render_seg, segs): print(res, flush=True)
