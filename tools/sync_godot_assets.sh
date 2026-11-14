#!/usr/bin/env bash
# Copia gli asset estratti dal disco (out/) nel progetto Godot (engines/godot/assets, ignorato da git).
# Prima: python3 -I pipeline/ac2_aircraft.py all out/aerei ; python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor
set -euo pipefail
cd "$(dirname "$0")/.."
D=engines/godot/assets
mkdir -p "$D/aerei" "$D/fighters_honor"
cp -u out/aerei/*.gltf out/aerei/*.png "$D/aerei/" 2>/dev/null || echo "ATTENZIONE: out/aerei vuoto (esegui ac2_aircraft.py)"
cp -ur out/fighters_honor/models/. "$D/fighters_honor/" 2>/dev/null; rm -f "$D/fighters_honor/.hd_done" || echo "ATTENZIONE: out/fighters_honor vuoto (esegui ac2_mission.py)"
cp -u out/fighters_honor/terreno/terreno.i16 out/fighters_honor/terreno/terreno.json out/fighters_honor/terreno/terreno_mesh* "$D/fighters_honor/" 2>/dev/null || true
cp -u out/fighters_honor/mission.json "$D/fighters_honor/" 2>/dev/null || echo "ATTENZIONE: manca mission.json (esegui ac2_export_godot.py)"
mkdir -p "$D/audio"
cp -u out/audio/sfx_*.wav out/audio/traccia_0[0-6]_*.wav "$D/audio/" 2>/dev/null || echo "ATTENZIONE: audio mancante (ac2_audio.py tracks, ac2_sfx_placeholder.py)"
mkdir -p "$D/fx"; cp -u out/tim/e002_1_3.png "$D/fx/explosion.png" 2>/dev/null || echo "ATTENZIONE: manca out/tim/e002_1_3.png (ac2_extract.py tims)"
echo "Asset copiati in $D"
