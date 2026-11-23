import math, json, sys, os, subprocess, random, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import geom as G

BASE = '/home/claude/d003'
W, H, S, FPS = 1080, 1920, 2, 30
W2, H2 = W * S, H * S
TL = json.load(open(BASE + '/timeline.json'))
SENTS = TL['sents']; DUR = TL['total']; NF = int(DUR * FPS)
def _s(p, s):
    for x in SENTS:
        if x['p'] == p and x['s'] == s: return x
    raise KeyError((p, s))
def Sx(p, s=0): return _s(p, s)['t0']
def Se(p, s=0): return _s(p, s)['t1']
def P(p): return Sx(p, 0)
BRK = re.compile(r"(\.\.\.|…|[,:;?!])(?=\s+\S)")
def tmap(x, txt):
    marks = [m.end() for m in BRK.finditer(txt)]
    pts = [(0, x['t0'])]
    for k, ts, te in x.get('breaks', []):
        if k < len(marks):
            pos = marks[k]; nxt = pos
            while nxt < len(txt) and txt[nxt] == ' ': nxt += 1
            pts += [(pos, ts), (nxt, te)]
    pts.append((len(txt), x['t1']))
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    return lambda c: float(np.interp(c, xs, ys))
def word_t(p, s, word):
    x = _s(p, s); i = x['text'].find(word)
    if i < 0: raise KeyError(word)
    return tmap(x, x['text'])(i)
NPARA = max(x['p'] for x in SENTS) + 1

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def sm(x): x = clamp(x); return x * x * (3 - 2 * x)
def ramp(t, a, b): return sm((t - a) / (b - a)) if b != a else float(t >= a)
def win(t, a, b, f=0.3): return ramp(t, a, a + f) * (1 - ramp(t, b - f, b))
def mix(c1, c2, k): return tuple(c1[i] + (c2[i] - c1[i]) * k for i in range(3))
def rgba(c, a): return (int(c[0]), int(c[1]), int(c[2]), int(clamp(a, 0, 255)))
FD = '/usr/share/fonts/opentype/inter/Inter-'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
MONOB = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
_fc = {}
def font(n, sz):
    k = (n, sz)
    if k not in _fc: _fc[k] = ImageFont.truetype(MONO if n == 'mono' else MONOB if n == 'monob' else FD + n + '.otf', sz)
    return _fc[k]

HOLO = (70, 232, 238); FOCUS = (255, 156, 58); ENV = (70, 160, 210); YEL = (255, 214, 70); RED = (255, 80, 64)
TS = np.array([15, 30, 45, 58, 70.]); TR = np.array([60, 110, 250, 255, 255.]); TG = np.array([150, 205, 205, 140, 80.]); TB = np.array([255, 255, 120, 50, 40.])
def tcol(T): return (float(np.interp(T, TS, TR)), float(np.interp(T, TS, TG)), float(np.interp(T, TS, TB)))
GAS = YEL; AIR = (200, 240, 255); FUME_H = (255, 150, 70); FUME_C = (190, 160, 235); COND = (90, 255, 160); VAP = (230, 240, 255)


# ---------------- stove colours ----------------
COLD = (110, 190, 255); HOTC = (255, 120, 60); FLAMEC = (255, 170, 60); EMBER = (255, 90, 40); PELLET = (214, 170, 110)
SMOKE = (175, 165, 160); ELEC = (255, 226, 90); GREEN = (110, 255, 160)

# ---------------- key times ----------------
T_REW = Sx(0, 4) - 0.1                               # "Regarde comment il fait." : rewind, stove cold and empty
T_FEED0 = word_t(2, 1, 'pousse') - 0.4               # the screw starts : first dose of pellets
T_FEED1 = Se(2, 2) + 0.4
T_IGN0 = P(3) + 0.1                                  # igniter heats up (red)
T_AIR = word_t(3, 1, "L'air") - 0.1                  # air drawn across it
T_FLAME = word_t(3, 3, 'la flamme') - 0.1            # pellets catch
T_IGN1 = word_t(3, 3, 'la bougie') + 0.4             # igniter switched off
T_CONV = word_t(5, 1, 'aspire') - 0.6                # room-air fan starts
T_STOP = word_t(7, 0, "la vis s'arrête") + 0.1       # extinction : screw stops first
T_FANS_OFF = Se(7, 1) + 0.8
T_BONUS = P(8) + 0.2                                 # bonus scene : stove running again
T_CUT = word_t(8, 2, 'Une coupure') + 0.05           # power cut
T_RESUME = P(9) - 0.2
CHANGES = [T_REW] + [P(p) for p in range(1, NPARA)]
FAST = [(T_IGN0 + 0.3, P(4) - 0.3), (P(6) + 0.3, P(8) - 0.3)]   # accelerated real time (ignition, regulation, extinction take minutes)

def tease(t): return 1 - ramp(t, T_REW, T_REW + 0.2)
def igniter(t):          # 0..1 glow of the igniter
    if t < T_REW: return 1.0
    return ramp(t, T_IGN0, T_IGN0 + 2.0) * (1 - ramp(t, T_IGN1, T_IGN1 + 0.8))
def power(t):            # flame power 0..1
    if t < T_REW: return 1.0
    p = ramp(t, T_FLAME, T_FLAME + 2.5) * (1 - 0.6 * ramp(t, Sx(6, 1) + 0.5, Se(6, 2)))
    p *= 1 - ramp(t, T_STOP + 0.6, T_STOP + 5.0)
    if t >= T_BONUS - 0.5:
        p = 0.7 * ramp(t, T_BONUS - 0.5, T_BONUS + 0.3) * (1 - ramp(t, T_CUT + 0.3, T_CUT + 3.5))
    if t >= T_RESUME: p = 0.7 * ramp(t, T_RESUME, T_RESUME + 0.8)
    return p
def mains(t):            # electricity available
    return 0.0 if T_CUT <= t < T_RESUME else 1.0
def feed(t):             # screw speed 0..1
    if t < T_REW: return 0.8
    f = win(t, T_FEED0, T_FEED1, 0.3)
    if T_FLAME + 1.0 <= t < T_STOP: f = max(f, 0.35 + 0.65 * power(t) / max(0.05, 1.0))
    if T_BONUS <= t < T_CUT: f = 0.6
    if t >= T_RESUME + 0.5: f = 0.6
    return f * mains(t)
def ext(t):              # smoke extractor 0..1
    if t < T_REW: return 1.0
    e = ramp(t, T_IGN0 - 0.4, T_IGN0 + 0.4) * (1 - ramp(t, T_FANS_OFF - 0.6, T_FANS_OFF))
    if t >= T_BONUS - 0.5: e = ramp(t, T_BONUS - 0.5, T_BONUS)
    return e * mains(t)
