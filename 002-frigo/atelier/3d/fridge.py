"""Photoreal fridge in Blender, built from the same geometry as the hologram (d002/geom.py).
usage: python3 fridge.py SHOT [samples] [scale]"""
import sys, math, json, time, random, importlib.util
sys.path.insert(0, '/home/claude/b3d')
import numpy as np
import bpy, bmesh
from mathutils import Vector
import boiler as Bo
spec = importlib.util.spec_from_file_location('gf', '/home/claude/d002/geom.py'); G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
B = Bo.B; principled = Bo.principled; emission = Bo.emission

SHOTS = {  # name: (target mm, az, el, d, fov, door angle deg)
 'front': ((40, 80, 160), -26, 6, 2600, 38, 105),
 'back':  ((50, -330, -300), 160, 10, 1750, 38, 0),
 'dial':  ((233, 553, 138), -64, 4, 430, 38, 105),
}
W, H = 1080, 1920

def door_xf(p, ang):
    th = math.radians(ang); hx, hz = G.HINGE_X, G.DOOR_Z[0]; vx, vz = p[0] - hx, p[2] - hz
    return (hx + vx * math.cos(th) + vz * math.sin(th), p[1], hz - vx * math.sin(th) + vz * math.cos(th))

def build(door_ang):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene; Bo.COL = sc.collection
    M = dict(enamel=principled('enamel', (0.86, 0.88, 0.9), 0, 0.25, coat=0.6), backp=principled('backp', (0.22, 0.23, 0.24), 0.3, 0.5), liner=principled('liner', (0.93, 0.95, 0.97), 0, 0.35),
             glass=principled('glass', (0.85, 0.95, 1.0), 0, 0.02, trans=1.0, ior=1.5), black=principled('black', (0.02, 0.02, 0.022), 0.6, 0.45),
             copper=principled('copper', (0.95, 0.5, 0.3), 1, 0.3), alu=principled('alu', (0.8, 0.83, 0.86), 1, 0.25, aniso=0.5),
             frost=principled('frost', (0.95, 0.97, 1.0), 0, 0.85), pot=principled('pot', (0.97, 0.97, 0.95), 0, 0.4),
             lid=principled('lid', (0.85, 0.15, 0.2), 0.8, 0.3), lid2=principled('lid2', (0.25, 0.45, 0.9), 0.8, 0.3),
             bottle=principled('bottle', (0.2, 0.6, 0.3), 0, 0.05, trans=0.9, ior=1.5), butter=principled('butter', (0.98, 0.9, 0.4), 0, 0.5),
             floor=principled('floor', (0.12, 0.13, 0.14), 0, 0.3), wall=principled('wall', (0.07, 0.08, 0.09), 0, 0.8),
             gasket=principled('gasket', (0.7, 0.72, 0.74), 0, 0.7), water=principled('water', (0.8, 0.9, 1.0), 0, 0.02, trans=1.0, ior=1.33),
             lamp=emission('lamp', (0.85, 0.93, 1.0), 5.0), disp=emission('disp', (0.3, 1.0, 0.72), 22.0), dispbg=principled('dispbg', (0.004, 0.006, 0.008), 0, 0.6))
    (x0, y0, z0), (x1, y1, z1) = G.CAB; t = 25
    # cabinet shell (open front), recessed machine compartment at back-bottom
    Bo.box('top', (x0, y1 - t, z0), (x1, y1, z1), M['enamel']); Bo.box('bot', (x0, -480, -150), (x1, -470 + t, z1), M['enamel'])
    Bo.box('plinth', (x0, y0, -150), (x1, -480, z1 - 20), M['enamel'])
    for x in (x0, x1 - t): Bo.box('side', (x, -480, z0), (x + t, y1, z1), M['enamel']); Bo.box('sideb', (x, y0, -150), (x + t, -480, z1), M['enamel'])
    Bo.box('back', (x0, -480, z0), (x1, y1, z0 + t), M['backp'])
    Bo.box('liner_back', (G.LIN[0][0], G.LIN[0][1], G.LIN[0][2]), (G.LIN[1][0], G.LIN[1][1], G.LIN[0][2] + 4), M['liner'])
    # shelves (glass) + crisper
    for y in G.SHELVES: Bo.box('shelf', (G.LIN[0][0], y - 3, G.LIN[0][2] + 5), (G.LIN[1][0], y + 3, G.LIN[1][2] - 15), M['glass'], bevel=1)
    Bo.box('crisper', (G.LIN[0][0] + 8, -462, -240), (G.LIN[1][0] - 8, -330, 230), M['glass'], bevel=3)
    # food
    rnd = random.Random(2)
    for k, (x, y, z) in enumerate(G.POTS):
        Bo.cyl('pot', (x, y, z), (x, y + G.POT_H - 6, z), G.POT_R, M['pot']); Bo.cyl('lid', (x, y + G.POT_H - 6, z), (x, y + G.POT_H, z), G.POT_R + 2, M['lid' if k % 2 == 0 else 'lid2'])
    (bx, by, bz), br, bh = G.BOTTLE
    Bo.cyl('bottle', (bx, by + 3, bz), (bx, by + bh * 0.7, bz), br, M['bottle']); Bo.cyl('neck', (bx, by + bh * 0.7, bz), (bx, by + bh, bz), br * 0.35, M['bottle'])
    Bo.box('butter', (-150, 223, -60), (-40, 268, 70), M['butter'], bevel=4)
    # evaporator plate with frost + gutter
    Bo.box('evap', (G.EVAP_X[0] - 20, G.EVAP_Y[0] - 25, G.EVAP_Z - 4), (G.EVAP_X[1] + 20, G.EVAP_Y[1] + 25, G.EVAP_Z + 2), M['alu'], bevel=1)
    for k in range(260):
        q = (rnd.uniform(G.EVAP_X[0] - 15, G.EVAP_X[1] + 15), rnd.uniform(G.EVAP_Y[0] - 20, G.EVAP_Y[1] + 20), G.EVAP_Z + 3)
        me = bpy.data.meshes.new('fr'); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=rnd.uniform(1.5, 4.5) * 0.001); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('frost', me); o.location = B(q); o.scale = (1, 0.5, 1); o.data.materials.append(M['frost']); Bo.link(o)
    Bo.tube('gutter', [(G.EVAP_X[0] - 20, G.GUTTER_Y + 10, -250), (0, G.GUTTER_Y - 4, -250), (G.EVAP_X[1] + 20, G.GUTTER_Y + 10, -250)], 6, M['liner'])
    Bo.tube('drain', G.DRAIN, 7, M['black'])
    # thermostat with display
    Bo.box('thermo', G.THERMO[0], G.THERMO[1], M['liner'], bevel=3)
    Bo.box('dispbg', (G.THERMO[0][0] - 1.5, 530, 95), (G.THERMO[0][0] + 1, 585, 180), M['dispbg'], bevel=0.5)
    tx = Bo.text('disp', '4°C', (G.THERMO[0][0] - 2.5, 557, 138), 34, M['disp']); tx.rotation_euler = (math.radians(90), 0, math.radians(-90))
    # lamp in the ceiling
    Bo.box('lamp', (-120, G.LIN[1][1] - 6, 0), (120, G.LIN[1][1] - 2, 120), M['lamp'], bevel=1)
    # door (with gasket and handle), swung open
    dpts = [(x0 - 4, y0 + 10, G.DOOR_Z[0]), (x1 + 4, y1, G.DOOR_Z[1])]
    if door_ang > 0:
        cx = (x0 + x1) / 2; c = door_xf((cx, 0, (G.DOOR_Z[0] + G.DOOR_Z[1]) / 2), door_ang)
        o = Bo.box('door', (c[0] - 302, y0 + 10, c[2] - 22), (c[0] + 302, y1, c[2] + 22), M['enamel'])
        o.rotation_euler = (0, 0, math.radians(door_ang))
        h = [door_xf(p, door_ang) for p in G.DOOR_HANDLE]; Bo.tube('handle', h, 9, M['alu'])
        # door bins on the inner face, with bottles and jars
        def dbox(name, cc, half, mat, bevel=2):
            c = door_xf(cc, door_ang); o = Bo.box(name, (c[0] - half[0], c[1] - half[1], c[2] - half[2]), (c[0] + half[0], c[1] + half[1], c[2] + half[2]), mat, bevel=bevel)
            o.rotation_euler = (0, 0, math.radians(door_ang)); return o
        for yb in (-330, 40, 380):
            dbox('binfloor', (0, yb, 262), (250, 3, 36), M['liner'])
            dbox('binlip', (0, yb + 45, 228), (250, 48, 3), M['glass'], bevel=1)
        for k, (x, r, hgt, mat) in enumerate(((-170, 34, 250, 'bottle'), (-90, 34, 250, 'bottle'), (-5, 42, 230, 'pot'), (110, 30, 210, 'bottle'), (185, 28, 180, 'lid2'))):
            c = door_xf((x, -327, 262), door_ang); Bo.cyl('dbot', c, (c[0], c[1] + hgt, c[2]), r, M[mat])
        for k, x in enumerate((-180, -120, -60, 0, 60)):
            c = door_xf((x, 43, 262), door_ang); Bo.cyl('jar', c, (c[0], c[1] + 75, c[2]), 26, M['pot' if k % 2 else 'butter'])
    else:
        Bo.box('door', dpts[0], dpts[1], M['enamel']); Bo.tube('handle', G.DOOR_HANDLE, 9, M['alu'])
    # back: condenser grille, compressor, tray, drier, lines
    Bo.tube('cond', G.COND_PATH, 4, M['black'])
    for x in np.linspace(G.COND_X[0] + 12, G.COND_X[1] - 12, 12): Bo.tube('wire', [(x, G.COND_Y[0] - 6, G.COND_Z - 5), (x, G.COND_Y[1] + 6, G.COND_Z - 5)], 1.2, M['black'])
    cc = G.COMP_C
    Bo.cyl('comp', (cc[0], G.COMP_Y[0], cc[2]), (cc[0], G.COMP_Y[1] - 25, cc[2]), G.COMP_R, M['black'])
    me = bpy.data.meshes.new('dome'); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=G.COMP_R * 0.001); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('dome', me); o.location = B((cc[0], G.COMP_Y[1] - 25, cc[2])); o.scale = (1, 1, 0.42); o.data.materials.append(M['black']); Bo.link(o)
    for f in o.data.polygons: f.use_smooth = True
    Bo.box('tray', G.TRAY[0], G.TRAY[1], M['pot'], bevel=3)
    Bo.box('trayw', (G.TRAY[0][0] + 6, G.TRAY[0][1] + 4, G.TRAY[0][2] + 6), (G.TRAY[1][0] - 6, G.TRAY[0][1] + 9, G.TRAY[1][2] - 6), M['water'], bevel=1)
    Bo.cyl('drier', G.DRIER[0], G.DRIER[1], G.DRIER_R, M['copper'])
    Bo.tube('suction', G.SUCTION, 5, M['copper']); Bo.tube('discharge', G.DISCHARGE, 4, M['copper']); Bo.tube('capillary', G.CAPILLARY, 1.6, M['copper'])
    Bo.tube('todrier', G.TO_DRIER, 4, M['black'])
    # kitchen
    Bo.box('floor', (-2500, G.KITCHEN_Y - 20, -900), (2500, G.KITCHEN_Y, 2500), M['floor'], bevel=0)
    if door_ang > 0: Bo.box('wall', (-2500, G.KITCHEN_Y, -640), (2500, 2000, -620), M['wall'], bevel=0)
    # lights
    def area(name, loc, target, energy, size, col):
        L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.size = size; L.color = col
        o = bpy.data.objects.new(name, L); o.location = B(loc); d = B(target) - B(loc); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('-Z', 'Y'); Bo.link(o)
    area('key', (-1300, 1100, 1500), (0, 0, 0), 70, 1.2, (1.0, 0.92, 0.85))
    area('rimc', (1200, 600, -900), (0, 0, -300), 260, 0.8, (0.3, 0.85, 1.0))
    area('rimc2', (-1200, 200, -900), (0, -100, -300), 190, 0.8, (0.3, 0.75, 1.0))
    area('fill', (400, -200, 1800), (0, 0, 0), 14, 1.6, (0.8, 0.9, 1.0))
    area('warm', (250, -650, -1000), (60, -520, -260), 45, 0.6, (1.0, 0.5, 0.25))      # warm glow behind (condenser heat)
    L = bpy.data.lights.new('inside', 'POINT'); L.energy = 14; L.color = (0.75, 0.88, 1.0); L.shadow_soft_size = 0.1
    o = bpy.data.objects.new('inside', L); o.location = B((0, 560, 60)); Bo.link(o)
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.004, 0.008, 0.012, 1)
    return sc

