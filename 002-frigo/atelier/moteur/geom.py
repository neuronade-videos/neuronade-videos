"""3D wireframe geometry of a domestic one-door fridge with static cold (units: mm, y up, z toward viewer, front at z=+300)."""
import math
import numpy as np

POLYS = []      # dict(pts, group, w, a, kind)
def add(pts, group, w=1.0, a=1.0, kind='line'):
    POLYS.append(dict(pts=np.asarray(pts, float), group=group, w=w, a=a, kind=kind))
def norm(v):
    v = np.asarray(v, float); n = np.linalg.norm(v); return v / n if n else v
def perp(d):
    d = norm(d); ref = np.array([0, 1, 0.]) if abs(d[1]) < 0.9 else np.array([1, 0, 0.])
    u = norm(np.cross(d, ref)); v = np.cross(d, u); return u, v
def circle(c, axis, r, n=24):
    u, v = perp(axis); c = np.asarray(c, float); a = np.linspace(0, 2 * math.pi, n + 1)
    return c + r * (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v)
def box(group, mn, mx, w=1.0, a=1.0, grid=0):
    x0, y0, z0 = mn; x1, y1, z1 = mx
    add([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z0)], group, w, a)
    add([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1),(x0,y0,z1)], group, w, a)
    for x, y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)): add([(x,y,z0),(x,y,z1)], group, w, a)
    if grid:
        for k in range(1, grid):
            y = y0 + (y1 - y0) * k / grid
            add([(x0,y,z1),(x1,y,z1)], group, w * 0.6, a * 0.3); add([(x0,y,z0),(x0,y,z1)], group, w * 0.6, a * 0.3)
def cylinder(group, c0, c1, r, rings=4, longs=8, n=28, w=1.0, a=1.0):
    c0 = np.asarray(c0, float); c1 = np.asarray(c1, float); ax = c1 - c0
    for k in range(rings): add(circle(c0 + ax * k / max(1, rings - 1), ax, r, n), group, w, a)
    u, v = perp(ax)
    for k in range(longs):
        t = 2 * math.pi * k / longs; off = r * (math.cos(t) * u + math.sin(t) * v); add([c0 + off, c1 + off], group, w * 0.8, a * 0.8)
