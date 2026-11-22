import math, json, sys, os, subprocess, random, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import geom as G

BASE = '/home/claude/v7'
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

# ---------------- key times ----------------
T_REW = word_t(0, 2, 'quand') - 0.1   # "...quand tu montes le thermostat" : rewind to cold start
T_DEMAND = word_t(2, 1, 'il envoie')
T_FAN = Sx(3, 0) + 0.7
T_GAS = Sx(4, 0) + 0.6
T_SPARK = Sx(5, 0) + 0.25
T_FLAME = word_t(5, 0, 'et la flamme') + 0.15
T_DHW = word_t(10, 2, 'bascule')
T_TAP = Sx(10, 0) + 0.5
T_ROOM20 = Sx(11, 0)
T_GASOFF = Sx(11, 1) + 0.35
T_POST = Se(11, 2) + 0.6
CHANGES = [T_REW] + [P(p) for p in range(1, NPARA)]

def tease(t): return 1 - ramp(t, T_REW, T_REW + 0.2)
def _demand(t): return ramp(t, T_DEMAND, T_DEMAND + 0.4) * (1 - ramp(t, T_ROOM20 + 0.6, T_ROOM20 + 1.0))
def _pump(t): return ramp(t, T_DEMAND + 0.6, T_DEMAND + 1.6) * (1 - ramp(t, T_POST, T_POST + 2.0))
def _fan(t): return ramp(t, T_FAN, T_FAN + 1.2) * (1 - 0.7 * ramp(t, T_GASOFF, T_GASOFF + 1.5)) * (1 - ramp(t, T_POST, T_POST + 2.0))
def _gas(t): return ramp(t, T_GAS, T_GAS + 0.4) * (1 - ramp(t, T_GASOFF, T_GASOFF + 0.3))
def _flame(t): return ramp(t, T_FLAME, T_FLAME + 0.25) * (1 - ramp(t, T_GASOFF + 0.1, T_GASOFF + 0.6))
def dhw(t): return ramp(t, T_DHW, T_DHW + 0.6) * (1 - ramp(t, T_ROOM20 - 0.7, T_ROOM20 - 0.1))
def tap(t): return ramp(t, T_TAP, T_TAP + 0.4) * (1 - ramp(t, T_ROOM20 - 0.9, T_ROOM20 - 0.4))
def _power(t):
    p = 1.0 - 0.5 * ramp(t, Sx(6, 2) + 0.4, Sx(6, 2) + 3.0) + 0.08 * math.sin(t * 0.7)
    p = p + (1 - p) * dhw(t)
    return clamp(p) * _flame(t)
def _heat(t): return ramp(t, T_FLAME + 0.4, Sx(6, 1) + 2.0) * (1 - 0.65 * ramp(t, T_GASOFF + 0.5, DUR))
def _rad(t): return (0.3 * ramp(t, T_FLAME + 3.0, Sx(7, 0)) + 0.7 * ramp(t, Sx(7, 0) + 0.8, Se(7, 1))) * (1 - 0.35 * dhw(t)) * (1 - 0.5 * ramp(t, T_GASOFF + 1, DUR))
def _cond(t):
    a = word_t(8, 2, 'elles passent'); return ramp(t, a, a + 1.2) * (1 - ramp(t, T_GASOFF + 1, T_GASOFF + 4))
def pump(t): return max(_pump(t), tease(t))
def fan(t): return max(_fan(t), tease(t))
def gas(t): return max(_gas(t), tease(t))
def flame(t): return max(_flame(t), tease(t))
def power(t): return max(_power(t), 0.6 * tease(t))
def heat(t): return max(_heat(t), tease(t))
def radwarm(t): return max(_rad(t), tease(t))
def cond(t): return max(_cond(t), tease(t))
def demand(t): return _demand(t)
def T_dep(t): return 25 + 45 * heat(t)
def T_ret(t): return 25 + 18 * radwarm(t)
def room(t): return 17 + 2.8 * ramp(t, Se(7, 1), T_DHW) + 0.2 * ramp(t, T_ROOM20 - 0.6, T_ROOM20)
def fumes(t): return max(flame(t), 0.6 * fan(t) * ramp(t, T_FLAME, T_FLAME + 1))
def pressure(t): return 1.5 + 0.3 * _heat(t)

_ph = None
def phases():
    global _ph
    if _ph is None:
        ts = np.arange(NF + 2) / FPS
        f = lambda fn, k: np.cumsum([fn(x) * k / FPS for x in ts])
        _ph = dict(heat=f(pump, 380), air=f(fan, 420), gas=f(gas, 300), fume=f(fumes, 0.33), tap=f(tap, 380),
                   fanang=f(fan, 1100), pumpang=f(pump, 700), cond=f(cond, 0.42))
    return _ph

# ---------------- camera ----------------
def CK(t, T, az, el, d, dur=1.2, rate=0.0, fov=38):
    return dict(t=t, T=np.array(T, float), az=az, el=el, d=d, dur=dur, rate=rate, fov=fov)
