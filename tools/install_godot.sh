#!/usr/bin/env bash
# Installa Godot 4 (ultima release stabile, build standard x86_64) in ~/Tools/godot, senza sudo.
# Verifica il checksum SHA-512 pubblicato nella release. Crea il comando ~/.local/bin/godot.
# Uso:  ./tools/install_godot.sh
set -euo pipefail

DEST="$HOME/Tools/godot"; BIN="$HOME/.local/bin"
mkdir -p "$DEST" "$BIN"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

REL=$(curl -fsSL https://api.github.com/repos/godotengine/godot/releases/latest)
read -r TAG ZIP_URL SUMS_URL ZIP_NAME < <(python3 -c "
import sys,json
r=json.load(sys.stdin); a={x['name']:x['browser_download_url'] for x in r['assets']}
zn=[n for n in a if n.endswith('_linux.x86_64.zip') and 'mono' not in n][0]
print(r['tag_name'], a[zn], a.get('SHA512-SUMS.txt',''), zn)" <<<"$REL")
echo "Godot $TAG  ($ZIP_NAME)"

curl -fL -o "$TMP/$ZIP_NAME" "$ZIP_URL"
if [[ -n "$SUMS_URL" ]]; then
  curl -fsSL -o "$TMP/SUMS" "$SUMS_URL"
  ( cd "$TMP" && grep " $ZIP_NAME\$" SUMS | sha512sum -c - )   # fallisce lo script se non combacia
else
  echo "ATTENZIONE: checksum non pubblicato per questa release, salto la verifica."
fi

unzip -qo "$TMP/$ZIP_NAME" -d "$DEST"
EXE=$(find "$DEST" -maxdepth 1 -name 'Godot_v*_linux.x86_64' | head -1)
chmod +x "$EXE"
ln -sf "$EXE" "$BIN/godot"
echo "Fatto: $EXE"
echo "Comando: godot   (assicurati che $BIN sia nel PATH)"
"$EXE" --version || true
