"""Photoreal cut-away gas boiler in Blender, built from the same geometry as the hologram (v3/geom.py).
usage: python3 boiler.py SHOT [samples] [scale]"""
import sys, math, json, time, random
sys.path.insert(0, '/home/claude/v3')
import numpy as np
import bpy, bmesh
from mathutils import Vector
import geom as G

SHOTS = {
 # name: (target mm, az, el, d, fov, flame, extra)
 'hook1': ((-60, -150, 0), -28, 6, 2250, 38, True),
 'hook2': ((0, 150, 10), -20, 8, 900, 38, True),
 'ign':   ((-15, 175, 30), -22, 5, 560, 38, True),
 'cond':  ((-88, 28, 32), -12, -4, 330, 38, True),
 'gauge': ((120, -343, 172), -12, 4, 210, 38, False),
}
W, H = 1080, 1920

def B(p):  # my coords (mm, y up, z to viewer) -> blender metres
    x, y, z = p; return Vector((x * 0.001, -z * 0.001, y * 0.001))

def cam_pos(T, az, el, d):
    az, el = math.radians(az), math.radians(el); T = np.array(T, float)
    return T + d * np.array([math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)])

# ---------------- materials ----------------
def principled(name, col, metal=0.0, rough=0.4, coat=0.0, trans=0.0, ior=1.45, aniso=0.0, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough; b.inputs['IOR'].default_value = ior
    if coat: b.inputs['Coat Weight'].default_value = coat
    if trans: b.inputs['Transmission Weight'].default_value = trans
    if aniso: b.inputs['Anisotropic'].default_value = aniso
    if alpha < 1: b.inputs['Alpha'].default_value = alpha
    return m
def emission(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission')
    e.inputs[0].default_value = (*col, 1); e.inputs[1].default_value = strength; nt.links.new(e.outputs[0], o.inputs[0]); return m
def flame_mat(name, col, strength, alpha, scale=40.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 6
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.42; cr.color_ramp.elements[1].position = 0.72
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = alpha
    e.inputs[0].default_value = (*col, 1); e.inputs[1].default_value = strength
    nt.links.new(nz.outputs['Fac'], cr.inputs[0]); nt.links.new(cr.outputs[0], mul.inputs[0]); nt.links.new(mul.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(e.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], o.inputs[0]); return m
def burner_mat():
    m = bpy.data.materials.new('burner'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission')
    vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 220
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 0.6
    mr.inputs['To Min'].default_value = 0.6; mr.inputs['To Max'].default_value = 4.5
    e.inputs[0].default_value = (1.0, 0.16, 0.02, 1)
    nt.links.new(vo.outputs['Distance'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], e.inputs[1]); nt.links.new(e.outputs[0], o.inputs[0]); return m

# ---------------- primitives ----------------
COL = None
def link(o): COL.objects.link(o); return o
def tube(name, pts, r, mat, res=10, caps=True):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r * 0.001; cu.bevel_resolution = 3; cu.use_fill_caps = caps
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts): v = B(p); sp.points[i].co = (v.x, v.y, v.z, 1)
    o = bpy.data.objects.new(name, cu); o.data.materials.append(mat); return link(o)
def cyl(name, c0, c1, r, mat, verts=48, cap=True):
    c0, c1 = B(c0), B(c1); d = c1 - c0
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=verts, radius1=r * 0.001, radius2=r * 0.001, depth=d.length)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me)
    o.location = (c0 + c1) / 2; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth = True
    return link(o)
def box(name, mn, mx, mat, bevel=2.0):
    a, b = B(mn), B(mx); lo = Vector((min(a.x, b.x), min(a.y, b.y), min(a.z, b.z))); hi = Vector((max(a.x, b.x), max(a.y, b.y), max(a.z, b.z)))
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = (lo + hi) / 2; o.scale = hi - lo; o.data.materials.append(mat); link(o)
    if bevel:
        mod = o.modifiers.new('bv', 'BEVEL'); mod.width = bevel * 0.001; mod.segments = 3; mod.affect = 'EDGES'
        bpy.context.view_layer.objects.active = o
    return o
def partial_shell(name, c, r, y0, y1, a0, a1, mat, thick=2.5, segs=64):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rows = []
    for y in (y0, y1):
        row = []
        for k in range(segs + 1):
            a = a0 + (a1 - a0) * k / segs; row.append(bm.verts.new(B((c[0] + r * math.cos(a), y, c[2] + r * math.sin(a)))))
        rows.append(row)
    for k in range(segs): bm.faces.new((rows[0][k], rows[0][k + 1], rows[1][k + 1], rows[1][k]))
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); o.data.materials.append(mat)
    for f in o.data.polygons: f.use_smooth = True
    s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = thick * 0.001; return link(o)
