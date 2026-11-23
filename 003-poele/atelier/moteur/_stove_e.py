def LB(t0, t1, key, txt=None, hot=False, side=None): return (t0, t1, key, txt, hot, side)
LABELS = []
for key, w in (('hopper', 'un réservoir'), ('auger', 'une vis'), ('pot', 'un creuset'), ('fans', 'deux ventilateurs')):
    LABELS.append(LB(word_t(1, 0, w), Se(1, 0) + 0.3, key))
LABELS += [LB(Sx(1, 1) + 0.2, Se(1, 1) + 0.3, 'pellets', "Granulés", True),
           LB(Sx(2, 1) + 0.2, word_t(2, 1, 'petit moteur') - 0.2, 'auger', None, True),
           LB(word_t(2, 1, 'petit moteur'), Se(2, 1) + 0.2, 'motor', None, True),
           LB(word_t(2, 2, 'une goulotte') - 0.1, word_t(2, 2, 'puis dans') - 0.1, 'chute', None, True),
           LB(word_t(2, 2, 'puis dans'), P(3) - 0.3, 'pot', None, True),
           LB(Sx(2, 4) + 0.2, P(3) - 0.3, 'drop', None, True),
           LB(P(3) + 0.2, Sx(3, 1) - 0.1, 'igniter', None, True),
           LB(Sx(3, 1) + 0.1, Se(3, 2) + 0.2, 'intake', "Air aspiré", True),
           LB(P(4) + 0.2, Sx(4, 1) + 2.5, 'extractor', None, True),
           LB(word_t(4, 1, 'le conduit') - 0.2, Sx(4, 2) - 0.1, 'flue', None, True),
           LB(Sx(4, 2) + 0.2, Sx(4, 3) - 0.15, 'pressostat', None, True),
           LB(P(5) + 0.2, Sx(5, 1) - 0.1, 'exchanger', None, True),
           LB(Sx(5, 1) + 0.2, word_t(5, 1, 'et te le souffle') - 0.2, 'conv_fan', None, True),
           LB(word_t(5, 1, 'et te le souffle'), Sx(5, 2) + 0.5, 'grille', None, True),
           LB(P(6) + 0.2, Sx(6, 1) - 0.1, 'probe', None, True),
           LB(word_t(7, 0, 'la vis') + 0.2, Sx(7, 1) - 0.1, 'auger', "Vis arrêtée", True),
           LB(Sx(7, 1) + 0.2, P(8) - 0.3, 'extractor', None, True),
           LB(Sx(8, 1) + 0.3, T_CUT - 0.1, 'board', None, True),
           ]