def conv(t):             # room-air fan 0..1
    if t < T_REW: return 1.0
    c = ramp(t, T_CONV, T_CONV + 0.8) * (1 - ramp(t, T_FANS_OFF - 0.6, T_FANS_OFF))
    if t >= T_BONUS - 0.5: c = ramp(t, T_BONUS - 0.5, T_BONUS)
    return c * mains(t)
def room(t):
    if t < T_REW: return 20.0
    r = 17.0 + 2.5 * ramp(t, T_FLAME + 2, P(6)) + 0.5 * ramp(t, P(6), Sx(6, 2))
    return r
def fumes(t):
    if t < T_REW: return 140.0
    if t >= T_BONUS - 0.5: return 20 + 170 * power(t)
    base = ramp(t, T_FLAME, T_FLAME + 4) * (1 - ramp(t, T_STOP, T_FANS_OFF))
    return 20 + 140 * base * (0.45 + 0.55 * power(t))
def pile(t):             # pellets in the burn pot 0..1
    if t < T_REW: return 0.8
    if t >= T_BONUS - 0.5: return 0.6
    p = ramp(t, T_FEED0 + 1.2, T_FEED1 + 0.6) * (1 - 0.35 * ramp(t, T_FLAME, T_FLAME + 3))
    return p * (1 - ramp(t, T_STOP + 1, T_STOP + 6))
def display_text(t):
    if mains(t) < 0.5: return None
    if t < T_REW: return "CHAUFFE"
    if t < T_FEED0 - 0.2: return "ARRÊT"
    if t < T_IGN0: return "CHARGEMENT"
    if t < T_FLAME + 2: return "ALLUMAGE"
    if t < Sx(6, 1): return "CHAUFFE"
    if t < T_STOP: return "MODULATION"
    if t < T_FANS_OFF: return "EXTINCTION"
    if t < T_BONUS - 0.5: return "ARRÊT"
    return "CHAUFFE"

_ph = None
def phases():
    global _ph
    if _ph is None:
        ts = np.arange(NF + 2) / FPS
        f = lambda fn, k: np.cumsum([fn(x) * k / FPS for x in ts])
        _ph = dict(feed=f(feed, 1.0), ext=f(ext, 900), conv=f(conv, 700), air=f(ext, 1.0), flame=f(lambda x: 1.0, 1.0), hum=f(lambda x: 1.0, 1.0))
    return _ph

# ---------------- camera ----------------
def CK(t, T, az, el, d, dur=1.2, rate=0.0, fov=38):
    return dict(t=t, T=np.array(T, float), az=az, el=el, d=d, dur=dur, rate=rate, fov=fov)
KEYS = [
 CK(0.0, (0, 0, 0), 30, 10, 3300, 0, 0),
 CK(T_REW + 0.05, (0, 0, 0), 34, 12, 3400, 1.0, 1.0),
 CK(P(1), (0, 0, 0), 28, 10, 3300, 1.0, 1.2),
 CK(word_t(1, 0, 'un réservoir') - 0.2, (0, 300, -160), 140, 26, 1750, 1.0, 0.8),
 CK(word_t(1, 0, 'une vis') - 0.2, (-50, 110, -125), 100, 14, 1350, 1.0, 0.6),
 CK(word_t(1, 0, 'un creuset') - 0.2, (-50, -160, 100), 22, 14, 1000, 1.0, 0.6),
 CK(word_t(1, 0, 'deux ventilateurs') - 0.2, (20, -360, 0), 122, 10, 1900, 1.0, 0.6),
 CK(Sx(1, 1), (0, 240, -160), 160, 34, 1250, 1.2, 0.6),
 CK(Sx(1, 2), (0, 0, 0), 40, 12, 3250, 1.2, 1.0),
 CK(P(2), (0, 250, -160), 150, 28, 1500, 1.2, 0.6),
 CK(Sx(2, 1), (-50, 100, -130), 95, 12, 1400, 1.2, 0.6),
 CK(Sx(2, 2), (-50, -60, 50), 88, 8, 1150, 1.1, 0.5),
 CK(Sx(2, 3), (-50, -84, 86), 80, 5, 640, 1.0, 0.4),
 CK(Sx(2, 5), (-50, 20, 0), 70, 8, 1700, 1.1, 0.6),
 CK(P(3), (-50, -165, -30), 72, 16, 900, 1.2, 0.5),
 CK(Sx(3, 1), (-50, -165, 30), 52, 18, 820, 1.1, 0.5),
 CK(Sx(3, 3), (30, 30, 120), 20, 8, 1500, 1.2, 0.5),
 CK(P(4), (170, -380, -170), 150, 12, 1100, 1.2, 0.6),
 CK(Sx(4, 1), (0, 0, -60), 125, 12, 3050, 1.2, 0.8),
 CK(Sx(4, 2), (225, -255, -215), 140, 16, 720, 1.1, 0.5),
 CK(Sx(4, 3), (-30, 0, -60), 100, 10, 2450, 1.1, 0.6),
 CK(Sx(4, 4), (0, 0, 0), 22, 10, 3100, 1.2, 0.8),
 CK(P(5), (-50, 336, 50), 35, 30, 1300, 1.2, 0.5),
 CK(Sx(5, 1), (-45, -330, 150), 40, 8, 1150, 1.1, 0.5),
 CK(word_t(5, 1, 'le fait passer') - 0.2, (-20, 80, 100), -48, 10, 2650, 1.2, 0.6),
 CK(word_t(5, 1, 'et te le souffle') - 0.2, (60, 420, 220), 25, 16, 1300, 1.1, 0.5),
 CK(Sx(5, 2), (-50, 340, 60), 28, 26, 1350, 1.2, 0.5),
 CK(P(6), (-235, -490, -360), -125, 14, 900, 1.2, 0.5),
 CK(Sx(6, 1), (0, 0, 0), -40, 10, 2850, 1.2, 0.8),
 CK(Sx(6, 2), (-50, -110, 100), 16, 8, 1250, 1.1, 0.5),
 CK(Sx(6, 3), (0, 0, 0), 30, 10, 3100, 1.2, 0.8),
 CK(P(7), (-50, 110, -125), 100, 12, 1500, 1.2, 0.5),
 CK(Sx(7, 1), (0, -100, 0), 60, 10, 2650, 1.2, 0.8),
 CK(P(8), (0, -100, -100), 150, 15, 2650, 1.2, 0.6),
 CK(Sx(8, 2), (0, 0, 0), 25, 10, 3050, 1.2, 0.8),
 CK(P(9), (0, 0, 0), 30, 12, 3350, 1.3, 2.0),
]
def shake(t): return (0.0, 0.0)

