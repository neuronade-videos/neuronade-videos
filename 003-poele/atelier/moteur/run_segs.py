import sys, os
sys.path.insert(0, '/home/claude/d003')
import holo8 as H8
skip = set(int(x) for x in sys.argv[2].split(',')) if len(sys.argv) > 2 and sys.argv[2] else set()
allk = [k for k in range((H8.V.NF + 149) // 150) if k not in skip and not os.path.exists('/home/claude/d003/seg/seg_%03d.mp4' % k)]
from multiprocessing import Pool
with Pool(int(sys.argv[1])) as p:
    for res in p.imap_unordered(H8.render_seg, allk): print(res, flush=True)
