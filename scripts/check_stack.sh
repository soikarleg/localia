#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/docker"
CUDA_IMAGE_TAG="${CUDA_IMAGE_TAG:-12.0.1-base-ubuntu22.04}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker est introuvable dans le PATH."
  exit 1
fi

echo "=== Localia stack check ==="

echo "[1/5] Etat des services Docker Compose"
(
  cd "${DOCKER_DIR}"
  docker compose ps
)

echo

echo "[2/5] Verifier OpenWebUI /health"
health_status="down"
for _ in {1..20}; do
  if curl -fsS --max-time 5 "http://localhost:3000/health" >/tmp/localia_health.json 2>/dev/null; then
    health_status="up"
    break
  fi
  sleep 1
done

if [ "${health_status}" = "up" ]; then
  echo "OK: OpenWebUI repond sur /health"
  cat /tmp/localia_health.json
else
  echo "ERROR: OpenWebUI ne repond pas sur /health"
fi

echo

echo "[3/5] Verifier la liste des modeles Ollama"
models_count="0"
if (
  cd "${DOCKER_DIR}"
  docker compose exec -T ollama ollama list
) >/tmp/localia_ollama_models.txt 2>/tmp/localia_ollama_models.err; then
  cat /tmp/localia_ollama_models.txt
  models_count="$(awk 'NR>1 && NF>0 {c++} END {print c+0}' /tmp/localia_ollama_models.txt)"
  echo "Modeles detectes: ${models_count}"
else
  echo "ERROR: impossible de lister les modeles Ollama"
  cat /tmp/localia_ollama_models.err
fi

echo

echo "[4/5] Verifier le GPU cote hote"
if command -v nvidia-smi >/dev/null 2>&1; then
  if nvidia-smi -L >/tmp/localia_gpu_host.txt 2>/tmp/localia_gpu_host.err; then
    echo "OK: GPU detecte cote hote"
    cat /tmp/localia_gpu_host.txt
  else
    echo "ERROR: nvidia-smi a echoue"
    cat /tmp/localia_gpu_host.err
  fi
else
  echo "WARN: nvidia-smi introuvable (pilote NVIDIA absent ou non installe)"
fi

echo

echo "[5/5] Verifier le GPU cote Docker"
if docker run --rm --gpus all "nvidia/cuda:${CUDA_IMAGE_TAG}" nvidia-smi >/tmp/localia_gpu_docker.txt 2>/tmp/localia_gpu_docker.err; then
  echo "OK: GPU detecte dans Docker"
  sed -n '1,20p' /tmp/localia_gpu_docker.txt
  docker_gpu_ok=1
else
  echo "WARN: GPU non detecte dans Docker"
  cat /tmp/localia_gpu_docker.err
  docker_gpu_ok=0
fi

echo
if [ "${health_status}" = "up" ] && [ "${models_count}" -gt 0 ]; then
  echo "RESULTAT: stack applicative OK (OpenWebUI + modeles Ollama)."
else
  echo "RESULTAT: stack applicative partiellement KO."
fi

if [ "${docker_gpu_ok}" -eq 1 ]; then
  echo "RESULTAT GPU: OK dans Docker."
else
  echo "RESULTAT GPU: non disponible dans Docker (toolkit/runtime/CDI a configurer)."
fi