def lerp(a, b, k): return a + (b - a) * k
_cams = None
def cams():
    global _cams
    if _cams is not None: return _cams
    out = []; cur = None; start = None; ki = 0
    for i in range(NF + 1):
        t = i / FPS
        while ki < len(KEYS) and KEYS[ki]['t'] <= t:
            k = KEYS[ki]; start = (cur if cur is not None else k, t); ki += 1
        k = KEYS[ki - 1]; s0, ts = start
        drift = k['rate'] * (t - k['t'])
        u = sm((t - ts) / k['dur']) if k['dur'] > 0 else 1.0
        tgt = dict(T=k['T'], az=k['az'] + drift, el=k['el'], d=k['d'], fov=k['fov'])
        if u >= 1 or s0 is k: c = tgt
        else:
            c = dict(T=lerp(s0['T'], tgt['T'], u), az=lerp(s0['az'], tgt['az'], u), el=lerp(s0['el'], tgt['el'], u),
                     d=math.exp(lerp(math.log(s0['d']), math.log(tgt['d']), u)), fov=lerp(s0['fov'], tgt['fov'], u))
        c = dict(c); c['az_live'] = c['az'] + 1.0 * math.sin(t * 0.37); c['el_live'] = c['el'] + 0.7 * math.sin(t * 0.29 + 1)
        out.append(c); cur = c
    _cams = out; return out

class Cam:
    def __init__(self, c, scale, t=0.0):
        az, el = math.radians(c['az_live']), math.radians(c['el_live'])
        T = c['T']; d = c['d']
        self.C = T + d * np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])
        f = T - self.C; f /= np.linalg.norm(f)
        r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r); u = np.cross(r, f)
        self.R = np.stack([r, u, f]); self.sc = scale
        self.F = (H * scale / 2) / math.tan(math.radians(c['fov']) / 2)
        sx, sy = shake(t)
        self.cx = W * scale / 2 + sx * scale; self.cy = H * scale * 0.455 + sy * scale; self.d = d
    def proj(self, pts):
        q = (pts - self.C) @ self.R.T
        z = np.maximum(q[:, 2], 1.0)
        return np.stack([self.cx + self.F * q[:, 0] / z, self.cy - self.F * q[:, 1] / z], 1), q[:, 2]
    def p1(self, p):
        s, z = self.proj(np.asarray(p, float)[None]); return s[0], z[0]

POLYS = G.build()
ALLP = np.concatenate([p['pts'] for p in POLYS]); OFF = np.cumsum([0] + [len(p['pts']) for p in POLYS])
YMIN = np.array([p['pts'][:, 1].min() for p in POLYS])

class Path:
    def __init__(self, pts):
        self.p = np.asarray(pts, float); seg = np.linalg.norm(np.diff(self.p, axis=0), axis=1)
        self.cum = np.concatenate([[0], np.cumsum(seg)]); self.L = self.cum[-1]
    def at(self, s):
        s = np.clip(s, 0, self.L)
        return np.stack([np.interp(s, self.cum, self.p[:, k]) for k in range(3)], 1)
    def dir(self, s):
        a = self.at(s); b = self.at(s + 2.0); d = b - a; n = np.linalg.norm(d, axis=1, keepdims=True); return d / np.maximum(n, 1e-6)
def cat(*ps):
    out = []
    for p in ps:
        p = [tuple(x) for x in p]
        if out and np.allclose(out[-1], p[0]): p = p[1:]
        out += p
    return out

# ---------------- flows ----------------
FEEDP = Path(cat([G.AUGER[0], G.AUGER[1]], [G.CHUTE[0], G.CHUTE[1], G.DROP_BOT]))
L_AUGER = Path([G.AUGER[0], G.AUGER[1]]).L; L_CHUTE = Path([G.CHUTE[0], G.CHUTE[1]]).L
AIRP = Path(cat(G.INTAKE, [G.IGN_TIP, (-50, -150, 95)]))
L_IGN = Path(G.INTAKE).L
FUMEPS = []
for k, x in enumerate((-110, -50, 10)):
    z = 0 if k % 2 == 0 else 90
    FUMEPS.append(Path(cat([(-50 + (x + 50) * 0.3, -120, 100), (x, 150, 60), (x, 298, z), (x, 372, z), (x, 384, z)],
                           [(185, 386, -40)], G.FUME_DOWN, [G.EXTRACTOR_C], G.FLUE)))
EXCH_END = [Path(cat([(-50 + (x + 50) * 0.3, -120, 100), (x, 150, 60), (x, 298, 0 if k % 2 == 0 else 90), (x, 372, 0 if k % 2 == 0 else 90)])).L for k, x in enumerate((-110, -50, 10))]
CONVP = Path(cat(G.AIR_IN, G.AIR_UP))
CONV_HOT0 = Path(cat(G.AIR_IN, G.AIR_UP[:4])).L; CONV_HOT1 = Path(cat(G.AIR_IN, G.AIR_UP[:6])).L
SIGNAL = [G.PROBE[-1], G.PROBE[0], (-200, -380, -248), (-60, -200, -230), G.MOTOR[1]]
rng0 = random.Random(1)
HOPPER_PTS = []
while len(HOPPER_PTS) < 260:
    p = (rng0.uniform(-205, 205), rng0.uniform(-50, 470), rng0.uniform(-242, -78))
    if p[1] < 120 and abs(p[0] + 50) > 40 + (p[1] + 60) * 1.0: continue
    HOPPER_PTS.append(p)
HOPPER_PTS = np.array(HOPPER_PTS)
POT_PTS = np.array([(rng0.uniform(-108, 8), rng0.uniform(-203, -150), rng0.uniform(47, 153)) for _ in range(70)])
POT_PTS = POT_PTS[np.argsort(POT_PTS[:, 1])]

def make_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.6)) ** 2)
    v = np.clip(1 - r, 0, 1) ** 1.6
    return Image.fromarray(np.stack([2 + 6 * v, 4 + 16 * v, 6 + 20 * v], 2).astype(np.uint8))
def make_scan():
    a = np.full((H, W, 3), 255, np.uint8); a[::4] = 228; return Image.fromarray(a)
def dline(d, cam, pts, col, a, w):
    s, z = cam.proj(np.asarray(pts, float))
    if (z < 40).any(): return
    d.line(s.ravel().tolist(), fill=rgba(col, a), width=max(1, int(round(w * S))), joint='curve')