def text(name, s, pos, size, mat, rot_y=0.0, align='CENTER', font=None):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = s; cu.size = size * 0.001; cu.align_x = align; cu.align_y = 'CENTER'
    if font: cu.font = font
    cu.extrude = 0.0002
    o = bpy.data.objects.new(name, cu); o.location = B(pos); o.rotation_euler = (math.radians(90), 0, rot_y); o.data.materials.append(mat); return link(o)

def build(flame=True):
    global COL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene; COL = sc.collection
    M = dict(
        enamel=principled('enamel', (0.86, 0.87, 0.89), rough=0.32, coat=0.4),
        steel=principled('steel', (0.78, 0.79, 0.8), metal=1, rough=0.22, aniso=0.4),
        steel_dark=principled('steel_dark', (0.45, 0.46, 0.48), metal=1, rough=0.35),
        copper=principled('copper', (0.96, 0.58, 0.4), metal=1, rough=0.2),
        brass=principled('brass', (0.92, 0.72, 0.38), metal=1, rough=0.28),
        black=principled('black', (0.015, 0.016, 0.02), rough=0.35, coat=0.3),
        grey=principled('grey', (0.07, 0.075, 0.08), rough=0.5),
        green=principled('pumpgreen', (0.03, 0.18, 0.12), rough=0.35, coat=0.3),
        red=principled('red', (0.55, 0.03, 0.025), rough=0.3, coat=0.5),
        yellow=principled('yellow', (0.95, 0.66, 0.05), rough=0.35, coat=0.3),
        plastic=principled('plastic', (0.92, 0.95, 1.0), rough=0.12, trans=0.85, ior=1.46),
        water=principled('water', (0.95, 0.98, 1.0), rough=0.02, trans=1.0, ior=1.33),
        ceramic=principled('ceramic', (0.95, 0.94, 0.9), rough=0.5),
        pvc=principled('pvc', (0.93, 0.93, 0.92), rough=0.4),
        floor=principled('floor', (0.012, 0.014, 0.017), rough=0.28),
        wall=principled('wall', (0.008, 0.01, 0.013), rough=0.85),
        disp=emission('disp', (0.2, 0.9, 1.0), 6), dial=principled('dial', (0.95, 0.95, 0.93), rough=0.3, coat=0.8),
        ink=principled('ink', (0.01, 0.01, 0.01), rough=0.6), needle=principled('needle', (0.75, 0.04, 0.02), rough=0.35),
        glass=principled('glass', (1, 1, 1), rough=0.0, trans=1.0, ior=1.5),
        burner=burner_mat(),
        flame_b=flame_mat('flame_b', (0.2, 0.5, 1.0), 3.5, 0.9, 55), flame_o=flame_mat('flame_o', (1.0, 0.4, 0.06), 2.5, 0.6, 30),
    )
    # room
    box('floor', (-1500, -702, -400), (1500, -700, 900), M['floor'], 0)
    box('wall', (-1500, -700, -176), (1500, 900, -172), M['wall'], 0)
    # casing (cut-away: back, sides, top, bottom; no front)
    (x0, y0, z0), (x1, y1, z1) = G.CAS
    box('back', (x0, y0, z0), (x1, y1, z0 + 4), M['enamel'])
    box('left', (x0, y0, z0), (x0 + 4, y1, z1), M['enamel'])
    box('right', (x1 - 4, y0, z0), (x1, y1, z1 - 150), M['enamel'])
    box('top', (x0, y1 - 4, z0), (x1, y1, z1), M['enamel'])
    box('bottom', (x0, y0, z0), (x1, y0 + 4, z1), M['enamel'])
    # heat exchanger: shell cut open toward the viewer, coil, burner, collector
    partial_shell('shell', (0, 0, 10), G.EXC_R, G.EXC_Y[0], G.EXC_Y[1], math.radians(185), math.radians(395), M['steel'], 2.5)
    partial_shell('shell_in', (0, 0, 10), G.EXC_R - 4, G.EXC_Y[0], G.EXC_Y[1], math.radians(185), math.radians(395), M['steel_dark'], 1.0)
    cyl('lid', (0, G.EXC_Y[1], 10), (0, G.EXC_Y[1] + 14, 10), G.EXC_R + 4, M['steel'])
    cyl('collector', (0, -40, 10), (0, G.EXC_Y[0], 10), G.EXC_R + 2, M['steel_dark'])
    seg = []; k = 0
    for p in G.COIL:
        a = math.degrees(math.atan2(p[2] - 10, p[0])) % 360
        if 55 <= a <= 165:
            if len(seg) > 1: tube('coil%d' % k, seg, 11, M['steel'], caps=False); k += 1
            seg = []
        else: seg.append(tuple(p))
    if len(seg) > 1: tube('coil%d' % k, seg, 11, M['steel'], caps=False)
    cyl('burner', (0, G.BURN_Y[0], 10), (0, G.BURN_Y[1], 10), G.BURN_R, M['burner'] if flame else M['steel_dark'])
    if flame:
        cyl('flame_in', (0, G.BURN_Y[0] + 2, 10), (0, G.BURN_Y[1] - 2, 10), G.BURN_R + 9, M['flame_b'], cap=False)
        cyl('flame_out', (0, G.BURN_Y[0] + 4, 10), (0, G.BURN_Y[1] - 4, 10), G.BURN_R + 20, M['flame_o'], cap=False)
        L = bpy.data.lights.new('fire', 'POINT'); L.energy = 90; L.color = (1.0, 0.45, 0.15); L.shadow_soft_size = 0.03
        o = bpy.data.objects.new('fire', L); o.location = B((0, 190, 10)); link(o)
    # electrodes
    for gx in (-45, 45):
        tube('el%d' % gx, [(gx, G.EXC_Y[1] + 6, 40), (gx, 165, 40), (gx * 0.82, 158, 34)], 1.6, M['steel'])
        cyl('ins%d' % gx, (gx, G.EXC_Y[1] + 14, 40), (gx, G.EXC_Y[1] + 40, 40), 7, M['ceramic'])
    # fan, venturi, duct
    cyl('fan', G.FAN_C + (0, 0, -23), G.FAN_C + (0, 0, 23), G.FAN_R, M['black'])
    cyl('fan_motor', G.FAN_C + (0, 0, 23), G.FAN_C + (0, 0, 45), 20, M['grey'])
    tube('venturi', G.VENT_PATH, 15, M['grey']); tube('duct', G.DUCT_PATH, 16, M['steel_dark'])
    # flue (white concentric)
    tube('flue', G.FLUE_AX, G.FLUE_RO, M['pvc']); tube('fumeduct', G.FUME_DUCT, 28, M['steel_dark'])
    # expansion vessel
    vc = (0, -185, -128); cyl('vessel', (vc[0], vc[1], vc[2] - 24), (vc[0], vc[1], vc[2] + 24), 136, M['red'], verts=72)
    # hydraulics
    cyl('pump_motor', (130, -235, 15), (130, -235, 85), 40, M['green']); cyl('pump_volute', (130, -235, -5), (130, -235, 15), 54, M['steel_dark'])
    box('v3', (-175, -275, 20), (-125, -235, 60), M['brass'], 3); cyl('v3act', (-150, -255, 60), (-150, -255, 96), 22, M['black'])
    box('phx', (-95, -275, 20), (5, -145, 60), M['steel'], 2)
    for k in range(1, 10): box('pl%d' % k, (-95 + 10 * k - 1, -276, 18), (-95 + 10 * k + 1, -144, 62), M['steel_dark'], 0)
    box('gasvalve', (35, -180, 20), (105, -120, 70), M['black'], 4); cyl('gascoil', (70, -120, 45), (70, -88, 45), 16, M['yellow'])
    cyl('flowmeter', (80, -375, 25), (80, -345, 25), 14, M['brass']); cyl('safety', (205, -340, 60), (205, -300, 60), 12, M['brass'])
    box('limiter', (-182, 180, 20), (-158, 205, 36), M['black'], 2)
    # control box & display & manometer
    box('ctrl', (-180, -372, 110), (180, -318, 165), M['black'], 5)
    box('screen', (-60, -355, 165), (40, -330, 167), M['disp'], 0)
    gc = (120, -343, 166); cyl('gauge_body', gc, (120, -343, 172), 19, M['steel']); cyl('gauge_face', (120, -343, 172), (120, -343, 173), 16, M['dial'])
    font = None
    try: font = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    except Exception: pass
    for k in range(9):
        a = math.radians(225 - 270 * k / 8); r0 = 11.5 if k % 2 == 0 else 12.8
        p0 = (120 + r0 * math.cos(a), -343 + r0 * math.sin(a), 173.2); p1 = (120 + 15 * math.cos(a), -343 + 15 * math.sin(a), 173.2)
        tube('tick%d' % k, [p0, p1], 0.45 if k % 2 == 0 else 0.3, M['ink'])
        if k % 2 == 0: text('num%d' % k, str(k // 2), (120 + 8.8 * math.cos(a), -343 + 8.8 * math.sin(a), 173.3), 3.2, M['ink'], font=font)
    text('bar', 'bar', (120, -349.5, 173.3), 2.4, M['ink'], font=font)
    # zone red > 3 bar
    for k in range(7):
        a0 = math.radians(225 - 270 * (3 + k / 6) / 4); a1 = math.radians(225 - 270 * (3 + (k + 1) / 6) / 4)
        tube('red%d' % k, [(120 + 14 * math.cos(a0), -343 + 14 * math.sin(a0), 173.2), (120 + 14 * math.cos(a1), -343 + 14 * math.sin(a1), 173.2)], 0.7, M['needle'])
    ga = math.radians(225 - 270 * 1.5 / 4)
    tube('needle', [(120 - 2.5 * math.cos(ga), -343 - 2.5 * math.sin(ga), 174), (120 + 12 * math.cos(ga), -343 + 12 * math.sin(ga), 174)], 0.45, M['needle'])
    cyl('hub', (120, -343, 173.6), (120, -343, 174.6), 1.4, M['black'])
    text('logo', 'NEURONADE', (0, 330, 172), 12, M['disp'], font=font) if False else None
    # siphon (translucent) & drain & funnel
    tube('siph_in', G.SIPHON_IN, 9, M['plastic']); cyl('siph_pot', (-195, -230, -70), (-195, -120, -70), 26, M['plastic'])
    cyl('siph_water', (-195, -228, -70), (-195, -170, -70), 23, M['water'])
    tube('siph_out', G.SIPHON_OUT, 9, M['plastic'])
    me = bpy.data.meshes.new('funnel'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.010, radius2=0.038, depth=0.036); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('funnel', me); o.location = B((-195, -650, -70)); o.data.materials.append(M['steel']); link(o)
    for f in o.data.polygons: f.use_smooth = True
    s = o.modifiers.new('sol', 'SOLIDIFY'); s.thickness = 0.0015
    tube('drain', [(-195, -668, -70), (-195, -702, -70)], 9, M['pvc'])
    # pipes
    for nm, p, r, mt in (('ret', G.RET_TO_PUMP, 11, 'copper'), ('p2c', G.PUMP_TO_COIL, 11, 'copper'), ('c2v', G.COIL_TO_VALVE, 11, 'copper'),
                         ('v2d', G.VALVE_TO_DEP, 11, 'copper'), ('v2p', G.VALVE_TO_PHX, 8, 'copper'), ('p2p', G.PHX_TO_PUMP, 8, 'copper'),
                         ('ef', G.EF_PATH, 8, 'copper'), ('ecs', G.ECS_PATH, 8, 'copper'), ('gas', G.GAS_PATH, 9, 'yellow'), ('gas2', G.GAS_PATH2, 9, 'yellow')):
        tube(nm, p, r, M[mt])
    # radiator (white)
    (rx0, ry0, rz0), (rx1, ry1, rz1) = G.RAD
    for k in range(10):
        xc = rx0 + 25 + (rx1 - rx0 - 50) * k / 9; box('rad%d' % k, (xc - 20, ry0, -150), (xc + 20, ry1, -100), M['enamel'], 8)
    # condensate droplets on the lower coil turns + in collector
    rnd = random.Random(3)
    if True:
        for k in range(260):
            u = rnd.uniform(0.0, 0.28); idx = int(u * (len(G.COIL) - 1)); p = G.COIL[idx]
            a = math.atan2(p[2] - 10, p[0]); rr = rnd.uniform(-9, 9)
            if 55 <= math.degrees(a) % 360 <= 165: continue
            q = (p[0] + rr * math.cos(a) * 0.3, p[1] - 10.5 - rnd.uniform(0, 1.5), p[2] + rr * math.sin(a) * 0.3)
            me = bpy.data.meshes.new('dr'); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=10, radius=rnd.uniform(1.6, 3.6) * 0.001)
            bm.to_mesh(me); bm.free(); o = bpy.data.objects.new('drop', me); o.location = B(q); o.scale = (1, 1, 1.35); o.data.materials.append(M['water']); link(o)
            for f in o.data.polygons: f.use_smooth = True
    # lights
    def area(name, loc, target, energy, size, col):
        L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.size = size; L.color = col
        o = bpy.data.objects.new(name, L); o.location = B(loc); d = B(target) - B(loc); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('-Z', 'Y'); link(o)
    area('key', (-900, 700, 1200), (0, 0, 0), 160, 1.0, (1.0, 0.9, 0.8))
    area('rimc', (900, 400, -500), (0, 0, 0), 420, 0.6, (0.3, 0.85, 1.0))
    area('rimc2', (-900, -100, -400), (0, -100, 0), 260, 0.6, (0.3, 0.75, 1.0))
    area('fill', (300, -300, 1500), (0, -100, 0), 35, 1.5, (0.8, 0.9, 1.0))
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.004, 0.008, 0.012, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    return sc

def setup_cam(sc, shot, scale):
    T, az, el, d, fov, _ = SHOTS[shot]
    C = cam_pos(T, az, el, d)
    cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.angle = math.radians(fov)
    cd.shift_y = -(0.5 - 0.455)
    cd.dof.use_dof = True; cd.dof.focus_distance = d * 0.001; cd.dof.aperture_fstop = 2.8 if d < 1000 else 5.6
    o = bpy.data.objects.new('cam', cd); o.location = B(C); dv = B(T) - B(C); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = dv.to_track_quat('-Z', 'Y')
    link(o); sc.camera = o
    sc.render.resolution_x, sc.render.resolution_y = int(W * scale), int(H * scale)
    return o

def project(sc, cam, pts):
    from bpy_extras.object_utils import world_to_camera_view
    out = []
    for p in pts:
        v = world_to_camera_view(sc, cam, B(p)); out.append((v.x * W, (1 - v.y) * H, v.z))
    return out

if __name__ == '__main__':
    shot = sys.argv[1]; samples = int(sys.argv[2]) if len(sys.argv) > 2 else 64; scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
    sc = build(SHOTS[shot][5]); cam = setup_cam(sc, shot, scale)
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.glossy_bounces = 4; sc.cycles.diffuse_bounces = 2
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Punchy'
    except Exception: pass
    sc.view_settings.exposure = 0.0
    sc.render.filepath = '/home/claude/b3d/shot_%s.png' % shot
    anchors = {'drain': (-195, -600, -70), 'funnel': (-195, -640, -70), 'burner': (0, 188, 10), 'spark': (-32, 159, 26),
               'coilbot': (0, 5, 108), 'coilbot2': (60, 5, 92), 'coilbot3': (-50, 5, 95), 'gauge': (120, -343, 172), 'siphon': (-195, -175, -44),
               'exchanger': (-112, 120, 62)}
    pr = project(sc, cam, list(anchors.values()))
    json.dump({k: pr[i] for i, k in enumerate(anchors)}, open('/home/claude/b3d/anch_%s.json' % shot, 'w'))
    t0 = time.time(); bpy.ops.render.render(write_still=True); print(shot, 'render', round(time.time() - t0, 1), 's', flush=True)
