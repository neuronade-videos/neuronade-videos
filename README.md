# neuronade.ia : vidéos et atelier

Chaque dossier a son dossier : la vidéo publiée et la couverture (branche `main`, liens publics utilisés par Metricool), et l'atelier qui permet de la refaire (branche `atelier`).

## Dossier #001 : la chaudière à gaz
- `001-chaudiere/chaudiere.mp4` : version publiée (2 min 48, 1080x1920, -14 LUFS).
- `001-chaudiere/atelier/` : tout pour la reconstruire.
  - `script.txt` : texte de la voix off.
  - `audio/` : voix ElevenLabs « Neuronade » (voice_id `aVUJAgmLcus20Zv2bK1v`, modèle eleven_v4) + phrase « pleure ! » refaite.
  - `moteur/` : moteur hologramme (Python/PIL), calage voix, sous-titres terminal, inserts photoréalistes, identité, anomalies, mix.
  - `3d/` : scène Blender de la chaudière et rendus photoréalistes.
  - `restore.sh` : remet tout en place dans `/home/claude/v7`, `/home/claude/b3d`, `/home/claude/brand`.
- `commun/` : identité (logo, intro « DOSSIER #00N », outro, signature sonore).

## Refaire la vidéo #001
1. `bash 001-chaudiere/atelier/restore.sh`, puis recréer `lore.json` (messages secrets, voir le calendrier privé).
2. `cd /home/claude/v7 && python3 holo7.py render 2` (rendu), `python3 holo8.py render` (anomalies), `python3 brand7.py` (intro, outro, signature).
3. `python3 mix3.py && python3 music_st.py && python3 glitch_audio.py && bash mix_final.sh` (son).
4. Concaténer `seg/a_intro.mp4`, `seg/seg_000…032.mp4`, `seg/z_outro.mp4`, puis encoder avec `audio/master.wav`.

## Nouveau dossier
Le moteur est écrit pour la chaudière (géométrie `geom.py`, signaux et caméras dans `holo3.py`). Pour un nouveau sujet : copier l'atelier #001, remplacer la géométrie, les signaux, les étiquettes et le script, garder tout le reste (style, identité, sous-titres, mix).

Les messages secrets du terminal ne sont jamais publiés ici.
