
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
