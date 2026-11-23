import sys, wave, math, numpy as np
sys.path.insert(0, '/home/claude/d003')
import holo3 as V
from scipy.signal import fftconvolve, butter, sosfilt
SR = 44100; DUR = V.DUR; N = int(DUR * SR); t = np.arange(N) / SR
rng = np.random.default_rng(5)
BPM = 100; BEAT = 60 / BPM; BAR = 4 * BEAT
def hz(m): return 440 * 2 ** ((m - 69) / 12)
# Dm - Bb - F - C  (2 bars each)
CH = [(62, 65, 69), (58, 62, 65), (65, 69, 72), (60, 64, 67)]
ROOT = [38, 34, 41, 36]
def chord_at(x): return int(x // (2 * BAR)) % 4
lp = lambda f, x, o=2: sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
hp = lambda f, x, o=2: sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
# --- pad: per chord segment, detuned saws lowpassed, slow attack/release
pad = np.zeros(N); padR = np.zeros(N); seg = int(2 * BAR * SR)
for k in range(int(N / seg) + 1):
    i0 = k * seg; i1 = min(N, i0 + seg + int(1.5 * SR))
    if i0 >= N: break
    L = i1 - i0; x = np.arange(L) / SR; s = np.zeros(L); s2 = np.zeros(L)
    for m in CH[k % 4]:
        for det in (-0.1, 0.0, 0.1):
            f = hz(m - 12) * 2 ** (det / 12); f2 = hz(m - 12) * 2 ** ((det + 0.06) / 12)
            s += (2 * ((f * x + rng.random()) % 1) - 1) * 0.33; s2 += (2 * ((f2 * x + rng.random()) % 1) - 1) * 0.33
    e = np.minimum(1, x / 1.2) * np.clip((L / SR - x) / 1.5, 0, 1)
    pad[i0:i1] += s * e; padR[i0:i1] += s2 * e
pad = lp(900, pad, 4) * 0.22; padR = lp(900, padR, 4) * 0.22
# --- arpeggio: 8th notes through chord tones, plucked sine/triangle, + echo
arp = np.zeros(N); step = BEAT / 2; pat = [0, 1, 2, 1, 2, 0, 1, 2]
n = 0; x0 = 0.0
while x0 < DUR:
    ch = CH[chord_at(x0)]; m = ch[pat[n % 8]] + 12 + (12 if n % 16 >= 12 else 0)
    L = int(0.45 * SR); x = np.arange(L) / SR; f = hz(m)
    note = (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 7)
    i0 = int(x0 * SR); i1 = min(N, i0 + L); arp[i0:i1] += note[:i1 - i0] * 0.18
    n += 1; x0 += step
d = int(BEAT * 0.75 * SR); eL = np.zeros(N); eR = np.zeros(N); eR[d:] = arp[:-d] * 0.42; eL[2 * d:] = arp[:-2 * d] * 0.22; eR[3 * d:] += arp[:-3 * d] * 0.1
arpL = lp(3500, arp + eL); arpR = lp(3500, arp + eR); arp = (arpL + arpR) / 2
# --- bass: root on beats 1 and 3 (+ syncopation)
bass = np.zeros(N); x0 = 0.0
while x0 < DUR:
    for b, ln in ((0, 1.4), (2, 0.9), (3.5, 0.4)):
        tt = x0 + b * BEAT
        if tt >= DUR: continue
        f = hz(ROOT[chord_at(tt)]); L = int(ln * BEAT * SR); x = np.arange(L) / SR
        nt = np.sin(2 * np.pi * f * x) * np.minimum(1, x / 0.01) * np.exp(-x * 1.5)
        i0 = int(tt * SR); i1 = min(N, i0 + L); bass[i0:i1] += nt[:i1 - i0] * 0.42
    x0 += BAR
bass = lp(220, bass)
# --- drums: soft kick 1&3, hats on 8ths, light clap on 2&4
kick = np.zeros(N); hat = np.zeros(N); clap = np.zeros(N)
L = int(0.35 * SR); x = np.arange(L) / SR
K = np.sin(2 * np.pi * (52 + 70 * np.exp(-x * 30)) * x) * np.exp(-x * 9)
Lh = int(0.05 * SR); Hh = hp(7000, rng.standard_normal(Lh)) * np.exp(-np.arange(Lh) / SR * 90)
Lc = int(0.2 * SR); C = sosfilt(butter(2, [900, 2500], 'band', fs=SR, output='sos'), rng.standard_normal(Lc)) * np.exp(-np.arange(Lc) / SR * 22)
bt = 0.0; k = 0
while bt < DUR:
    i0 = int(bt * SR)
    if k % 4 in (0, 2) and i0 + L < N: kick[i0:i0 + L] += K
    if k % 4 in (1, 3) and i0 + Lc < N: clap[i0:i0 + Lc] += C
    for h in (0, 0.5):
        j = int((bt + h * BEAT) * SR)
        if j + Lh < N: hat[j:j + Lh] += Hh * (0.6 if h else 0.35)
    k += 1; bt += BEAT
drums = kick * 0.55 + hat * 0.12 + clap * 0.10
# --- arrangement envelopes
def ramp(a, b): return np.clip((t - a) / (b - a), 0, 1)
start_beat = V.P(1) - 0.3; stop_beat = V.Sx(9, 1) - 0.2
g_drums = ramp(start_beat - 0.01, start_beat) * (1 - ramp(stop_beat, stop_beat + 0.3))
g_bass = ramp(V.T_REW, V.T_REW + 2.5) * (1 - ramp(stop_beat, stop_beat + 1.5))
g_arp = 0.55 + 0.45 * ramp(V.T_REW, V.T_REW + 2)
fade = np.clip(t / 0.8, 0, 1) * np.clip((DUR - t) / 2.0, 0, 1)
L_ = (pad * 1.0 + arpL * g_arp + bass * g_bass + (kick * 0.55 + hat * 0.08 + clap * 0.12) * g_drums) * fade
R_ = (padR * 1.0 + arpR * g_arp + bass * g_bass + (kick * 0.55 + hat * 0.16 + clap * 0.08) * g_drums) * fade
ir_L = int(2.0 * SR)
def mk_ir():
    ir = rng.standard_normal(ir_L) * np.exp(-np.arange(ir_L) / SR * 2.8); ir = lp(5500, ir); return ir / np.sqrt(np.sum(ir ** 2))
irl, irr = mk_ir(), mk_ir()
L_ = L_ + fftconvolve((pad + arpL * g_arp) * fade, irl)[:N] * 0.35
R_ = R_ + fftconvolve((padR + arpR * g_arp) * fade, irr)[:N] * 0.35
pk = max(np.abs(L_).max(), np.abs(R_).max()); L_ = L_ / pk * 0.9; R_ = R_ / pk * 0.9
st = np.stack([L_, R_], 1)
with wave.open('/home/claude/d003/music_st.wav', 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes())
print('music stereo ok')
