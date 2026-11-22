"""Sentence-level alignment of the ElevenLabs voice to the known script.
Silence detection + dynamic programming over candidate pauses (expected durations ~ characters)."""
import json, sys
import numpy as np, soundfile as sf

V3 = json.load(open('/home/claude/v3/timeline.json'))
NEW = {(0, 0): "Ta chaudière pleure ?",
       (0, 1): "Pas de panique : ce n'est pas une dépression... c'est de la condensation.",
       (0, 2): "Regarde ce qui se passe à l'intérieur quand tu montes le thermostat.",
       (9, 0): "Voilà pourquoi ta chaudière « pleure » !"}
SENTS = [dict(p=s['p'], s=s['s'], text=NEW.get((s['p'], s['s']), s['text'])) for s in V3['sents']]

x, sr = sf.read('/home/claude/v7/audio/voice_el.wav')
hop = int(sr * 0.01)
n = len(x) // hop
rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
db = 20 * np.log10(rms)
thr = np.percentile(db, 95) - 38            # relative threshold
sil = db < thr
# silent runs
runs = []; i = 0
while i < n:
    if sil[i]:
        j = i
        while j < n and sil[j]: j += 1
        runs.append((i, j)); i = j
    else: i += 1
speech_start = next(j for (i, j) in runs if i == 0) if runs and runs[0][0] == 0 else 0
speech_end = runs[-1][0] if runs and runs[-1][1] == n else n
cands = [(i, j) for (i, j) in runs if i > speech_start and j < speech_end and (j - i) >= 12]  # >=120 ms
print('threshold dB', round(thr, 1), 'speech', speech_start / 100, speech_end / 100, 'candidate pauses', len(cands), file=sys.stderr)

N = len(SENTS)
L = np.array([len(s['text']) for s in SENTS], float)
tot_speech = (speech_end - speech_start) / 100.0
# boundary k (between sentence k and k+1) is chosen among cands; DP over cands in order
C = len(cands)
mid = np.array([(i + j) / 2 / 100 for (i, j) in cands]); plen = np.array([(j - i) / 100 for (i, j) in cands])
para_break = [SENTS[k]['p'] != SENTS[k + 1]['p'] for k in range(N - 1)]
rate = tot_speech / L.sum()
INF = 1e18
# dp[k][c]: best cost with boundary k placed at cand c
dp = np.full((N - 1, C), INF); bk = np.zeros((N - 1, C), int)
def seg_cost(t0, t1, k):
    exp = L[k] * rate; d = t1 - t0
    return ((d - exp) / max(0.6, exp * 0.25)) ** 2
s0 = speech_start / 100; s1 = speech_end / 100
for c in range(C):
    dp[0][c] = seg_cost(s0, cands[c][0] / 100, 0) - (6 if para_break[0] else 3) * min(plen[c], 1.0)
for k in range(1, N - 1):
    bonus = (6 if para_break[k] else 3)
    for c in range(k, C):
        prev = dp[k - 1][:c] + np.array([seg_cost(cands[q][1] / 100, cands[c][0] / 100, k) for q in range(c)])
        q = int(np.argmin(prev)); dp[k][c] = prev[q] - bonus * min(plen[c], 1.0); bk[k][c] = q
fin = dp[N - 2] + np.array([seg_cost(cands[c][1] / 100, s1, N - 1) for c in range(C)])
c = int(np.argmin(fin)); path = [c]
for k in range(N - 2, 0, -1): c = bk[k][c]; path.append(c)
path = path[::-1]
out = []; t = s0
for k in range(N):
    if k < N - 1:
        i, j = cands[path[k]]; t1 = i / 100; nxt = j / 100
    else: t1 = s1; nxt = None
    out.append(dict(p=SENTS[k]['p'], s=SENTS[k]['s'], text=SENTS[k]['text'], t0=round(t, 3), t1=round(t1, 3)))
    t = nxt
for o in out:
    exp = len(o['text']) * rate
    print('%2d.%d %7.2f %7.2f  dur %5.2f exp %5.2f  %s' % (o['p'], o['s'], o['t0'], o['t1'], o['t1'] - o['t0'], exp, o['text'][:60]))
# report unused long pauses (possible internal pauses)
used = set(path)
print('internal pauses >=0.35 s not used as boundaries:')
for q, (i, j) in enumerate(cands):
    if q not in used and (j - i) >= 35: print('   %.2f-%.2f (%.2f s)' % (i / 100, j / 100, (j - i) / 100))
json.dump(dict(sents=out, total=round(len(x) / sr, 3)), open('/home/claude/v7/timeline_raw.json', 'w'), ensure_ascii=False, indent=1)
