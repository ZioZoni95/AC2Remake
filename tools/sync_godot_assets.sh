#!/usr/bin/env bash
# Copia gli asset estratti dal disco (out/) nel progetto Godot (engines/godot/assets, ignorato da git).
# Prima: python3 -I pipeline/ac2_aircraft.py all out/aerei ; python3 -I pipeline/ac2_mission.py extract 32 out/fighters_honor
set -euo pipefail
cd "$(dirname "$0")/.."
D=engines/godot/assets
mkdir -p "$D/aerei" "$D/fighters_honor"
cp -u out/aerei/*.gltf out/aerei/*.png "$D/aerei/" 2>/dev/null || echo "ATTENZIONE: out/aerei vuoto (esegui ac2_aircraft.py)"
cp -ur out/fighters_honor/models/. "$D/fighters_honor/" 2>/dev/null || echo "ATTENZIONE: out/fighters_honor vuoto (esegui ac2_mission.py)"
cp -u out/fighters_honor/mission.json "$D/fighters_honor/" 2>/dev/null || echo "ATTENZIONE: manca mission.json (esegui ac2_export_godot.py)"
echo "Asset copiati in $D"
