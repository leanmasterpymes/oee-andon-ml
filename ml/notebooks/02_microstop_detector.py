"""Detector de microparadas con Isolation Forest sobre el gap entre ciclos.

Idea: si la maquina deberia producir 1 pieza cada 12s y de pronto pasa 90s
sin pieza sin que nadie reporte parada, eso es una microparada perdida.

Salida:
    ml/models/microstop_detector.pkl
    docs/images/microstop_hist.png
"""

from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import IsolationForest


HERE = Path(__file__).parent
MODELS = HERE.parent / "models"
IMAGES = HERE.parent.parent / "docs" / "images"
MODELS.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODELS / "microstop_detector.pkl"
IMG_PATH = IMAGES / "microstop_hist.png"


def synth_gaps(n_normal: int = 5000, n_micro: int = 200, ideal: float = 12.0, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    normal = rng.normal(loc=ideal, scale=1.5, size=n_normal).clip(min=ideal * 0.85)
    micro = rng.uniform(low=ideal * 4, high=ideal * 12, size=n_micro)
    return np.concatenate([normal, micro])


def main() -> None:
    gaps = synth_gaps()
    X = gaps.reshape(-1, 1)

    model = IsolationForest(contamination=0.04, random_state=42, n_estimators=200)
    model.fit(X)
    joblib.dump(model, MODEL_PATH)
    print(f"Modelo guardado en {MODEL_PATH}")

    # Grafica para el articulo: histograma con zona anomala marcada.
    preds = model.predict(X)
    threshold = X[preds == -1].min()

    plt.figure(figsize=(9, 4))
    plt.hist(gaps, bins=80, color="#0ea5e9", alpha=0.8, edgecolor="white")
    plt.axvspan(threshold, gaps.max(), color="#dc2626", alpha=0.15,
                label=f"Microparada (gap > {threshold:.1f}s)")
    plt.axvline(12, linestyle="--", color="#16a34a", label="Ciclo ideal (12s)")
    plt.title("Distribucion de tiempos entre ciclos\nLa zona roja la detecta Isolation Forest sin que nadie la reporte")
    plt.xlabel("Segundos entre ciclos consecutivos")
    plt.ylabel("Frecuencia")
    plt.legend()
    plt.tight_layout()
    plt.savefig(IMG_PATH, dpi=130, facecolor="white")
    print(f"Grafica guardada en {IMG_PATH}")


if __name__ == "__main__":
    main()
