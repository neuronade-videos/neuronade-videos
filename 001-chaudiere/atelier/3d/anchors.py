import sys, json
sys.argv = [sys.argv[0]]
import boiler as Bo
import bpy
anchors = {'drain': (-195, -604, -70), 'funnel': (-195, -640, -70), 'burner': (0, 188, 10), 'spark': (-32, 159, 26),
           'coilbot': (-96, 3, 40), 'coilbot2': (-104, 3, 0), 'coilbot3': (-92, 20, 55), 'gauge': (120, -343, 172), 'siphon': (-195, -175, -44),
           'exchanger': (-112, 120, 62)}
for shot in Bo.SHOTS:
    sc = Bo.build(Bo.SHOTS[shot][5]); cam = Bo.setup_cam(sc, shot, 1.0)
    bpy.context.view_layer.update()
    pr = Bo.project(sc, cam, list(anchors.values()))
    json.dump({k: pr[i] for i, k in enumerate(anchors)}, open('/home/claude/b3d/anch_%s.json' % shot, 'w'))
    print(shot, {k: [round(v, 1) for v in pr[i][:2]] for i, k in enumerate(anchors) if k in ('drain', 'burner', 'coilbot', 'gauge')})