def ddots(d, cam, pts, col, a, r, cols=None, rmax=2.4, hollow=None):
    if len(pts) == 0: return
    s, z = cam.proj(np.asarray(pts, float)); k = cam.d / np.maximum(z, 50)
    for i in range(len(s)):
        if z[i] < 40: continue
        rr = r * S * clamp(k[i], 0.35, rmax); c = cols[i] if cols is not None else col
        x, y = s[i]
        d.ellipse([x - rr * 2.2, y - rr * 2.2, x + rr * 2.2, y + rr * 2.2], fill=rgba(c, a * 0.22))
        if hollow is not None and hollow[i] > 0.5:
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=rgba(mix(c, (255, 255, 255), 0.45), a), width=max(1, int(rr * 0.45)))
        else:
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=rgba(mix(c, (255, 255, 255), 0.45), a))
def stream(path, phase, spacing, offset=0.0):
    n = max(1, int(path.L // spacing)); return (phase + offset + np.arange(n) * path.L / n) % path.L

def scene_focus(t):
    F = []
    def on(a, b, groups):
        if a <= t < b: F.extend(groups)
    on(word_t(1, 0, 'un réservoir') - 0.2, word_t(1, 0, 'une vis') - 0.2, ['hopper'])
    on(word_t(1, 0, 'une vis') - 0.2, word_t(1, 0, 'un creuset') - 0.2, ['auger', 'motor'])
    on(word_t(1, 0, 'un creuset') - 0.2, word_t(1, 0, 'deux ventilateurs') - 0.2, ['pot'])
    on(word_t(1, 0, 'deux ventilateurs') - 0.2, Se(1, 0) + 0.3, ['extractor', 'conv_fan'])
    on(Sx(1, 1), Se(1, 1) + 0.3, ['hopper'])
    on(P(2), Sx(2, 1), ['hopper'])
    on(Sx(2, 1), Sx(2, 2), ['auger', 'motor'])
    on(Sx(2, 2), P(3) - 0.3, ['chute', 'pot'])
    on(P(3), Sx(3, 3), ['igniter', 'intake', 'pot'])
    on(Sx(3, 3), P(4) - 0.3, ['pot', 'igniter'])
    on(P(4), Sx(4, 2), ['extractor', 'flue', 'intake'])
    on(Sx(4, 2), Sx(4, 4), ['pressostat', 'extractor', 'auger'])
    on(P(5), Sx(5, 1), ['exchanger', 'fume_duct'])
    on(Sx(5, 1), Sx(5, 2), ['conv_fan', 'air_duct', 'exchanger', 'grille'])
    on(Sx(5, 2), P(6) - 0.3, ['exchanger'])
    on(P(6), Sx(6, 1), ['probe', 'board'])
    on(Sx(6, 1), P(7) - 0.3, ['auger', 'motor', 'pot'])
    on(P(7), Sx(7, 1), ['auger', 'motor'])
    on(Sx(7, 1), P(8) - 0.3, ['extractor', 'conv_fan'])
    on(Sx(8, 1), T_CUT, ['auger', 'motor', 'igniter', 'extractor', 'conv_fan', 'board', 'display'])
    return set(F), (0.36 if F else 1.0)

GROUP_TINT = {'env': ENV, 'body': (110, 210, 235), 'door': (120, 215, 240), 'fire': (90, 190, 230), 'air_duct': (120, 200, 255)}

# ---------------- text with real alpha ----------------
def text(img, d, xy, s, f, col, a=1.0, anchor='la', stroke=0, scol=(0, 0, 0)):
    if a <= 0.01 or not s: return
    if a >= 0.995:
        d.text(xy, s, font=f, fill=rgba(col, 255), anchor=anchor, stroke_width=stroke, stroke_fill=rgba(scol, 255)); return
    x0, y0, x1, y1 = d.textbbox(xy, s, font=f, anchor=anchor, stroke_width=stroke)
    x0, y0 = int(x0) - 2, int(y0) - 2; x1, y1 = int(x1) + 2, int(y1) + 2
    if x1 <= x0 or y1 <= y0: return
    lay = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.text((xy[0] - x0, xy[1] - y0), s, font=f, fill=rgba(col, 255), anchor=anchor, stroke_width=stroke, stroke_fill=rgba(scol, 255))
    al = lay.getchannel('A').point(lambda v: int(v * a)); lay.putalpha(al)
    img.paste(lay, (x0, y0), lay)

SAFE = dict(x0=36, x1=930, y0=330, y1=1380)



SAFE = dict(x0=36, x1=930, y0=330, y1=1380)
ELEC_TARGETS = [G.MOTOR[0], G.IGNITER[0], G.EXTRACTOR_C, (-45, -360, 150), G.DISPLAY_C]

class Renderer:
    def __init__(self):
        self.bg = make_bg(); self.scan = make_scan(); cams(); phases()
    def frame(self, i):
        t = i / FPS; c = cams()[i]; cam = Cam(c, S, t)
        img = Image.new('RGB', (W2, H2)); d = ImageDraw.Draw(img, 'RGBA')
        focus, dim = scene_focus(t)
        reveal = None
        if T_REW <= t < T_REW + 1.1: reveal = -560 + 1300 * sm((t - T_REW) / 1.05)
        PTS = ALLP
        sp, z = cam.proj(PTS)
        zmean = np.add.reduceat(z, OFF[:-1]) / np.diff(OFF)
        flick = 0.93 + 0.07 * math.sin(t * 13.0) * math.sin(t * 7.3)
        pw = power(t); ig = igniter(t)
        for k, p in enumerate(POLYS):
            if reveal is not None and YMIN[k] > reveal: continue
            i0, i1 = OFF[k], OFF[k + 1]
            if z[i0:i1].min() < 40: continue
            g = p['group']
            depth = clamp(1.25 - (zmean[k] - cam.d) / 2600, 0.3, 1.15)
            col = GROUP_TINT.get(g, HOLO); a = p['a'] * 235 * depth * flick
            if g in focus: col = FOCUS; a = min(255, a * 1.5 + 40)
            elif focus and g != 'env': a *= dim
            if g == 'pot' and g not in focus: col = mix(col, FLAMEC, 0.55 * pw)
            if g == 'igniter': col = mix(col, EMBER, ig); a = max(a, 230 * ig)
            if g in ('exchanger', 'fume_duct', 'flue') and g not in focus: col = mix(col, HOTC, 0.35 * clamp((fumes(t) - 40) / 120))
            if g == 'display' and mains(t) < 0.5: a *= 0.35
            seg = sp[i0:i1]
            if reveal is not None:
                yv = PTS[i0:i1, 1]
                if yv.max() > reveal:
                    keep = yv <= reveal
                    if keep.sum() < 2:
                        if len(yv) == 2:
                            k2 = (reveal - yv[0]) / (yv[1] - yv[0] + 1e-9)
                            q = PTS[i0] + (PTS[i0 + 1] - PTS[i0]) * k2
                            seg, _ = cam.proj(np.stack([PTS[i0], q]))
                        else: continue
                    else: seg = seg[keep]
            d.line(seg.ravel().tolist(), fill=rgba(col, a), width=max(1, int(round(p['w'] * S))))
        if reveal is not None:
            ra = 1 - ramp(reveal, 450, 740)
            if ra > 0.01:
                dline(d, cam, G.circle((0, reveal, 0), (0, 1, 0), 420, 60), (170, 250, 255), 230 * ra, 2.5)
                dline(d, cam, G.circle((0, reveal, 0), (0, 1, 0), 440, 60), (120, 230, 255), 90 * ra, 6)
        self.dynamic(d, cam, t, i, focus)
        img = img.reduce(S)
        small = img.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4))
        g1 = small.resize((W, H), Image.BILINEAR).point(lambda v: min(255, int(v * 1.9)))
        small2 = img.resize((W // 10, H // 10), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
        g2 = small2.resize((W, H), Image.BILINEAR).point(lambda v: min(255, int(v * 1.5)))
        img = ImageChops.screen(img, g1); img = ImageChops.screen(img, g2); img = ImageChops.screen(img, self.bg)
        img = ImageChops.multiply(img, self.scan)
        img = self.post_fx(img, t, i)
        d1 = ImageDraw.Draw(img, 'RGBA'); cam1 = Cam(c, 1, t)
        self.overlays3d(img, d1, cam1, t)
        self.labels(img, d1, cam1, t)
        self.hud(img, d1, t)
        self.captions(img, d1, t)
        return img

    def post_fx(self, img, t, i):
        g = 0.0
        for tc in CHANGES:
            dur = 0.5 if tc == T_REW else 0.16
            if tc - 0.04 <= t < tc + dur: g = max(g, 1 - (t - tc + 0.04) / (dur + 0.04))
        if g > 0:
            a = np.asarray(img).copy(); rng = random.Random(i)
            for _ in range(int(6 + 10 * g)):
                y0 = rng.randrange(0, H - 40); hh = rng.randrange(6, 60); dx = int(rng.uniform(-60, 60) * g)
                a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], dx, axis=1)
                if rng.random() < 0.5: a[y0:y0 + hh, :, 0] = np.roll(a[y0:y0 + hh, :, 0], int(8 * g), axis=1)
            img = Image.fromarray(a)
            img = ImageChops.screen(img, Image.new('RGB', (W, H), tuple(int(v * 0.28 * g) for v in (120, 240, 255))))
        return img

    def dynamic(self, d, cam, t, i, focus):
        ph = phases(); pw = power(t); ig = igniter(t); ex = ext(t); cv = conv(t); fd = feed(t)
        fdim = lambda groups: 1.0 if (not focus or any(g in focus for g in groups)) else 0.45
        # pellets in the hopper (level drops slowly once the stove runs)
        level = 470 - 60 * ramp(t, T_FEED0, P(8)) if t >= T_REW else 430
        hp = G.HOPPER_PTS if hasattr(G, 'HOPPER_PTS') else HOPPER_PTS
        sel = hp[hp[:, 1] < level]
        ddots(d, cam, sel, PELLET, 120 * fdim(['hopper']), 1.5, rmax=1.8)
        # pellets carried by the screw, sliding down the chute, falling into the pot
        s = stream(FEEDP, ph['feed'][i] * 130, 30)
        Lg = L_AUGER + L_CHUTE
        for x in s:
            if x > Lg and fd < 0.1: continue
            ddots(d, cam, FEEDP.at(np.array([x])), PELLET, 220 * fdim(['auger', 'chute', 'pot']), 2.3)
        # rotating marks on the screw
        a0, a1 = np.array(G.AUGER[0], float), np.array(G.AUGER[1], float); ax = a1 - a0; u, v = G.perp(ax)
        for k in range(14):
            q = (k / 14 + ph['feed'][i] * 0.08) % 1.0; ang = ph['feed'][i] * 9 + k * 0.42 * 17
            p = a0 + ax * q + G.AUGER_R * (math.cos(ang) * u + math.sin(ang) * v)
            ddots(d, cam, [p], FOCUS if 'auger' in focus else HOLO, 200 * fdim(['auger']), 1.6)
        # pellets in the burn pot (glowing when burning)
        n = int(len(POT_PTS) * clamp(pile(t)))
        if n > 0:
            col = mix(PELLET, EMBER, clamp(pw * 1.4))
            ddots(d, cam, POT_PTS[:n], col, 230 * fdim(['pot']), 2.1)
        # igniter glow + hot air puff
        if ig > 0.02:
            tip = np.array(G.IGN_TIP, float)
            dline(d, cam, [G.IGNITER[0], G.IGNITER[1]], EMBER, 240 * ig, 5)
            ddots(d, cam, [tip], (255, 140, 60), 255 * ig, 7, rmax=4)
        # combustion air : outdoor intake -> igniter tube -> burn pot (heated by the igniter)
        if ex > 0.05:
            for x in stream(AIRP, ph['air'][i] * 320, 46):
                p = AIRP.at(np.array([x]))
                hot = ramp(x, L_IGN - 120, L_IGN) * max(ig, 0.0)
                ddots(d, cam, p, mix(COLD, HOTC, hot), 210 * ex * fdim(['intake', 'igniter', 'pot', 'extractor']), 2.2)
        # flame
        if pw > 0.02:
            rng = random.Random(21)
            for k in range(int(70 * pw) + 6):
                uu = (t * 1.2 * (0.7 + 0.6 * rng.random()) + rng.random()) % 1.0
                sx, sz = rng.uniform(-55, 55), rng.uniform(-50, 50)
                h = 90 + 330 * pw * (0.6 + 0.4 * rng.random())
                p = (G.POT_C[0] + sx * (1 - 0.7 * uu) + 12 * math.sin(t * 7 + k), -125 + h * uu, G.POT_C[2] + sz * (1 - 0.7 * uu))
                col = mix((255, 240, 170), FLAMEC, clamp(uu * 1.6)) if uu < 0.6 else mix(FLAMEC, EMBER, (uu - 0.6) / 0.4)
                ddots(d, cam, [p], col, 245 * pw * (1 - uu) ** 0.7 * fdim(['pot', 'fire']), 3.4 * (1 - 0.5 * uu), rmax=3.5)
        # fumes : burn pot -> exchanger tubes -> descending duct -> extractor -> flue
        ft = fumes(t)
        if ft > 35 and ex > 0.05:
            for k, fp in enumerate(FUMEPS):
                for x in stream(fp, ph['air'][i] * 380, 70, offset=k * 23):
                    col = FUME_H if x < EXCH_END[k] else mix(FUME_H, SMOKE, clamp((x - EXCH_END[k]) / 300))
                    ddots(d, cam, fp.at(np.array([x])), col, 170 * ex * clamp((ft - 35) / 60) * fdim(['exchanger', 'fume_duct', 'extractor', 'flue', 'fire']), 2.4)
        # extractor wheel and room-air fan (spinning)
        ec = np.array(G.EXTRACTOR_C, float)
        for k in range(6):
            a_ = math.radians(ph['ext'][i]) + k * math.pi / 3
            dline(d, cam, [ec, ec + G.EXTRACTOR_R * 0.85 * np.array([math.cos(a_), math.sin(a_), 0])], FOCUS if 'extractor' in focus else HOLO, 220 * fdim(['extractor']), 1.8)
        f0, f1 = np.array(G.CONV_FAN[0], float), np.array(G.CONV_FAN[1], float)
        for k in range(5):
            a_ = math.radians(ph['conv'][i]) + k * 2 * math.pi / 5; off = G.CONV_R * 0.8 * np.array([0, math.cos(a_), math.sin(a_)])
            dline(d, cam, [f0 + off, f1 + off], FOCUS if 'conv_fan' in focus else HOLO, 200 * fdim(['conv_fan']), 1.5)
        # room air : bottom intake -> fan -> side duct -> around the exchanger tubes -> out of the top grille
        if cv > 0.05:
            for x in stream(CONVP, ph['air'][i] * 300 * 0 + ph['conv'][i] * 0.42, 44):
                hot = ramp(x, CONV_HOT0, CONV_HOT1)
                ddots(d, cam, CONVP.at(np.array([x])), mix(COLD, HOTC, hot * clamp(pw * 1.3)), 200 * cv * fdim(['conv_fan', 'air_duct', 'exchanger', 'grille']), 2.2)
            for k in range(7):
                uu = (t * 0.5 + k / 7) % 1.0
                p = (110 + 120 * math.sin(k * 2.1) * uu, 428 + 160 * uu, 340 + 520 * uu)
                ddots(d, cam, [p], mix(HOTC, (255, 200, 150), uu), 160 * cv * clamp(pw * 1.3) * (1 - uu), 3.0)
        # room probe -> board -> screw motor (regulation signal)
        if P(6) + 0.2 <= t < P(7) - 0.4:
            sp_ = Path(SIGNAL); uu = ((t - P(6)) * 0.6) % 1.0
            for k in range(5):
                x = (uu * 1.15 - k * 0.04) * sp_.L
                if 0 <= x <= sp_.L: ddots(d, cam, sp_.at(np.array([x])), GREEN, 255 * (1 - k * 0.18), 4.0)
        # bonus : everything electrical is powered from the board
        el = win(t, Sx(8, 1) - 0.2, T_CUT, 0.3)
        if el > 0.02:
            bc = np.array([(G.BOARD[0][k] + G.BOARD[1][k]) / 2 for k in range(3)])
            for k, tg in enumerate(ELEC_TARGETS):
                ln = Path([bc, (bc[0], tg[1], bc[2]), tg]); dline(d, cam, ln.at(np.linspace(0, ln.L, 20)), ELEC, 150 * el, 2)
                x = ((t * 0.9 + k * 0.2) % 1.0) * ln.L; ddots(d, cam, ln.at(np.array([x])), ELEC, 255 * el, 4.0)

    def overlays3d(self, img, d, cam, t):
        dc = np.array(G.DISPLAY_C, float); sc, zc = cam.p1(dc)
        facing = (cam.C - dc) @ np.array([0, 0, 1.0]) / max(1e-6, np.linalg.norm(cam.C - dc))
        txt = display_text(t)
        if txt and zc > 50 and facing > 0.3:
            fs = int(clamp(20 * cam.F / zc, 6, 110)); av = ramp(sc[1], 400, 480) * (1 - ramp(sc[1], 1180, 1260)) * ramp(facing, 0.3, 0.5)
            if fs >= 11 and av > 0.01 and -100 < sc[0] < W + 100 and sc[1] < H + 100:
                text(img, d, (sc[0], sc[1] - fs * 0.35), txt, font('monob', fs), (120, 255, 200), av, 'mm')
                text(img, d, (sc[0], sc[1] + fs * 0.75), "%.1f°" % room(t), font('mono', max(8, int(fs * 0.8))), (160, 235, 255), 0.9 * av, 'mm')
        if Sx(4, 2) <= t < Sx(4, 4):
            pc = np.array([225, -200, -215.]); sc, zc = cam.p1(pc)
            if zc > 50 and SAFE['y0'] < sc[1] < 1300:
                a = win(t, Sx(4, 2), Sx(4, 4), 0.25)
                if t < Sx(4, 3) - 0.1: text(img, d, (sc[0], sc[1] - 40), "✓ TIRAGE OK", font('monob', 30), GREEN, a * (1 - ramp(t, Sx(4, 3) - 0.4, Sx(4, 3) - 0.1)), 'mm', 4)

    def labels(self, img, d, cam, t):
        return

    def hud(self, img, d, t):
        c = (110, 225, 255)
        for (x, y, sx, sy) in ((40, 120, 1, 1), (W - 40, 120, -1, 1), (40, 1590, 1, -1), (W - 40, 1590, -1, -1)):
            d.line([x, y + 40 * sy, x, y, x + 40 * sx, y], fill=(110, 225, 255, 110), width=2)
        hk = 1 - ramp(t, T_REW - 0.15, T_REW + 0.05)
        if hk > 0:
            text(img, d, (W / 2, 232), "TON POÊLE", font('Bold', 72), (255, 255, 255), hk, 'mm', 6)
            pulse = 1 + 0.04 * math.sin(t * 6)
            text(img, d, (W / 2, 335), "S'ALLUME TOUT SEUL", font('Bold', int(84 * pulse)), FOCUS, hk, 'mm', 7)
        if T_REW <= t < P(1) - 0.1:
            a = win(t, T_REW + 0.3, P(1) - 0.1, 0.25)
            text(img, d, (W / 2, 250), "◄◄  RETOUR AU DÉBUT", font('monob', 40), c, a, 'mm')
            text(img, d, (W / 2, 305), "poêle froid · réservoir plein · pièce à 17 °C", font('mono', 26), (200, 230, 240), a, 'mm')
        pi = max(x['p'] for x in SENTS if x['t0'] <= t + 0.4) if t > 0.2 else 0
        if 1 <= pi < NPARA:
            t0 = P(pi) - 0.4; a = ramp(t, t0, t0 + 0.4) * (1 - ramp(t, Sx(9, 1) - 0.5, Sx(9, 1) - 0.1))
            text(img, d, (70, 194), "%02d" % pi, font('monob', 42), FOCUS, a, 'lm')
            text(img, d, (138, 194), CHAP[pi], font('Bold', 46), (255, 255, 255), a, 'lm')
            d.line([70, 236, 70 + 940 * ramp(t, t0, t0 + 0.7), 236], fill=rgba(c, 120 * a), width=2)
            if pi < 9:
                pw = power(t); fd = feed(t) > 0.1
                items = [("PIÈCE", "%.1f°C" % room(t), room(t) >= 19.95), ("FLAMME", "%d%%" % round(100 * pw), pw > 0.05),
                         ("VIS", "MARCHE" if fd else "ARRÊT", fd), ("FUMÉES", "%d°C" % round(fumes(t)), fumes(t) > 60)]
                x = 70
                for lab, val, hot in items:
                    text(img, d, (x, 266), lab, font('mono', 20), c, 0.75 * a, 'lm')
                    text(img, d, (x, 302), val, font('monob', 34), FOCUS if hot else (235, 248, 255), a, 'lm')
                    x += 238
        B = [(Sx(1, 2) - 0.1, P(2) - 0.15, "1 kg DE GRANULÉS ≈ 5 kWh", YEL),
             (Sx(2, 4), P(3) - 0.15, "LE FEU NE PEUT PAS REMONTER", GREEN),
             (word_t(3, 1, 'et arrive'), Se(3, 2) + 0.2, "BOUGIE ROUGE + AIR → AIR BRÛLANT", HOTC),
             (Sx(4, 1), Sx(4, 2) - 0.1, "AIR FRAIS ENTRE · FUMÉES SORTENT", COLD),
             (Sx(4, 3), Se(4, 4) + 0.2, "SI PAS DE TIRAGE → VIS COUPÉE", RED),
             (Sx(5, 2), P(6) - 0.15, "FUMÉES ET AIR NE SE TOUCHENT PAS", GREEN),
             (Sx(6, 1), Sx(6, 3) - 0.1, "CONSIGNE PROCHE → VIS PLUS LENTE", GREEN),
             (Sx(6, 3), P(7) - 0.15, "≈ 1 kg DE GRANULÉS PAR HEURE", YEL),
             (word_t(7, 0, "la vis"), Sx(7, 1) - 0.1, "VIS ARRÊTÉE → LA FLAMME BAISSE", FOCUS),
             (Sx(7, 1), P(8) - 0.15, "VENTILATEURS ENCORE EN MARCHE", COLD),
             (Sx(8, 1), T_CUT - 0.1, "TOUT EST ÉLECTRIQUE", ELEC),
             (T_CUT, P(9) - 0.15, "COUPURE → TOUT S'ARRÊTE", RED)]
        for (a0, a1, s, col) in B:
            if a0 <= t < a1:
                w = min(980, 27 * len(s) + 90); self.box(img, d, (W - w) / 2, 1190, w, s, col, win(t, a0, a1, 0.2))
        if P(9) <= t:
            a = 1 - ramp(t, Sx(9, 1) - 0.5, Sx(9, 1) - 0.1)
            for k, (w, col, key) in enumerate((("DU BOIS COMPRESSÉ", PELLET, 'Du bois'), ("UNE VIS QUI DOSE", FOCUS, 'une vis'), ("DE L'AIR QUI SOUFFLE", COLD, "de l'air"))):
                tk = word_t(9, 0, key); ak = a * ramp(t, tk - 0.1, tk + 0.2)
                text(img, d, (W / 2, 880 + k * 84), w, font('Bold', 64), col, ak, 'mm', 5)
            if t > Sx(9, 1) - 0.3:
                a = ramp(t, Sx(9, 1) - 0.3, Sx(9, 1) + 0.3)
                text(img, d, (W / 2, 222), "ET CHEZ TOI,", font('Bold', 62), (255, 255, 255), a, 'mm', 6)
                text(img, d, (W / 2, 318), "TU TE CHAUFFES COMMENT ?", font('Bold', 64), FOCUS, a, 'mm', 7)
                a2 = ramp(t, Sx(9, 2) - 0.2, Sx(9, 2) + 0.3)
                text(img, d, (W / 2, 1228), "Réponds en commentaire ↓", font('Bold', 50), (255, 255, 255), a2, 'mm', 6)

    def box(self, img, d, x0, y, w, s, col, a):
        if a <= 0.01: return
        d.rectangle([x0, y - 34, x0 + w, y + 34], outline=rgba(col, 230 * a), width=3, fill=(0, 0, 0, int(170 * a)))
        text(img, d, (x0 + w / 2, y), s, font('monob', 32), col, a, 'mm')

    def captions(self, img, d, t):
        for cap in CAPS:
            if cap['t0'] - 0.05 <= t < cap['t1']:
                a = ramp(t, cap['t0'] - 0.05, cap['t0'] + 0.06)
                f = font('Bold', 56); words = cap['words']
                sp = d.textlength(' ', font=f); widths = [d.textlength(w['w'], font=f) for w in words]
                totw = sum(widths) + sp * (len(words) - 1)
                if totw <= 880: lines = [list(range(len(words)))]
                else:
                    best = None
                    for b in range(1, len(words)):
                        w1 = sum(widths[:b]) + sp * (b - 1); w2 = sum(widths[b:]) + sp * (len(words) - b - 1)
                        bw = re.sub(r"[^\wÀ-ÿ']", '', words[b - 1]['w'].lower())
                        pen = max(w1, w2) + (400 if (bw in NOEND or bw.isdigit()) else 0) + (2000 if max(w1, w2) > 880 else 0)
                        if best is None or pen < best[0]: best = (pen, b)
                    lines = [list(range(best[1])), list(range(best[1], len(words)))]
                y0 = 1450 - (len(lines) - 1) * 34
                for j, ln in enumerate(lines):
                    tot = sum(widths[k] for k in ln) + sp * (len(ln) - 1); x = W / 2 - tot / 2
                    for k in ln:
                        w = words[k]; cur = w['t0'] <= t < w['t1'] + 0.05
                        col = (110, 245, 255) if cur else (w['col'] or (255, 255, 255))
                        text(img, d, (x, y0 + j * 68), w['w'], f, col, a, 'lm', 6)
                        x += widths[k] + sp
                break


