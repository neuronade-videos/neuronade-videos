"""Transcribe each aligned sentence with Whisper (sherpa-onnx) and compare to the script."""
import json, glob, re, unicodedata, difflib
import numpy as np, soundfile as sf, sherpa_onnx
from scipy.signal import resample_poly

D = '/home/claude/models/sherpa-onnx-whisper-small/'
enc = sorted(glob.glob(D + '*encoder.int8.onnx'))[0]; dec = sorted(glob.glob(D + '*decoder.int8.onnx'))[0]; tok = sorted(glob.glob(D + '*tokens.txt'))[0]
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=enc, decoder=dec, tokens=tok, language='fr', task='transcribe', num_threads=4)
x, sr = sf.read('/home/claude/v7/audio/voice_el.wav')
x16 = resample_poly(x, 160, 441).astype(np.float32)
TL = json.load(open('/home/claude/v7/timeline_raw.json'))
def norm(s):
    s = unicodedata.normalize('NFKD', s.lower()); s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('’', "'").replace('-', ' ')
    return re.sub(r"[^a-z0-9' ]", ' ', s).split()
NUM = {'17': 'dix sept', '20': 'vingt', '10': 'dix', '60': 'soixante', '70': 'soixante dix', '3': 'trois', '55': 'cinquante cinq', '1': 'un', '%': 'pour cent'}
bad = 0
for s in TL['sents']:
    a = max(0, int((s['t0'] - 0.12) * 16000)); b = int((s['t1'] + 0.15) * 16000)
    st = rec.create_stream(); st.accept_waveform(16000, x16[a:b]); rec.decode_stream(st)
    hyp = st.result.text.strip()
    h = ' '.join(norm(hyp)); h = ' '.join(NUM.get(w, w) for w in h.split())
    r = ' '.join(norm(s['text']))
    ratio = difflib.SequenceMatcher(None, r, h).ratio()
    flag = '  <<<' if ratio < 0.9 else ''
    if flag: bad += 1
    print('%2d.%d %.2f | %s\n       ASR: %s%s' % (s['p'], s['s'], ratio, s['text'], hyp, flag), flush=True)
print('sentences below 0.90:', bad)
