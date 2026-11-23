
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
