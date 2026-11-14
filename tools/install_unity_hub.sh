#!/usr/bin/env bash
# Installa Unity Hub dal repository apt ufficiale (comandi dalla pagina docs.unity.com/hub/install-hub-linux).
# Poi l'Editor si installa dal Hub (serve il login con un account Unity per la licenza Personal).
# Uso:  ./tools/install_unity_hub.sh      (chiede la password sudo)
set -euo pipefail

sudo apt update
sudo apt install -y curl
sudo install -d /etc/apt/keyrings
curl -fsSL https://hub.unity3d.com/linux/keys/public | sudo gpg --dearmor --yes -o /etc/apt/keyrings/unityhub.gpg

sudo tee /etc/apt/sources.list.d/unityhub.sources > /dev/null << EOF
Types: deb
URIs: https://hub.unity3d.com/linux/repos/deb
Suites: stable
Components: main
Signed-By: /etc/apt/keyrings/unityhub.gpg
EOF

sudo apt update
sudo apt install -y unityhub

echo
echo "Unity Hub installato. Avvialo con:  unityhub"
echo "Poi: Installs -> Install Editor -> Unity 6 LTS (Official releases)."
