#!/bin/bash
# Remet l'atelier du Dossier #003 (frigo) aux emplacements attendus par les scripts (/home/claude/d003, b3d).
set -e
H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../.." && pwd)
mkdir -p /home/claude/d003/audio /home/claude/d003/seg /home/claude/d003/prev /home/claude/d003/b3d /home/claude/d003/brand_out /home/claude/b3d
cp "$H"/moteur/* /home/claude/d003/
cp "$H"/script.txt /home/claude/d003/
cp "$H"/3d/* /home/claude/d003/b3d/
cp "$ROOT"/001-chaudiere/atelier/3d/boiler.py /home/claude/b3d/      # stove.py réutilise les helpers Blender de boiler.py
cp "$ROOT"/commun/logo_holo2.png /home/claude/b3d/
cp "$H/audio/voix_complete_neuronade.mp3" /home/claude/d003/audio/voice_el.mp3
ffmpeg -y -loglevel error -i "$H/audio/voix_calee.flac" -c:a pcm_s16le /home/claude/d003/audio/voice_el.wav   # voix ralentie ×0,93 + pauses ≥ 1,25 s
pip install -q --break-system-packages pillow numpy scipy soundfile sherpa-onnx 2>/dev/null || true
[ -f /home/claude/d003/lore.json ] || echo "ATTENTION : lore.json (messages secrets du terminal) n'est pas dans le dépôt public. Le recréer depuis l'onglet « Journal du terminal » du calendrier (colonne Calage)."
echo "Atelier #003 restauré. Rendu : python3 run_segs.py 2 '' ; sons : mixF.py, music_st.py, brand2 (sonic), glitch_audio.py, mix_final.sh"
