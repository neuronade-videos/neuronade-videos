#!/bin/bash
# Final premium mix: Neuronade voice + music (ducked) + SFX + ambience + sonic signature, mastered to Instagram loudness (~-14 LUFS).
set -e
cd /home/claude/d002
INTRO=2.3; TOTAL=151.9; MAINEND=$(python3 -c "print(2.3+143.984)")
D=2300
DUCK=$(cat audio/duck_expr.txt)
# 1) voice: gentle clean-up, compression, normalised to -16 LUFS
ffmpeg -y -loglevel error -i audio/voice_el.wav -af "highpass=f=70,equalizer=f=250:t=q:w=1.2:g=-1.5,equalizer=f=3300:t=q:w=1.0:g=1.2,deesser=i=0.25,acompressor=threshold=-20dB:ratio=2.2:attack=8:release=140:makeup=1.5,loudnorm=I=-16:TP=-2:LRA=7" -ar 44100 -ac 1 audio/voice_proc.wav
# 2) stems laid on the final timeline (intro offset), then mixed
ffmpeg -y -loglevel error \
  -i audio/voice_proc.wav -i music_st.wav -i sfx.wav -i bed.wav -i audio/sonic.wav -i audio/glitch.wav \
  -filter_complex "\
[0:a]adelay=${D},apad,atrim=0:${TOTAL},pan=stereo|c0=c0|c1=c0,asplit=3[v][k1][k2];\
[1:a]loudnorm=I=-24:TP=-3,aformat=channel_layouts=stereo,adelay=${D}|${D},apad,atrim=0:${TOTAL},afade=t=in:st=${INTRO}:d=0.4,afade=t=out:st=$(python3 -c "print(${MAINEND}-2.2)"):d=2.2,volume='if(${DUCK},0.06,1)':eval=frame[m];\
[m][k1]sidechaincompress=threshold=0.04:ratio=5:attack=25:release=450:makeup=1[md];\
[2:a]volume=4dB,adelay=${D},apad,atrim=0:${TOTAL},pan=stereo|c0=c0|c1=c0[s];\
[s][k2]sidechaincompress=threshold=0.06:ratio=2:attack=15:release=300[sd];\
[3:a]adelay=${D},apad,atrim=0:${TOTAL},pan=stereo|c0=c0|c1=c0,volume='if(${DUCK},0.06,1)':eval=frame[b];\
[4:a]volume='if(lt(t,10),0.89,1.45)':eval=frame,pan=stereo|c0=c0|c1=c0,atrim=0:${TOTAL},volume='if(${DUCK},0.06,1)':eval=frame[g];[5:a]atrim=0:${TOTAL}[gl];\
[v][md][sd][b][g][gl]amix=inputs=6:normalize=0,acompressor=threshold=-14dB:ratio=1.8:attack=20:release=250:makeup=1[mix]" \
  -map "[mix]" -ar 44100 -c:a pcm_s24le audio/premaster.wav
# 3) master: measure, then gain + true-peak limiter to land at -14 LUFS / -1.2 dBTP
I=$(ffmpeg -i audio/premaster.wav -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}')
G=$(python3 -c "print(round(-14.0 - (${I}), 2))")
echo "premaster ${I} LUFS -> gain ${G} dB"
ffmpeg -y -loglevel error -i audio/premaster.wav -af "volume=${G}dB,alimiter=limit=0.74:attack=3:release=60:level=disabled" -ar 48000 -c:a pcm_s24le audio/master.wav
ffmpeg -i audio/master.wav -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|LRA|Peak):" | tail -3
