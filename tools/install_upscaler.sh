#!/usr/bin/env bash
# Installa Real-ESRGAN (ncnn-vulkan, build Ubuntu del 2022-04-24) in ~/Tools/realesrgan, senza sudo.
# Upscaling delle texture con rete neurale su GPU via Vulkan. Fonte: github.com/xinntao/Real-ESRGAN (release v0.2.5.0).
# Scarica ~45 MB (eseguibile + modelli). Va lanciato dall'utente: scarica ed esegue software di terze parti.
# Uso:  ./tools/install_upscaler.sh
set -euo pipefail
URL="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip"
DEST="$HOME/Tools/realesrgan"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
curl -fL -o "$TMP/re.zip" "$URL"
unzip -tq "$TMP/re.zip"                       # integrita' dello zip
rm -rf "$DEST"; mkdir -p "$DEST"
unzip -q "$TMP/re.zip" -d "$DEST"
chmod +x "$DEST"/realesrgan-ncnn-vulkan
echo "Installato in $DEST"
ls "$DEST/models" | sed 's/\..*//' | sort -u | tr '\n' ' '; echo
"$DEST/realesrgan-ncnn-vulkan" -h 2>&1 | head -3
