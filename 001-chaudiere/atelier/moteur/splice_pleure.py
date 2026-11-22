"""Remplace la phrase « Voilà pourquoi ta chaudière pleure ! » (2e prise, intonation normale) dans la voix complète."""
import numpy as np, soundfile as sf
x, sr = sf.read('/home/claude/v7/audio/voice_el_orig.wav'); y, _ = sf.read('/home/claude/v7/audio/pleure_new.wav')
seg = y[int(0.03 * sr):int(2.10 * sr)].copy() * 10 ** (-0.7 / 20)
f = int(0.012 * sr); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
out = x.copy(); out[int(102.49 * sr):int(105.65 * sr)] = 0.0
i0 = int(102.92 * sr); out[i0:i0 + len(seg)] += seg
sf.write('/home/claude/v7/audio/voice_el.wav', out, sr, subtype='PCM_16')
