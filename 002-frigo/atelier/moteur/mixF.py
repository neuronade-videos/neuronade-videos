import sys, wave, math, numpy as np
sys.path.insert(0, '/home/claude/d002')
import holo3 as V
V.T_JET = V.word_t(0, 1, 'jette') - 0.15

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
ts = np.arange(0, DUR, 0.01)
def curve(fn): return np.interp(t_all, ts, [fn(x) for x in ts])
def clack(g=1.0):
    L = int(0.12 * SR); x = np.arange(L) / SR
    return bandnoise(L, 2500, q=1.0) * np.exp(-x * 120) + 0.8 * np.sin(2 * np.pi * 110 * x) * np.exp(-x * 30)
def drip():
    L = int(0.12 * SR); x = np.arange(L) / SR; f = 1500 - 600 * (x / 0.12)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 45) + 0.3 * bandnoise(L, 5000) * np.exp(-x * 200)
def whoosh(dur, fc, q=0.5, peak=0.5):
    L = int(dur * SR); x = np.arange(L) / SR
    return bandnoise(L, fc, q=q) * np.exp(-((x - peak * dur) / (0.3 * dur)) ** 2)
# --- intro hit (boom + shimmer)
L = int(2.2 * SR); x = np.arange(L) / SR
put(sfx, 0.0, np.sin(2 * np.pi * (58 - 18 * x) * x) * np.exp(-x * 2.6) + 0.25 * bandnoise(L, 4000, q=0.8) * np.exp(-x * 3), 0.85)
# --- hook: warm air leaving the back of the fridge
put(sfx, V.word_t(0, 1, 'jette') - 0.3, whoosh(1.6, 500, 0.6, 0.35), 0.35)
# --- rewind glitch
L = int(0.7 * SR); x = np.arange(L) / SR
sw = bandnoise(L, 1500, q=1.2) * np.exp(-((x - 0.25) / 0.18) ** 2)
sq = np.sign(np.sin(2 * np.pi * (900 - 700 * x / 0.7) * x)) * (np.sin(2 * np.pi * 23 * x) > 0.3) * np.exp(-x * 4)
put(sfx, V.T_REW - 0.05, 0.6 * sw + 0.12 * sq, 0.6)
# --- chapter whooshes
for p in range(1, V.NPARA):
    put(sfx, V.P(p) - 0.55, whoosh(0.8, 1800, 0.5, 0.62), 0.3)
# --- compressor: relay clicks, motor hum (50 Hz family + mechanical rattle), refrigerant hiss
cp = curve(V.comp)
hum = (np.sin(2 * np.pi * 50 * t_all) + 0.6 * np.sin(2 * np.pi * 100 * t_all + 1) + 0.35 * np.sin(2 * np.pi * 150 * t_all + 2)
       + 0.15 * np.sin(2 * np.pi * 300 * t_all)) / 2.1
rattle = lowpass_noise(N, 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 25 * t_all))
emph = curve(lambda t: 1.0 + 1.6 * V.win(t, V.Sx(4, 2) - 0.3, V.P(5) - 0.2, 0.4) + 0.6 * V.win(t, V.T_JET if hasattr(V, 'T_JET') else 6.1, V.T_REW, 0.3))
sfx += (0.07 * hum + 0.03 * rattle) * cp * emph
hiss = bandnoise(N, 4200, q=0.7) * (0.75 + 0.25 * np.sin(2 * np.pi * 3.1 * t_all))
caph = curve(lambda t: V.win(t, V.Sx(6, 1) - 0.2, V.P(7) - 0.4, 0.3))
sfx += hiss * cp * (0.012 + 0.07 * caph)
gurgle = lowpass_noise(N, 900) * (np.sin(2 * np.pi * 1.7 * t_all) > 0.6)
sfx += 0.02 * gurgle * cp
for tc in (V.T_ON, V.T_ON2, V.T_ON3):
    put(sfx, tc - 0.06, clack(), 0.5)
    L = int(0.6 * SR); x = np.arange(L) / SR; put(sfx, tc, np.sin(2 * np.pi * (35 + 15 * x) * x) * env(L, 0.02, 0.25), 0.45)
