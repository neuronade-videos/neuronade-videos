"""3D wireframe geometry of a wall-hung condensing combi gas boiler (units: mm, y up, z toward viewer)."""
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
    u, v = perp(axis); c = np.asarray(c, float)
    a = np.linspace(0, 2 * math.pi, n + 1)
    return c + r * (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v)

def box(group, mn, mx, w=1.0, a=1.0, grid=0):
    x0, y0, z0 = mn; x1, y1, z1 = mx
    add([(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z0)], group, w, a)
    add([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1),(x0,y0,z1)], group, w, a)
    for x, y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)): add([(x,y,z0),(x,y,z1)], group, w, a)
    if grid:
        for k in range(1, grid):
            y = y0 + (y1 - y0) * k / grid
            add([(x0,y,z1),(x1,y,z1)], group, w * 0.6, a * 0.35)
            add([(x0,y,z0),(x0,y,z1)], group, w * 0.6, a * 0.35)

def cylinder(group, c0, c1, r, rings=4, longs=8, n=28, w=1.0, a=1.0):
    c0 = np.asarray(c0, float); c1 = np.asarray(c1, float); ax = c1 - c0
    for k in range(rings):
        add(circle(c0 + ax * k / max(1, rings - 1), ax, r, n), group, w, a)
    u, v = perp(ax)
    for k in range(longs):
        t = 2 * math.pi * k / longs; off = r * (math.cos(t) * u + math.sin(t) * v)
        add([c0 + off, c1 + off], group, w * 0.8, a * 0.8)

