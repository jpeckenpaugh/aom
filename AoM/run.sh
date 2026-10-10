#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

VENV="../.aom-pygbag-venv"

if [ ! -x "$VENV/bin/python" ]; then
  python -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip
  "$VENV/bin/python" -m pip install pygbag==0.9.3
fi

"$VENV/bin/python" -m pygbag --template default-browserfs.tmpl --width 1280 --height 720 .
