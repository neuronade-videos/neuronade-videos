"""3D wireframe geometry of a pellet stove (units: mm, y up, z toward viewer, front glass at z=+250, floor at y=-500)."""
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
FLOOR_Y = -500
BODY = ((-260, -480, -260), (260, 520, 250))
DOOR = ((-235, -240, 250), (125, 300, 262)); GLASS = ((-205, -210, 262), (95, 270, 262))
DISPLAY = ((150, 190, 252), (232, 280, 252)); DISPLAY_C = (191, 238, 254)
GRILLE = ((-225, 385, 252), (225, 470, 252))
FIRE = ((-205, -240, -30), (125, 300, 240))
POT = ((-115, -205, 40), (15, -125, 160)); POT_C = (-50, -165, 100)
HOPPER = ((-215, -60, -250), (215, 515, -70))
AUGER = [(-50, -40, -205), (-50, 255, -45)]          # inclined screw, bottom of hopper -> top front
AUGER_R = 26
MOTOR = [(-50, 268, -38), (-50, 318, -11)]
CHUTE = [(-50, 250, -25), (-50, -40, 75)]           # sloped duct, ends 85 mm above the burn pot : the fire cannot climb back
DROP_TOP = (-50, -40, 75); DROP_BOT = (-50, -128, 98)
IGNITER = [(-50, -165, -110), (-50, -165, 54)]; IGN_TIP = (-50, -165, 50)
INTAKE = [(-50, -165, -420), (-50, -165, -262), (-50, -165, -110)]   # outdoor air -> igniter tube -> burn pot
EXCH_X = [-170, -110, -50, 10, 70]; EXCH_Y = (300, 372); EXCH_Z = (0, 210)
PLENUM = ((-205, 372, -30), (210, 395, 120))
FUME_DOWN = [(185, 380, -60), (185, -320, -60), (185, -360, -140)]
EXTRACTOR_C = (170, -380, -170); EXTRACTOR_R = 72
FLUE = [(170, -380, -205), (170, -380, -420), (170, 900, -420)]
PRESSO = ((205, -280, -235), (245, -230, -195)); PRESSO_TUBE = [(225, -255, -195), (225, -300, -150), (185, -330, -150)]
CONV_FAN = [(-200, -360, 150), (110, -360, 150)]; CONV_R = 48     # tangential room-air fan, under the fire chamber
AIR_IN = [(0, -470, -262), (0, -455, -120), (-40, -380, 60), (-150, -360, 150)]
AIR_UP = [(-150, -360, 150), (-235, -300, 200), (-235, 330, 200), (-180, 335, 45), (60, 335, 45), (110, 345, 170), (110, 428, 215), (110, 428, 340)]
PROBE = [(-235, -440, -262), (-235, -470, -320), (-235, -495, -360)]
BOARD = ((-245, -440, -258), (-150, -320, -240))
WALL_Z = -700

