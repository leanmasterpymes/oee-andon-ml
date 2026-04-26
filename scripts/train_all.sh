#!/usr/bin/env bash
# Entrena los 3 modelos del MVP y genera las graficas del articulo.

set -euo pipefail
cd "$(dirname "$0")/.."

python ml/notebooks/01_cause_classifier.py
python ml/notebooks/02_microstop_detector.py
python ml/notebooks/03_oee_shift_forecast.py

echo "Listo: modelos en ml/models/, graficas en docs/images/"