KEYS = [
 CK(0.0, (-150, -330, -50), -30, 4, 1500, 0, 0),
 CK(0.05, (-195, -575, -70), -24, 5, 760, 2.6, 1.0),
 CK(Sx(0, 1) - 0.1, (20, 60, 0), -22, 9, 2900, 1.5, 0.8),
 CK(P(1), (60, 40, 0), 18, 8, 2750, 5.0, 0.6),
 CK(word_t(1, 0, 'vanne gaz') - 0.2, (60, -60, 20), 32, 4, 2150, 2.4, -0.6),
 CK(P(2), (-780, 250, -150), 18, 4, 640, 1.1, 1.5),
 CK(T_DEMAND - 0.1, (-400, 20, -100), 8, 4, 2300, 1.2, 0.3),
 CK(T_DEMAND + 1.2, (-120, -330, 120), -14, 6, 880, 1.0, 0.8),
 CK(P(3), (130, 330, 40), -24, 12, 880, 1.1, 1.4),
 CK(word_t(3, 1, 'ventouse') - 0.3, (200, 480, -40), -58, 22, 1400, 1.3, 0.9),
 CK(word_t(3, 1, "l'air frais") - 0.1, (320, 520, -50), -82, 10, 880, 1.1, 0.6),
 CK(P(4), (70, -150, 45), 24, 6, 720, 1.1, 0.8),
 CK(Sx(4, 1), (150, 40, 50), 30, 4, 1850, 1.3, -0.4),
 CK(word_t(4, 1, 'environ') - 0.3, (150, 215, 55), 18, 6, 680, 1.1, 0.6),
 CK(P(5), (-30, 168, 30), -22, 4, 480, 1.1, 0.5),
 CK(T_FLAME + 0.05, (0, 190, 15), -14, 6, 860, 0.8, 0.9),
 CK(Sx(5, 1), (40, 165, 35), 16, 4, 540, 1.1, 0.6),
 CK(Sx(5, 2), (60, 30, 30), 8, 6, 1450, 1.1, 0.4),
 CK(P(6), (0, 130, 10), 24, 12, 1180, 1.2, 1.4),
 CK(word_t(6, 1, 'entre') - 0.25, (70, 30, 40), 36, 2, 680, 0.9, 0.6),
 CK(word_t(6, 1, 'ressort') - 0.15, (-70, 235, 0), -22, 10, 680, 0.9, 0.6),
 CK(Sx(6, 2), (0, 130, 10), -10, 8, 1300, 1.1, 0.9),
 CK(P(7), (130, -235, 60), 20, 6, 680, 1.1, 0.9),
 CK(word_t(7, 0, 'radiateurs') - 0.5, (430, -190, -60), -8, 6, 3250, 1.3, 0.4),
 CK(Sx(7, 1) + 0.9, (810, -360, -120), -16, 8, 1350, 1.1, 0.6),
 CK(Sx(7, 2), (40, -200, -20), 38, 10, 1250, 1.2, -0.7),
 CK(Sx(7, 3), (170, -320, 80), 20, 4, 640, 1.0, 0.5),
 CK(P(8), (0, 100, 10), -24, 0, 1120, 1.2, 0.9),
 CK(Sx(8, 1), (0, 150, 30), -10, 4, 780, 1.0, 0.6),
 CK(Sx(8, 2), (40, 40, 60), -30, -2, 620, 1.0, 0.7),
 CK(Sx(8, 3), (70, 25, 95), -38, -4, 420, 1.0, 0.5),
 CK(P(9), (-195, -575, -70), -24, 5, 700, 1.1, 0.8),
 CK(Sx(9, 1) + 0.3, (-195, -200, -70), -36, 6, 1080, 1.2, 0.4),
 CK(Sx(9, 2), (230, 490, -40), -50, 18, 1280, 1.2, 0.7),
 CK(P(10), (-780, -200, -60), 14, 4, 880, 1.1, 0.7),
 CK(Sx(10, 1), (80, -370, 30), 20, 4, 640, 1.0, 0.5),
 CK(word_t(10, 2, 'bascule') - 0.35, (-150, -250, 60), 10, 4, 600, 0.9, 0.6),
 CK(word_t(10, 2, 'plaques') - 0.45, (-45, -210, 40), 24, 6, 840, 1.0, 0.6),
 CK(Sx(10, 3), (-420, -250, -60), 14, 4, 2550, 1.2, 0.4),
 CK(P(11), (-780, 250, -150), 10, 4, 640, 1.0, 1.2),
 CK(Sx(11, 1), (60, 40, 20), -12, 6, 1300, 1.1, 0.5),
 CK(Sx(11, 2), (60, -40, 0), -20, 8, 2450, 1.3, 0.6),
 CK(P(12), (0, -20, 0), -18, 8, 2400, 1.0, 0.7),
 CK(word_t(12, 0, 'flamme absente') - 0.15, (0, 190, 15), -10, 6, 800, 0.6, 0.6),
 CK(word_t(12, 0, 'surchauffe') - 0.15, (-170, 190, 30), -25, 4, 620, 0.6, 0.6),
 CK(word_t(12, 0, 'manque') - 0.15, (120, -343, 171), 10, 2, 560, 0.6, 0.4),
 CK(word_t(12, 0, 'code') - 0.3, (0, -345, 165), 0, 4, 850, 0.6, 0.4),
 CK(P(13), (40, 60, 0), -30, 12, 3200, 1.3, 2.0),
 CK(Sx(13, 1) - 0.25, (120, -343, 171), 0, 0, 430, 1.5, 0.25),
]
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

def shake(t):
    a = win(t, T_FLAME, T_FLAME + 0.45, 0.05) * (1 - ramp(t, T_FLAME + 0.1, T_FLAME + 0.45))
    return (a * 9 * math.sin(t * 91), a * 7 * math.sin(t * 73 + 1))

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
COILP = [tuple(x) for x in G.COIL]
HEAT_LOOP = Path(cat(G.PUMP_TO_COIL, COILP, G.COIL_TO_VALVE, G.VALVE_TO_DEP, G.RAD_PATH, G.RET_TO_PUMP))
DHW_LOOP = Path(cat(G.PUMP_TO_COIL, COILP, G.COIL_TO_VALVE, G.VALVE_TO_PHX, G.PHX_PRIM, G.PHX_TO_PUMP))
def zones(parts):
    b = []; acc = 0
    for p in parts: b.append(acc); acc += Path(p).L
    return np.array(b + [acc])
HZ = zones([G.PUMP_TO_COIL, COILP, G.COIL_TO_VALVE, G.VALVE_TO_DEP, G.RAD_PATH, G.RET_TO_PUMP])
DZ = zones([G.PUMP_TO_COIL, COILP, G.COIL_TO_VALVE, G.VALVE_TO_PHX, G.PHX_PRIM, G.PHX_TO_PUMP])
GASP = Path(cat(G.GAS_PATH, [(70, -150, 50)], G.GAS_PATH2))
FLUE_AIR = Path(G.FLUE_AX); AIRC = Path(G.AIR_IN_CASING); MIXP = Path(G.DUCT_PATH)
FUMEP = Path(cat(G.FUME_DUCT, list(reversed(G.FLUE_AX))))
DHWW = Path(cat(G.EF_PATH, G.PHX_SEC, G.ECS_PATH))
SIPH = Path(cat(G.SIPHON_IN, [(-195, -230, -70)], G.SIPHON_OUT))

def heat_temp(z, s, t):
    td, tr = T_dep(t), T_ret(t)
    out = np.full(len(s), tr)
    c0, c1 = z[1], z[2]
    inc = (s >= c0) & (s < c1); u = (s[inc] - c0) / (c1 - c0); out[inc] = tr + (td - tr) * u ** 0.8
    hot = (s >= c1) & (s < z[4]); out[hot] = td
    if len(z) > 6:
        rad = (s >= z[4]) & (s < z[5]); u = (s[rad] - z[4]) / (z[5] - z[4]); out[rad] = td + (tr - td) * u
    return out

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
def ddots(d, cam, pts, col, a, r, cols=None, rmax=2.4):
    if len(pts) == 0: return
    s, z = cam.proj(np.asarray(pts, float)); k = cam.d / np.maximum(z, 50)
    for i in range(len(s)):
        if z[i] < 40: continue
        rr = r * S * clamp(k[i], 0.35, rmax); c = cols[i] if cols is not None else col
        x, y = s[i]
        d.ellipse([x - rr * 2.2, y - rr * 2.2, x + rr * 2.2, y + rr * 2.2], fill=rgba(c, a * 0.22))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=rgba(mix(c, (255, 255, 255), 0.45), a))