def build():
    POLYS.clear()
    (x0, y0, z0), (x1, y1, z1) = BODY
    box('body', BODY[0], BODY[1], 1.2, 0.85)
    for k in range(1, 5):
        y = y0 + (y1 - y0) * k / 5; add([(x0, y, z0), (x0, y, z1)], 'body', 0.6, 0.22); add([(x1, y, z0), (x1, y, z1)], 'body', 0.6, 0.22)
    for x in (x0 + 30, x1 - 30):
        for z in (z0 + 30, z1 - 30): add([(x, FLOOR_Y, z), (x, y0, z)], 'body', 1.0, 0.6)
    # door + glass + handle
    box('door', DOOR[0], DOOR[1], 1.2, 0.85)
    (gx0, gy0, gz), (gx1, gy1, _) = GLASS
    add([(gx0, gy0, gz), (gx1, gy0, gz), (gx1, gy1, gz), (gx0, gy1, gz), (gx0, gy0, gz)], 'door', 1.0, 0.7)
    add([(110, -60, 266), (110, 140, 266)], 'door', 2.4, 1.0)
    # display + buttons
    (dx0, dy0, dz), (dx1, dy1, _) = DISPLAY
    add([(dx0, dy0, dz), (dx1, dy0, dz), (dx1, dy1, dz), (dx0, dy1, dz), (dx0, dy0, dz)], 'display', 1.3, 1.0)
    for k in range(3): add(circle((dx0 + 15 + k * 26, dy0 - 28, dz), (0, 0, 1), 8, 12), 'display', 0.9, 0.8)
    # top hot-air grille
    (rx0, ry0, rz), (rx1, ry1, _) = GRILLE
    add([(rx0, ry0, rz), (rx1, ry0, rz), (rx1, ry1, rz), (rx0, ry1, rz), (rx0, ry0, rz)], 'grille', 1.0, 0.8)
    for y in np.linspace(ry0 + 12, ry1 - 12, 5): add([(rx0 + 10, y, rz), (rx1 - 10, y, rz)], 'grille', 0.7, 0.55)
    # fire chamber, burn pot with air holes
    box('fire', FIRE[0], FIRE[1], 0.9, 0.5)
    box('pot', POT[0], POT[1], 1.3, 0.95)
    for x in np.linspace(POT[0][0] + 15, POT[1][0] - 15, 5):
        for z in np.linspace(POT[0][2] + 15, POT[1][2] - 15, 4): add(circle((x, POT[0][1] + 1, z), (0, 1, 0), 4, 8), 'pot', 0.7, 0.6)
    # hopper (with funnel bottom), auger in its tube, motor, chute
    (hx0, hy0, hz0), (hx1, hy1, hz1) = HOPPER
    add([(hx0, hy1, hz0), (hx1, hy1, hz0), (hx1, hy1, hz1), (hx0, hy1, hz1), (hx0, hy1, hz0)], 'hopper', 1.2, 0.9)
    for (x, z) in ((hx0, hz0), (hx1, hz0), (hx1, hz1), (hx0, hz1)): add([(x, hy1, z), (x, 120, z)], 'hopper', 1.1, 0.85)
    for (x, z) in ((hx0, hz0), (hx1, hz0), (hx1, hz1), (hx0, hz1)): add([(x, 120, z), (-50 + (x + 50) * 0.18, hy0, -160 + (z + 160) * 0.25)], 'hopper', 1.0, 0.75)
    add([(hx0, 120, hz0), (hx1, 120, hz0), (hx1, 120, hz1), (hx0, 120, hz1), (hx0, 120, hz0)], 'hopper', 0.8, 0.5)
    add([(hx0 - 5, hy1 + 5, hz0), (hx1 + 5, hy1 + 5, hz0), (hx1 + 5, hy1 + 5, hz1 + 20), (hx0 - 5, hy1 + 5, hz1 + 20), (hx0 - 5, hy1 + 5, hz0)], 'hopper', 1.0, 0.7)  # lid
    cylinder('auger', AUGER[0], AUGER[1], AUGER_R + 8, rings=6, longs=6, n=20, w=0.8, a=0.55)
    a0, a1 = np.array(AUGER[0], float), np.array(AUGER[1], float); ax = a1 - a0; u, v = perp(ax)
    helix = [a0 + ax * (k / 240) + AUGER_R * (math.cos(k * 0.42) * u + math.sin(k * 0.42) * v) for k in range(241)]
    add(helix, 'auger', 1.2, 0.95); add([a0, a1], 'auger', 1.4, 0.9)
    cylinder('motor', MOTOR[0], MOTOR[1], 36, rings=3, longs=8, n=24, w=1.1, a=0.9)
    c0, c1 = np.array(CHUTE[0], float), np.array(CHUTE[1], float)
    for dx in (-30, 30):
        add([c0 + (dx, 0, 0), c1 + (dx, 0, 0)], 'chute', 1.1, 0.85)
    add([c0 + (-30, 0, 0), c0 + (30, 0, 0)], 'chute', 1.0, 0.8); add([c1 + (-30, 0, 0), c1 + (30, 0, 0)], 'chute', 1.0, 0.8)
    for k in range(1, 6): q = c0 + (c1 - c0) * k / 6; add([q + (-30, 0, 0), q + (30, 0, 0)], 'chute', 0.6, 0.4)
    # igniter in its air tube, outdoor-air intake
    tube('igniter', IGNITER, 14, step=50, longs=4, w=0.9, a=0.85)
    tube('intake', INTAKE[:2], 30, step=60, longs=4, w=0.7, a=0.6)
    # heat exchanger tubes (fumes inside), plenum, descending fume duct, extractor, flue
    for x in EXCH_X:
        for z in (0, 90): cylinder('exchanger', (x, EXCH_Y[0], z), (x, EXCH_Y[1], z), 16, rings=3, longs=4, n=14, w=0.9, a=0.8)
    box('exchanger', PLENUM[0], PLENUM[1], 0.8, 0.5)
    tube('fume_duct', FUME_DOWN, 30, step=80, longs=4, w=0.8, a=0.6)
    cylinder('extractor', (EXTRACTOR_C[0], EXTRACTOR_C[1], EXTRACTOR_C[2] - 30), (EXTRACTOR_C[0], EXTRACTOR_C[1], EXTRACTOR_C[2] + 30), EXTRACTOR_R, rings=3, longs=10, n=30, w=1.1, a=0.9)
    tube('flue', FLUE, 40, step=90, longs=4, w=0.9, a=0.7)
    box('pressostat', PRESSO[0], PRESSO[1], 1.1, 0.9); add(PRESSO_TUBE, 'pressostat', 0.9, 0.7)
    # tangential room-air fan + its ducts
    cylinder('conv_fan', CONV_FAN[0], CONV_FAN[1], CONV_R, rings=4, longs=12, n=24, w=1.0, a=0.85)
    add([(-235, -300, 175), (-235, 330, 175), (-235, 330, 235), (-235, -300, 235), (-235, -300, 175)], 'air_duct', 0.8, 0.45)
    add([(0, -480, -258), (0, -430, -258)], 'air_duct', 0.8, 0.4)
    for x in np.linspace(-120, 120, 7): add([(x, -470, -262), (x, -420, -262)], 'air_duct', 0.7, 0.5)
    # electronics, room probe
    box('board', BOARD[0], BOARD[1], 1.0, 0.85)
    add(PROBE, 'probe', 0.9, 0.7); add(circle(PROBE[-1], (0, 1, 0), 10, 12), 'probe', 1.2, 0.9)
    # room : floor + wall
    for k in range(-5, 6):
        add([(k * 200, FLOOR_Y, WALL_Z), (k * 200, FLOOR_Y, 1000)], 'env', 0.6, 0.18); add([(-1000, FLOOR_Y, WALL_Z + (k + 5) * 170), (1000, FLOOR_Y, WALL_Z + (k + 5) * 170)], 'env', 0.6, 0.18)
    for k in range(0, 8):
        add([(-1000, FLOOR_Y + k * 220, WALL_Z), (1000, FLOOR_Y + k * 220, WALL_Z)], 'env', 0.5, 0.12)
    return POLYS

