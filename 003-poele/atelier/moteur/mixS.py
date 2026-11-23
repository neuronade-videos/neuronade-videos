import sys, wave, math, numpy as np
sys.path.insert(0, '/home/claude/d003')
import holo3 as V

SR = 44100; DUR = V.DUR; N = int(DUR * SR)
rng = np.random.default_rng(11)
t_all = np.arange(N) / SR

def bandnoise(L, f0, f1=None, q=0.5):
    nz = rng.standard_normal(L); F = np.fft.rfft(nz); fr = np.fft.rfftfreq(L, 1 / SR)
    fc = f0 if f1 is None else math.sqrt(f0 * f1)
    F *= np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / q)
    w = np.fft.irfft(F, L); return w / (np.abs(w).max() + 1e-9)
def lowpass_noise(L, fc):
    nz = rng.standard_normal(L); F = np.fft.rfft(nz); fr = np.fft.rfftfreq(L, 1 / SR)
    F *= 1 / (1 + (fr / fc) ** 4); w = np.fft.irfft(F, L); return w / (np.abs(w).max() + 1e-9)
def put(buf, t, sig, g):
    i0 = int(t * SR)
    if i0 < 0: sig = sig[-i0:]; i0 = 0
    i1 = min(len(buf), i0 + len(sig)); buf[i0:i1] += g * sig[:i1 - i0]
def env(L, a, d):
    x = np.arange(L) / SR; return np.minimum(1, x / max(a, 1e-4)) * np.exp(-np.maximum(0, x - a) / d)

V.T_IGNSHOT_S = V.Sx(0, 2) - 0.15
sfx = np.zeros(N); bed = np.zeros(N)
ts = np.arange(0, DUR, 0.01)
def curve(fn): return np.interp(t_all, ts, [fn(x) for x in ts])
def clack(g=1.0):
    L = int(0.12 * SR); x = np.arange(L) / SR
    return bandnoise(L, 2500, q=1.0) * np.exp(-x * 120) + 0.8 * np.sin(2 * np.pi * 110 * x) * np.exp(-x * 30)
def tick(f=3200):
    L = int(0.03 * SR); x = np.arange(L) / SR
    return bandnoise(L, f, q=0.6) * np.exp(-x * 260)
def whoosh(dur, fc, q=0.5, peak=0.5):
    L = int(dur * SR); x = np.arange(L) / SR
    return bandnoise(L, fc, q=q) * np.exp(-((x - peak * dur) / (0.3 * dur)) ** 2)
# --- intro hit
L = int(2.2 * SR); x = np.arange(L) / SR
put(sfx, 0.0, np.sin(2 * np.pi * (58 - 18 * x) * x) * np.exp(-x * 2.6) + 0.25 * bandnoise(L, 4000, q=0.8) * np.exp(-x * 3), 0.85)
# --- rewind glitch
L = int(0.7 * SR); x = np.arange(L) / SR
sw = bandnoise(L, 1500, q=1.2) * np.exp(-((x - 0.25) / 0.18) ** 2)
sq = np.sign(np.sin(2 * np.pi * (900 - 700 * x / 0.7) * x)) * (np.sin(2 * np.pi * 23 * x) > 0.3) * np.exp(-x * 4)
put(sfx, V.T_REW - 0.05, 0.6 * sw + 0.12 * sq, 0.6)
# --- chapter whooshes
for p in range(1, V.NPARA):
    put(sfx, V.P(p) - 0.55, whoosh(0.8, 1800, 0.5, 0.62), 0.3)
# --- fire crackle (proportional to the flame) + low roar
pw = curve(V.power)
crack = np.zeros(N); tt = 0.0
while tt < DUR:
    put(crack, tt, tick(rng.uniform(1500, 4500)), rng.uniform(0.3, 1.0)); tt += rng.exponential(0.09)
roar = lowpass_noise(N, 260)
sfx += (0.10 * crack + 0.05 * roar) * pw
# --- smoke extractor hum + room-air fan whoosh
ex = curve(V.ext); cv = curve(V.conv)
hum = (np.sin(2 * np.pi * 95 * t_all) + 0.5 * np.sin(2 * np.pi * 190 * t_all + 1) + 0.25 * np.sin(2 * np.pi * 380 * t_all + 2)) / 1.75
sfx += 0.035 * hum * ex + 0.03 * bandnoise(N, 900, q=0.9) * ex
sfx += 0.035 * bandnoise(N, 600, q=0.6) * cv
emph = curve(lambda t: V.win(t, V.P(4), V.Sx(4, 2), 0.4))
sfx += 0.05 * hum * ex * emph
# --- screw motor whir + pellet ticks (dose by dose)
fd = curve(V.feed)
sfx += 0.03 * (np.sin(2 * np.pi * 140 * t_all) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t_all))) * fd
tt = 0.0
while tt < DUR:
    if V.feed(tt) > 0.1: put(sfx, tt, tick(rng.uniform(2200, 3600)), 0.10 * V.feed(tt))
    tt += 0.33
