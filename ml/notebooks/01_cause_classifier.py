"""Entrena clasificador LightGBM para sugerir causa de parada en el Andon.

Genera un dataset sintetico que imita la realidad: las causas dependen del
turno, hora del dia, maquina y duracion de la parada.

Salida:
    ml/models/cause_classifier.pkl
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


HERE = Path(__file__).parent
MODELS = HERE.parent / "models"
MODELS.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODELS / "cause_classifier.pkl"

CAUSES = ["BREAKDOWN", "SETUP", "MICROSTOP", "SLOW", "DEFECT", "STARTUP"]
SHIFTS = ["M", "T", "N"]
MACHINES = ["maquina01", "maquina02", "maquina03"]
ALARMS = ["A000"] + [f"A{i}" for i in range(100, 1000, 50)]


def make_dataset(n: int = 8000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        machine = rng.choice(MACHINES)
        hour = int(rng.integers(0, 24))
        if 6 <= hour < 14: shift = "M"
        elif 14 <= hour < 22: shift = "T"
        else: shift = "N"

        # Probabilidades de causa segun contexto (encoded business rules).
        if hour in (6, 14, 22):                 # arranque de turno
            probs = [0.05, 0.30, 0.10, 0.05, 0.05, 0.45]
        elif rng.random() < 0.04:               # falla esporadica
            probs = [0.55, 0.10, 0.15, 0.05, 0.10, 0.05]
        else:
            probs = [0.05, 0.10, 0.55, 0.10, 0.15, 0.05]
        cause = rng.choice(CAUSES, p=probs)

        # Duracion segun causa.
        dur_map = {
            "BREAKDOWN": rng.uniform(300, 1800),
            "SETUP":     rng.uniform(600, 1500),
            "MICROSTOP": rng.uniform(20, 180),
            "SLOW":      rng.uniform(60, 600),
            "DEFECT":    rng.uniform(0, 30),
            "STARTUP":   rng.uniform(120, 600),
        }
        dur = dur_map[cause] * rng.uniform(0.85, 1.15)

        alarm = "A000" if cause != "BREAKDOWN" else rng.choice(ALARMS[1:])

        rows.append({
            "machine_id": machine,
            "hour": hour,
            "shift": shift,
            "alarm_code": alarm,
            "stop_duration_s": dur,
            "cause": cause,
        })
    return pd.DataFrame(rows)


def build_pipeline() -> Pipeline:
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"),
         ["machine_id", "shift", "alarm_code"]),
    ], remainder="passthrough")
    return Pipeline([
        ("pre", pre),
        ("clf", LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                               class_weight="balanced", random_state=42)),
    ])


def main() -> None:
    df = make_dataset()
    X = df.drop(columns=["cause"])
    y = df["cause"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.2, random_state=42)

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    print(classification_report(y_test, pipe.predict(X_test)))
    joblib.dump(pipe, MODEL_PATH)
    print(f"Modelo guardado en {MODEL_PATH}")


if __name__ == "__main__":
    main()