CHAP = {1: "VUE D'ENSEMBLE", 2: "LA VIS", 3: "L'ALLUMAGE", 4: "L'EXTRACTEUR", 5: "L'ÉCHANGEUR", 6: "LA RÉGULATION", 7: "L'ARRÊT", 8: "LE BONUS", 9: "EN RÉSUMÉ"}
DISPLAY = [("cinq kilowattheures", "5 kWh"), ("un kilo par heure", "1 kg/h")]
NOEND = set("le la les l' un une des de du d' à au aux en par pour sur dans et ou où qui que qu' ce cette ces son sa ses ta ton tes se s' ne n' y sous avant entre très plus".split())
KEYC = {'granulés': PELLET, 'granulés,': PELLET, 'vis': FOCUS, 'feu': HOTC, 'flamme': HOTC, 'brûlant': HOTC, 'chaud.': HOTC, 'chaud': HOTC, 'air': COLD,
        "l'air": COLD, 'frais': COLD, 'fumées': SMOKE, 'électrique.': ELEC, 'électrique': ELEC, "l'électricité": ELEC, 'courant': ELEC, 'courant ?': ELEC,
        'bougie': EMBER, 'sèche-cheveux': YEL, 'sèche-cheveux.': YEL, 'extracteur': FOCUS, 'échangeur.': FOCUS, 'pressostat': FOCUS, 'creuset.': FOCUS,
        'réservoir.': FOCUS, 'goulotte,': FOCUS, 'consigne,': GREEN, 'coupure,': RED, 'allumette.': RED}

