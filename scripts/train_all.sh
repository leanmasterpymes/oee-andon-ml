#!/usr/bin/env bash
# Entrena los 3 modelos del MVP y genera las graficas del articulo.

set -euo pipefail
cd "$(dirname "$0")/.."

# Usa el venv del proyecto si existe, si no python3 del sistema.
PYTHON=".venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

"$PYTHON" ml/notebooks/01_cause_classifier.py
"$PYTHON" ml/notebooks/02_microstop_detector.py
"$PYTHON" ml/notebooks/03_oee_shift_forecast.py

echo "Listo: modelos en ml/models/, graficas en docs/images/"