for tc in (V.T_OFF1, V.T_OFF2):
    put(sfx, tc, clack(), 0.5)
    L = int(0.5 * SR); x = np.arange(L) / SR; put(sfx, tc + 0.05, np.sin(2 * np.pi * (50 - 25 * x) * x) * env(L, 0.01, 0.18), 0.35)
# --- thermostat: tiny beep when the set point is reached + signal sweep to the compressor
for tc, f0 in ((V.T_OFF1 - 0.5, 2000), (V.T_ON2 - 0.5, 1500)):
    for k in range(2):
        L = int(0.07 * SR); x = np.arange(L) / SR
        put(sfx, tc + k * 0.14, np.sin(2 * np.pi * f0 * x) * env(L, 0.003, 0.03), 0.2)
# --- heat handed to the kitchen (condenser) : warm low whoosh
put(sfx, V.word_t(5, 1, 'cède') - 0.4, whoosh(1.8, 380, 0.6, 0.4), 0.4)
# --- frost: tiny crystal tinkles ; defrost: drips into the tray ; evaporation sigh
tt = V.Sx(8, 2) + 0.2
while tt < V.Se(8, 2):
    L = int(0.25 * SR); x = np.arange(L) / SR; f = rng.uniform(3500, 6000)
    put(sfx, tt, np.sin(2 * np.pi * f * x) * env(L, 0.002, 0.06), 0.06); tt += rng.uniform(0.12, 0.3)
tt = V.word_t(8, 3, 'fond') + 0.2
while tt < V.P(9) - 0.4:
    put(sfx, tt, drip(), 0.28); tt += 0.7
put(sfx, V.word_t(8, 3, 'évapore') - 0.3, whoosh(1.4, 2500, 0.8, 0.5), 0.12)
# --- 'Raté.' : two soft descending tones
for k, f in enumerate((520, 390)):
    L = int(0.2 * SR); x = np.arange(L) / SR
    put(sfx, V.Sx(9, 1) - 0.05 + k * 0.16, (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * 2 * f * x)) * env(L, 0.004, 0.09), 0.18)
# --- door: open (seal pop + air), close (soft thump)
L = int(0.5 * SR); x = np.arange(L) / SR
put(sfx, V.T_DOOR_O - 0.05, 0.9 * lowpass_noise(L, 700) * env(L, 0.005, 0.08) + 0.5 * bandnoise(L, 1200, q=0.6) * env(L, 0.05, 0.25), 0.5)
put(sfx, V.T_DOOR_C - 0.08, 0.9 * np.sin(2 * np.pi * (70 - 30 * x) * x) * env(L, 0.003, 0.08) + 0.4 * lowpass_noise(L, 500) * env(L, 0.002, 0.05), 0.6)
# --- label pops
for lb in V.LABELS:
    L = int(0.035 * SR); x = np.arange(L) / SR
    put(sfx, lb[0] + 0.05, np.sin(2 * np.pi * 1800 * x) * env(L, 0.002, 0.012), 0.1)
# --- outro rise + ding
L = int(1.4 * SR); x = np.arange(L) / SR
put(sfx, V.Sx(10, 1) - 1.3, bandnoise(L, 2500, q=0.7) * (x / 1.4) ** 2 * np.exp(-np.maximum(0, x - 1.3) * 30), 0.35)
L = int(1.6 * SR); x = np.arange(L) / SR
put(sfx, V.Sx(10, 1) - 0.05, (np.sin(2 * np.pi * 1320 * x) + 0.5 * np.sin(2 * np.pi * 1980 * x)) * env(L, 0.004, 0.5), 0.14)
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
wr('/home/claude/d002/sfx.wav', sfx * 0.5); wr('/home/claude/d002/bed.wav', bed * 0.16)
print('ok', round(np.abs(sfx * 0.5).max(), 3), round(np.sqrt(np.mean((sfx * 0.5) ** 2)), 4))