def make_caps():
    caps = []
    for x in SENTS:
        txt = x['text']
        for a_, b_ in DISPLAY: txt = txt.replace(a_, b_)
        toks = txt.split(' ')
        # merge lone punctuation tokens (":" "?" "!")
        ws = []
        for tk in toks:
            if tk in (':', '?', '!', ';') and ws: ws[-1] += ' ' + tk
            else: ws.append(tk)
        chunks = []; cur = []
        for k, w in enumerate(ws):
            cur.append(w); ln = len(' '.join(cur)); nxt = ws[k + 1] if k + 1 < len(ws) else None
            base = re.sub(r"[^\wÀ-ÿ']", '', w.lower())
            if nxt is None: chunks.append(cur); cur = []; continue
            if re.search(r'[,:;.?!]$', w) and ln >= 12: chunks.append(cur); cur = []; continue
            okb = base not in NOEND and not base.endswith("'") and not base.isdigit() and not (base == 'eau' and nxt.lower().startswith(('chaude', 'froide')))
            if ln >= 22 and okb and len(' '.join(cur + [nxt])) > 30: chunks.append(cur); cur = []; continue
            if ln >= 34: chunks.append(cur); cur = []
        if cur: chunks.append(cur)
        if len(chunks) > 1 and len(' '.join(chunks[-1])) < 10: chunks[-2] += chunks[-1]; chunks.pop()
        tm = tmap(x, txt); pos = 0
        for j, c in enumerate(chunks):
            words = []
            for w in c:
                i0 = txt.find(w, pos); i0 = pos if i0 < 0 else i0; pos = i0 + len(w)
                t = tm(i0); dt = max(0.02, tm(pos) - t)
                base = re.sub(r"[^\wÀ-ÿ']", '', w.lower())
                disp = w.rstrip(',;') if w.endswith((',', ';')) else w
                disp = disp[:-2] if disp.endswith(' :') else disp
                words.append(dict(w=disp, t0=t, t1=t + dt, col=KEYC.get(base)))
            caps.append(dict(t0=words[0]['t0'], t1=words[-1]['t1'] + (0.2 if j == len(chunks) - 1 else 0), words=words))
    return caps
