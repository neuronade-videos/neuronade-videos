#!/bin/bash
# Remet l'atelier du Dossier #001 aux emplacements attendus par les scripts (/home/claude/v7, b3d, brand).
set -e
H=$(cd "$(dirname "$0")" && pwd); ROOT=$(cd "$H/../.." && pwd)
mkdir -p /home/claude/v7/audio /home/claude/v7/seg /home/claude/v7/prev /home/claude/b3d /home/claude/brand
cp "$H"/moteur/* /home/claude/v7/
cp "$H"/3d/* /home/claude/b3d/
cp "$ROOT"/commun/brand.py /home/claude/brand/ ; cp "$ROOT"/commun/logo_holo2.png /home/claude/b3d/
ffmpeg -y -loglevel error -i "$H/audio/voix_complete_neuronade.mp3" -ar 44100 -ac 1 /home/claude/v7/audio/voice_el_orig.wav
ffmpeg -y -loglevel error -i "$H/audio/phrase_pleure_v2.mp3" -ar 44100 -ac 1 /home/claude/v7/audio/pleure_new.wav
cp "$H/audio/voix_complete_neuronade.mp3" /home/claude/v7/audio/voice_el.mp3
python3 /home/claude/v7/splice_pleure.py
pip install -q --break-system-packages pillow numpy scipy soundfile sherpa-onnx 2>/dev/null || true
[ -f /home/claude/v7/lore.json ] || echo "ATTENTION : lore.json (messages secrets du terminal) n'est pas dans le dépôt public. Le recréer depuis l'onglet « Journal du terminal » du calendrier."
echo "Atelier #001 restauré."