def tube(group, path, r, step=40, longs=4, w=0.8, a=0.7):
    path = np.asarray(path, float)
    for i in range(len(path) - 1):
        p0, p1 = path[i], path[i + 1]; d = p1 - p0; L = np.linalg.norm(d)
        if L < 1e-6: continue
        u, v = perp(d)
        for k in range(longs):
            t = 2 * math.pi * k / longs + math.pi / 4; off = r * (math.cos(t) * u + math.sin(t) * v); add([p0 + off, p1 + off], group, w, a * 0.8)
        n = max(1, int(L // step))
        for j in range(n + 1): add(circle(p0 + d * j / n, d, r, 10), group, w * 0.6, a * 0.5)

# ---------------- layout ----------------
CAB = ((-300, -700, -300), (300, 700, 300))
LIN = ((-262, -470, -258), (262, 662, 262))
DOOR_Z = (300, 345); HINGE_X = 300
SHELVES = [-300, -40, 220, 460]
POTS = [(-185, -40, 70), (-110, -40, 70), (-35, -40, 70), (-148, -40, -10)]      # yaourts (x, shelf y, z)
POT_R, POT_H = 32, 70
BOTTLE = ((165, -300, 40), 42, 230)
EVAP_Z = -250; EVAP_X = (-215, 215); EVAP_Y = (270, 600)
GUTTER_Y = 230; HOLE = (0, 214, -256)
COMP_C = (110, -612, -225); COMP_R = 74; COMP_Y = (-690, -545)
TRAY = ((35, -541, -292), (205, -518, -160))
COND_Z = -332; COND_X = (-240, 240); COND_Y = (-440, 640)
DRIER = ((-240, -462, -332), (-240, -528, -332)); DRIER_R = 14
THERMO = ((234, 505, 70), (258, 600, 205)); THERMO_C = (233, 553, 138)
DOOR_HANDLE = [(-268, 120, 372), (-268, 420, 372)]

# evaporator serpentine (inlet top-left, outlet bottom-right)
def _serp(x0, x1, ys, z):
    pts = []
    for k, y in enumerate(ys):
        a, b = (x0, x1) if k % 2 == 0 else (x1, x0); pts += [(a, y, z), (b, y, z)]
    return pts
EVAP_YS = list(np.linspace(EVAP_Y[1], EVAP_Y[0], 8))
EVAP_PATH = _serp(EVAP_X[0], EVAP_X[1], EVAP_YS, EVAP_Z + 6)
COND_YS = list(np.linspace(COND_Y[1], COND_Y[0], 19))
COND_PATH = _serp(COND_X[1], COND_X[0], COND_YS, COND_Z)
SUCTION = [EVAP_PATH[-1], (EVAP_X[1] + 30, EVAP_Y[0], EVAP_Z), (EVAP_X[1] + 30, EVAP_Y[0], -318), (245, -470, -318), (150, -520, -270), (COMP_C[0] - 40, COMP_Y[1] - 10, COMP_C[2] - 10)]
IN_COMP = [SUCTION[-1], (COMP_C[0], -600, COMP_C[2]), (COMP_C[0] + 40, COMP_Y[1] - 10, COMP_C[2] - 20)]
DISCHARGE = [IN_COMP[-1], (200, -540, -300), (262, -470, -334), (262, COND_Y[1] + 30, -334), (COND_X[1], COND_Y[1], COND_Z)]
TO_DRIER = [COND_PATH[-1], (COND_X[0], COND_Y[0] - 22, COND_Z), DRIER[0]]
CAPILLARY = [DRIER[1], (-240, -548, -332), (-205, -548, -316)]
for k in range(10):   # small coil of capillary (the 'detendeur')
    a = k * 1.2; CAPILLARY.append((-205 + 16 * math.cos(a), -548 + 26 * k / 9 + 8 * math.sin(a), -316 + 14 * math.sin(a)))
CAPILLARY += [(-205, -480, -316), (-205, 630, -316), (-222, 630, -286), (EVAP_X[0] - 20, EVAP_Y[1], EVAP_Z), EVAP_PATH[0]]
DRAIN = [HOLE, (0, HOLE[1], -312), (0, -480, -312), (95, -500, -250), (110, -508, -228)]
WIRE = [(246, 505, 120), (246, 420, 40), (200, 380, -230), (120, 360, -246)]    # thermostat sensor bulb on evaporator
KITCHEN_Y = -700

def build():
    POLYS.clear()
    # cabinet (outer), with a recessed machine compartment at the back-bottom
    (x0, y0, z0), (x1, y1, z1) = CAB
    add([(x0,-480,z0),(x0,y1,z0),(x1,y1,z0),(x1,-480,z0),(x0,-480,z0)], 'cabinet', 1.2, 0.9)
    add([(x0,y0,z1),(x0,y1,z1),(x1,y1,z1),(x1,y0,z1),(x0,y0,z1)], 'cabinet', 1.2, 0.9)
    for x in (x0, x1):
        add([(x,y1,z0),(x,y1,z1)], 'cabinet', 1.2, 0.9); add([(x,y0,-150),(x,y0,z1)], 'cabinet', 1.2, 0.9)
        add([(x,-480,z0),(x,-480,-150),(x,y0,-150)], 'cabinet', 1.0, 0.6); add([(x,y0,z1),(x,y1,z1)], 'cabinet', 1.0, 0.5)
        add([(x,-480,z0),(x,y1,z0)], 'cabinet', 1.0, 0.6)
    add([(x0,y0,-150),(x1,y0,-150)], 'cabinet', 1.0, 0.6); add([(x0,-480,z0),(x1,-480,z0)], 'cabinet', 1.0, 0.6)
    for k in range(1, 6):
        y = -480 + (y1 + 480) * k / 6; add([(x0, y, z0), (x0, y, z1)], 'cabinet', 0.6, 0.25); add([(x1, y, z0), (x1, y, z1)], 'cabinet', 0.6, 0.25)
    # inner liner
    box('liner', LIN[0], LIN[1], 0.8, 0.45)
    # door (closed), with handle and gasket
    box('door', (x0 - 4, y0 + 10, DOOR_Z[0]), (x1 + 4, y1, DOOR_Z[1]), 1.1, 0.75)
    add(DOOR_HANDLE, 'door', 2.4, 1.0)
    add([(x0 + 20, y0 + 30, DOOR_Z[0] - 2), (x1 - 20, y0 + 30, DOOR_Z[0] - 2), (x1 - 20, y1 - 20, DOOR_Z[0] - 2), (x0 + 20, y1 - 20, DOOR_Z[0] - 2), (x0 + 20, y0 + 30, DOOR_Z[0] - 2)], 'gasket', 0.8, 0.5)
    # shelves
    for y in SHELVES:
        add([(LIN[0][0], y, LIN[0][2]), (LIN[1][0], y, LIN[0][2]), (LIN[1][0], y, LIN[1][2] - 15), (LIN[0][0], y, LIN[1][2] - 15), (LIN[0][0], y, LIN[0][2])], 'shelf', 0.9, 0.6)
        for x in np.linspace(LIN[0][0], LIN[1][0], 7)[1:-1]: add([(x, y, LIN[0][2]), (x, y, LIN[1][2] - 15)], 'shelf', 0.4, 0.18)
    box('shelf', (LIN[0][0] + 8, -462, -240), (LIN[1][0] - 8, -330, 230), 0.8, 0.45)   # crisper drawer
    # food
    for (x, y, z) in POTS: cylinder('food', (x, y, z), (x, y + POT_H, z), POT_R, rings=3, longs=6, n=20, w=0.9, a=0.85)
    (bx, by, bz), br, bh = BOTTLE
    cylinder('food', (bx, by, bz), (bx, by + bh * 0.7, bz), br, rings=3, longs=6, n=20, w=0.9, a=0.8)
    cylinder('food', (bx, by + bh * 0.7, bz), (bx, by + bh, bz), br * 0.35, rings=2, longs=4, n=14, w=0.8, a=0.8)
    box('food', (-150, 220, -60), (-40, 268, 70), 0.9, 0.8)
    # evaporator plate + serpentine + gutter + drain hole
    add([(EVAP_X[0] - 20, EVAP_Y[0] - 25, EVAP_Z), (EVAP_X[1] + 20, EVAP_Y[0] - 25, EVAP_Z), (EVAP_X[1] + 20, EVAP_Y[1] + 25, EVAP_Z), (EVAP_X[0] - 20, EVAP_Y[1] + 25, EVAP_Z), (EVAP_X[0] - 20, EVAP_Y[0] - 25, EVAP_Z)], 'evaporator', 1.2, 0.9)
    add(EVAP_PATH, 'evaporator', 1.0, 0.7)
    add([(EVAP_X[0] - 20, GUTTER_Y + 10, -252), (0, GUTTER_Y - 4, -252), (EVAP_X[1] + 20, GUTTER_Y + 10, -252)], 'gutter', 1.4, 0.9)
    add(circle(HOLE, (0, 0, 1), 9, 16), 'gutter', 1.4, 1.0)
    tube('drain', DRAIN, 7, step=70, longs=3, w=0.7, a=0.7)
    # compressor + tray + mounts
    cylinder('compressor', (COMP_C[0], COMP_Y[0], COMP_C[2]), (COMP_C[0], COMP_Y[1] - 25, COMP_C[2]), COMP_R, rings=4, longs=10, n=32, w=1.1, a=0.9)
    for k in range(4):
        r = COMP_R * math.cos(k / 4 * math.pi / 2); y = COMP_Y[1] - 25 + 25 * math.sin(k / 4 * math.pi / 2)
        add(circle((COMP_C[0], y, COMP_C[2]), (0, 1, 0), r, 28), 'compressor', 1.0, 0.85)
    box('compressor', (COMP_C[0] - 95, KITCHEN_Y, COMP_C[2] - 70), (COMP_C[0] + 95, COMP_Y[0], COMP_C[2] + 70), 0.7, 0.45)
    box('tray', TRAY[0], TRAY[1], 1.1, 0.9)
    # condenser (wire-and-tube grille on the back) + drier
    add(COND_PATH, 'condenser', 1.0, 0.75)
    for x in np.linspace(COND_X[0] + 12, COND_X[1] - 12, 12): add([(x, COND_Y[0] - 6, COND_Z - 4), (x, COND_Y[1] + 6, COND_Z - 4)], 'condenser', 0.5, 0.35)
    cylinder('drier', DRIER[0], DRIER[1], DRIER_R, rings=3, longs=6, n=16, w=1.0, a=0.9)
    # refrigerant lines
    tube('pipe_suction', SUCTION, 5, step=60, longs=3, w=0.7, a=0.6)
    tube('pipe_discharge', DISCHARGE, 4, step=60, longs=3, w=0.7, a=0.6)
    add(CAPILLARY, 'capillary', 0.9, 0.8)
    add(TO_DRIER, 'condenser', 1.0, 0.75)
    # thermostat (+ sensor wire)
    box('thermostat', THERMO[0], THERMO[1], 1.1, 0.95)
    add(WIRE, 'wire', 0.7, 0.5)
    # kitchen floor + wall (environment)
    for k in range(-5, 6):
        add([(k * 200, KITCHEN_Y, -520), (k * 200, KITCHEN_Y, 900)], 'env', 0.6, 0.18); add([(-1000, KITCHEN_Y, -520 + (k + 5) * 142), (1000, KITCHEN_Y, -520 + (k + 5) * 142)], 'env', 0.6, 0.18)
    for k in range(0, 8):
        add([(-1000, KITCHEN_Y + k * 220, -520), (1000, KITCHEN_Y + k * 220, -520)], 'env', 0.5, 0.12)
    return POLYS

ANCH = {
    'compressor': ((COMP_C[0], -600, COMP_C[2] + 60), "Compresseur"),
    'condenser': ((0, 150, COND_Z), "Condenseur"),
    'capillary': ((-205, -520, -316), "Détendeur (tube capillaire)"),
    'evaporator': ((0, 440, EVAP_Z), "Évaporateur"),
    'thermostat': ((THERMO_C[0], THERMO_C[1], THERMO_C[2]), "Thermostat"),
    'tray': ((120, -518, -226), "Bac d'évaporation"),
    'hole': (HOLE, "Trou d'évacuation"),
    'drier': ((-240, -495, -332), "Filtre"),
    'door': ((-268, 270, 372), "Porte"),
    'food': ((-110, 0, 70), "Tes yaourts"),
    'fluid': ((-205, 150, -316), "Fluide (isobutane)"),
    'suction': ((245, -100, -318), "Gaz froid"),
    'discharge': ((262, 150, -334), "Gaz brûlant"),
    'gutter': ((-110, GUTTER_Y + 5, -252), "Gouttière"),
}
