CHAP = {1: "VUE D'ENSEMBLE", 2: "LA VIS", 3: "L'ALLUMAGE", 4: "L'EXTRACTEUR", 5: "L'ÉCHANGEUR", 6: "LA RÉGULATION", 7: "L'ARRÊT", 8: "LE BONUS", 9: "EN RÉSUMÉ"}
DISPLAY = [("cinq kilowattheures", "5 kWh"), ("un kilo par heure", "1 kg/h")]
NOEND = set("le la les l' un une des de du d' à au aux en par pour sur dans et ou où qui que qu' ce cette ces son sa ses ta ton tes se s' ne n' y sous avant entre très plus".split())
KEYC = {'granulés': PELLET, 'granulés,': PELLET, 'vis': FOCUS, 'feu': HOTC, 'flamme': HOTC, 'brûlant': HOTC, 'chaud.': HOTC, 'chaud': HOTC, 'air': COLD,
        "l'air": COLD, 'frais': COLD, 'fumées': SMOKE, 'électrique.': ELEC, 'électrique': ELEC, "l'électricité": ELEC, 'courant': ELEC, 'courant ?': ELEC,
        'bougie': EMBER, 'sèche-cheveux': YEL, 'sèche-cheveux.': YEL, 'extracteur': FOCUS, 'échangeur.': FOCUS, 'pressostat': FOCUS, 'creuset.': FOCUS,
        'réservoir.': FOCUS, 'goulotte,': FOCUS, 'consigne,': GREEN, 'coupure,': RED, 'allumette.': RED}
