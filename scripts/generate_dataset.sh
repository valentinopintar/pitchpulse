#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "No python3 on PATH. Install Python or set PYTHON=/path/to/python3" >&2
  exit 1
fi
"$PYTHON" -m pitchpulse.data.generate_match --match "${1:-syn-001}" --seed "${2:-42}"
"$PYTHON" -m pitchpulse.data.validate_events --match "${1:-syn-001}"
"$PYTHON" -m pitchpulse.interpret.assert_demo_alerts --match "${1:-syn-001}"
