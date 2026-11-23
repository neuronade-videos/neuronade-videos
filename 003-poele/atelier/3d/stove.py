"""Photoreal pellet stove in Blender, built from the same geometry as the hologram (d003/geom.py).
usage: python3 stove.py SHOT [samples] [scale]"""
import sys, math, json, time, random, importlib.util
sys.path.insert(0, '/home/claude/b3d')
import numpy as np
import bpy, bmesh
import boiler as Bo
spec = importlib.util.spec_from_file_location('gs', '/home/claude/d003/geom.py'); G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
B = Bo.B; principled = Bo.principled; emission = Bo.emission

SHOTS = {  # name: (target mm, az, el, d, fov, inside view)
 'front':   ((0, 20, 60), 22, 6, 2650, 38, False),
 'igniter': ((-50, -140, 78), 4, 50, 380, 38, True),
}
W, H = 1080, 1920

def ico(name, c, r, mat, sx=1, sy=1, sz=1, sub=2):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r * 0.001); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = B(c); o.scale = (sx, sz, sy); o.data.materials.append(mat); Bo.link(o)
    for f in o.data.polygons: f.use_smooth = True
    return o

def build(inside):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene; Bo.COL = sc.collection
    M = dict(body=principled('body', (0.045, 0.047, 0.05), 0.55, 0.38, coat=0.3), black=principled('black', (0.012, 0.012, 0.014), 0.3, 0.5),
             steel=principled('steel', (0.55, 0.56, 0.58), 1, 0.3), cast=principled('cast', (0.03, 0.028, 0.026), 0.6, 0.7),
             glass=principled('glass', (0.95, 0.93, 0.9), 0, 0.02, trans=1.0, ior=1.5), vermi=principled('vermi', (0.13, 0.095, 0.07), 0, 0.9),
             pellet=principled('pellet', (0.24, 0.14, 0.06), 0, 0.8), ember=emission('ember', (1.0, 0.22, 0.03), 4.0),
             flame1=emission('flame1', (1.0, 0.22, 0.02), 2.6), flame2=emission('flame2', (1.0, 0.45, 0.06), 3.6),
             glow=emission('glow', (1.0, 0.1, 0.01), 4.5), disp=emission('disp', (0.4, 1.0, 0.8), 10.0), dispbg=principled('dispbg', (0.004, 0.006, 0.008), 0, 0.5),
             floor=principled('floor', (0.23, 0.14, 0.08), 0, 0.45), wall=principled('wall', (0.16, 0.15, 0.14), 0, 0.85), rug=principled('rug', (0.32, 0.30, 0.27), 0, 1.0))
    (x0, y0, z0), (x1, y1, z1) = G.BODY
    # body shell : sides, top, back, plinth (front left open around the door)
    Bo.box('side_l', (x0, y0, z0), (x0 + 12, y1, z1), M['body'], bevel=3); Bo.box('side_r', (x1 - 12, y0, z0), (x1, y1, z1), M['body'], bevel=3)
    Bo.box('top', (x0, y1 - 12, z0), (x1, y1, z1 + 10), M['body'], bevel=4); Bo.box('back', (x0, y0, z0), (x1, y1, z0 + 12), M['body'])
    Bo.box('plinth', (x0, y0, z1 - 20), (x1, G.DOOR[0][1] - 5, z1), M['body'], bevel=2)
    Bo.box('front_top', (x0, G.DOOR[1][1] + 5, z1 - 20), (x1, y1, z1), M['body'], bevel=2)
    Bo.box('front_right', (G.DOOR[1][0] + 5, G.DOOR[0][1] - 5, z1 - 20), (x1, G.DOOR[1][1] + 5, z1), M['body'], bevel=2)
    for (x, z) in ((x0 + 30, z0 + 30), (x1 - 30, z0 + 30), (x0 + 30, z1 - 30), (x1 - 30, z1 - 30)): Bo.cyl('foot', (x, G.FLOOR_Y, z), (x, y0, z), 18, M['black'])
    # top grille
    (rx0, ry0, rz), (rx1, ry1, _) = G.GRILLE
    for y in np.linspace(ry0 + 8, ry1 - 8, 6): Bo.box('slat', (rx0, y - 5, z1 - 2), (rx1, y + 5, z1 + 6), M['black'], bevel=1)
    # fire chamber : vermiculite walls, burn pot, pellets
    (fx0, fy0, fz0), (fx1, fy1, fz1) = G.FIRE
    Bo.box('fb', (fx0, fy0, fz0), (fx1, fy1, fz0 + 15), M['vermi']); Bo.box('fl', (fx0, fy0, fz0), (fx0 + 15, fy1, fz1), M['vermi']); Bo.box('fr', (fx1 - 15, fy0, fz0), (fx1, fy1, fz1), M['vermi'])
    Bo.box('ff', (fx0, fy0, fz0), (fx1, fy0 + 15, fz1), M['cast']); Bo.box('ft', (fx0, fy1 - 12, fz0), (fx1, fy1, fz1), M['cast'])
    (px0, py0, pz0), (px1, py1, pz1) = G.POT
    Bo.box('pot_b', (px0, py0, pz0), (px1, py0 + 8, pz1), M['cast'])
    for a, b in (((px0, py0, pz0), (px0 + 8, py1, pz1)), ((px1 - 8, py0, pz0), (px1, py1, pz1)), ((px0, py0, pz0), (px1, py1, pz0 + 8)), ((px0, py0, pz1 - 8), (px1, py1, pz1))):
        Bo.box('pot_w', a, b, M['cast'], bevel=1)
    rnd = random.Random(4)
    for k in range(70):
        c = (rnd.uniform(px0 + 14, px1 - 14), rnd.uniform(py0 + 12, py0 + 48), rnd.uniform(pz0 + 14, pz1 - 14))
        d = np.array([rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3), rnd.uniform(-1, 1)]); d = d / np.linalg.norm(d) * 10
        hot = (rnd.random() < 0.08) if inside else (c[1] > py0 + 30 or rnd.random() < 0.4)
        Bo.cyl('pel', tuple(np.array(c) - d), tuple(np.array(c) + d), 3.2, M['ember' if hot else 'pellet'], verts=10)
    # flames (none during ignition : only the glowing igniter and the first embers)
    for k in (range(16) if not inside else []):
        c = (G.POT_C[0] + rnd.uniform(-35, 35), py1 + rnd.uniform(20, 90), G.POT_C[2] + rnd.uniform(-30, 30))
        ico('flame', c, rnd.uniform(10, 18), M['flame1' if k % 2 else 'flame2'], sx=0.55, sy=rnd.uniform(3.0, 5.5), sz=0.55)
    for k in (range(6) if not inside else []):
        ico('flame_top', (G.POT_C[0] + rnd.uniform(-25, 25), py1 + rnd.uniform(140, 210), G.POT_C[2] + rnd.uniform(-20, 20)), rnd.uniform(10, 16), M['flame1'], sx=0.7, sy=3.5, sz=0.7)
    L = bpy.data.lights.new('fire', 'POINT'); L.energy = 38 if not inside else 0.5; L.color = (1.0, 0.55, 0.2); L.shadow_soft_size = 0.06
    o = bpy.data.objects.new('fire', L); o.location = B((G.POT_C[0], py1 + 120, G.POT_C[2])); Bo.link(o)
    # igniter tube + glowing tip (inside view)
    Bo.cyl('ign', G.IGNITER[0], (G.IGNITER[1][0], G.IGNITER[1][1], G.IGNITER[1][2] - 10), 14, M['steel'])
    Bo.cyl('ign_tip', (G.IGNITER[1][0], G.IGNITER[1][1], G.IGNITER[1][2] - 12), G.IGNITER[1], 10, M['glow'])
    if inside:
        L = bpy.data.lights.new('ign', 'POINT'); L.energy = 5; L.color = (1.0, 0.35, 0.08); L.shadow_soft_size = 0.02
        o = bpy.data.objects.new('ign', L); o.location = B((G.IGN_TIP[0], G.IGN_TIP[1] + 15, G.IGN_TIP[2] + 30)); Bo.link(o)
    # chute end above the pot
    Bo.box('chute', (-80, -40, 50), (-20, 10, 80), M['cast'], bevel=1)
    # door + glass + handle
    (dx0, dy0, dz0), (dx1, dy1, dz1) = G.DOOR; (gx0, gy0, _), (gx1, gy1, _) = G.GLASS
    if not inside:
        Bo.box('door_t', (dx0, gy1, dz0), (dx1, dy1, dz1), M['black'], bevel=3); Bo.box('door_b', (dx0, dy0, dz0), (dx1, gy0, dz1), M['black'], bevel=3)
        Bo.box('door_l', (dx0, gy0, dz0), (gx0, gy1, dz1), M['black'], bevel=3); Bo.box('door_r', (gx1, gy0, dz0), (dx1, gy1, dz1), M['black'], bevel=3)
        Bo.box('glass', (gx0, gy0, dz0 + 4), (gx1, gy1, dz0 + 9), M['glass'], bevel=1)
        Bo.cyl('handle', (110, -60, dz1 + 2), (110, 140, dz1 + 2), 7, M['steel'])
    # display
    (sx0, sy0, sz), (sx1, sy1, _) = G.DISPLAY
    Bo.box('dispbg', (sx0, sy0, z1 - 2), (sx1, sy1, z1 + 3), M['dispbg'], bevel=1)
    t1 = Bo.text('disp1', 'CHAUFFE', ((sx0 + sx1) / 2, (sy0 + sy1) / 2 + 12, z1 + 3.5), 15, M['disp']); t1.rotation_euler = (math.radians(90), 0, 0)
    t2 = Bo.text('disp2', '20.0°', ((sx0 + sx1) / 2, (sy0 + sy1) / 2 - 22, z1 + 3.5), 15, M['disp']); t2.rotation_euler = (math.radians(90), 0, 0)
    for k in range(3): Bo.cyl('btn', (sx0 + 15 + k * 26, sy0 - 28, z1), (sx0 + 15 + k * 26, sy0 - 28, z1 + 5), 8, M['steel'], verts=20)
    # flue pipe at the back
    Bo.tube('flue', G.FLUE, 40, M['black'])
    # room
    Bo.box('floor', (-3000, G.FLOOR_Y - 20, -900), (3000, G.FLOOR_Y, 3000), M['floor'], bevel=0)
    Bo.box('wall', (-3000, G.FLOOR_Y, G.WALL_Z - 20), (3000, 2500, G.WALL_Z), M['wall'], bevel=0)
    Bo.box('hearth', (-450, G.FLOOR_Y, -450), (450, G.FLOOR_Y + 8, 520), M['steel'] if False else M['black'], bevel=2)
    Bo.box('rug', (-900, G.FLOOR_Y, 800), (900, G.FLOOR_Y + 6, 2000), M['rug'], bevel=0)
    # lights : dim cool room + warm fire glow
    def area(name, loc, target, energy, size, col):
        L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.size = size; L.color = col
        o = bpy.data.objects.new(name, L); o.location = B(loc); d = B(target) - B(loc); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('-Z', 'Y'); Bo.link(o)
    area('key', (-1600, 1300, 1600), (0, 0, 0), 55, 1.4, (0.75, 0.85, 1.0))
    area('rim', (1300, 900, -500), (0, 200, 0), 140, 0.8, (0.35, 0.8, 1.0))
    area('glowout', (0, 0, 650), (0, -200, 1200), 60, 0.8, (1.0, 0.5, 0.2))
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.004, 0.006, 0.01, 1)
    return sc

