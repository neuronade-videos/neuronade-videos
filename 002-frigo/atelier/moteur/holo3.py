import math, json, sys, os, subprocess, random, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import geom as G

BASE = '/home/claude/d002'
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


# ---------------- fridge temperatures -> colours ----------------
FT = np.array([-25, -10, 5, 20, 35, 55.]); FR = np.array([70, 90, 150, 225, 255, 255.]); FG = np.array([120, 200, 235, 235, 214, 100.]); FB = np.array([255, 255, 255, 230, 70, 50.])
def tcol(T): return (float(np.interp(T, FT, FR)), float(np.interp(T, FT, FG)), float(np.interp(T, FT, FB)))
COLD = (110, 190, 255); HOTC = (255, 120, 60); FROST = (220, 240, 255); WATER = (90, 255, 200); COND = (90, 255, 160); VAP = (230, 240, 255)

# ---------------- key times ----------------
T_REW = Sx(0, 4) - 0.1                         # "Regarde comment il fait." : rewind, fridge unplugged
T_ON = word_t(1, 1, 'tourne') - 0.2            # compressor starts : the fluid starts to circulate
T_OFF1 = word_t(7, 1, 'il arrête') + 0.25      # 4 C reached : thermostat stops the compressor
T_ON2 = word_t(7, 2, 'relance') + 0.1
T_OFF2 = word_t(8, 3, "s'arrête")              # off-cycle : the frost melts
T_ON3 = P(9) + 0.3
T_DOOR_O = Sx(9, 0) + 0.5; T_DOOR_C = Se(9, 3) + 0.25
T_FLAME = T_ON                                 # (name kept for the shared photoreal layer)
CHANGES = [T_REW] + [P(p) for p in range(1, NPARA)]
def tease(t): return 1 - ramp(t, T_REW, T_REW + 0.2)
def _comp(t):
    on = ramp(t, T_ON, T_ON + 0.6) * (1 - ramp(t, T_OFF1, T_OFF1 + 0.4))
    on = max(on, ramp(t, T_ON2, T_ON2 + 0.5) * (1 - ramp(t, T_OFF2, T_OFF2 + 0.4)))
    return max(on, ramp(t, T_ON3, T_ON3 + 0.6))
def comp(t): return max(_comp(t), tease(t))
def door(t): return ramp(t, T_DOOR_O, T_DOOR_O + 0.9) * (1 - ramp(t, T_DOOR_C - 0.6, T_DOOR_C + 0.3))
def interior(t):
    if t < T_REW: return 4.0
    T = 20.0 - 16.0 * ramp(t, T_ON + 1.0, Sx(7, 1) + 1.2) ** 0.7
    T += 1.0 * ramp(t, T_OFF1, T_ON2) * (1 - ramp(t, T_ON2, T_ON2 + 3.0))
    T += 0.8 * ramp(t, T_OFF2, T_OFF2 + 5.0) * (1 - ramp(t, T_ON3, T_ON3 + 4))
    T += 5.0 * ramp(t, T_DOOR_O, T_DOOR_O + 4.0) * (1 - ramp(t, T_DOOR_C, T_DOOR_C + 8.0))
    return T
def evap_T(t):
    if t < T_REW: return -20.0
    run = ramp(t, T_ON, T_ON + 4.0)
    T = 20 + (-20 - 20) * run
    T += 20 * ramp(t, T_OFF1, T_OFF1 + 3.0) * (1 - ramp(t, T_ON2, T_ON2 + 2.0))
    T += 23 * ramp(t, T_OFF2, T_OFF2 + 2.5) * (1 - ramp(t, T_ON3, T_ON3 + 2.5))
    return T
def kitchen(t): return 20.0 + 0.6 * ramp(t, Sx(9, 2), Se(9, 3))
def frost(t):
    f = ramp(t, T_ON + 6, P(8)) if t >= T_REW else 1.0
    return f * (1 - ramp(t, T_OFF2 + 0.6, word_t(8, 3, 'coule') + 0.4))
def melt(t): return win(t, T_OFF2 + 0.4, Se(8, 3) + 1.0, 0.4)
def heat_in(t): return comp(t) * (win(t, Sx(3, 2) - 0.3, P(4) + 0.6, 0.4) + 0.6 * win(t, P(10), DUR + 1, 0.4) + win(t, T_DOOR_O, T_DOOR_C, 0.4))
def heat_out(t): return comp(t) * (win(t, P(5), P(6) + 0.2, 0.4) + win(t, Sx(9, 2) - 0.4, T_DOOR_C + 1.0, 0.4) + 0.6 * win(t, P(10), DUR + 1, 0.4) + 0.5 * win(t, P(1) + 1, P(2), 0.4))

