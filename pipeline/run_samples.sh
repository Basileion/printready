#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python pipeline/score_mesh.py samples/*.stl "$@"
