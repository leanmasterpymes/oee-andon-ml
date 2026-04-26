"""Forecast del OEE de cierre de turno.

Estrategia: ajusta una regresion lineal sobre el OEE acumulado intra-turno
(features: minuto del turno, OEE actual, perdida acumulada, paradas a la
fecha) y proyecta hasta el final del turno con banda de incertidumbre.

Para el MVP basta una regresion + bootstrap de residuos. En produccion se
puede reemplazar por LightGBM con lags y/o Prophet usando OEE histo.

Salida:
    docs/images/forecast_shift.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).parent
IMAGES = HERE.parent.parent / "docs" / "images"
IMAGES.mkdir(parents=True, exist_ok=True)
IMG_PATH = IMAGES / "forecast_shift.png"


def synth_shift(seed: int = 11):
    """Simula un turno de 8h con OEE muestreado cada 15min."""
    rng = np.random.default_rng(seed)
    minutes = np.arange(0, 8 * 60, 15)
    target = 0.85
    # Comienza bajo (arranque) y va estabilizando.
    base = 0.55 + 0.30 * (1 - np.exp(-minutes / 90))
    noise = rng.normal(0, 0.025, size=len(minutes))
    oee = (base + noise).clip(0.2, 0.95)
    return minutes, oee, target


def forecast(minutes: np.ndarray, oee: np.ndarray, until_min: int = 480, n_boot: int = 200):
    """Forecast lineal simple con bootstrap de residuos para banda IC95%."""
    cut = int(len(minutes) * 0.55)  # 'ahora' es a media hora del turno
    x_obs, y_obs = minutes[:cut], oee[:cut]

    # Ajuste: y = a + b * (1 - exp(-x/tau)).  Tau fijo por simplicidad.
    tau = 90
    feat = 1 - np.exp(-x_obs / tau)
    A = np.vstack([np.ones_like(feat), feat]).T
    coef, *_ = np.linalg.lstsq(A, y_obs, rcond=None)
    pred_obs = A @ coef
    residuals = y_obs - pred_obs

    x_fc = np.arange(0, until_min + 15, 15)
    feat_fc = 1 - np.exp(-x_fc / tau)
    A_fc = np.vstack([np.ones_like(feat_fc), feat_fc]).T
    pred_fc = A_fc @ coef

    rng = np.random.default_rng(0)
    boots = np.array([
        pred_fc + rng.choice(residuals, size=len(pred_fc), replace=True)
        for _ in range(n_boot)
    ])
    lo = np.percentile(boots, 2.5, axis=0)
    hi = np.percentile(boots, 97.5, axis=0)

    return cut, x_fc, pred_fc, lo, hi


def main() -> None:
    minutes, oee, target = synth_shift()
    cut, x_fc, pred_fc, lo, hi = forecast(minutes, oee)

    plt.figure(figsize=(10, 4.5))
    plt.plot(minutes[:cut] / 60, oee[:cut], "o-", color="#0ea5e9", label="OEE observado")
    plt.plot(x_fc / 60, pred_fc, "--", color="#7c3aed", label="OEE proyectado")
    plt.fill_between(x_fc / 60, lo, hi, color="#7c3aed", alpha=0.15, label="IC 95%")
    plt.axhline(target, linestyle=":", color="#16a34a", label=f"Meta ({target:.0%})")
    plt.axvline(minutes[cut - 1] / 60, color="#94a3b8", linestyle=":")
    plt.text(minutes[cut - 1] / 60 + 0.05, 0.25, "Ahora", color="#475569")

    final_oee = pred_fc[-1]
    delta = (final_oee - target) * 100
    plt.title(
        "Forecast del cierre de turno\n"
        f"Si nada cambia, vas a cerrar en {final_oee:.0%}  ({delta:+.1f} pts vs. meta)"
    )
    plt.xlabel("Hora del turno")
    plt.ylabel("OEE")
    plt.ylim(0.2, 1.0)
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(IMG_PATH, dpi=130, facecolor="white")
    print(f"Grafica guardada en {IMG_PATH}")


if __name__ == "__main__":
    main()