def stream(path, phase, spacing, offset=0.0):
    n = max(1, int(path.L // spacing)); return (phase + offset + np.arange(n) * path.L / n) % path.L

def scene_focus(t):
    F = []
    def on(a, b, groups):
        if a <= t < b: F.extend(groups)
    on(0, T_REW, ['siphon', 'drain', 'collector'])
    on(P(2), P(3) - 0.3, ['thermostat', 'wire', 'board'])
    on(P(3), P(4) - 0.3, ['fan', 'flue', 'flue_in', 'venturi', 'duct'])
    on(P(4), P(5) - 0.3, ['gasvalve', 'pipe_gas', 'venturi'])
    on(P(5), Sx(5, 2), ['burner', 'ignition', 'ionisation'])
    on(Sx(5, 2), P(6) - 0.3, ['burner', 'ionisation', 'gasvalve'])
    on(P(6), P(7) - 0.3, ['coil', 'burner'])
    on(P(7), Sx(7, 2), ['pump', 'radiator', 'pipe_heat'])
    on(Sx(7, 2), Sx(7, 3), ['vessel', 'gauge'])
    on(Sx(7, 3), P(8) - 0.3, ['safety', 'gauge'])
    on(P(8), P(9) - 0.3, ['collector', 'coil'])
    on(P(9), Sx(9, 2), ['siphon', 'drain', 'collector'])
    on(Sx(9, 2), P(10) - 0.3, ['flue', 'flue_in', 'fumeduct'])
    on(P(10), Sx(10, 2), ['tap', 'flowmeter', 'pipe_ef', 'pipe_ecs'])
    on(Sx(10, 2), P(11) - 0.3, ['valve3', 'phx', 'pipe_dhwp', 'pipe_ef', 'pipe_ecs'])
    on(Sx(13, 1) - 0.3, DUR + 1, ['gauge'])
    return set(F), (0.36 if F else 1.0)

GROUP_TINT = {'pipe_gas': (230, 210, 120), 'env': ENV, 'pipe_ecs': (150, 210, 255), 'pipe_ef': (120, 190, 255)}

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

class Renderer:
    def __init__(self):
        self.bg = make_bg(); self.scan = make_scan(); cams(); phases()
    def frame(self, i):
        t = i / FPS; c = cams()[i]; cam = Cam(c, S, t)
        img = Image.new('RGB', (W2, H2)); d = ImageDraw.Draw(img, 'RGBA')
        focus, dim = scene_focus(t)
        reveal = None
        if T_REW <= t < T_REW + 1.1: reveal = -760 + 1560 * sm((t - T_REW) / 1.05)
        sp, z = cam.proj(ALLP)
        zmean = np.add.reduceat(z, OFF[:-1]) / np.diff(OFF)
        flick = 0.93 + 0.07 * math.sin(t * 13.0) * math.sin(t * 7.3)
        sf = self.safety_flash(t)
        for k, p in enumerate(POLYS):
            if reveal is not None and YMIN[k] > reveal: continue
            i0, i1 = OFF[k], OFF[k + 1]
            if z[i0:i1].min() < 40: continue
            g = p['group']
            depth = clamp(1.25 - (zmean[k] - cam.d) / 2600, 0.3, 1.15)
            col = GROUP_TINT.get(g, HOLO); a = p['a'] * 235 * depth * flick
            if g in focus: col = FOCUS; a = min(255, a * 1.5 + 40)
            elif focus and g != 'env': a *= dim
            if g == 'vessel' and g not in focus: a *= 0.55
            if g in sf: col = mix(col, RED, sf[g]); a = min(255, a + 120 * sf[g])
            if g == 'gasvalve' and g not in focus: col = mix(col, GAS, 0.6 * gas(t))
            seg = sp[i0:i1]
            if reveal is not None:
                yv = p['pts'][:, 1]
                if yv.max() > reveal:
                    keep = yv <= reveal
                    if keep.sum() < 2:
                        if len(yv) == 2:
                            k2 = (reveal - yv[0]) / (yv[1] - yv[0] + 1e-9)
                            q = p['pts'][0] + (p['pts'][1] - p['pts'][0]) * k2
                            seg, _ = cam.proj(np.stack([p['pts'][0], q]))
                        else: continue
                    else: seg = seg[keep]
            d.line(seg.ravel().tolist(), fill=rgba(col, a), width=max(1, int(round(p['w'] * S))))
        if reveal is not None:
            ra = 1 - ramp(reveal, 420, 760)
            if ra > 0.01:
                dline(d, cam, G.circle((40, reveal, 0), (0, 1, 0), 520, 60), (170, 250, 255), 230 * ra, 2.5)
                dline(d, cam, G.circle((40, reveal, 0), (0, 1, 0), 540, 60), (120, 230, 255), 90 * ra, 6)
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
        # glitch at chapter changes + rewind ; ignition flash
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
        f = win(t, T_FLAME - 0.02, T_FLAME + 0.35, 0.03) * (1 - ramp(t, T_FLAME, T_FLAME + 0.35))
        if f > 0: img = ImageChops.screen(img, Image.new('RGB', (W, H), tuple(int(v * 0.45 * f) for v in (255, 190, 120))))
        return img

    def safety_flash(self, t):
        out = {}
        if Sx(5, 2) <= t < P(6) - 0.2:
            out['gasvalve'] = 0.6 + 0.4 * math.sin(t * 14) if t < Se(5, 2) else 0
        if P(12) <= t < P(13):
            for g, w in ((('burner', 'ionisation'), 'flamme absente'), (('limiter',), 'surchauffe'), (('gauge', 'vessel'), 'manque'), (('board',), 'code')):
                t0 = word_t(12, 0, w); a = win(t, t0 - 0.1, t0 + 1.5, 0.25) * (0.75 + 0.25 * math.sin(t * 18))
                for gg in g: out[gg] = max(out.get(gg, 0), a)
        return out

    def dynamic(self, d, cam, t, i, focus):
        ph = phases()
        fdim = lambda groups: 1.0 if (not focus or any(g in focus for g in groups)) else 0.45
        hm = 1 - dhw(t); td, tr = T_dep(t), T_ret(t)
        n = 36; cp = G.COIL; L = len(cp)
        for k in range(n):
            a0, a1 = k * (L - 1) // n, (k + 1) * (L - 1) // n + 1
            u = (k + 0.5) / n; T = tr + (td - tr) * u ** 0.8
            dline(d, cam, cp[a0:a1], tcol(T), 210 * fdim(['coil']), 3.4)
        def core(pts, T, a, grp, w=2.6): dline(d, cam, pts, tcol(T), a * fdim([grp]), w)
        core(G.PUMP_TO_COIL, tr, 200, 'pipe_heat'); core(G.RET_TO_PUMP, tr, 200 * (0.4 + 0.6 * hm), 'pipe_heat')
        core(G.COIL_TO_VALVE, td, 200, 'pipe_heat'); core(G.VALVE_TO_DEP, td * hm + tr * (1 - hm), 200 * (0.45 + 0.55 * hm), 'pipe_heat')
        core(G.VALVE_TO_PHX, td, 70 + 150 * dhw(t), 'pipe_dhwp'); core(G.PHX_TO_PUMP, tr, 70 + 150 * dhw(t), 'pipe_dhwp')
        core(G.PHX_PRIM, td, 40 + 180 * dhw(t), 'phx', 2.0)
        hotw = 15 + 40 * tap(t) * heat(t) * dhw(t)
        core(G.EF_PATH, 15, 80 + 150 * tap(t), 'pipe_ef'); core(G.PHX_SEC, hotw, 40 + 180 * tap(t), 'phx', 2.0)
        core(G.ECS_PATH, hotw, 80 + 150 * tap(t), 'pipe_ecs')
        dline(d, cam, G.GAS_PATH, GAS, (90 + 120 * gas(t)) * fdim(['pipe_gas']), 2.4)
        dline(d, cam, G.GAS_PATH2, GAS, (40 + 170 * gas(t)) * fdim(['pipe_gas']), 2.4)
        rw = radwarm(t); (rx0, ry0, rz0), (rx1, ry1, rz1) = G.RAD
        for k in range(10):
            xc = rx0 + 25 + (rx1 - rx0 - 50) * k / 9
            for j in range(6):
                y0 = ry1 - 20 - (ry1 - ry0 - 40) * j / 6; y1 = ry1 - 20 - (ry1 - ry0 - 40) * (j + 1) / 6
                T = tr + (td - tr) * (1 - j / 6) * rw if rw > 0 else 25
                dline(d, cam, [(xc, y0, -125), (xc, y1, -125)], tcol(T), (60 + 160 * rw) * fdim(['radiator']), 5)
        if rw > 0.05:
            for k in range(5):
                xc = rx0 + 60 + (rx1 - rx0 - 120) * k / 4
                pts = [(xc + 12 * math.sin(j * 0.6 - t * 4 + k), ry1 + 30 + j * 14, -125) for j in range(18)]
                dline(d, cam, pts, (255, 160, 90), 130 * rw * fdim(['radiator']), 2)
        if pump(t) > 0.02:
            loopP, Z = (HEAT_LOOP, HZ) if hm > 0.5 else (DHW_LOOP, DZ)
            s = stream(loopP, ph['heat'][i], 46)
            temps = heat_temp(Z, s, t) if hm > 0.5 else heat_temp(Z[:5], s, t)
            ddots(d, cam, loopP.at(s), None, 230 * min(1, pump(t) * 1.4) * fdim(['pipe_heat', 'coil', 'pump', 'radiator', 'phx', 'pipe_dhwp']), 2.6, cols=[tcol(x) for x in temps])
        if tap(t) > 0.02:
            s = stream(DHWW, ph['tap'][i], 40)
            ddots(d, cam, DHWW.at(s), None, 230 * tap(t), 2.6, cols=[tcol(15) if x < DHWW.L * 0.45 else tcol(hotw) for x in s])
            fall = [(-780 + 4 * math.sin(k * 3), -200 - 120 * ((t * 2.2 + k / 14) % 1.0), -60) for k in range(14)]
            ddots(d, cam, fall, tcol(hotw), 220 * tap(t), 3.2)
        if gas(t) > 0.02:
            s = stream(GASP, ph['gas'][i], 40); ddots(d, cam, GASP.at(s), GAS, 235 * gas(t) * fdim(['pipe_gas', 'gasvalve', 'venturi']), 2.6)
        fa = fan(t)
        if fa > 0.02:
            s = stream(FLUE_AIR, ph['air'][i], 34); pos = FLUE_AIR.at(s); dr = FLUE_AIR.dir(s); offs = []
            for k in range(len(s)):
                u, v = G.perp(dr[k]); ang = k * 2.39996; offs.append(pos[k] + 48 * (math.cos(ang) * u + math.sin(ang) * v))
            ddots(d, cam, offs, AIR, 210 * fa * fdim(['flue', 'fan']), 2.2)
            s = stream(AIRC, ph['air'][i], 38); ddots(d, cam, AIRC.at(s), AIR, 200 * fa * fdim(['fan', 'venturi']), 2.2)
            s = stream(MIXP, ph['air'][i], 22)
            ddots(d, cam, MIXP.at(s), None, 220 * fa * fdim(['duct', 'fan', 'venturi', 'burner']), 2.2, cols=[GAS if (k % 3 == 0 and gas(t) > 0.3) else AIR for k in range(len(s))])
        ang = math.radians(ph['fanang'][i]); fc = G.FAN_C + (0, 0, 24)
        for k in range(7):
            a = ang + k * 2 * math.pi / 7
            dline(d, cam, [fc + 12 * np.array([math.cos(a), math.sin(a), 0]), fc + 40 * np.array([math.cos(a + 0.5), math.sin(a + 0.5), 0])], FOCUS if 'fan' in focus else HOLO, 230 * fdim(['fan']), 1.6)
        ang = math.radians(ph['pumpang'][i]); pc = np.array([130, -235, 86.])
        for k in range(5):
            a = ang + k * 2 * math.pi / 5
            dline(d, cam, [pc, pc + 34 * np.array([math.cos(a), math.sin(a), 0])], FOCUS if 'pump' in focus else HOLO, 230 * fdim(['pump']), 1.8)
        # flames
        fl = flame(t); pw = power(t)
        if fl > 0.01:
            bc = np.array([0, 0, 10.])
            sc, zc = cam.p1((0, 188, 10)); rr = 46 * cam.F / max(zc, 50)
            for k in range(3):
                q = rr * (1 + k * 0.3)
                d.ellipse([sc[0] - q, sc[1] - q * 1.5, sc[0] + q, sc[1] + q * 1.5], fill=(255, 120, 40, int(5 * fl * (0.5 + pw))))
            for hk in range(7):
                y = G.BURN_Y[0] + (G.BURN_Y[1] - G.BURN_Y[0]) * (hk + 0.5) / 7
                for ak in range(18):
                    a = ak * 2 * math.pi / 18 + hk * 0.17; rv = np.array([math.cos(a), 0, math.sin(a)])
                    fk = 0.75 + 0.25 * math.sin(t * 17 + ak * 1.3 + hk * 2.1) + 0.15 * math.sin(t * 29 + ak)
                    Lf = (16 + 32 * pw) * fk * fl
                    p0 = bc + (0, y, 0) + rv * G.BURN_R; p1 = p0 + rv * Lf * 0.35; p2 = p0 + rv * Lf
                    dline(d, cam, [p0, p1], (120, 190, 255), 235 * fl, 2.6)
                    dline(d, cam, [p1, p2], (255, 150 + 60 * (1 - pw), 60), 220 * fl, 2.4)
            # ignition burst ring
            b = ramp(t, T_FLAME, T_FLAME + 0.6)
            if 0 < b < 1:
                dline(d, cam, G.circle((0, 188, 10), (0, 1, 0), 40 + 120 * b, 40), (255, 200, 120), 255 * (1 - b), 4)
        # spark
        if T_SPARK <= t < T_FLAME + 0.2 and int(t * 18) % 3 != 0:
            rng = random.Random(i); a = np.array([-37, 158, 34.]); b = np.array([-27, 160, 18.])
            pts = [a + (b - a) * k / 6 + np.array([rng.uniform(-3, 3), rng.uniform(-3, 3), 0]) * (0 < k < 6) for k in range(7)]
            s, zz = cam.proj(np.array(pts)); m = s[3]
            d.ellipse([m[0] - 90, m[1] - 90, m[0] + 90, m[1] + 90], fill=(255, 250, 200, 45))
            d.ellipse([m[0] - 40, m[1] - 40, m[0] + 40, m[1] + 40], fill=(255, 255, 230, 90))
            d.line(s.ravel().tolist(), fill=(255, 240, 150, 140), width=18); d.line(s.ravel().tolist(), fill=(255, 255, 255, 255), width=6)
        if fl > 0.5 and Sx(5, 1) - 0.2 <= t < Sx(5, 2):
            s, zz = cam.p1((37, 158, 34))
            for k in range(3):
                u = ((t * 1.4 + k / 3) % 1.0); q = 14 + 120 * u
                d.ellipse([s[0] - q, s[1] - q, s[0] + q, s[1] + q], outline=(90, 255, 180, int(230 * (1 - u))), width=5)
        # fumes
        fu = fumes(t)
        if fu > 0.02:
            N = 90; pts = []; cols = []
            for k in range(N):
                u = (ph['fume'][i] + k / N) % 1.0; a = k * 2.39996; y0 = 140 + (k * 37 % 100)
                if u < 0.35:
                    q = u / 0.35; r = G.BURN_R + 8 + (G.COIL_R + 18 - G.BURN_R - 8) * q; y = y0 - 50 * q
                    pts.append((r * math.cos(a), y, 10 + r * math.sin(a))); T = 70 - 10 * q
                elif u < 0.7:
                    q = (u - 0.35) / 0.35; r = G.COIL_R + 20; y = (y0 - 50) * (1 - q) - 15 * q; aa = a + q * 0.6
                    pts.append((r * math.cos(aa), y, 10 + r * math.sin(aa))); T = 60 - 12 * q
                else:
                    q = (u - 0.7) / 0.3; pts.append(tuple(FUMEP.at(np.array([q * FUMEP.L]))[0])); T = 46
                cols.append(mix(FUME_H, FUME_C, clamp((70 - T) / 22)))
            ddots(d, cam, pts, None, 160 * fu * fdim(['flue', 'flue_in', 'fumeduct', 'collector', 'coil', 'burner']), 2.4, cols=cols)
            for k in range(8):
                u = ((t * 0.5 + k / 8) % 1.0); x = G.FLUE_END_X + 20 + 260 * u
                ddots(d, cam, [(x, G.FLUE_TOP_Y + 40 * u * u, -50 + 15 * math.sin(k))], FUME_C, 150 * fu * (1 - u), 3 + 6 * u)
        # condensation: vapour -> droplets -> siphon -> drain drip
        cd = cond(t)
        if cd > 0.02:
            vap = []; drops = []; dsz = []
            for k in range(150):
                u = (ph['cond'][i] + k / 150) % 1.0; a = k * 2.39996; r = G.COIL_R + 12 + 8 * math.sin(k)
                if u < 0.2:
                    q = u / 0.2; vap.append((r * math.cos(a), 140 - 80 * q, 10 + r * math.sin(a)))
                elif u < 0.55:
                    q = (u - 0.2) / 0.35; drops.append((r * math.cos(a), 60 - 55 * q * q, 10 + r * math.sin(a))); dsz.append(1.6 + 3.2 * min(1, q * 1.6))
                elif k % 3 == 0:
                    q = (u - 0.55) / 0.45; drops.append(tuple(SIPH.at(np.array([q * SIPH.L]))[0])); dsz.append(3.6)
            ddots(d, cam, vap, VAP, 150 * cd * fdim(['collector', 'coil']), 1.6)
            s, zz = cam.proj(np.array(drops)) if drops else (None, None)
            for k, p in enumerate(drops): ddots(d, cam, [p], COND, 245 * cd * fdim(['collector', 'coil', 'siphon', 'drain']), dsz[k], rmax=3.5)
            # drain drip into funnel
            for k in range(3):
                u = ((t * 1.25 + k / 3) % 1.0); y = G.DRAIN_END[1] - 6 - 34 * u * u
                ddots(d, cam, [(-195, y, -70)], COND, 255 * cd, 4.5, rmax=4.0)
                if u > 0.85:
                    q = (u - 0.85) / 0.15
                    dline(d, cam, G.circle((-195, G.FUNNEL_Y + 6, -70), (0, 1, 0), 6 + 22 * q, 20), COND, 200 * cd * (1 - q), 2)
        # dew line (55 C threshold)
        if P(8) <= t < P(9):
            a = win(t, word_t(8, 2, 'elles passent') - 0.3, P(9), 0.4)
            ring = G.circle((0, 60, 10), (0, 1, 0), G.EXC_R + 6, 64)
            for k in range(0, 64, 2): dline(d, cam, ring[k:k + 2], (120, 255, 190), 230 * a, 2.2)
        # expansion vessel membrane
        vc = np.array([0, -185, -128.]); mz = -6 + 12 * _heat(t)
        dline(d, cam, G.circle(vc + (0, 0, mz), (0, 0, 1), 128, 40), FOCUS if 'vessel' in focus else (120, 200, 255), 200 * fdim(['vessel']) * (1 if 'vessel' in focus else 0.6), 2.4)
        # manometer needle
        gc = np.array([120, -343, 172.]); ga = math.radians(225 - 270 * pressure(t) / 4)
        dline(d, cam, [gc, gc + 12 * np.array([math.cos(ga), math.sin(ga), 0])], (255, 120, 80), 255 * fdim(['gauge']), 1.6)
        # thermostat signal
        for (a0, a1, colr) in ((T_DEMAND - 0.4, T_DEMAND + 1.4, (255, 180, 70)), (T_ROOM20 - 0.2, T_ROOM20 + 1.4, (90, 255, 180))):
            if a0 <= t < a1:
                wp = Path(G.WIRE); u = (t - a0) / (a1 - a0)
                for k in range(5):
                    s = (u * 1.25 - k * 0.05) * wp.L
                    if 0 <= s <= wp.L: ddots(d, cam, wp.at(np.array([s])), colr, 255 * (1 - k * 0.18), 5.5)

    def overlays3d(self, img, d, cam, t):
        # thermostat display
        sc, zc = cam.p1(G.THERMO_C + (0, 5, 14))
        if zc > 50:
            k = cam.F / zc; fs = int(clamp(26 * k, 8, 110))
            if fs >= 16 and -100 < sc[0] < W + 100 and -100 < sc[1] < H + 100:
                col = (90, 255, 180) if t >= T_ROOM20 else (255, 200, 120)
                text(img, d, (sc[0], sc[1]), "%.1f°" % room(t), font('Bold', fs), col, 1.0, 'mm')
                if P(2) <= t < P(3): text(img, d, (sc[0], sc[1] + fs * 0.95), "consigne 20°", font('mono', max(10, int(fs * 0.34))), HOLO, 0.9, 'mm')
        # board display
        sc, zc = cam.p1((-10, -342, 171))
        if zc > 50:
            k = cam.F / zc; fs = int(clamp(15 * k, 8, 90))
            err = word_t(12, 0, 'code') - 0.2 <= t < P(13)
            if fs >= 18 and 0 < sc[0] < W and 0 < sc[1] < 1380 and (err or T_DEMAND + 0.8 <= t < P(3)):
                if err:
                    if int(t * 4) % 2 == 0: text(img, d, (sc[0], sc[1]), "ERR", font('monob', fs), RED, 1.0, 'mm')
                else: text(img, d, (sc[0], sc[1]), "%d°" % round(T_dep(t)), font('monob', fs), (120, 255, 220), 0.95, 'mm')

    def labels(self, img, d, cam, t):
        for (t0, t1, key, txt, hot, side) in LABELS:
            a = win(t, t0, t1, 0.3)
            if a <= 0.01: continue
            anchor = G.ANCH[key][0] if key in G.ANCH else key
            s, z = cam.p1(anchor)
            if z < 50: continue
            if not (SAFE['x0'] - 10 < s[0] < W - 20 and SAFE['y0'] - 40 < s[1] < SAFE['y1'] + 60): continue
            if s[0] > 940 and s[1] > 960: continue
            txt_ = txt or G.ANCH[key][1]
            f = font('SemiBold', 32); tw = d.textlength(txt_, font=f)
            right = (s[0] < W * 0.52) if side is None else (side == 'r')
            grow = ramp(t, t0, t0 + 0.3)
            ex = s[0] + (66 if right else -66); ey = clamp(s[1] - 54, SAFE['y0'], SAFE['y1'])
            hx = ex + (32 if right else -32)
            if side is None:
                if right and hx + 12 + tw > SAFE['x1']: right = False; ex = s[0] - 66; hx = ex - 32
                if not right and hx - 12 - tw < SAFE['x0']: right = True; ex = s[0] + 66; hx = ex + 32
            if right and hx + 12 + tw > SAFE['x1']: hx = SAFE['x1'] - 12 - tw; ex = min(ex, hx - 10)
            if not right and hx - 12 - tw < SAFE['x0']: hx = SAFE['x0'] + 12 + tw; ex = max(ex, hx + 10)
            col = FOCUS if hot else (140, 236, 255)
            d.ellipse([s[0] - 7, s[1] - 7, s[0] + 7, s[1] + 7], outline=rgba(col, 255 * a), width=2)
            d.ellipse([s[0] - 3, s[1] - 3, s[0] + 3, s[1] + 3], fill=rgba(col, 255 * a))
            mx_, my_ = s[0] + (ex - s[0]) * grow, s[1] + (ey - s[1]) * grow
            d.line([s[0], s[1], mx_, my_], fill=rgba(col, 230 * a), width=2)
            if grow > 0.6:
                d.line([ex, ey, hx, ey], fill=rgba(col, 230 * a), width=2)
                tx = hx + 12 if right else hx - 12
                n = max(1, int(len(txt_) * ramp(t, t0 + 0.15, t0 + 0.5)))
                if right: text(img, d, (tx, ey), txt_[:n], f, (255, 255, 255), a, 'lm', 3)
                else: text(img, d, (tx, ey), txt_, f, (255, 255, 255), a * ramp(t, t0 + 0.15, t0 + 0.5), 'rm', 3)

    def hud(self, img, d, t):
        c = (110, 225, 255)
        for (x, y, sx, sy) in ((40, 120, 1, 1), (W - 40, 120, -1, 1), (40, 1590, 1, -1), (W - 40, 1590, -1, -1)):
            d.line([x, y + 40 * sy, x, y, x + 40 * sx, y], fill=(110, 225, 255, 110), width=2)
        # hook
        hk = 1 - ramp(t, T_REW - 0.15, T_REW + 0.05)
        if hk > 0:
            text(img, d, (W / 2, 232), "TA CHAUDIÈRE", font('Bold', 72), (255, 255, 255), hk, 'mm', 6)
            pulse = 1 + 0.04 * math.sin(t * 6)
            text(img, d, (W / 2, 335), "PLEURE ?", font('Bold', int(118 * pulse)), FOCUS, hk, 'mm', 7)
        if T_REW <= t < P(1) - 0.1:
            a = win(t, T_REW + 0.3, P(1) - 0.1, 0.25)
            text(img, d, (W / 2, 250), "◄◄  RETOUR AU DÉBUT", font('monob', 40), c, a, 'mm')
            text(img, d, (W / 2, 305), "chaudière à l'arrêt · pièce à 17 °C", font('mono', 26), (200, 230, 240), a, 'mm')
        pi = max(x['p'] for x in SENTS if x['t0'] <= t + 0.4) if t > 0.2 else 0
        if 1 <= pi < NPARA:
            t0 = P(pi) - 0.4; a = ramp(t, t0, t0 + 0.4) * (1 - ramp(t, Sx(13, 1) - 0.5, Sx(13, 1) - 0.1))
            text(img, d, (70, 194), "%02d" % pi, font('monob', 42), FOCUS, a, 'lm')
            text(img, d, (138, 194), CHAP[pi], font('Bold', 46), (255, 255, 255), a, 'lm')
            d.line([70, 236, 70 + 940 * ramp(t, t0, t0 + 0.7), 236], fill=rgba(c, 120 * a), width=2)
            if pi < 13:
                items = [("PIÈCE", "%.1f°C" % room(t), False), ("EAU DÉPART", "%d°C" % round(T_dep(t)), T_dep(t) > 40),
                         ("FLAMME", "%d%%" % round(100 * power(t)), power(t) > 0.05), ("PRESSION", "%.1f bar" % pressure(t), False)]
                x = 70
                for lab, val, hot in items:
                    text(img, d, (x, 266), lab, font('mono', 20), c, 0.75 * a, 'lm')
                    text(img, d, (x, 302), val, font('monob', 34), FOCUS if hot else (235, 248, 255), a, 'lm')
                    x += 238
        if Sx(5, 2) - 0.1 <= t < P(6) - 0.2:
            self.box(img, d, 90, 1190, 900, "PAS DE FLAMME = GAZ COUPÉ", RED, win(t, Sx(5, 2) - 0.1, P(6) - 0.2, 0.25))
        if Sx(6, 2) - 0.2 <= t < P(7) - 0.2:
            a = win(t, Sx(6, 2) - 0.2, P(7) - 0.2, 0.25); x0, y0 = 120, 1190
            text(img, d, (x0, y0), "MODULATION", font('monob', 28), c, a, 'lm')
            d.rectangle([x0 + 230, y0 - 14, x0 + 740, y0 + 14], outline=rgba(c, 200 * a), width=2)
            d.rectangle([x0 + 234, y0 - 10, x0 + 234 + 502 * power(t), y0 + 10], fill=rgba(FOCUS, 230 * a))
            text(img, d, (x0 + 760, y0), "%d%%" % round(100 * power(t)), font('monob', 30), (255, 255, 255), a, 'lm')
        if word_t(8, 3, 'condense') - 0.2 <= t < word_t(8, 3, 'jusqu') - 0.1:
            self.box(img, d, 190, 1190, 700, "VAPEUR  →  GOUTTES D'EAU", COND, win(t, word_t(8, 3, 'condense') - 0.2, word_t(8, 3, 'jusqu') - 0.1, 0.2))
        if word_t(8, 3, 'jusqu') - 0.1 <= t < P(9) - 0.1:
            self.box(img, d, 170, 1190, 740, "+ ~10 % D'ÉNERGIE RÉCUPÉRÉE", COND, win(t, word_t(8, 3, 'jusqu') - 0.1, P(9) - 0.1, 0.2))
        if P(9) - 0.1 <= t < Sx(9, 1) + 0.3:
            self.box(img, d, 170, 1190, 740, "LES « LARMES » = CONDENSATS", COND, win(t, P(9) - 0.1, Sx(9, 1) + 0.3, 0.2))
        if P(12) <= t < P(13) - 0.15:
            a = win(t, P(12), P(13) - 0.15, 0.25)
            rows = (('flamme absente', 'FLAMME ABSENTE', '→ GAZ COUPÉ'), ('surchauffe', 'SURCHAUFFE', '→ ARRÊT'),
                    ('manque', 'MANQUE DE PRESSION', '→ ARRÊT'), ('code', 'CODE D\'ERREUR AFFICHÉ', ''))
            for k, (w, txt, res) in enumerate(rows):
                ak = a * ramp(t, word_t(12, 0, w) - 0.1, word_t(12, 0, w) + 0.25)
                if ak <= 0.01: continue
                y = 1010 + k * 64
                d.rectangle([110, y - 26, 940, y + 26], outline=rgba(RED, 220 * ak), width=2, fill=(30, 6, 6, int(170 * ak)))
                text(img, d, (140, y), "⚠  " + txt, font('monob', 30), (255, 150, 130), ak, 'lm')
                if res: text(img, d, (915, y), res, font('monob', 26), (255, 255, 255), ak, 'rm')
        if P(13) <= t:
            words = [("AIR", AIR, 'Air'), ("GAZ", GAS, 'gaz'), ("FLAMME", FOCUS, 'flamme'), ("EAU CHAUDE", (255, 110, 70), 'eau'), ("RADIATEURS", (140, 200, 255), 'radiateurs')]
            for k, (w, col, key) in enumerate(words):
                tk = word_t(13, 0, key); a = ramp(t, tk - 0.1, tk + 0.2) * (1 - ramp(t, Sx(13, 1) - 0.5, Sx(13, 1) - 0.1))
                text(img, d, (W / 2, 880 + k * 74), w, font('Bold', 62), col, a, 'mm', 5)
            if t > Sx(13, 1) - 0.3:
                a = ramp(t, Sx(13, 1) - 0.3, Sx(13, 1) + 0.3)
                text(img, d, (W / 2, 222), "ET TA CHAUDIÈRE,", font('Bold', 62), (255, 255, 255), a, 'mm', 6)
                text(img, d, (W / 2, 318), "COMBIEN DE BARS ?", font('Bold', 84), FOCUS, a, 'mm', 7)
                a2 = ramp(t, Sx(13, 2) - 0.2, Sx(13, 2) + 0.3)
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

CHAP = {1: "VUE D'ENSEMBLE", 2: "LA DEMANDE", 3: "L'AIR", 4: "LE GAZ", 5: "L'ALLUMAGE", 6: "L'ÉCHANGEUR", 7: "LA CIRCULATION",
        8: "LA CONDENSATION", 9: "POURQUOI ELLE PLEURE", 10: "L'EAU CHAUDE", 11: "L'ARRÊT", 12: "LES SÉCURITÉS", 13: "EN RÉSUMÉ"}

DISPLAY = [("dix-sept degrés", "17 °C"), ("demandes vingt", "demandes 20"), ("dix volumes d'air pour un volume de gaz", "10 volumes d'air pour 1 volume de gaz"),
           ("soixante, soixante-dix degrés", "60-70 °C"), ("trois bars", "3 bars"), ("cinquante-cinq degrés", "55 °C"), ("dix pour cent", "10 %"), ("À vingt degrés", "À 20 °C")]
NOEND = set("le la les l' un une des de du d' à au aux en par pour sur dans et ou où qui que qu' ce cette ces son sa ses ta ton tes se s' ne n' y sous avant entre très plus un".split())
KEYC = {'gaz': GAS, 'flamme': FOCUS, 'étincelles': FOCUS, 'condensation': COND, 'condense': COND, 'condensats': COND, 'goutte': COND, 'pleure': COND, 'dépression': RED,
        'vapeur': VAP, 'siphon': COND, 'radiateurs': (255, 140, 90), 'chaude': (255, 140, 90), 'froide': (120, 190, 255), 'air': AIR, "l'air": AIR}
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
LABELS = [LB(0.4, T_REW - 0.1, (-195, -600, -70), "Évacuation des condensats", True, 'r'),
          LB(1.0, T_REW - 0.1, 'siphon', None, False, 'r')]
for key, w in (('burner', 'brûleur'), ('exchanger', 'un échangeur'), ('fan', 'ventilateur'), ('gasvalve', 'vanne gaz'), ('pump', 'circulateur'), ('board', 'carte')):
    LABELS.append(LB(word_t(1, 0, w), P(2) - 0.3, key))
LABELS += [LB(P(2) + 0.3, T_DEMAND - 0.1, 'thermostat', None, True), LB(T_DEMAND + 1.4, P(3) - 0.3, 'board', None, True),
           LB(Sx(3, 0) + 0.4, word_t(3, 1, 'ventouse') - 0.3, 'fan', None, True), LB(word_t(3, 1, 'ventouse'), P(4) - 0.3, 'flue', None, True),
           LB(word_t(3, 1, "l'air frais") + 0.6, P(4) - 0.3, (FLUE_END := G.FLUE_END_X - 40, G.FLUE_TOP_Y + 52, -50), "Air frais (tube extérieur)", False, 'l'),
           LB(Sx(4, 0) + 0.3, Sx(4, 1) - 0.1, 'gasvalve', None, True), LB(word_t(4, 1, 'brûleur'), P(5) - 0.3, 'venturi', None, True),
           LB(Sx(5, 0) + 0.2, T_FLAME + 0.1, 'ignition', None, True, 'l'), LB(Sx(5, 1) + 0.2, Sx(5, 2) - 0.1, 'ionisation', None, True, 'l'),
           LB(Sx(5, 2) + 0.3, P(6) - 0.3, 'gasvalve', "Vanne gaz", True),
           LB(Sx(6, 0) + 0.4, word_t(6, 1, 'entre') - 0.3, 'exchanger', "Échangeur (serpentin inox)", True),
           LB(word_t(6, 1, 'entre') + 0.3, word_t(6, 1, 'ressort') - 0.2, tuple(G.COIL_IN), "Entrée : eau tiède", False),
           LB(word_t(6, 1, 'ressort') + 0.3, Sx(6, 2) - 0.1, tuple(G.COIL_OUT), "Sortie : 60-70 °C", True),
           LB(Sx(7, 0) + 0.2, word_t(7, 0, 'radiateurs') - 0.5, 'pump', None, True), LB(word_t(7, 0, 'radiateurs') + 0.6, Sx(7, 2) - 0.2, 'radiator', None, True),
           LB(word_t(7, 2, 'vase'), Sx(7, 3) - 0.1, 'vessel', None, True),
           LB(Sx(7, 3) + 0.2, P(8) - 0.3, 'safety', None, True, 'l'), LB(Sx(7, 3) + 0.6, P(8) - 0.3, 'gauge', "Manomètre", False, 'r'),
           LB(word_t(8, 2, 'elles passent'), Sx(8, 3) - 0.1, (G.EXC_R + 6, 60, 10), "Seuil : 55 °C", True),
           LB(Sx(8, 3) + 0.2, P(9) - 0.3, (100, 10, 60), "Gouttes de condensation", True),
           LB(P(9) + 0.3, Sx(9, 1) - 0.1, (-195, -600, -70), "Les larmes", True, 'r'),
           LB(Sx(9, 1) + 0.6, Sx(9, 2) - 0.1, 'siphon', None, True, 'r'),
           LB(Sx(9, 2) + 0.3, P(10) - 0.3, (G.FLUE_END_X, G.FLUE_TOP_Y + 20, -50), "Sortie des fumées", True),
           LB(Sx(10, 0) + 0.3, Sx(10, 1) - 0.1, 'tap', None, True), LB(Sx(10, 1) + 0.3, word_t(10, 2, 'bascule') - 0.4, 'flowmeter', None, True),
           LB(word_t(10, 2, 'vanne') + 0.3, word_t(10, 2, 'plaques') - 0.45, 'valve3', None, True), LB(word_t(10, 2, 'plaques') + 0.2, Sx(10, 3) - 0.1, 'phx', None, True),
           LB(P(11) + 0.2, Sx(11, 1) - 0.1, 'thermostat', "20 °C atteints", True), LB(Sx(11, 1) + 0.6, Sx(11, 2) - 0.1, 'gasvalve', "Vanne gaz fermée", True),
           LB(Sx(11, 2) + 0.5, P(12) - 0.3, 'fan', "Post-ventilation", False), LB(Sx(11, 2) + 1.0, P(12) - 0.3, 'pump', "Post-circulation", False),
           LB(Sx(13, 1) + 0.6, DUR + 1, 'gauge', "1,5 bar = pression normale", True, 'r'),
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
        print('REW', T_REW, 'FLAME', T_FLAME, 'DHW', T_DHW)
    else:
        from multiprocessing import Pool
        SEG = 150; os.makedirs(BASE + '/seg', exist_ok=True)
        segs = [(k, k * SEG, min(NF, (k + 1) * SEG)) for k in range((NF + SEG - 1) // SEG)]
        segs = [s for s in segs if not os.path.exists(BASE + '/seg/seg_%03d.mp4' % s[0])]
        with Pool(2) as p:
            for res in p.imap_unordered(render_seg, segs): print(res, flush=True)
