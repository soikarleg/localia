#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID}" -ne 0 ]; then
  echo "Ce script doit etre lance en root."
  echo "Commande: sudo ./scripts/setup_nvidia_docker.sh"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: apt-get introuvable. Script cible Ubuntu/Mint/Debian."
  exit 1
fi

source /etc/os-release
codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-unknown}}"

echo "=== NVIDIA Docker setup (codename: ${codename}) ==="

echo "[0/6] Verifier les depots Docker invalides (xia)"
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
  [ -f "$f" ] || continue
  if grep -Eq 'download\.docker\.com/linux/ubuntu[[:space:]]+xia' "$f"; then
    echo "Correction du depot Docker dans $f (xia -> noble)"
    sed -Ei 's#download\.docker\.com/linux/ubuntu[[:space:]]+xia#download.docker.com/linux/ubuntu noble#g' "$f"
  fi
done

echo "[1/6] Installer la cle et le repo NVIDIA container toolkit"
install -d -m 0755 /usr/share/keyrings
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --batch --yes --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL "https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list" \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list

echo "[2/6] apt-get update"
apt-get update

echo "[3/6] Installer nvidia-container-toolkit"
apt-get install -y nvidia-container-toolkit

echo "[4/6] Generer la spec CDI"
mkdir -p /etc/cdi
nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

echo "[5/6] Configurer le runtime Docker NVIDIA"
nvidia-ctk runtime configure --runtime=docker

echo "[6/6] Redemarrer Docker et tester"
systemctl restart docker

docker run --rm --gpus all nvidia/cuda:12.0.1-base-ubuntu22.04 nvidia-smi

echo "Setup termine: GPU Docker operationnel."
