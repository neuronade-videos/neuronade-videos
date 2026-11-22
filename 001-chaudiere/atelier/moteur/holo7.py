"""Final build: holo5 (terminal captions + tags + photoreal inserts) + joke gag + slow-motion tag + corner logo."""
import sys, os, math, subprocess
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, '/home/claude/v7')
import holo3 as V
import holo5 as H5

W, H, FPS = V.W, V.H, V.FPS
V.SAFE['y0'] = 356   # keep component tags clear of the HUD readouts
LOGO = Image.open('/home/claude/b3d/logo_holo2.png').convert('RGB')
def logo_disc(size):
    im = LOGO.resize((size, size), Image.LANCZOS).convert('RGBA'); m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255); im.putalpha(m); return im
LOGO96 = logo_disc(96)

T_DEP = V.word_t(0, 1, 'dépression') - 0.05
T_CND = V.word_t(0, 1, 'condensation') - 0.05
T_GAG_END = V.Sx(0, 2) - 0.1
SLOW0, SLOW1 = V.T_GAS - 0.1, V.T_FLAME + 1.0
GREEN = (110, 255, 160)

def cross(d, cx, cy, r, col, a, w=7):
    d.line([cx - r, cy - r, cx + r, cy + r], fill=V.rgba(col, 255 * a), width=w)
    d.line([cx - r, cy + r, cx + r, cy - r], fill=V.rgba(col, 255 * a), width=w)
def check(d, cx, cy, r, col, a, w=7):
    d.line([cx - r, cy + 2, cx - r * 0.25, cy + r * 0.8, cx + r, cy - r * 0.85], fill=V.rgba(col, 255 * a), width=w, joint='curve')

class R7(H5.R5):
    def frame(self, i):
        img = super().frame(i); t = i / FPS
        d = ImageDraw.Draw(img, 'RGBA')
        # --- joke gag: DÉPRESSION ✗ / CONDENSATION ✓ (terminal style, above the captions)
        if T_DEP <= t < T_GAG_END:
            a = V.win(t, T_DEP, T_GAG_END, 0.2)
            x0, x1, y0, y1 = 190, 890, 455, 637
            d.rectangle([x0, y0, x1, y1], fill=(0, 12, 16, int(215 * a)), outline=V.rgba(V.HOLO, 190 * a), width=2)
            V.text(img, d, (x0 + 18, y0 + 22), "neuronade.ia ~ $ diagnostic", V.font('mono', 22), V.HOLO, 0.85 * a, 'lm')
            f = V.font('monob', 54)
            # row 1 : DÉPRESSION (red, crossed out)
            a1 = a * V.ramp(t, T_DEP, T_DEP + 0.15)
            pop = 1 + 0.18 * (1 - V.ramp(t, T_DEP, T_DEP + 0.25))
            cross(d, x0 + 70, y0 + 92, 20 * pop, V.RED, a1)
            V.text(img, d, (x0 + 120, y0 + 92), "DÉPRESSION", f, V.RED, a1, 'lm')
            k = V.ramp(t, T_DEP + 0.25, T_DEP + 0.6)
            if k > 0:
                tw = d.textlength("DÉPRESSION", font=f)
                d.line([x0 + 116, y0 + 94, x0 + 116 + (tw + 8) * k, y0 + 94], fill=V.rgba(V.RED, 255 * a1), width=6)
            # row 2 : CONDENSATION (green, checked)
            a2 = a * V.ramp(t, T_CND, T_CND + 0.15)
            if a2 > 0.01:
                pop = 1 + 0.25 * (1 - V.ramp(t, T_CND, T_CND + 0.3))
                check(d, x0 + 70, y0 + 152, 22 * pop, GREEN, a2)
                V.text(img, d, (x0 + 120, y0 + 152), "CONDENSATION", f, GREEN, a2, 'lm')
        # --- slow-motion tag: gas -> sparks -> flame really happens in about one second
        if SLOW0 <= t < SLOW1:
            a = V.win(t, SLOW0, SLOW1, 0.3)
            s = "RALENTI ×10"; f = V.font('monob', 28); tw = d.textlength(s, font=f)
            x1 = W - 60; x0 = x1 - tw - 58; y = 194
            d.rectangle([x0, y - 24, x1, y + 24], fill=(0, 12, 16, int(200 * a)), outline=V.rgba(V.HOLO, 170 * a), width=2)
            if int(t * 2) % 2 == 0: d.ellipse([x0 + 14, y - 9, x0 + 32, y + 9], fill=V.rgba(V.RED, 255 * a))
            V.text(img, d, (x0 + 44, y), s, f, (235, 248, 255), a, 'lm')
        # --- signature: logo in the top-right corner, gentle pulse
        pul = 0.82 + 0.13 * math.sin(t * 2.4)
        lg = LOGO96.copy(); lg.putalpha(lg.getchannel('A').point(lambda v: int(v * pul)))
        img.paste(lg, (W - 60 - 96, 420), lg)
        return img

def render_seg(args):
    idx, f0, f1 = args
    r = R7(); out = '/home/claude/v7/seg/seg_%03d' % idx
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(FPS), '-f', 'mp4', out + '.tmp.mp4']
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1): p.stdin.write(r.frame(i).tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.rename(out + '.tmp.mp4', out + '.mp4')
    return idx, rc

if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        import time
        r = R7(); os.makedirs('/home/claude/v7/prev', exist_ok=True)
        for ts in sys.argv[2:]:
            t0 = time.time(); r.frame(int(float(ts) * FPS)).save('/home/claude/v7/prev/f_%s.png' % ts); print(ts, round(time.time() - t0, 2), flush=True)
    else:
        from multiprocessing import Pool
        os.makedirs('/home/claude/v7/seg', exist_ok=True); SEG = 150
        segs = [(k, k * SEG, min(V.NF, (k + 1) * SEG)) for k in range((V.NF + SEG - 1) // SEG)]
        segs = [s for s in segs if not os.path.exists('/home/claude/v7/seg/seg_%03d.mp4' % s[0])]
        with Pool(int(sys.argv[2]) if len(sys.argv) > 2 else 4) as p:
            for res in p.imap_unordered(render_seg, segs): print(res, flush=True)
