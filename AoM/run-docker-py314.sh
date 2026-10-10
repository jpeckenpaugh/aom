#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE="aom-pygbag-py314"
CONTAINER="aom-pygbag-py314-8001"

docker build -f AoM/Dockerfile.py314 -t "$IMAGE" .

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  docker rm -f "$CONTAINER" >/dev/null
fi

docker run --rm \
  --name "$CONTAINER" \
  -p 8001:8001 \
  -e HOME=/tmp \
  -v "$PWD:/workspace" \
  -w /workspace/AoM \
  "$IMAGE"