def tube(group, path, r, step=34, longs=4, w=0.8, a=0.75, core=None):
    path = np.asarray(path, float)
    for i in range(len(path) - 1):
        p0, p1 = path[i], path[i + 1]; d = p1 - p0; L = np.linalg.norm(d)
        if L < 1e-6: continue
        u, v = perp(d)
        for k in range(longs):
            t = 2 * math.pi * k / longs + math.pi / 4; off = r * (math.cos(t) * u + math.sin(t) * v)
            add([p0 + off, p1 + off], group, w, a * 0.8)
        n = max(1, int(L // step))
        for j in range(n + 1):
            add(circle(p0 + d * j / n, d, r, 12), group, w * 0.7, a * 0.55)
    if core: add(path, core, 2.2, 1.0, kind='core')

def helix(c, r, y0, y1, turns, a0, n_per_turn=48):
    N = int(turns * n_per_turn) + 1; u = np.linspace(0, 1, N)
    ang = a0 + 2 * math.pi * turns * u
    return np.stack([c[0] + r * np.cos(ang), y0 + (y1 - y0) * u, c[2] + r * np.sin(ang)], 1)

# ---------------- layout ----------------
CAS = ((-220, -380, -170), (220, 380, 170))
EXC_C = np.array([0, 0, 10.]); EXC_R = 128; EXC_Y = (-10, 275)
COIL_R = 98; COIL_Y = (15, 245); COIL_T = 7.5
A0 = math.atan2(22, 95.5)
BURN_R = 34; BURN_Y = (125, 250)
FAN_C = np.array([150, 318, 60.]); FAN_R = 44
VENT_X, VENT_Z = 150, 60
FLUE_BASE = np.array([0, 380, -50.]); FLUE_TOP_Y = 520; FLUE_END_X = 430; FLUE_RO, FLUE_RI = 58, 38
THERMO_C = np.array([-780, 250, -150.])
TAP_C = np.array([-780, -150, -60.])
RAD = ((560, -560, -150), (1060, -170, -100))

COIL = helix(EXC_C, COIL_R, COIL_Y[0], COIL_Y[1], COIL_T, A0)
COIL_IN = COIL[0]; COIL_OUT = COIL[-1]

# heating water paths
RET_TO_PUMP = [(1060,-540,-125),(1110,-540,-125),(1110,-620,-125),(160,-620,-125),(160,-470,-110),(160,-430,40),(160,-290,40),(130,-290,40),(130,-275,40)]
PUMP_TO_COIL = [(130,-195,40),(130,15,40),tuple(COIL_IN)]
COIL_TO_VALVE = [tuple(COIL_OUT),(-170,245,20),(-170,-225,20),(-150,-240,40)]
VALVE_TO_DEP = [(-150,-270,40),(-160,-300,40),(-160,-430,40),(-160,-470,-120),(500,-470,-120),(500,-190,-120),(560,-190,-125)]
RAD_PATH = [(560,-190,-125),(1035,-190,-125),(1035,-540,-125),(1060,-540,-125)]
VALVE_TO_PHX = [(-150,-240,40),(-125,-240,40),(-125,-165,40),(-95,-165,40)]
PHX_PRIM = [(-95,-165,40),(-85,-165,40),(-85,-255,40),(-65,-255,40),(-65,-165,40),(-45,-165,40),(-45,-255,40),(-25,-255,40),(-25,-165,40),(-5,-165,40),(-5,-260,40),(5,-260,40)]
PHX_TO_PUMP = [(5,-260,40),(60,-260,40),(60,-290,40),(130,-290,40),(130,-275,40)]
# domestic hot water
EF_PATH = [(80,-700,40),(80,-430,40),(80,-320,25),(-5,-320,25),(-5,-275,25)]
PHX_SEC = [(-5,-275,25),(-15,-275,25),(-15,-150,25),(-35,-150,25),(-35,-270,25),(-55,-270,25),(-55,-150,25),(-75,-150,25),(-75,-270,25),(-85,-275,25)]
ECS_PATH = [(-85,-275,25),(-85,-320,25),(-80,-430,40),(-80,-500,-120),(-780,-500,-120),(-780,-150,-160),(-780,-150,-60),(-780,-195,-60)]
# gas
GAS_PATH = [(0,-700,40),(0,-430,40),(0,-395,75),(70,-395,75),(70,-180,60)]
GAS_PATH2 = [(70,-120,45),(70,-100,45),(195,-100,45),(195,205,55),(164,205,60)]
# air & mixture
VENT_PATH = [(VENT_X,165,VENT_Z),(VENT_X,272,VENT_Z)]
DUCT_PATH = [(106,318,60),(30,318,40),(0,318,10),(0,278,10)]
FLUE_AX = [(FLUE_END_X, FLUE_TOP_Y, -50), (60, FLUE_TOP_Y, -50), (0, FLUE_TOP_Y - 60, -50), tuple(FLUE_BASE)]
AIR_IN_CASING = [tuple(FLUE_BASE + (40, -10, 30)), (120, 330, 120), (205, 250, 120), (205, 150, 90), (VENT_X, 150, VENT_Z), (VENT_X, 272, VENT_Z), (150, 318, 60)]
FUME_DUCT = [(0,-28,-40),(0,-28,-140),(0,330,-140),(0,362,-50),tuple(FLUE_BASE)]
# condensate
SIPHON_IN = [(-50,-35,-60),(-195,-35,-70),(-195,-120,-70)]
SIPHON_OUT = [(-195,-230,-70),(-195,-600,-70)]
DRAIN_END = (-195, -600, -70); FUNNEL_Y = -640
# thermostat wire
WIRE = [tuple(THERMO_C + (0, 0, -15)), (-260, 250, -165), (-260, -345, -165), (-260, -345, 140), (-180, -345, 140)]

ANCH = {
 'burner': ((0, 190, 45), "Brûleur"), 'exchanger': ((-112, 120, 62), "Échangeur"),
 'fan': ((150, 318, 84), "Ventilateur"), 'gasvalve': ((70, -150, 72), "Vanne gaz"),
 'pump': ((130, -235, 86), "Circulateur"), 'board': ((-60, -345, 166), "Carte électronique"),
 'flue': ((300, FLUE_TOP_Y + 58, -50), "Ventouse"), 'vessel': ((110, -150, -128), "Vase d'expansion"),
 'phx': ((-45, -150, 62), "Échangeur à plaques"), 'valve3': ((-150, -255, 96), "Vanne 3 voies"),
 'siphon': ((-195, -175, -44), "Siphon"), 'gauge': ((120, -343, 172), "Manomètre"),
 'ignition': ((-45, 172, 40), "Électrode d'allumage"), 'ionisation': ((45, 172, 40), "Sonde d'ionisation"),
 'thermostat': ((-780, 310, -150), "Thermostat"), 'radiator': ((810, -170, -100), "Radiateur"),
 'flowmeter': ((80, -360, 50), "Débitmètre"), 'safety': ((205, -320, 60), "Soupape 3 bar"),
 'venturi': ((150, 190, 76), "Venturi (mélange)"), 'tap': ((-780, -110, -60), "Robinet"),
 'limiter': ((-170, 190, 36), "Limiteur de surchauffe"),
}

def build():
    POLYS.clear()
    # casing + back plate
    box('casing', CAS[0], CAS[1], 1.0, 0.45, grid=6)
    (x0, y0, z0), (x1, y1, z1) = CAS
    for k in range(1, 8):
        x = x0 + (x1 - x0) * k / 8
        add([(x, y0, z0), (x, y1, z0)], 'casing', 0.6, 0.2)
    # front control strip
    box('board', (-180, -372, 110), (180, -318, 165), 1.0, 0.8)
    add([(-60,-355,170),(40,-355,170),(40,-330,170),(-60,-330,170),(-60,-355,170)], 'board', 1.2, 1.0)
    for k in range(4): add(circle((-140 + k * 22, -343, 170), (0, 0, 1), 6, 10), 'board', 0.8, 0.8)
    add(circle((120, -343, 171), (0, 0, 1), 16, 24), 'gauge', 1.2, 1.0)
    # heat exchanger shell
    cylinder('exchanger', (0, EXC_Y[0], 10), (0, EXC_Y[1], 10), EXC_R, rings=6, longs=16, w=1.0, a=0.55)
    add(circle((0, EXC_Y[1] + 6, 10), (0, 1, 0), 60, 28), 'exchanger', 1.0, 0.8)
    # collector dish under exchanger
    for k, (yy, rr) in enumerate(((-10, 128), (-26, 100), (-36, 60))):
        add(circle((0, yy, 10), (0, 1, 0), rr, 28), 'collector', 0.9, 0.6)
    # coil edges (core drawn dynamically)
    for off in (-11, 11):
        add(helix(EXC_C, COIL_R + off, COIL_Y[0], COIL_Y[1], COIL_T, A0), 'coil', 0.9, 0.55)
    # burner
    cylinder('burner', (0, BURN_Y[0], 10), (0, BURN_Y[1], 10), BURN_R, rings=7, longs=12, w=1.0, a=0.9)
    add(circle((0, BURN_Y[0], 10), (0, 1, 0), 20, 16), 'burner', 1.0, 0.9)
    # electrodes
    for gx, grp in ((-45, 'ignition'), (45, 'ionisation')):
        add([(gx, EXC_Y[1] + 6, 40), (gx, 165, 40), (gx * 0.82, 158, 34)], grp, 1.6, 1.0)
        add(circle((gx, EXC_Y[1] + 10, 40), (0, 1, 0), 8, 12), grp, 1.0, 1.0)
    # fan + venturi + duct
    cylinder('fan', FAN_C + (0, 0, -23), FAN_C + (0, 0, 23), FAN_R, rings=3, longs=12, w=1.0, a=0.9)
    add(circle(FAN_C + (0, 0, 23), (0, 0, 1), 12, 14), 'fan', 1.0, 0.9)
    tube('venturi', VENT_PATH, 15, step=22, longs=6, w=1.0, a=0.9)
    add(circle((VENT_X, 165, VENT_Z), (0, 1, 0), 24, 20), 'venturi', 1.0, 0.9)
    tube('duct', DUCT_PATH, 16, step=26, longs=4, w=0.9, a=0.7)
    # flue (concentric)
    fl = np.array(FLUE_AX, float)
    for i in range(len(fl) - 1):
        p0, p1 = fl[i], fl[i + 1]; d = p1 - p0; L = np.linalg.norm(d); n = max(1, int(L // 40))
        for j in range(n + 1):
            add(circle(p0 + d * j / n, d, FLUE_RO, 26), 'flue', 0.9, 0.7)
            if j % 2 == 0: add(circle(p0 + d * j / n, d, FLUE_RI, 20), 'flue_in', 0.8, 0.6)
        u, v = perp(d)
        for k in range(10):
            t = 2 * math.pi * k / 10; o = math.cos(t) * u + math.sin(t) * v
            add([p0 + FLUE_RO * o, p1 + FLUE_RO * o], 'flue', 0.8, 0.6)
            if k % 2 == 0: add([p0 + FLUE_RI * o, p1 + FLUE_RI * o], 'flue_in', 0.7, 0.55)
    add(circle((FLUE_END_X + 10, FLUE_TOP_Y, -50), (1, 0, 0), FLUE_RO + 8, 26), 'flue', 1.2, 0.9)
    tube('fumeduct', FUME_DUCT, 30, step=40, longs=4, w=0.8, a=0.5)
    # expansion vessel
    vc = np.array([0, -185, -128.])
    for dz, rr in ((-22, 130), (-10, 136), (10, 136), (22, 130)): add(circle(vc + (0, 0, dz), (0, 0, 1), rr, 40), 'vessel', 1.0, 0.75)
    add(circle(vc + (0, 0, 24), (0, 0, 1), 14, 12), 'vessel', 1.0, 0.8)
    # hydraulic block
    cylinder('pump', (130, -235, 15), (130, -235, 85), 40, rings=4, longs=12)
    add(circle((130, -235, 8), (0, 0, 1), 54, 30), 'pump', 1.0, 0.9)
    box('valve3', (-175, -275, 20), (-125, -235, 60), 1.0, 0.9)
    cylinder('valve3', (-150, -255, 60), (-150, -255, 96), 22, rings=3, longs=8)
    box('phx', (-95, -275, 20), (5, -145, 60), 1.1, 0.95)
    for k in range(1, 10):
        x = -95 + 10 * k; add([(x, -275, 60), (x, -145, 60), (x, -145, 20)], 'phx', 0.7, 0.7)
    box('gasvalve', (35, -180, 20), (105, -120, 70), 1.1, 0.95)
    cylinder('gasvalve', (70, -120, 45), (70, -88, 45), 16, rings=3, longs=8)
    cylinder('flowmeter', (80, -375, 25), (80, -345, 25), 14, rings=3, longs=8)
    cylinder('safety', (205, -300, 60), (205, -340, 60), 12, rings=3, longs=6)
    add([(160, -310, 40), (205, -310, 60)], 'safety', 1.0, 0.9)
    box('limiter', (-182, 180, 20), (-158, 205, 36), 1.0, 0.9)
    # siphon pot
    cylinder('siphon', (-195, -230, -70), (-195, -120, -70), 26, rings=5, longs=10)
    tube('siphon', SIPHON_IN, 9, step=30, longs=3, w=0.8, a=0.7)
    tube('siphon', SIPHON_OUT, 9, step=40, longs=3, w=0.8, a=0.6)
    for yy, rr in ((-632, 38), (-645, 28), (-658, 16), (-668, 10)): add(circle((-195, yy, -70), (0, 1, 0), rr, 24), 'drain', 1.0, 0.9)
    for k in range(8):
        t = 2 * math.pi * k / 8; add([(-195 + 38 * math.cos(t), -632, -70 + 38 * math.sin(t)), (-195 + 10 * math.cos(t), -668, -70 + 10 * math.sin(t))], 'drain', 0.8, 0.8)
    tube('drain', [(-195, -668, -70), (-195, -700, -70)], 9, step=20, longs=3, w=0.8, a=0.7)
    # manometer dial ticks (0..4 bar over 270 deg)
    gc = np.array([120, -343, 171.])
    for k in range(9):
        a = math.radians(225 - 270 * k / 8); r0 = 12.5 if k % 2 == 0 else 13.5
        add([gc + (r0 * math.cos(a), r0 * math.sin(a), 0), gc + (15 * math.cos(a), 15 * math.sin(a), 0)], 'gauge', 1.0, 1.0)
    # bottom connection stubs
    for x in (-160, -80, 0, 80, 160): add(circle((x, -380, 40), (0, 1, 0), 15, 14), 'casing', 1.0, 0.8)
    # water / gas pipes (tubes; cores dynamic)
    for name, p, r in (('heat', RET_TO_PUMP, 12), ('heat', PUMP_TO_COIL, 12), ('heat', COIL_TO_VALVE, 12),
                       ('heat', VALVE_TO_DEP, 12), ('dhwp', VALVE_TO_PHX, 9), ('dhwp', PHX_TO_PUMP, 9),
                       ('ef', EF_PATH, 9), ('ecs', ECS_PATH, 9), ('gas', GAS_PATH, 9), ('gas', GAS_PATH2, 9)):
        tube('pipe_' + name, p, r, step=44, longs=4, w=0.75, a=0.55)
    # radiator
    (rx0, ry0, rz0), (rx1, ry1, rz1) = RAD
    ncol = 10
    for k in range(ncol):
        xc = rx0 + 25 + (rx1 - rx0 - 50) * k / (ncol - 1)
        for zz in (rz0, rz1):
            add([(xc - 18, ry0 + 20, zz), (xc - 18, ry1 - 20, zz), (xc, ry1, zz), (xc + 18, ry1 - 20, zz), (xc + 18, ry0 + 20, zz), (xc, ry0, zz), (xc - 18, ry0 + 20, zz)], 'radiator', 0.9, 0.7)
    for yy in (-190, -540):
        cylinder('radiator', (rx0, yy, -125), (rx1, yy, -125), 16, rings=6, longs=4, w=0.8, a=0.6)
    for k in range(3):
        y = -650 - k * 0.0
    # floor & wall hints
    for x in range(-1100, 1301, 200): add([(x, -700, -170), (x, -700, 300)], 'env', 0.6, 0.18)
    for z in range(-170, 301, 94): add([(-1100, -700, z), (1300, -700, z)], 'env', 0.6, 0.18)
    for x in range(-1100, 1301, 200): add([(x, -700, -172), (x, 700, -172)], 'env', 0.5, 0.1)
    # thermostat
    t = THERMO_C
    box('thermostat', t + (-50, -55, -20), t + (50, 55, 12), 1.2, 1.0)
    add(circle(t + (0, 5, 13), (0, 0, 1), 32, 30), 'thermostat', 1.2, 1.0)
    tube('wire', WIRE, 3, step=200, longs=2, w=0.6, a=0.4)
    # tap
    add([(-780, -150, -172), (-780, -150, -60), (-780, -195, -60)], 'tap', 2.0, 1.0)
    add(circle((-780, -150, -172), (0, 0, 1), 22, 18), 'tap', 1.0, 1.0)
    add(circle((-780, -195, -60), (0, 1, 0), 10, 12), 'tap', 1.0, 1.0)
    for k in range(3): add(circle((-780, -320 - k * 4, -40), (0, 1, 0), 120 - k * 8, 30), 'tap', 0.8, 0.6)
    return POLYS