# --- pellets dropping into the pot during the first load
tt = V.T_FEED0 + 1.0
while tt < V.T_FEED1:
    put(sfx, tt, tick(1800), 0.18); tt += rng.uniform(0.18, 0.4)
# --- igniter : electric buzz + hot air hiss (the "hair dryer"), then the whoomp of ignition
ig = curve(V.igniter)
sfx += (0.025 * np.sign(np.sin(2 * np.pi * 100 * t_all)) * 0.3 + 0.05 * bandnoise(N, 3500, q=0.7)) * ig * curve(lambda t: 1.0 if t >= V.T_IGNSHOT_S else 0.0)
L = int(1.2 * SR); x = np.arange(L) / SR
put(sfx, V.T_FLAME, lowpass_noise(L, 300) * env(L, 0.08, 0.5), 0.5)
put(sfx, V.Sx(0, 2) - 0.2, whoosh(1.4, 2600, 0.6, 0.4), 0.25)
# --- pressure switch : click, then the hypothetical "no draft" buzz
put(sfx, V.Sx(4, 2) + 0.2, clack(), 0.35)
L = int(0.35 * SR); x = np.arange(L) / SR
put(sfx, V.Sx(4, 3) + 0.1, np.sign(np.sin(2 * np.pi * 220 * x)) * env(L, 0.01, 0.12) * 0.5, 0.12)
# --- extinction : screw stops (clunk), fans run on, then switch off
put(sfx, V.T_STOP, clack(), 0.4)
put(sfx, V.T_FANS_OFF - 0.6, whoosh(1.0, 500, 0.6, 0.3), 0.2)
# --- bonus : electric zaps, then the power cut (thunk + everything spins down)
for k in range(4):
    L = int(0.12 * SR); x = np.arange(L) / SR
    put(sfx, V.Sx(8, 1) + 0.2 + k * 0.9, bandnoise(L, 5000, q=0.5) * env(L, 0.003, 0.04), 0.12)
L = int(0.9 * SR); x = np.arange(L) / SR
put(sfx, V.T_CUT, np.sin(2 * np.pi * (80 - 50 * x) * x) * env(L, 0.004, 0.3) + 0.4 * lowpass_noise(L, 400) * env(L, 0.002, 0.08), 0.6)
put(sfx, V.T_CUT, np.sin(2 * np.pi * np.cumsum(190 - 160 * x) / SR) * np.exp(-x * 3), 0.12)
# --- label pops
for lb in V.LABELS:
    L = int(0.035 * SR); x = np.arange(L) / SR
    put(sfx, lb[0] + 0.05, np.sin(2 * np.pi * 1800 * x) * env(L, 0.002, 0.012), 0.1)
# --- outro rise + ding
L = int(1.4 * SR); x = np.arange(L) / SR
put(sfx, V.Sx(9, 1) - 1.3, bandnoise(L, 2500, q=0.7) * (x / 1.4) ** 2 * np.exp(-np.maximum(0, x - 1.3) * 30), 0.35)
L = int(1.6 * SR); x = np.arange(L) / SR
put(sfx, V.Sx(9, 1) - 0.05, (np.sin(2 * np.pi * 1320 * x) + 0.5 * np.sin(2 * np.pi * 1980 * x)) * env(L, 0.004, 0.5), 0.14)
# --- ambient pad (D minor)
for f, a in ((73.42, 0.5), (110.0, 0.35), (146.83, 0.3), (174.61, 0.18), (220.0, 0.16), (293.66, 0.07)):
    for det in (-0.25, 0.25):
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.03 + f / 9000) * t_all + f)
        bed += a * lfo * np.sin(2 * np.pi * (f + det) * t_all + rng.uniform(0, 6))
bed = bed / np.abs(bed).max() * 0.55 + 0.1 * bandnoise(N, 900, q=0.6)
bed *= np.clip(t_all / 1.5, 0, 1) * np.clip((DUR - t_all) / 1.5, 0, 1)
def wr(name, a):
    a = np.clip(a, -1, 1)
    with wave.open(name, 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((a * 32767).astype(np.int16).tobytes())
wr('/home/claude/d003/sfx.wav', sfx * 0.5); wr('/home/claude/d003/bed.wav', bed * 0.16)
print('ok', round(np.abs(sfx * 0.5).max(), 3), round(np.sqrt(np.mean((sfx * 0.5) ** 2)), 4))
