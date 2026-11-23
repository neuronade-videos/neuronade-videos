"""Find the internal pauses of each sentence and tie them to its punctuation (for precise caption / animation sync)."""
import json, re
import numpy as np, soundfile as sf
TLP = '/home/claude/d003/timeline.json'
TL = json.load(open(TLP))
x, sr = sf.read('/home/claude/d003/audio/voice_el.wav'); hop = sr // 100; n = len(x) // hop
db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, 1) + 1e-12)); thr = np.percentile(db, 95) - 38; sil = db < thr
runs = []; i = 0
while i < n:
    if sil[i]:
        j = i
        while j < n and sil[j]: j += 1
        runs.append((i / 100, j / 100)); i = j
    else: i += 1
BRK = re.compile(r"(\.\.\.|…|[,:;?!])(?=\s+\S)")
tot_breaks = 0
for s in TL['sents']:
    txt = s['text']; t0, t1 = s['t0'], s['t1']
    marks = [m.end() for m in BRK.finditer(txt)]
    pauses = [(a, b) for (a, b) in runs if a > t0 + 0.15 and b < t1 - 0.15 and b - a >= 0.07]
    P_, M_ = len(pauses), len(marks)
    exp = [t0 + (t1 - t0) * pos / len(txt) for pos in marks]
    dp = [[0.0] * (M_ + 1) for _ in range(P_ + 1)]; bk = [[None] * (M_ + 1) for _ in range(P_ + 1)]
    for i in range(P_ + 1):
        for j in range(M_ + 1):
            if i == 0 and j == 0: continue
            best = (-1e9, None)
            if i > 0 and dp[i - 1][j] > best[0]: best = (dp[i - 1][j], 'p')
            if j > 0 and dp[i][j - 1] > best[0]: best = (dp[i][j - 1], 'm')
            if i > 0 and j > 0:
                dl = abs(exp[j - 1] - pauses[i - 1][0])
                if dl < 1.3 and dp[i - 1][j - 1] + 1 + 0.2 * (1 - dl / 1.3) > best[0]: best = (dp[i - 1][j - 1] + 1 + 0.2 * (1 - dl / 1.3), 'x')
            dp[i][j], bk[i][j] = best
    out = []; i, j = P_, M_
    while i > 0 or j > 0:
        b = bk[i][j]
        if b == 'x': out.append([j - 1, round(pauses[i - 1][0], 3), round(pauses[i - 1][1], 3)]); i -= 1; j -= 1
        elif b == 'p': i -= 1
        else: j -= 1
    out = out[::-1]
    s['breaks'] = out; tot_breaks += len(out)
    print('%2d.%d %d/%d  %s' % (s['p'], s['s'], len(out), len(marks), ' | '.join('%s@%.2f' % (txt[max(0, marks[k] - 8):marks[k]], a) for k, a, b in out)))

json.dump(TL, open(TLP, 'w'), ensure_ascii=False, indent=1)
print('breaks', tot_breaks)
