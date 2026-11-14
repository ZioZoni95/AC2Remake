#!/usr/bin/env bash
# Installa gli strumenti per il reverse-engineering statico di AC2Remake:
#   - openjdk-21-jdk (richiesto da Ghidra), curl, unzip, binutils MIPS
#   - Ghidra (ultima release da GitHub) in ~/Tools/ghidra
# Uso:  ./tools/install_re_tools.sh        (chiede la password sudo per apt)
set -euo pipefail

sudo apt update
sudo apt install -y openjdk-21-jdk curl unzip binutils-mipsel-linux-gnu

DEST="$HOME/Tools"
mkdir -p "$DEST"

# Ultima release pubblicata dal progetto NSA su GitHub (API pubblica, nessun dato personale inviato)
URL=$(curl -fsSL https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print([a['browser_download_url'] for a in r['assets'] if a['name'].endswith('.zip')][0])")
echo "Scarico: $URL"

TMP=$(mktemp -d)
curl -fL -o "$TMP/ghidra.zip" "$URL"
unzip -tq "$TMP/ghidra.zip"                      # controllo integrità dello zip
rm -rf "$DEST/ghidra"
unzip -q "$TMP/ghidra.zip" -d "$TMP/x"
mv "$TMP"/x/ghidra_* "$DEST/ghidra"
rm -rf "$TMP"

echo
echo "Fatto."
java -version 2>&1 | head -1
echo "Ghidra GUI:       $DEST/ghidra/ghidraRun"
echo "Ghidra headless:  $DEST/ghidra/support/analyzeHeadless"