CAPS = make_caps()


def LB(t0, t1, key, txt=None, hot=False, side=None): return (t0, t1, key, txt, hot, side)
LABELS = []
for key, w in (('hopper', 'un réservoir'), ('auger', 'une vis'), ('pot', 'un creuset'), ('fans', 'deux ventilateurs')):
    LABELS.append(LB(word_t(1, 0, w), Se(1, 0) + 0.3, key))
LABELS += [LB(Sx(1, 1) + 0.2, Se(1, 1) + 0.3, 'pellets', "Granulés", True),
           LB(Sx(2, 1) + 0.2, word_t(2, 1, 'petit moteur') - 0.2, 'auger', None, True),
           LB(word_t(2, 1, 'petit moteur'), Se(2, 1) + 0.2, 'motor', None, True),
           LB(word_t(2, 2, 'une goulotte') - 0.1, word_t(2, 2, 'puis dans') - 0.1, 'chute', None, True),
           LB(word_t(2, 2, 'puis dans'), P(3) - 0.3, 'pot', None, True),
           LB(Sx(2, 4) + 0.2, P(3) - 0.3, 'drop', None, True),
           LB(P(3) + 0.2, Sx(3, 1) - 0.1, 'igniter', None, True),
           LB(Sx(3, 1) + 0.1, Se(3, 2) + 0.2, 'intake', "Air aspiré", True),
           LB(P(4) + 0.2, Sx(4, 1) + 2.5, 'extractor', None, True),
           LB(word_t(4, 1, 'le conduit') - 0.2, Sx(4, 2) - 0.1, 'flue', None, True),
           LB(Sx(4, 2) + 0.2, Sx(4, 3) - 0.15, 'pressostat', None, True),
           LB(P(5) + 0.2, Sx(5, 1) - 0.1, 'exchanger', None, True),
           LB(Sx(5, 1) + 0.2, word_t(5, 1, 'et te le souffle') - 0.2, 'conv_fan', None, True),
           LB(word_t(5, 1, 'et te le souffle'), Sx(5, 2) + 0.5, 'grille', None, True),
           LB(P(6) + 0.2, Sx(6, 1) - 0.1, 'probe', None, True),
           LB(word_t(7, 0, 'la vis') + 0.2, Sx(7, 1) - 0.1, 'auger', "Vis arrêtée", True),
           LB(Sx(7, 1) + 0.2, P(8) - 0.3, 'extractor', None, True),
           LB(Sx(8, 1) + 0.3, T_CUT - 0.1, 'board', None, True),
           ]

