import json, wave, numpy as np
SR = 44100; TOTAL = 168.5
g = json.load(open('/home/claude/v7/audio/glitch_times.json')); rng = np.random.default_rng(7)
N = int(TOTAL * SR); L = np.zeros(N); R = np.zeros(N)
for t, dur in zip(g['times'], g['durs']):
    n = int(dur * SR); x = np.arange(n) / SR
    nz = rng.standard_normal(n); F = np.fft.rfft(nz); fr = np.fft.rfftfreq(n, 1 / SR); F *= (fr > 1500) * (fr < 9000)
    st = np.fft.irfft(F, n); st /= np.abs(st).max()
    gate = (np.sin(2 * np.pi * 47 * x) > -0.2).astype(float)            # stuttering digital static
    bit = np.sin(2 * np.pi * 820 * x) * 0.25 * (x < 0.06)       # tiny data chirp at the start
    env = np.minimum(1, x / 0.004) * np.minimum(1, (dur - x) / 0.02)
    s = (st * gate * 0.5 + bit) * env * 0.22
    i0 = int(t * SR); L[i0:i0 + n] += s; R[i0:i0 + n] += np.roll(s, 37)
out = np.clip(np.stack([L, R], 1), -1, 1)
with wave.open('/home/claude/v7/audio/glitch.wav', 'wb') as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((out * 32767).astype(np.int16).tobytes())
expr = '+'.join('between(t,%.3f,%.3f)' % (t - 0.01, t + d + 0.02) for t, d in zip(g['times'], g['durs']))
open('/home/claude/v7/audio/duck_expr.txt', 'w').write(expr); print(expr)