_ph = None
def phases():
    global _ph
    if _ph is None:
        ts = np.arange(NF + 2) / FPS
        f = lambda fn, k: np.cumsum([fn(x) * k / FPS for x in ts])
        _ph = dict(fluid=f(comp, 260), heat=f(lambda x: 1.0, 0.45), angle=f(comp, 900), drip=f(melt, 1.0))
    return _ph

# ---------------- camera ----------------
def CK(t, T, az, el, d, dur=1.2, rate=0.0, fov=38):
    return dict(t=t, T=np.array(T, float), az=az, el=el, d=d, dur=dur, rate=rate, fov=fov)
TH = G.THERMO_C
KEYS = [
 CK(0.0, (0, 0, 0), 30, 10, 3300, 0, 0),
 CK(T_REW + 0.05, (0, 20, 0), 34, 12, 3350, 1.0, 1.0),
 CK(P(1), (0, 20, 0), 28, 10, 3200, 1.0, 1.2),
 CK(word_t(1, 0, 'compresseur') - 0.2, (110, -600, -225), 150, 12, 1250, 1.0, 0.8),
 CK(word_t(1, 0, 'condenseur') - 0.2, (0, 100, -332), 172, 6, 2850, 1.1, 0.6),
 CK(word_t(1, 0, 'détendeur') - 0.2, (-205, -500, -316), 212, 6, 1150, 1.0, 0.6),
 CK(word_t(1, 0, 'évaporateur') - 0.2, (0, 430, -250), 18, 8, 1500, 1.0, 0.6),
 CK(Sx(1, 1), (0, 0, -150), 138, 12, 3250, 1.3, 1.0),
 CK(P(2), (0, 430, -240), 14, 4, 1050, 1.2, 0.6),
 CK(Sx(2, 2), (0, 430, -245), -10, 0, 760, 1.0, 0.4),
 CK(P(3), (0, 330, -150), 26, 8, 1700, 1.2, 0.8),
 CK(Sx(3, 2), (-70, 160, -60), 32, 10, 1450, 1.1, 0.6),
 CK(P(4), (110, -600, -225), 150, 14, 820, 1.2, 0.8),
 CK(Sx(4, 1), (200, -250, -320), 168, 8, 1700, 1.1, 0.6),
 CK(Sx(4, 2), (110, -600, -225), 140, 8, 640, 1.0, 0.5),
 CK(P(5), (0, 100, -332), 182, 6, 2850, 1.2, 0.7),
 CK(Sx(5, 1), (0, 0, -300), 205, 10, 3100, 1.2, 0.8),
 CK(P(6), (-210, -520, -316), 210, 10, 900, 1.2, 0.6),
 CK(Sx(6, 1), (-205, -535, -316), 222, 6, 620, 1.0, 0.5),
 CK(Sx(6, 2), (-120, 150, -280), 200, 8, 2300, 1.2, 0.6),
 CK(word_t(6, 2, 'la boucle') - 0.2, (0, 0, -150), 130, 10, 3250, 1.2, 1.2),
 CK(P(7), (TH[0], TH[1], TH[2]), -64, 4, 640, 1.2, 0.5),
 CK(word_t(7, 1, 'il arrête') - 0.3, (40, -250, -150), 120, 8, 2700, 1.0, 0.8),
 CK(Sx(7, 3), (0, 0, 0), 40, 10, 3300, 1.2, 1.0),
 CK(P(8), (0, 380, -245), 12, 12, 1150, 1.2, 0.5),
 CK(Sx(8, 3), (0, 150, -260), 18, 6, 1350, 1.1, 0.5),
 CK(word_t(8, 3, 'coule') - 0.2, (0, -150, -312), 150, 8, 2450, 1.2, 0.6),
 CK(word_t(8, 3, 'un bac') - 0.3, (120, -525, -226), 150, 22, 820, 1.1, 0.5),
 CK(P(9), (0, 0, 120), 38, 10, 3450, 1.2, 0.8),
 CK(Sx(9, 2), (0, -50, -150), 150, 10, 3350, 1.2, 0.8),
 CK(P(10), (0, 20, 0), 30, 12, 3400, 1.3, 2.0),
 CK(Sx(10, 1) - 0.25, (TH[0], TH[1], TH[2]), -64, 4, 500, 1.5, 0.25),
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

# ---------------- refrigerant loop ----------------
LOOP_PARTS = [G.EVAP_PATH, G.SUCTION, G.IN_COMP, G.DISCHARGE, G.COND_PATH, G.TO_DRIER + [G.DRIER[1]], G.CAPILLARY]
LOOP = Path(cat(*LOOP_PARTS))
def zones(parts):
    b = []; acc = 0
    for p in parts: b.append(acc); acc += Path(p).L
    return np.array(b + [acc])
LZ = zones(LOOP_PARTS)   # evap, suction, comp, discharge, condenser, drier, capillary
COIL_END = LZ[6] + Path(G.CAPILLARY[:13]).L
def thermal(t): return ramp(t, T_ON, T_ON + 4.0) if t >= T_REW else 1.0
def loop_state(s, t):
    """temperature (C) and liquid fraction (1 = liquid, 0 = gas) of the refrigerant at curvilinear abscissa s"""
    th = thermal(t) * (0.35 + 0.65 * comp(t)); te = evap_T(t)
    T = np.empty(len(s)); liq = np.empty(len(s))
    for k, x in enumerate(s):
        if x < LZ[1]:
            u = (x - LZ[0]) / (LZ[1] - LZ[0]); T[k] = te; liq[k] = 1 - u ** 0.8
        elif x < LZ[2]:
            u = (x - LZ[1]) / (LZ[2] - LZ[1]); T[k] = te + (15 * th) * u; liq[k] = 0
        elif x < LZ[3]:
            u = (x - LZ[2]) / (LZ[3] - LZ[2]); T[k] = te + 15 * th + (55 * th + 20 * (1 - th) - te - 15 * th) * u; liq[k] = 0
        elif x < LZ[4]:
            T[k] = 55 * th + 20 * (1 - th) - 4 * th * (x - LZ[3]) / (LZ[4] - LZ[3]); liq[k] = 0
        elif x < LZ[5]:
            u = (x - LZ[4]) / (LZ[5] - LZ[4]); T[k] = (51 - 16 * u) * th + 20 * (1 - th); liq[k] = min(1, max(0, (u - 0.25) / 0.5))
        elif x < LZ[6]:
            T[k] = 35 * th + 20 * (1 - th); liq[k] = 1
        elif x < COIL_END:
            u = (x - LZ[6]) / (COIL_END - LZ[6]); T[k] = (35 * th + 20 * (1 - th)) * (1 - u) + te * u; liq[k] = 1
        else:
            T[k] = te; liq[k] = 1
    return T, liq
FOOD_SRC = [(x, y + 40, z) for (x, y, z) in G.POTS] + [(165, -150, 40), (-95, 245, 5)]
DRAINP = Path(cat([(0, 300, -248), (0, G.GUTTER_Y + 2, -250)], G.DRAIN))

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
    on(0, T_REW, ['condenser', 'compressor'])
    on(Sx(1, 1), P(2) - 0.3, ['pipe_suction', 'pipe_discharge', 'capillary', 'evaporator', 'condenser'])
    on(P(2), P(3) - 0.3, ['evaporator'])
    on(P(3), Sx(3, 2), ['evaporator', 'capillary'])
    on(Sx(3, 2), P(4) - 0.3, ['evaporator', 'food'])
    on(P(4), Sx(4, 1), ['compressor', 'pipe_suction'])
    on(Sx(4, 1), Sx(4, 2), ['compressor', 'pipe_discharge'])
    on(Sx(4, 2), P(5) - 0.3, ['compressor'])
    on(P(5), P(6) - 0.3, ['condenser', 'pipe_discharge'])
    on(P(6), Sx(6, 2), ['capillary', 'drier'])
    on(Sx(6, 2), P(7) - 0.3, ['capillary', 'evaporator'])
    on(P(7), word_t(7, 1, 'il arrête') - 0.3, ['thermostat', 'wire'])
    on(word_t(7, 1, 'il arrête') - 0.3, P(8) - 0.3, ['thermostat', 'compressor'])
    on(P(8), Sx(8, 3), ['evaporator', 'gutter'])
    on(Sx(8, 3), P(9) - 0.3, ['gutter', 'drain', 'tray', 'compressor'])
    on(P(9), Sx(9, 2), ['door', 'gasket'])
    on(Sx(9, 2), P(10) - 0.3, ['condenser', 'compressor', 'door'])
    on(Sx(10, 1) - 0.3, DUR + 1, ['thermostat'])
    return set(F), (0.36 if F else 1.0)

GROUP_TINT = {'env': ENV, 'food': (235, 245, 255), 'door': (120, 215, 240), 'gasket': (120, 215, 240)}
DOOR_IDX = None

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

def door_points(t):
    """ALLP with the door group swung open around its hinge (x = 300, z = 300)"""
    th = math.radians(100) * sm(door(t))
    if th <= 1e-4: return ALLP
    P_ = ALLP.copy(); hx, hz = G.HINGE_X, G.DOOR_Z[0]
    vx = P_[DOOR_MASK, 0] - hx; vz = P_[DOOR_MASK, 2] - hz
    P_[DOOR_MASK, 0] = hx + vx * math.cos(th) + vz * math.sin(th)
    P_[DOOR_MASK, 2] = hz - vx * math.sin(th) + vz * math.cos(th)
    return P_
def door_points_one(p, t):
    th = math.radians(100) * sm(door(t)); hx, hz = G.HINGE_X, G.DOOR_Z[0]; vx, vz = p[0] - hx, p[2] - hz
    return (hx + vx * math.cos(th) + vz * math.sin(th), p[1], hz - vx * math.sin(th) + vz * math.cos(th))
DOOR_MASK = np.zeros(len(ALLP), bool)
for k_, p_ in enumerate(POLYS):
    if p_['group'] in ('door', 'gasket'): DOOR_MASK[OFF[k_]:OFF[k_ + 1]] = True

class Renderer:
    def __init__(self):
        self.bg = make_bg(); self.scan = make_scan(); cams(); phases()
    def frame(self, i):
        t = i / FPS; c = cams()[i]; cam = Cam(c, S, t)
        img = Image.new('RGB', (W2, H2)); d = ImageDraw.Draw(img, 'RGBA')
        focus, dim = scene_focus(t)
        reveal = None
        if T_REW <= t < T_REW + 1.1: reveal = -760 + 1560 * sm((t - T_REW) / 1.05)
        PTS = door_points(t)
        sp, z = cam.proj(PTS)
        zmean = np.add.reduceat(z, OFF[:-1]) / np.diff(OFF)
        flick = 0.93 + 0.07 * math.sin(t * 13.0) * math.sin(t * 7.3)
        for k, p in enumerate(POLYS):
            if reveal is not None and YMIN[k] > reveal: continue
            i0, i1 = OFF[k], OFF[k + 1]
            if z[i0:i1].min() < 40: continue
            g = p['group']
            depth = clamp(1.25 - (zmean[k] - cam.d) / 2600, 0.3, 1.15)
            col = GROUP_TINT.get(g, HOLO); a = p['a'] * 235 * depth * flick
            if g in focus: col = FOCUS; a = min(255, a * 1.5 + 40)
            elif focus and g != 'env': a *= dim
            if g == 'evaporator' and g not in focus: col = mix(col, COLD, 0.6 * thermal(t) * comp(t))
            if g == 'condenser' and g not in focus: col = mix(col, HOTC, 0.45 * thermal(t) * comp(t))
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
            ra = 1 - ramp(reveal, 520, 760)
            if ra > 0.01:
                dline(d, cam, G.circle((0, reveal, 0), (0, 1, 0), 470, 60), (170, 250, 255), 230 * ra, 2.5)
                dline(d, cam, G.circle((0, reveal, 0), (0, 1, 0), 490, 60), (120, 230, 255), 90 * ra, 6)
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
        f = win(t, T_ON - 0.02, T_ON + 0.5, 0.03) * (1 - ramp(t, T_ON, T_ON + 0.5))
        if f > 0: img = ImageChops.screen(img, Image.new('RGB', (W, H), tuple(int(v * 0.2 * f) for v in (120, 200, 255))))
        return img

    def dynamic(self, d, cam, t, i, focus):
        ph = phases(); cp = comp(t); th = thermal(t)
        fdim = lambda groups: 1.0 if (not focus or any(g in focus for g in groups)) else 0.45
        # refrigerant lines coloured by temperature
        for part, grp, w in ((G.SUCTION, 'pipe_suction', 2.4), (G.DISCHARGE, 'pipe_discharge', 2.4)):
            s0 = Path(part); s = np.linspace(0, s0.L, 12); pts = s0.at(s)
            base = LZ[1] if grp == 'pipe_suction' else LZ[3]
            T, _ = loop_state(base + s, t)
            for k in range(len(pts) - 1): dline(d, cam, pts[k:k + 2], tcol(T[k]), 170 * fdim([grp]), w)
        # moving refrigerant particles (liquid = full dot, gas = ring)
        sp_ = stream(LOOP, ph['fluid'][i], 48)
        T, liq = loop_state(sp_, t)
        a = (110 + 130 * min(1, cp * 1.3 + 0.25 * th)) if t >= T_REW else 220
        groups_at = ['evaporator', 'pipe_suction', 'compressor', 'pipe_discharge', 'condenser', 'drier', 'capillary']
        zi = np.clip(np.searchsorted(LZ, sp_, side='right') - 1, 0, 6)
        for k in range(len(sp_)):
            gk = groups_at[zi[k]]
            ddots(d, cam, LOOP.at(np.array([sp_[k]])), tcol(T[k]), a * fdim([gk]), 2.4 + 0.9 * liq[k], hollow=[1 - liq[k]])
        # evaporator: boiling bubbles + frost
        if th > 0.05 and cp > 0.05:
            rng = random.Random(7); ev = Path(G.EVAP_PATH)
            for k in range(40):
                u = (rng.random() + t * 0.6 * (0.6 + rng.random())) % 1.0; s = rng.random() * ev.L
                p = ev.at(np.array([s]))[0] + np.array([rng.uniform(-6, 6), 14 * u, 8 + 18 * u])
                ddots(d, cam, [p], (200, 235, 255), 150 * cp * (1 - u) * fdim(['evaporator']), 1.3)
        fr = frost(t)
        if fr > 0.02:
            rng = random.Random(3)
            for k in range(int(170 * fr)):
                p = (rng.uniform(G.EVAP_X[0] - 15, G.EVAP_X[1] + 15), rng.uniform(G.EVAP_Y[0] - 20, G.EVAP_Y[1] + 20), G.EVAP_Z + 9)
                tw = 0.6 + 0.4 * math.sin(t * 5 + k)
                ddots(d, cam, [p], FROST, 200 * fr * tw * fdim(['evaporator', 'gutter']), 1.2 + 1.2 * rng.random())
        # heat stolen from the food -> evaporator
        hi = heat_in(t)
        if hi > 0.02:
            rng = random.Random(11)
            for k in range(54):
                src = np.array(FOOD_SRC[k % len(FOOD_SRC)], float)
                dst = np.array((rng.uniform(-200, 200), rng.uniform(G.EVAP_Y[0], G.EVAP_Y[1]), G.EVAP_Z + 10), float)
                u = (ph['heat'][i] * (0.8 + 0.4 * rng.random()) + rng.random()) % 1.0
                p = src + (dst - src) * u + np.array([0, 60 * math.sin(math.pi * u), 0])
                ddots(d, cam, [p], mix(HOTC, COLD, u ** 1.5), 200 * hi * math.sin(math.pi * min(1, u * 1.1)) * fdim(['food', 'evaporator']), 2.0)
        # warm kitchen air rushing in when the door is open
        do = door(t)
        if do > 0.05:
            rng = random.Random(5)
            for k in range(40):
                u = (t * 0.5 * (0.6 + rng.random()) + rng.random()) % 1.0
                p = (rng.uniform(-240, 240), rng.uniform(-420, 640), 640 - 760 * u)
                ddots(d, cam, [p], HOTC, 170 * do * math.sin(math.pi * u), 2.2)
        # heat rejected by the condenser into the kitchen
        ho = heat_out(t)
        if ho > 0.02:
            for k in range(9):
                x = G.COND_X[0] + (G.COND_X[1] - G.COND_X[0]) * (k + 0.5) / 9
                for j in range(2):
                    ph0 = (t * 0.45 + k * 0.13 + j * 0.5) % 1.0
                    pts = [(x + 22 * math.sin(m * 0.5 - t * 3 + k), G.COND_Y[0] + (G.COND_Y[1] + 260 - G.COND_Y[0]) * (ph0 + m * 0.012), G.COND_Z - 60) for m in range(14)]
                    dline(d, cam, pts, (255, 150, 80), 150 * ho * math.sin(math.pi * ph0) * fdim(['condenser']), 2)
        # compressor: hot dome, spinning rotor mark, humming rings
        cc = np.array(G.COMP_C, float); top = cc + (0, G.COMP_Y[1] - cc[1] + 5, 0)
        if cp * th > 0.05:
            dline(d, cam, G.circle(top + (0, -60, 0), (0, 1, 0), G.COMP_R + 3, 32), HOTC, 160 * cp * th * fdim(['compressor']), 3)
        ang = math.radians(ph['angle'][i])
        for k in range(3):
            a_ = ang + k * 2 * math.pi / 3
            dline(d, cam, [top + (0, -40, 0), top + (0, -40, 0) + 46 * np.array([math.cos(a_), 0, math.sin(a_)])], FOCUS if 'compressor' in focus else HOLO, 220 * fdim(['compressor']), 1.6)
        hum = cp * win(t, Sx(4, 2) - 0.2, P(5) - 0.2, 0.3)
        if hum > 0.02:
            sc, zc = cam.p1(cc + (0, 10, 0))
            for k in range(3):
                u = ((t * 1.6 + k / 3) % 1.0); q = 40 + 220 * u
                d.ellipse([sc[0] - q, sc[1] - q * 0.7, sc[0] + q, sc[1] + q * 0.7], outline=(255, 190, 110, int(170 * hum * (1 - u))), width=5)
        # capillary : pressure drop flash in the coil
        cap = win(t, Sx(6, 1) - 0.2, P(7) - 0.4, 0.3)
        if cap > 0.02:
            cpth = Path(G.CAPILLARY[:14]); s = np.linspace(0, cpth.L, 14); pts = cpth.at(s)
            for k in range(len(pts) - 1):
                dline(d, cam, pts[k:k + 2], tcol(35 - 55 * k / 13), 230 * cap, 3.4)
        # defrost : drops slide down the plate, into the gutter, the hole, the drain, the tray ; then vapour
        me = melt(t)
        if me > 0.02:
            rng = random.Random(9)
            for k in range(26):
                x0 = rng.uniform(G.EVAP_X[0], G.EVAP_X[1]); u = (t * 0.35 + rng.random()) % 1.0
                if u < 0.55:
                    q = u / 0.55; p = (x0 * (1 - 0.15 * q), G.EVAP_Y[1] - (G.EVAP_Y[1] - G.GUTTER_Y) * q * q, G.EVAP_Z + 10)
                else:
                    q = (u - 0.55) / 0.45; p = tuple(DRAINP.at(np.array([q * DRAINP.L]))[0])
                ddots(d, cam, [p], WATER, 235 * me * fdim(['evaporator', 'gutter', 'drain', 'tray']), 3.0, rmax=3.2)
        tray_w = ramp(t, word_t(8, 3, 'un bac'), word_t(8, 3, 'un bac') + 1.5) * (1 - ramp(t, P(10), P(10) + 3))
        if tray_w > 0.02:
            (x0, y0, z0), (x1, y1, z1) = G.TRAY; yw = y0 + 8
            dline(d, cam, [(x0 + 6, yw, z0 + 6), (x1 - 6, yw, z0 + 6), (x1 - 6, yw, z1 - 6), (x0 + 6, yw, z1 - 6), (x0 + 6, yw, z0 + 6)], WATER, 220 * tray_w, 2.6)
            vap = tray_w * ramp(t, word_t(8, 3, 'évapore') - 0.6, word_t(8, 3, 'évapore'))
            if vap > 0.02:
                rng = random.Random(4)
                for k in range(16):
                    u = (t * 0.6 + rng.random()) % 1.0
                    p = (rng.uniform(x0 + 15, x1 - 15) + 12 * math.sin(u * 6 + k), y1 + 160 * u, rng.uniform(z0 + 15, z1 - 15))
                    ddots(d, cam, [p], (230, 245, 255), 170 * vap * (1 - u), 2.2)
        # thermostat signal to the compressor (stop / restart)
        for (a0, a1, colr) in ((T_OFF1 - 0.5, T_OFF1 + 0.9, (90, 255, 180)), (T_ON2 - 0.5, T_ON2 + 0.9, (255, 180, 70))):
            if a0 <= t < a1:
                wp = Path([TH, (240, 480, -150), (240, -480, -300), tuple(cc + (60, 0, 0))]); u = (t - a0) / (a1 - a0)
                for k in range(5):
                    s = (u * 1.25 - k * 0.05) * wp.L
                    if 0 <= s <= wp.L: ddots(d, cam, wp.at(np.array([s])), colr, 255 * (1 - k * 0.18), 5.5)

    def overlays3d(self, img, d, cam, t):
        sc, zc = cam.p1(np.array(TH) + (-3, 8, 0))
        facing = (np.array(TH) - cam.C) @ np.array([1.0, 0, 0]) / max(1e-6, np.linalg.norm(np.array(TH) - cam.C))
        if zc > 50 and facing > 0.35:
            k = cam.F / zc; fs = int(clamp(24 * k, 8, 120))
            if fs >= 16 and -100 < sc[0] < W + 100 and -100 < sc[1] < H + 100:
                Ti = interior(t); col = (90, 255, 180) if Ti <= 4.3 else (255, 200, 120); av = ramp(sc[1], 400, 480)
                if av <= 0.01: return
                text(img, d, (sc[0], sc[1]), "%.1f°" % Ti, font('Bold', fs), col, av, 'mm')
                if P(7) <= t < P(8) or t >= Sx(10, 1) - 0.3:
                    text(img, d, (sc[0], sc[1] + fs * 0.95), "consigne 4°", font('mono', max(10, int(fs * 0.34))), HOLO, 0.9 * av, 'mm')

    def labels(self, img, d, cam, t):
        return

    def hud(self, img, d, t):
        c = (110, 225, 255)
        for (x, y, sx, sy) in ((40, 120, 1, 1), (W - 40, 120, -1, 1), (40, 1590, 1, -1), (W - 40, 1590, -1, -1)):
            d.line([x, y + 40 * sy, x, y, x + 40 * sx, y], fill=(110, 225, 255, 110), width=2)
        hk = 1 - ramp(t, T_REW - 0.15, T_REW + 0.05)
        if hk > 0:
            text(img, d, (W / 2, 232), "TON FRIGO", font('Bold', 72), (255, 255, 255), hk, 'mm', 6)
            pulse = 1 + 0.04 * math.sin(t * 6)
            text(img, d, (W / 2, 335), "EST UN VOLEUR", font('Bold', int(100 * pulse)), FOCUS, hk, 'mm', 7)
        if T_REW <= t < P(1) - 0.1:
            a = win(t, T_REW + 0.3, P(1) - 0.1, 0.25)
            text(img, d, (W / 2, 250), "◄◄  RETOUR AU DÉBUT", font('monob', 40), c, a, 'mm')
            text(img, d, (W / 2, 305), "frigo débranché · intérieur à 20 °C", font('mono', 26), (200, 230, 240), a, 'mm')
        pi = max(x['p'] for x in SENTS if x['t0'] <= t + 0.4) if t > 0.2 else 0
        if 1 <= pi < NPARA:
            t0 = P(pi) - 0.4; a = ramp(t, t0, t0 + 0.4) * (1 - ramp(t, Sx(10, 1) - 0.5, Sx(10, 1) - 0.1))
            text(img, d, (70, 194), "%02d" % pi, font('monob', 42), FOCUS, a, 'lm')
            text(img, d, (138, 194), CHAP[pi], font('Bold', 46), (255, 255, 255), a, 'lm')
            d.line([70, 236, 70 + 940 * ramp(t, t0, t0 + 0.7), 236], fill=rgba(c, 120 * a), width=2)
            if pi < 10:
                cp = comp(t) > 0.5
                items = [("INTÉRIEUR", "%.1f°C" % interior(t), False), ("ÉVAPORATEUR", "%d°C" % round(evap_T(t)), evap_T(t) < 0),
                         ("COMPRESSEUR", "MARCHE" if cp else "ARRÊT", cp), ("CUISINE", "%.1f°C" % kitchen(t), kitchen(t) > 20.05)]
                x = 70
                for lab, val, hot in items:
                    text(img, d, (x, 266), lab, font('mono', 20), c, 0.75 * a, 'lm')
                    vcol = (COLD if lab == 'ÉVAPORATEUR' else FOCUS) if hot else (235, 248, 255)
                    text(img, d, (x, 302), val, font('monob', 34), vcol, a, 'lm')
                    x += 238
        B = [(word_t(2, 1, 'il absorbe') - 0.1, Sx(2, 2) - 0.1, "LIQUIDE + CHALEUR → GAZ", COND, 170, 740),
             (Sx(2, 2), P(3) - 0.15, "PRESSION BASSE → BOUT À -20 °C", COLD, 130, 820),
             (Sx(4, 1), Sx(4, 2), "GAZ COMPRIMÉ → +50 °C", FOCUS, 210, 660),
             (Sx(5, 1), P(6) - 0.15, "CHALEUR VOLÉE → TA CUISINE", FOCUS, 170, 740),
             (Sx(6, 1) + 0.3, Sx(6, 2), "CHUTE DE PRESSION → GLACÉ", COLD, 170, 740),
             (word_t(7, 1, 'il arrête'), Sx(7, 2) - 0.15, "4 °C ATTEINTS → COMPRESSEUR COUPÉ", COND, 110, 860),
             (word_t(8, 3, 'coule'), P(9) - 0.15, "GIVRE → EAU → BAC → VAPEUR", WATER, 170, 740),
             (Sx(9, 2), P(10) - 0.15, "CHALEUR VOLÉE + MOTEUR → CUISINE", FOCUS, 130, 820)]
        for (a0, a1, s, col, x0, w) in B:
            if a0 <= t < a1: self.box(img, d, x0, 1190, w, s, col, win(t, a0, a1, 0.2))
        if P(10) <= t:
            a = 1 - ramp(t, Sx(10, 1) - 0.5, Sx(10, 1) - 0.1)
            for k, (w, col, key) in enumerate((("VOLER LA CHALEUR", HOTC, 'Voler'), ("DEDANS", COLD, 'dedans'), ("LA JETER", HOTC, 'jeter'), ("DEHORS", FOCUS, 'dehors'))):
                tk = word_t(10, 0, key); ak = a * ramp(t, tk - 0.1, tk + 0.2)
                text(img, d, (W / 2, 860 + k * 80), w, font('Bold', 66), col, ak, 'mm', 5)
            if t > Sx(10, 1) - 0.3:
                a = ramp(t, Sx(10, 1) - 0.3, Sx(10, 1) + 0.3)
                text(img, d, (W / 2, 222), "ET TON FRIGO,", font('Bold', 62), (255, 255, 255), a, 'mm', 6)
                text(img, d, (W / 2, 318), "RÉGLÉ SUR COMBIEN ?", font('Bold', 80), FOCUS, a, 'mm', 7)
                a2 = ramp(t, Sx(10, 2) - 0.2, Sx(10, 2) + 0.3)
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



CHAP = {1: "VUE D'ENSEMBLE", 2: "LE SECRET", 3: "L'ÉVAPORATEUR", 4: "LE COMPRESSEUR", 5: "LE CONDENSEUR", 6: "LE DÉTENDEUR",
        7: "LE THERMOSTAT", 8: "IL PLEURE AUSSI", 9: "LE BONUS", 10: "EN RÉSUMÉ"}
DISPLAY = [("moins vingt degrés", "-20 °C"), ("cinquante degrés", "50 °C"), ("environ quatre degrés", "environ 4 °C")]
NOEND = set("le la les l' un une des de du d' à au aux en par pour sur dans et ou où qui que qu' ce cette ces son sa ses ta ton tes se s' ne n' y sous avant entre très plus un".split())
KEYC = {'froid': COLD, 'froid.': COLD, 'chaleur': HOTC, 'voleur': FOCUS, 'vole': FOCUS, 'volée': FOCUS, 'voler': FOCUS, 'glacé': COLD,
        'brûlant': HOTC, 'chauffe': HOTC, 'givre': FROST, 'pleure': WATER, 'liquide': COLD, 'gaz': YEL, "s'évapore": (230, 240, 255),
        'évapore': (230, 240, 255), 'tiède': HOTC, 'compresseur': FOCUS, 'cuisine': HOTC, 'dedans': COLD, 'dehors': FOCUS}

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
for key, w in (('compressor', 'compresseur'), ('condenser', 'condenseur'), ('capillary', 'détendeur'), ('evaporator', 'évaporateur')):
    LABELS.append(LB(word_t(1, 0, w), P(2) - 0.3, key))
LABELS += [LB(word_t(1, 1, 'fluide'), P(2) - 0.3, 'fluid', "Fluide isobutane", True),
           LB(Sx(3, 0) + 0.3, Sx(3, 2) - 0.1, 'evaporator', None, True),
           LB(word_t(3, 2, 'aliments') - 0.2, P(4) - 0.3, 'food', "Chaleur des aliments", True),
           LB(P(4) + 0.3, Sx(4, 1) - 0.1, 'compressor', None, True),
           LB(Sx(4, 1) + 0.3, Sx(4, 2) - 0.1, 'discharge', "Gaz brûlant", True),
           LB(Sx(4, 2) + 0.2, P(5) - 0.3, 'compressor', "Le bourdonnement", True),
           LB(P(5) + 0.3, P(6) - 0.3, 'condenser', None, True),
           LB(Sx(6, 1) + 0.2, Sx(6, 2) - 0.1, 'capillary', None, True),
           LB(word_t(6, 2, 'repart'), word_t(6, 2, 'la boucle') - 0.3, 'evaporator', "Retour à l'évaporateur", True),
           LB(P(7) + 0.2, word_t(7, 1, 'il arrête') - 0.3, 'thermostat', None, True),
           LB(word_t(7, 2, 'relance') + 0.2, P(8) - 0.3, 'compressor', "Compresseur relancé", True),
           LB(Sx(8, 2), Sx(8, 3) - 0.1, 'evaporator', "Givre", True),
           LB(word_t(8, 3, 'trou') - 0.1, word_t(8, 3, 'un bac') - 0.2, 'hole', None, True),
           LB(word_t(8, 3, 'un bac'), P(9) - 0.3, 'tray', None, True),
           LB(T_DOOR_O, Sx(9, 2) - 0.1, 'door', "Porte ouverte", True),
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
