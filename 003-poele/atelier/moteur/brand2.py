"""Intro 'DOSSIER #003' + outro '+1 neurone rafraichi' clips and the sonic-signature track, sized for the final video."""
import sys, os, subprocess, wave
import numpy as np
sys.path.insert(0, '/home/claude/d003')
import brand as B
import holo3 as V

W, H, FPS, SR = B.W, B.H, B.FPS, B.SR
INTRO, OUTRO, MAIN = B.INTRO, B.OUTRO, V.NF / V.FPS
OUT = '/home/claude/d003'

def clip(name, n, fn):
    tmp = '%s/seg/%s.tmp.mp4' % (OUT, name)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
           '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-r', str(FPS), '-f', 'mp4', tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(fn(i / FPS).tobytes())
    p.stdin.close()
    if p.wait() == 0: os.rename(tmp, '%s/seg/%s.mp4' % (OUT, name))

def sonic(total):
    N = int(total * SR); out = np.zeros(N); rng = np.random.default_rng(3)
    def put(t, sig, g):
        i0 = int(t * SR); i1 = min(N, i0 + len(sig)); out[i0:i1] += g * sig[:i1 - i0]
    def bell(f, dur, dec):
        x = np.arange(int(dur * SR)) / SR
        return (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(2 * np.pi * 2.01 * f * x) + 0.15 * np.sin(2 * np.pi * 3.0 * f * x)) * np.exp(-x * dec) * np.minimum(1, x / 0.004)
    def fizz(dur):
        L = int(dur * SR); nz = rng.standard_normal(L); F = np.fft.rfft(nz); fr = np.fft.rfftfreq(L, 1 / SR); F *= (fr > 5000) * (fr < 14000)
        w = np.fft.irfft(F, L); w /= np.abs(w).max(); crack = (rng.random(L) < 0.004) * rng.uniform(0.3, 1, L)
        return (w * 0.35 + crack) * np.linspace(0, 1, L) ** 1.5
    def bloop(f0=650, f1=140, dur=0.28):
        x = np.arange(int(dur * SR)) / SR; f = f1 + (f0 - f1) * np.exp(-x * 18)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 9)
    def sub(dur=0.9):
        x = np.arange(int(dur * SR)) / SR; return np.sin(2 * np.pi * (60 - 18 * x) * x) * np.exp(-x * 4)
    def ticks(t0, t1, step=0.045):
        t = t0
        while t < t1:
            L = int(0.012 * SR); x = np.arange(L) / SR; put(t, np.sin(2 * np.pi * 2600 * x) * np.exp(-x * 400), 0.08); t += step
    def signature(t0, final=False):
        put(t0 - 0.6, fizz(0.6), 0.5); put(t0, bloop(900, 300, 0.12), 0.5); put(t0, sub(), 0.6)
        notes = [587.3, 880.0, 1480.0] if not final else [587.3, 880.0, 1174.7, 1480.0]
        for i, f in enumerate(notes): put(t0 + 0.07 + i * 0.11, bell(f, 1.6, 3.2 if i < len(notes) - 1 else 1.8), 0.32)
    ticks(0.1, 0.85); signature(1.02)
    put(INTRO - 0.35, np.convolve(rng.standard_normal(int(0.35 * SR)), np.ones(40) / 40, 'same') * np.linspace(1, 0, int(0.35 * SR)), 0.25)
    o = INTRO + MAIN
    L = int(1.5 * SR); nz = rng.standard_normal(L); F = np.fft.rfft(nz); fr = np.fft.rfftfreq(L, 1 / SR); F *= np.exp(-((np.log(fr + 1) - np.log(1800)) ** 2) / 0.6)
    pour = np.fft.irfft(F, L); pour /= np.abs(pour).max(); put(o + 0.2, pour * np.sin(np.linspace(0, np.pi, L)) * (0.8 + 0.2 * np.sin(np.arange(L) / SR * 2 * np.pi * 9)), 0.22)
    put(o + 2.25, bloop(), 0.7); put(o + 2.25, fizz(0.5)[::-1], 0.25)
    signature(o + 2.8, final=True)
    # soft pad only under the intro and the outro (the main part has its own music)
    x = np.arange(N) / SR; pad = sum(np.sin(2 * np.pi * f * x + p) for f, p in ((146.8, 0), (220.0, 1), (293.7, 2), (370.0, 3))) * 0.04
    w_in = np.clip(x / 0.6, 0, 1) * np.clip((INTRO + 0.3 - x) / 0.5, 0, 1)
    w_out = np.clip((x - o + 0.2) / 0.8, 0, 1) * np.clip((total - x) / 1.0, 0, 1)
    out += pad * (w_in + w_out)
    out = out / np.abs(out).max() * 0.9
    with wave.open(OUT + '/audio/sonic.wav', 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((out * 32767).astype(np.int16).tobytes())

if __name__ == '__main__':
    os.makedirs(OUT + '/seg', exist_ok=True)
    clip('a_intro', int(round(INTRO * FPS)), B.intro_frame)
    clip('z_outro', int(round(OUTRO * FPS)), B.outro_frame)
    sonic(INTRO + MAIN + OUTRO)
    print('ok', INTRO, MAIN, OUTRO, INTRO + MAIN + OUTRO)
