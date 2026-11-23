
SAFE = dict(x0=36, x1=930, y0=330, y1=1380)
ELEC_TARGETS = [G.MOTOR[0], G.IGNITER[0], G.EXTRACTOR_C, (-45, -360, 150), G.DISPLAY_C]

class Renderer:
    def __init__(self):
        self.bg = make_bg(); self.scan = make_scan(); cams(); phases()
    def frame(self, i):
        t = i / FPS; c = cams()[i]; cam = Cam(c, S, t)
        img = Image.new('RGB', (W2, H2)); d = ImageDraw.Draw(img, 'RGBA')
        focus, dim = scene_focus(t)
        reveal = None
        if T_REW <= t < T_REW + 1.1: reveal = -560 + 1300 * sm((t - T_REW) / 1.05)
        PTS = ALLP
        sp, z = cam.proj(PTS)
        zmean = np.add.reduceat(z, OFF[:-1]) / np.diff(OFF)
        flick = 0.93 + 0.07 * math.sin(t * 13.0) * math.sin(t * 7.3)
        pw = power(t); ig = igniter(t)
        for k, p in enumerate(POLYS):
            if reveal is not None and YMIN[k] > reveal: continue
            i0, i1 = OFF[k], OFF[k + 1]
            if z[i0:i1].min() < 40: continue
            g = p['group']
            depth = clamp(1.25 - (zmean[k] - cam.d) / 2600, 0.3, 1.15)
            col = GROUP_TINT.get(g, HOLO); a = p['a'] * 235 * depth * flick
            if g in focus: col = FOCUS; a = min(255, a * 1.5 + 40)
            elif focus and g != 'env': a *= dim
            if g == 'pot' and g not in focus: col = mix(col, FLAMEC, 0.55 * pw)
            if g == 'igniter': col = mix(col, EMBER, ig); a = max(a, 230 * ig)
            if g in ('exchanger', 'fume_duct', 'flue') and g not in focus: col = mix(col, HOTC, 0.35 * clamp((fumes(t) - 40) / 120))
            if g == 'display' and mains(t) < 0.5: a *= 0.35
            seg = sp[i0:i1]
            if reveal is not None:
                yv = PTS[i0:i1, 1]
                if yv.max() > reveal:
                    keep = yv <= reveal
                    if keep.sum() < 2:
                        if len(yv) == 2:
                            k2 = (reveal - yv[0]) / (yv[1] - yv[0] + 1e-9)
                            q = PTS[i0] + (PTS[i0 + 1] - PTS[i0]) * k2
                            seg, _ = cam.proj(np.stack([PTS[i0], q]))
                        else: continue
                    else: seg = seg[keep]
            d.line(seg.ravel().tolist(), fill=rgba(col, a), width=max(1, int(round(p['w'] * S))))
        if reveal is not None:
            ra = 1 - ramp(reveal, 450, 740)
            if ra > 0.01:
                dline(d, cam, G.circle((0, reveal, 0), (0, 1, 0), 420, 60), (170, 250, 255), 230 * ra, 2.5)
                dline(d, cam, G.circle((0, reveal, 0), (0, 1, 0), 440, 60), (120, 230, 255), 90 * ra, 6)
        self.dynamic(d, cam, t, i, focus)
        img = img.reduce(S)
        small = img.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4))
        g1 = small.resize((W, H), Image.BILINEAR).point(lambda v: min(255, int(v * 1.9)))
        small2 = img.resize((W // 10, H // 10), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
        g2 = small2.resize((W, H), Image.BILINEAR).point(lambda v: min(255, int(v * 1.5)))
        img = ImageChops.screen(img, g1); img = ImageChops.screen(img, g2); img = ImageChops.screen(img, self.bg)
        img = ImageChops.multiply(img, self.scan)
        img = self.post_fx(img, t, i)
        d1 = ImageDraw.Draw(img, 'RGBA'); cam1 = Cam(c, 1, t)
        self.overlays3d(img, d1, cam1, t)
        self.labels(img, d1, cam1, t)
        self.hud(img, d1, t)
        self.captions(img, d1, t)
        return img

    def post_fx(self, img, t, i):
        g = 0.0
        for tc in CHANGES:
            dur = 0.5 if tc == T_REW else 0.16
            if tc - 0.04 <= t < tc + dur: g = max(g, 1 - (t - tc + 0.04) / (dur + 0.04))
        if g > 0:
            a = np.asarray(img).copy(); rng = random.Random(i)
            for _ in range(int(6 + 10 * g)):
                y0 = rng.randrange(0, H - 40); hh = rng.randrange(6, 60); dx = int(rng.uniform(-60, 60) * g)
                a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], dx, axis=1)
                if rng.random() < 0.5: a[y0:y0 + hh, :, 0] = np.roll(a[y0:y0 + hh, :, 0], int(8 * g), axis=1)
            img = Image.fromarray(a)
            img = ImageChops.screen(img, Image.new('RGB', (W, H), tuple(int(v * 0.28 * g) for v in (120, 240, 255))))
        return img

    def dynamic(self, d, cam, t, i, focus):
        ph = phases(); pw = power(t); ig = igniter(t); ex = ext(t); cv = conv(t); fd = feed(t)
        fdim = lambda groups: 1.0 if (not focus or any(g in focus for g in groups)) else 0.45
        # pellets in the hopper (level drops slowly once the stove runs)
        level = 470 - 60 * ramp(t, T_FEED0, P(8)) if t >= T_REW else 430
        hp = G.HOPPER_PTS if hasattr(G, 'HOPPER_PTS') else HOPPER_PTS
        sel = hp[hp[:, 1] < level]
        ddots(d, cam, sel, PELLET, 120 * fdim(['hopper']), 1.5, rmax=1.8)
        # pellets carried by the screw, sliding down the chute, falling into the pot
        s = stream(FEEDP, ph['feed'][i] * 130, 30)
        Lg = L_AUGER + L_CHUTE
        for x in s:
            if x > Lg and fd < 0.1: continue
            ddots(d, cam, FEEDP.at(np.array([x])), PELLET, 220 * fdim(['auger', 'chute', 'pot']), 2.3)
        # rotating marks on the screw
        a0, a1 = np.array(G.AUGER[0], float), np.array(G.AUGER[1], float); ax = a1 - a0; u, v = G.perp(ax)
        for k in range(14):
            q = (k / 14 + ph['feed'][i] * 0.08) % 1.0; ang = ph['feed'][i] * 9 + k * 0.42 * 17
            p = a0 + ax * q + G.AUGER_R * (math.cos(ang) * u + math.sin(ang) * v)
            ddots(d, cam, [p], FOCUS if 'auger' in focus else HOLO, 200 * fdim(['auger']), 1.6)
        # pellets in the burn pot (glowing when burning)
        n = int(len(POT_PTS) * clamp(pile(t)))
        if n > 0:
            col = mix(PELLET, EMBER, clamp(pw * 1.4))
            ddots(d, cam, POT_PTS[:n], col, 230 * fdim(['pot']), 2.1)
        # igniter glow + hot air puff
        if ig > 0.02:
            tip = np.array(G.IGN_TIP, float)
            dline(d, cam, [G.IGNITER[0], G.IGNITER[1]], EMBER, 240 * ig, 5)
            ddots(d, cam, [tip], (255, 140, 60), 255 * ig, 7, rmax=4)
        # combustion air : outdoor intake -> igniter tube -> burn pot (heated by the igniter)
        if ex > 0.05:
            for x in stream(AIRP, ph['air'][i] * 320, 46):
                p = AIRP.at(np.array([x]))
                hot = ramp(x, L_IGN - 120, L_IGN) * max(ig, 0.0)
                ddots(d, cam, p, mix(COLD, HOTC, hot), 210 * ex * fdim(['intake', 'igniter', 'pot', 'extractor']), 2.2)
        # flame
        if pw > 0.02:
            rng = random.Random(21)
            for k in range(int(70 * pw) + 6):
                uu = (t * 1.2 * (0.7 + 0.6 * rng.random()) + rng.random()) % 1.0
                sx, sz = rng.uniform(-55, 55), rng.uniform(-50, 50)
                h = 90 + 330 * pw * (0.6 + 0.4 * rng.random())
                p = (G.POT_C[0] + sx * (1 - 0.7 * uu) + 12 * math.sin(t * 7 + k), -125 + h * uu, G.POT_C[2] + sz * (1 - 0.7 * uu))
                col = mix((255, 240, 170), FLAMEC, clamp(uu * 1.6)) if uu < 0.6 else mix(FLAMEC, EMBER, (uu - 0.6) / 0.4)
                ddots(d, cam, [p], col, 245 * pw * (1 - uu) ** 0.7 * fdim(['pot', 'fire']), 3.4 * (1 - 0.5 * uu), rmax=3.5)
        # fumes : burn pot -> exchanger tubes -> descending duct -> extractor -> flue
        ft = fumes(t)
        if ft > 35 and ex > 0.05:
            for k, fp in enumerate(FUMEPS):
                for x in stream(fp, ph['air'][i] * 380, 70, offset=k * 23):
                    col = FUME_H if x < EXCH_END[k] else mix(FUME_H, SMOKE, clamp((x - EXCH_END[k]) / 300))
                    ddots(d, cam, fp.at(np.array([x])), col, 170 * ex * clamp((ft - 35) / 60) * fdim(['exchanger', 'fume_duct', 'extractor', 'flue', 'fire']), 2.4)
        # extractor wheel and room-air fan (spinning)
        ec = np.array(G.EXTRACTOR_C, float)
        for k in range(6):
            a_ = math.radians(ph['ext'][i]) + k * math.pi / 3
            dline(d, cam, [ec, ec + G.EXTRACTOR_R * 0.85 * np.array([math.cos(a_), math.sin(a_), 0])], FOCUS if 'extractor' in focus else HOLO, 220 * fdim(['extractor']), 1.8)
        f0, f1 = np.array(G.CONV_FAN[0], float), np.array(G.CONV_FAN[1], float)
        for k in range(5):
            a_ = math.radians(ph['conv'][i]) + k * 2 * math.pi / 5; off = G.CONV_R * 0.8 * np.array([0, math.cos(a_), math.sin(a_)])
            dline(d, cam, [f0 + off, f1 + off], FOCUS if 'conv_fan' in focus else HOLO, 200 * fdim(['conv_fan']), 1.5)
        # room air : bottom intake -> fan -> side duct -> around the exchanger tubes -> out of the top grille
        if cv > 0.05:
            for x in stream(CONVP, ph['air'][i] * 300 * 0 + ph['conv'][i] * 0.42, 44):
                hot = ramp(x, CONV_HOT0, CONV_HOT1)
                ddots(d, cam, CONVP.at(np.array([x])), mix(COLD, HOTC, hot * clamp(pw * 1.3)), 200 * cv * fdim(['conv_fan', 'air_duct', 'exchanger', 'grille']), 2.2)
            for k in range(7):
                uu = (t * 0.5 + k / 7) % 1.0
                p = (110 + 120 * math.sin(k * 2.1) * uu, 428 + 160 * uu, 340 + 520 * uu)
                ddots(d, cam, [p], mix(HOTC, (255, 200, 150), uu), 160 * cv * clamp(pw * 1.3) * (1 - uu), 3.0)
        # room probe -> board -> screw motor (regulation signal)
        if P(6) + 0.2 <= t < P(7) - 0.4:
            sp_ = Path(SIGNAL); uu = ((t - P(6)) * 0.6) % 1.0
            for k in range(5):
                x = (uu * 1.15 - k * 0.04) * sp_.L
                if 0 <= x <= sp_.L: ddots(d, cam, sp_.at(np.array([x])), GREEN, 255 * (1 - k * 0.18), 4.0)
        # bonus : everything electrical is powered from the board
        el = win(t, Sx(8, 1) - 0.2, T_CUT, 0.3)
        if el > 0.02:
            bc = np.array([(G.BOARD[0][k] + G.BOARD[1][k]) / 2 for k in range(3)])
            for k, tg in enumerate(ELEC_TARGETS):
                ln = Path([bc, (bc[0], tg[1], bc[2]), tg]); dline(d, cam, ln.at(np.linspace(0, ln.L, 20)), ELEC, 150 * el, 2)
                x = ((t * 0.9 + k * 0.2) % 1.0) * ln.L; ddots(d, cam, ln.at(np.array([x])), ELEC, 255 * el, 4.0)

    def overlays3d(self, img, d, cam, t):
        dc = np.array(G.DISPLAY_C, float); sc, zc = cam.p1(dc)
        facing = (cam.C - dc) @ np.array([0, 0, 1.0]) / max(1e-6, np.linalg.norm(cam.C - dc))
        txt = display_text(t)
        if txt and zc > 50 and facing > 0.3:
            fs = int(clamp(20 * cam.F / zc, 6, 110)); av = ramp(sc[1], 400, 480) * (1 - ramp(sc[1], 1180, 1260)) * ramp(facing, 0.3, 0.5)
            if fs >= 11 and av > 0.01 and -100 < sc[0] < W + 100 and sc[1] < H + 100:
                text(img, d, (sc[0], sc[1] - fs * 0.35), txt, font('monob', fs), (120, 255, 200), av, 'mm')
                text(img, d, (sc[0], sc[1] + fs * 0.75), "%.1f°" % room(t), font('mono', max(8, int(fs * 0.8))), (160, 235, 255), 0.9 * av, 'mm')
        if Sx(4, 2) <= t < Sx(4, 4):
            pc = np.array([225, -200, -215.]); sc, zc = cam.p1(pc)
            if zc > 50 and SAFE['y0'] < sc[1] < 1300:
                a = win(t, Sx(4, 2), Sx(4, 4), 0.25)
                if t < Sx(4, 3) - 0.1: text(img, d, (sc[0], sc[1] - 40), "✓ TIRAGE OK", font('monob', 30), GREEN, a * (1 - ramp(t, Sx(4, 3) - 0.4, Sx(4, 3) - 0.1)), 'mm', 4)

    def labels(self, img, d, cam, t):
        return

    def hud(self, img, d, t):
        c = (110, 225, 255)
        for (x, y, sx, sy) in ((40, 120, 1, 1), (W - 40, 120, -1, 1), (40, 1590, 1, -1), (W - 40, 1590, -1, -1)):
            d.line([x, y + 40 * sy, x, y, x + 40 * sx, y], fill=(110, 225, 255, 110), width=2)
        hk = 1 - ramp(t, T_REW - 0.15, T_REW + 0.05)
        if hk > 0:
            text(img, d, (W / 2, 232), "TON POÊLE", font('Bold', 72), (255, 255, 255), hk, 'mm', 6)
            pulse = 1 + 0.04 * math.sin(t * 6)
            text(img, d, (W / 2, 335), "S'ALLUME TOUT SEUL", font('Bold', int(84 * pulse)), FOCUS, hk, 'mm', 7)
        if T_REW <= t < P(1) - 0.1:
            a = win(t, T_REW + 0.3, P(1) - 0.1, 0.25)
            text(img, d, (W / 2, 250), "◄◄  RETOUR AU DÉBUT", font('monob', 40), c, a, 'mm')
            text(img, d, (W / 2, 305), "poêle froid · réservoir plein · pièce à 17 °C", font('mono', 26), (200, 230, 240), a, 'mm')
        pi = max(x['p'] for x in SENTS if x['t0'] <= t + 0.4) if t > 0.2 else 0
        if 1 <= pi < NPARA:
            t0 = P(pi) - 0.4; a = ramp(t, t0, t0 + 0.4) * (1 - ramp(t, Sx(9, 1) - 0.5, Sx(9, 1) - 0.1))
            text(img, d, (70, 194), "%02d" % pi, font('monob', 42), FOCUS, a, 'lm')
            text(img, d, (138, 194), CHAP[pi], font('Bold', 46), (255, 255, 255), a, 'lm')
            d.line([70, 236, 70 + 940 * ramp(t, t0, t0 + 0.7), 236], fill=rgba(c, 120 * a), width=2)
            if pi < 9:
                pw = power(t); fd = feed(t) > 0.1
                items = [("PIÈCE", "%.1f°C" % room(t), room(t) >= 19.95), ("FLAMME", "%d%%" % round(100 * pw), pw > 0.05),
                         ("VIS", "MARCHE" if fd else "ARRÊT", fd), ("FUMÉES", "%d°C" % round(fumes(t)), fumes(t) > 60)]
                x = 70
                for lab, val, hot in items:
                    text(img, d, (x, 266), lab, font('mono', 20), c, 0.75 * a, 'lm')
                    text(img, d, (x, 302), val, font('monob', 34), FOCUS if hot else (235, 248, 255), a, 'lm')
                    x += 238
        B = [(Sx(1, 2) - 0.1, P(2) - 0.15, "1 kg DE GRANULÉS ≈ 5 kWh", YEL),
             (Sx(2, 4), P(3) - 0.15, "LE FEU NE PEUT PAS REMONTER", GREEN),
             (word_t(3, 1, 'et arrive'), Se(3, 2) + 0.2, "BOUGIE ROUGE + AIR → AIR BRÛLANT", HOTC),
             (Sx(4, 1), Sx(4, 2) - 0.1, "AIR FRAIS ENTRE · FUMÉES SORTENT", COLD),
             (Sx(4, 3), Se(4, 4) + 0.2, "SI PAS DE TIRAGE → VIS COUPÉE", RED),
             (Sx(5, 2), P(6) - 0.15, "FUMÉES ET AIR NE SE TOUCHENT PAS", GREEN),
             (Sx(6, 1), Sx(6, 3) - 0.1, "CONSIGNE PROCHE → VIS PLUS LENTE", GREEN),
             (Sx(6, 3), P(7) - 0.15, "≈ 1 kg DE GRANULÉS PAR HEURE", YEL),
             (word_t(7, 0, "la vis"), Sx(7, 1) - 0.1, "VIS ARRÊTÉE → LA FLAMME BAISSE", FOCUS),
             (Sx(7, 1), P(8) - 0.15, "VENTILATEURS ENCORE EN MARCHE", COLD),
             (Sx(8, 1), T_CUT - 0.1, "TOUT EST ÉLECTRIQUE", ELEC),
             (T_CUT, P(9) - 0.15, "COUPURE → TOUT S'ARRÊTE", RED)]
        for (a0, a1, s, col) in B:
            if a0 <= t < a1:
                w = min(980, 27 * len(s) + 90); self.box(img, d, (W - w) / 2, 1190, w, s, col, win(t, a0, a1, 0.2))
        if P(9) <= t:
            a = 1 - ramp(t, Sx(9, 1) - 0.5, Sx(9, 1) - 0.1)
            for k, (w, col, key) in enumerate((("DU BOIS COMPRESSÉ", PELLET, 'Du bois'), ("UNE VIS QUI DOSE", FOCUS, 'une vis'), ("DE L'AIR QUI SOUFFLE", COLD, "de l'air"))):
                tk = word_t(9, 0, key); ak = a * ramp(t, tk - 0.1, tk + 0.2)
                text(img, d, (W / 2, 880 + k * 84), w, font('Bold', 64), col, ak, 'mm', 5)
            if t > Sx(9, 1) - 0.3:
                a = ramp(t, Sx(9, 1) - 0.3, Sx(9, 1) + 0.3)
                text(img, d, (W / 2, 222), "ET CHEZ TOI,", font('Bold', 62), (255, 255, 255), a, 'mm', 6)
                text(img, d, (W / 2, 318), "TU TE CHAUFFES COMMENT ?", font('Bold', 64), FOCUS, a, 'mm', 7)
                a2 = ramp(t, Sx(9, 2) - 0.2, Sx(9, 2) + 0.3)
                text(img, d, (W / 2, 1228), "Réponds en commentaire ↓", font('Bold', 50), (255, 255, 255), a2, 'mm', 6)