ANCH = {
    'hopper': ((0, 330, -160), "Réservoir"),
    'pellets': ((60, 200, -150), "Granulés"),
    'auger': ((-50, 110, -125), "Vis sans fin"),
    'motor': ((-50, 293, -24), "Moteur"),
    'chute': ((-50, 105, 25), "Goulotte"),
    'pot': ((POT_C[0], POT[1][1], POT_C[2]), "Creuset"),
    'drop': ((-50, -84, 86), "Vide de sécurité"),
    'igniter': ((-50, -165, -40), "Bougie d'allumage"),
    'intake': ((-50, -165, -330), "Air extérieur"),
    'extractor': ((EXTRACTOR_C[0], EXTRACTOR_C[1], EXTRACTOR_C[2]), "Extracteur de fumées"),
    'flue': ((170, 200, -420), "Conduit"),
    'pressostat': ((225, -255, -215), "Pressostat"),
    'exchanger': ((-50, 336, 100), "Échangeur"),
    'conv_fan': ((-45, -360, 150), "Ventilateur d'air chaud"),
    'grille': ((0, 428, 255), "Sortie d'air chaud"),
    'probe': ((-235, -495, -360), "Sonde d'ambiance"),
    'display': (DISPLAY_C, "Écran"),
    'board': ((-197, -380, -240), "Carte électronique"),
    'fire': ((-40, 60, 100), "Foyer"),
    'fans': ((20, -370, -10), "Deux ventilateurs"),
}