def setup_cam(sc, shot, scale):
    T, az, el, d, fov, _ = SHOTS[shot]
    C = Bo.cam_pos(T, az, el, d)
    cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.angle = math.radians(fov); cd.shift_y = -(0.5 - 0.455)
    cd.dof.use_dof = True; cd.dof.focus_distance = d * 0.001; cd.dof.aperture_fstop = 2.8 if d < 1000 else 5.6
    o = bpy.data.objects.new('cam', cd); o.location = B(C); dv = B(T) - B(C); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = dv.to_track_quat('-Z', 'Y')
    Bo.link(o); sc.camera = o; sc.render.resolution_x, sc.render.resolution_y = int(W * scale), int(H * scale)
    return o

ANCHORS = {'pots': (-110, 0, 70), 'plate': (0, 430, -248), 'door': (-268, 270, 372), 'compressor': (110, -600, -225), 'condenser': (0, 150, -332),
           'tray': (120, -518, -226), 'thermostat': (233, 553, 138), 'back': (0, 300, -332), 'cond_low': (0, -300, -332)}
if __name__ == '__main__':
    shot = sys.argv[1]; samples = int(sys.argv[2]) if len(sys.argv) > 2 else 28; scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
    sc = build(SHOTS[shot][5]); cam = setup_cam(sc, shot, scale)
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.glossy_bounces = 4; sc.cycles.diffuse_bounces = 2
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.6
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    bpy.context.view_layer.update()
    anch = {k: list(v) for k, v in zip(ANCHORS, Bo.project(sc, cam, [ANCHORS[k] for k in ANCHORS]))}
    json.dump(anch, open('/home/claude/d002/b3d/anch_%s.json' % shot, 'w'))
    sc.render.filepath = '/home/claude/d002/b3d/final_%s.png' % shot
    t0 = time.time(); bpy.ops.render.render(write_still=True); print(shot, 'render', round(time.time() - t0, 1), 's', flush=True)
