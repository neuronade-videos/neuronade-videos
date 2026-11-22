"""Hologram profile picture: wireframe glass + glowing lemonade + neuron, 1080x1080."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

S = 2; N = 1080; M = N * S
rnd = random.Random(4)
CY = (70, 232, 238); LEM = (255, 222, 60); WH = (240, 255, 250)
img = Image.new('RGB', (M, M)); d = ImageDraw.Draw(img, 'RGBA')
nodes = []
while len(nodes) < 70:
    x, y = rnd.uniform(0, M), rnd.uniform(0, M)
    if math.hypot(x - M / 2, y - M / 2) < 0.47 * M: nodes.append((x, y))
for i, (x, y) in enumerate(nodes):
    for (x2, y2) in nodes[i + 1:]:
        dd = math.hypot(x - x2, y - y2)
        if dd < 0.16 * M: d.line([(x, y), (x2, y2)], fill=(40, 150, 160, int(70 * (1 - dd / (0.16 * M)))), width=3)
for (x, y) in nodes:
    r_ = rnd.uniform(4, 9); d.ellipse([x - r_, y - r_, x + r_, y + r_], fill=(60, 190, 200, 120))

# simple perspective: glass axis vertical, camera slightly above -> ellipses
cx = M / 2; top_y = 0.27 * M; bot_y = 0.83 * M; rt = 0.232 * M; rb = 0.186 * M; k = 0.20   # ellipse ratio
def ell(y, r): return [cx - r, y - r * k, cx + r, y + r * k]
def ring_pts(y, r, a0=0, a1=2 * math.pi, n=90):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), y + r * k * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
def lerp(a, b, u): return a + (b - a) * u
# liquid body (filled, glowing)
ly = lerp(top_y, bot_y, 0.18); lr = lerp(rt, rb, 0.18)
poly = ring_pts(ly, lr, math.pi, 2 * math.pi, 60) + ring_pts(bot_y - 0.012 * M, rb - 6, 0, math.pi, 60)
d.polygon(poly, fill=(255, 196, 30, 105))
d.ellipse(ell(ly, lr), fill=(255, 225, 80, 110), outline=LEM + (255,), width=5)
# liquid surface ripples
for q in (0.75, 0.5):
    d.ellipse(ell(ly, lr * q), outline=LEM + (120,), width=3)
# bubbles
for _ in range(30):
    u = rnd.random(); y = lerp(ly + 40, bot_y - 40, u); r = lerp(lr, rb, u) - 40
    x = cx + rnd.uniform(-r, r); s = rnd.uniform(6, 15)
    d.ellipse([x - s, y - s, x + s, y + s], outline=(255, 245, 190, 200), width=3)
# neuron (soma + branching dendrites), floating near surface
nx, ny = cx + 0.015 * M, ly + 0.105 * M
def branch(x, y, ang, length, w, depth):
    pts = [(x, y)]; a = ang
    for i in range(8):
        a += rnd.uniform(-0.35, 0.35); x += math.cos(a) * length / 8; y += math.sin(a) * length / 8 * 0.85; pts.append((x, y))
    d.line(pts, fill=(20, 140, 160, 200), width=max(4, int(w * 2.2)), joint='curve')
    d.line(pts, fill=(150, 250, 255, 255), width=max(2, int(w * 0.9)), joint='curve')
    if depth > 0:
        for s_ in (-1, 1): branch(x, y, a + s_ * rnd.uniform(0.35, 0.8), length * 0.62, w * 0.65, depth - 1)
    else:
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(170, 255, 255, 255))
for i in range(7):
    a = 2 * math.pi * i / 7 + rnd.uniform(-0.25, 0.25)
    branch(nx + math.cos(a) * 80, ny + math.sin(a) * 68, a, rnd.uniform(150, 210), 17, 2)
d.ellipse([nx - 100, ny - 88, nx + 100, ny + 88], fill=(20, 140, 160, 255))
d.ellipse([nx - 88, ny - 76, nx + 88, ny + 76], fill=(90, 225, 240, 255), outline=(220, 255, 255, 255), width=7)
d.ellipse([nx - 36, ny - 30, nx + 36, ny + 30], fill=(255, 240, 150, 255))
# glass wireframe: rings + verticals (back half dimmer)
for j in range(9):
    u = j / 8; y = lerp(top_y, bot_y, u); r = lerp(rt, rb, u)
    d.line(ring_pts(y, r, math.pi, 2 * math.pi), fill=CY + (70,), width=3)
    d.line(ring_pts(y, r, 0, math.pi), fill=CY + (200 if j in (0, 8) else 120,), width=6 if j in (0, 8) else 3)
for i in range(16):
    a = 2 * math.pi * i / 16; front = math.sin(a) > 0
    d.line([(cx + rt * math.cos(a), top_y + rt * k * math.sin(a)), (cx + rb * math.cos(a), bot_y + rb * k * math.sin(a))], fill=CY + (190 if front else 60,), width=4 if front else 2)
d.ellipse(ell(top_y, rt), outline=CY + (255,), width=8)
d.ellipse(ell(bot_y, rb), outline=CY + (230,), width=6)
d.ellipse(ell(bot_y + 0.03 * M, rb), outline=CY + (150,), width=4)
# fizz: glowing bubbles / sparks rising out of the glass
for _ in range(46):
    u = rnd.random() ** 1.6; y = top_y - 0.02 * M - u * 0.2 * M; x = cx + rnd.uniform(-rt * 0.8, rt * 0.8) * (1 - u * 0.3)
    r_ = rnd.uniform(4, 12) * (1 - u * 0.5); col = LEM if rnd.random() < 0.6 else (150, 250, 255)
    d.ellipse([x - r_, y - r_, x + r_, y + r_], fill=col + (int(230 * (1 - u * 0.7)),))
# lemon slice on the rim (hologram style)
lx, ly2, lr2 = cx + rt * 0.78, top_y - 0.035 * M, 0.088 * M
d.ellipse([lx - lr2, ly2 - lr2, lx + lr2, ly2 + lr2], fill=(255, 215, 50, 60), outline=LEM + (255,), width=10)
d.ellipse([lx - lr2 * 0.84, ly2 - lr2 * 0.84, lx + lr2 * 0.84, ly2 + lr2 * 0.84], outline=(255, 245, 190, 200), width=4)
for i in range(10):
    a = 2 * math.pi * i / 10
    d.line([(lx, ly2), (lx + lr2 * 0.8 * math.cos(a), ly2 + lr2 * 0.8 * math.sin(a))], fill=LEM + (220,), width=5)
d.ellipse([lx - 9, ly2 - 9, lx + 9, ly2 + 9], fill=LEM + (255,))
# straw
sx0, sy0 = cx - 0.07 * M, bot_y - 0.12 * M; sx1, sy1 = cx - 0.15 * M, top_y - 0.20 * M
for t in range(10):
    u0, u1 = t / 10, (t + 1) / 10
    col = LEM if t % 2 else CY
    d.line([(lerp(sx0, sx1, u0), lerp(sy0, sy1, u0)), (lerp(sx0, sx1, u1), lerp(sy0, sy1, u1))], fill=col + (235,), width=22)
# scanner ring around (fits Instagram circle)
R = 0.455 * M
for a0 in range(0, 360, 30):
    d.arc([cx - R, M / 2 - R, cx + R, M / 2 + R], a0 + 4, a0 + 22, fill=CY + (150,), width=6)
for a in range(0, 360, 6):
    ra = math.radians(a); r1 = R - (22 if a % 30 == 0 else 10)
    d.line([(cx + R * math.cos(ra), M / 2 + R * math.sin(ra)), (cx + r1 * math.cos(ra), M / 2 + r1 * math.sin(ra))], fill=CY + (110,), width=3)
img = img.reduce(S)
# glow
g1 = img.resize((N // 4, N // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((N, N), Image.BILINEAR).point(lambda v: min(255, int(v * 1.25)))
g2 = img.resize((N // 10, N // 10), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4)).resize((N, N), Image.BILINEAR).point(lambda v: min(255, int(v * 1.1)))
img = ImageChops.screen(ImageChops.screen(img, g1), g2)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32); r = np.sqrt((xx - N / 2) ** 2 + (yy - N / 2) ** 2) / (N / 2)
bg = np.stack([3 + 12 * np.clip(1 - r, 0, 1), 10 + 48 * np.clip(1 - r, 0, 1), 14 + 52 * np.clip(1 - r, 0, 1)], 2).astype(np.uint8)
img = ImageChops.screen(img, Image.fromarray(bg))
img.save('/home/claude/b3d/logo_holo2.png'); print('ok')