def setup_cam(sc, shot, scale):
    T, az, el, d, fov, _ = SHOTS[shot]
    C = Bo.cam_pos(T, az, el, d)
    cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.angle = math.radians(fov); cd.shift_y = -(0.5 - 0.455)
    cd.dof.use_dof = True; cd.dof.focus_distance = d * 0.001; cd.dof.aperture_fstop = 2.8 if d < 1000 else 5.6
    o = bpy.data.objects.new('cam', cd); o.location = B(C); dv = B(T) - B(C); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = dv.to_track_quat('-Z', 'Y')
    Bo.link(o); sc.camera = o; sc.render.resolution_x, sc.render.resolution_y = int(W * scale), int(H * scale)
    return o

ANCHORS = {'display': G.DISPLAY_C, 'pot': G.POT_C, 'flame': (G.POT_C[0], -40, G.POT_C[2]), 'igniter': G.IGN_TIP, 'grille': (0, 428, 255), 'glass': (-55, 30, 262)}
if __name__ == '__main__':
    shot = sys.argv[1]; samples = int(sys.argv[2]) if len(sys.argv) > 2 else 28; scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
    sc = build(SHOTS[shot][5]); cam = setup_cam(sc, shot, scale)
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.glossy_bounces = 4; sc.cycles.diffuse_bounces = 2
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.exposure = -0.4 if not SHOTS[shot][5] else -0.9
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    bpy.context.view_layer.update()
    anch = {k: list(v) for k, v in zip(ANCHORS, Bo.project(sc, cam, [ANCHORS[k] for k in ANCHORS]))}
    json.dump(anch, open('/home/claude/d003/b3d/anch_%s.json' % shot, 'w'))
    sc.render.filepath = '/home/claude/d003/b3d/final_%s.png' % shot
    t0 = time.time(); bpy.ops.render.render(write_still=True); print(shot, 'render', round(time.time() - t0, 1), 's', flush=True)