def render_seg(args):
    idx, f0, f1 = args
    r = Renderer(); out = BASE + '/seg/seg_%03d' % idx
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-crf', '19', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(FPS), '-f', 'mp4', out + '.tmp.mp4']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1): p.stdin.write(r.frame(i).tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.rename(out + '.tmp.mp4', out + '.mp4')
    return idx, rc

if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        import time
        r = Renderer(); os.makedirs(BASE + '/prev', exist_ok=True)
        for ts in sys.argv[2:]:
            t0 = time.time(); im = r.frame(int(float(ts) * FPS)); im.save(BASE + '/prev/p_%s.png' % ts)
            print(ts, round(time.time() - t0, 2), 's', flush=True)
    elif sys.argv[1] == 'caps':
        for c in CAPS: print(round(c['t0'], 2), ' '.join(w['w'] for w in c['words']))
    elif sys.argv[1] == 'times':
        for p in range(NPARA): print(p, round(P(p), 2), CHAP.get(p))
        print('REW', T_REW, 'FLAME', T_FLAME, 'CUT', T_CUT)
    else:
        from multiprocessing import Pool
        SEG = 150; os.makedirs(BASE + '/seg', exist_ok=True)
        segs = [(k, k * SEG, min(NF, (k + 1) * SEG)) for k in range((NF + SEG - 1) // SEG)]
        segs = [s for s in segs if not os.path.exists(BASE + '/seg/seg_%03d.mp4' % s[0])]
        with Pool(2) as p:
            for res in p.imap_unordered(render_seg, segs): print(res, flush=True)
