import sys, wave, math, numpy as np
sys.path.insert(0, '/home/claude/v7')
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

sfx = np.zeros(N); bed = np.zeros(N)
# --- intro hit (boom + shimmer)
L = int(2.2 * SR); x = np.arange(L) / SR
put(sfx, 0.0, np.sin(2 * np.pi * (58 - 18 * x) * x) * np.exp(-x * 2.6) + 0.25 * bandnoise(L, 4000, q=0.8) * np.exp(-x * 3), 0.85)
# --- drips (hook + answer)
def drip():
    L = int(0.12 * SR); x = np.arange(L) / SR; f = 1500 - 600 * (x / 0.12)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 45) + 0.3 * bandnoise(L, 5000) * np.exp(-x * 200)
for a, b in ((0.3, V.T_REW - 0.1), (V.P(9) + 0.4, V.Sx(9, 1) + 0.6)):
    tt = a
    while tt < b: put(sfx, tt, drip(), 0.32); tt += 0.8
# --- rewind glitch
L = int(0.7 * SR); x = np.arange(L) / SR
sw = bandnoise(L, 1500, q=1.2) * np.exp(-((x - 0.25) / 0.18) ** 2)
sq = np.sign(np.sin(2 * np.pi * (900 - 700 * x / 0.7) * x)) * (np.sin(2 * np.pi * 23 * x) > 0.3) * np.exp(-x * 4)
put(sfx, V.T_REW - 0.05, 0.6 * sw + 0.12 * sq, 0.6)
# --- chapter whooshes
for p in range(1, V.NPARA):
    L = int(0.8 * SR); x = np.arange(L) / SR
    w = bandnoise(L, 1800, q=0.5) * np.exp(-((x - 0.5) / 0.16) ** 2)
    put(sfx, V.P(p) - 0.55, w, 0.3)
# --- thermostat beeps + signal sweep
for k in range(2):
    L = int(0.07 * SR); x = np.arange(L) / SR
    put(sfx, V.T_DEMAND - 0.45 + k * 0.14, np.sin(2 * np.pi * 2000 * x) * env(L, 0.003, 0.03), 0.22)
for (a0, a1) in ((V.T_DEMAND - 0.4, V.T_DEMAND + 1.4), (V.T_ROOM20 - 0.2, V.T_ROOM20 + 1.4)):
    L = int((a1 - a0) * SR); x = np.arange(L) / SR; f = 300 + 900 * x / (a1 - a0)
    put(sfx, a0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * x / (a1 - a0)) ** 2, 0.06)
# --- clicks (gas valve on/off, 3-way valve)
def clack():
    L = int(0.12 * SR); x = np.arange(L) / SR
    return bandnoise(L, 2500, q=1.0) * np.exp(-x * 120) + 0.8 * np.sin(2 * np.pi * 110 * x) * np.exp(-x * 30)
put(sfx, V.T_GAS, clack(), 0.45); put(sfx, V.T_GASOFF, clack(), 0.45)
L = int(0.7 * SR); x = np.arange(L) / SR
buzz = np.sign(np.sin(2 * np.pi * 140 * x)) * 0.5 + np.sin(2 * np.pi * 280 * x)
put(sfx, V.T_DHW, buzz * np.sin(np.pi * x / 0.7) ** 2 * 0.3, 0.18); put(sfx, V.T_DHW + 0.65, clack(), 0.3)
# --- sparks
tt = V.T_SPARK
while tt < V.T_FLAME:
    L = int(0.04 * SR); x = np.arange(L) / SR
    put(sfx, tt, bandnoise(L, 3500, q=1.5) * np.exp(-x * 150) + 0.4 * np.sin(2 * np.pi * 3200 * x) * np.exp(-x * 90), 0.5); tt += 0.11
# --- ignition whoomp
L = int(1.3 * SR); x = np.arange(L) / SR
wh = lowpass_noise(L, 260) * env(L, 0.03, 0.45) + 0.7 * np.sin(2 * np.pi * (62 - 20 * x) * x) * env(L, 0.02, 0.5)
put(sfx, V.T_FLAME - 0.03, wh, 0.95)
# --- continuous beds: burner roar, fan, pump, tap
ts = np.arange(0, DUR, 0.01)
def curve(fn): return np.interp(t_all, ts, [fn(x) for x in ts])
roar = lowpass_noise(N, 220); fanw = bandnoise(N, 700, q=0.8); hum = np.sin(2 * np.pi * 100 * t_all) + 0.5 * np.sin(2 * np.pi * 200 * t_all)
water = bandnoise(N, 3500, q=0.9) * (0.7 + 0.3 * np.sin(2 * np.pi * 7 * t_all))
cont = 0.32 * roar * curve(lambda t: V.flame(t) * (0.5 + 0.5 * V.power(t))) + 0.11 * fanw * curve(V.fan) + 0.025 * hum * curve(V.pump) + 0.16 * water * curve(V.tap)
sfx += cont
# --- label pops + alert tones + error beeps
for lb in V.LABELS:
    L = int(0.035 * SR); x = np.arange(L) / SR
    put(sfx, lb[0] + 0.05, np.sin(2 * np.pi * 1800 * x) * env(L, 0.002, 0.012), 0.1)
for w in ('flamme absente', 'surchauffe', 'manque'):
    t0 = V.word_t(12, 0, w)
    for k, f in enumerate((880, 660)):
        L = int(0.11 * SR); x = np.arange(L) / SR
        put(sfx, t0 + k * 0.12, np.sin(2 * np.pi * f * x) * env(L, 0.005, 0.06), 0.16)
t0 = V.word_t(12, 0, 'code') - 0.2
for k in range(3):
    L = int(0.08 * SR); x = np.arange(L) / SR
    put(sfx, t0 + k * 0.25, np.sign(np.sin(2 * np.pi * 1200 * x)) * env(L, 0.002, 0.04), 0.07)
# --- outro rise + ding
L = int(1.4 * SR); x = np.arange(L) / SR
put(sfx, V.Sx(13, 1) - 1.3, bandnoise(L, 2500, q=0.7) * (x / 1.4) ** 2 * np.exp(-np.maximum(0, x - 1.3) * 30), 0.35)
L = int(1.6 * SR); x = np.arange(L) / SR
put(sfx, V.Sx(13, 1) - 0.05, (np.sin(2 * np.pi * 1320 * x) + 0.5 * np.sin(2 * np.pi * 1980 * x)) * env(L, 0.004, 0.5), 0.14)
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
wr('/home/claude/v7/sfx.wav', sfx * 0.5); wr('/home/claude/v7/bed.wav', bed * 0.16)
print('ok', round(np.abs(sfx * 0.5).max(), 3), round(np.sqrt(np.mean((sfx * 0.5) ** 2)), 4))
