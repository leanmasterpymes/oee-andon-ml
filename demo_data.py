"""Datos sinteticos en memoria para correr el dashboard / andon sin BD ni broker.

Permite que la demo publica en Streamlit Cloud funcione sola: si la app detecta
que TimescaleDB no responde (o se fuerza con DEMO_MODE=1) cae a estos datos.

El escenario imita 3 maquinas en distintos estados, alineado con el modo demo
del Andon: maquina01 estable, maquina02 con microparadas, maquina03 detenida.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pandas as pd


_RNG = random.Random(42)

MACHINES = [
    {"machine_id": "maquina01", "name": "Empacadora 1", "line": "linea1",
     "area": "empaque", "ideal_cycle_s": 12.0, "target_oee": 0.85},
    {"machine_id": "maquina02", "name": "Empacadora 2", "line": "linea1",
     "area": "empaque", "ideal_cycle_s": 8.0,  "target_oee": 0.85},
    {"machine_id": "maquina03", "name": "Etiquetadora", "line": "linea2",
     "area": "empaque", "ideal_cycle_s": 20.0, "target_oee": 0.85},
]

# Perfil de cada maquina para que los KPIs cuenten una historia consistente.
PROFILES = {
    "maquina01": {"oee": 0.78, "availability": 0.92, "performance": 0.89, "quality": 0.95,
                  "pieces_total": 1180, "pieces_good": 1120},
    "maquina02": {"oee": 0.62, "availability": 0.84, "performance": 0.79, "quality": 0.93,
                  "pieces_total": 1480, "pieces_good": 1376},
    "maquina03": {"oee": 0.41, "availability": 0.55, "performance": 0.78, "quality": 0.96,
                  "pieces_total":  490, "pieces_good":  470},
}

# Pareto que justifica los OEE de arriba (en minutos perdidos en las ultimas 8h).
PARETO = [
    ("MICROSTOP",  92.0),
    ("BREAKDOWN",  68.0),
    ("SETUP",      41.0),
    ("SLOW",       25.0),
    ("STARTUP",    14.0),
    ("DEFECT",      9.0),
]


def get_machines() -> pd.DataFrame:
    return pd.DataFrame(MACHINES)


def get_latest_oee() -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    rows = []
    for m in MACHINES:
        p = PROFILES[m["machine_id"]]
        rows.append({
            "machine_id": m["machine_id"],
            "ts": now,
            "availability": p["availability"],
            "performance":  p["performance"],
            "quality":      p["quality"],
            "oee":          p["oee"],
            "pieces_total": p["pieces_total"],
            "pieces_good":  p["pieces_good"],
        })
    return pd.DataFrame(rows)


def get_oee_trend(hours: int = 8) -> pd.DataFrame:
    """OEE muestreado cada 5 min para los ultimos N horas, por maquina."""
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    n_points = hours * 12  # cada 5 min
    rows = []
    for m in MACHINES:
        base = PROFILES[m["machine_id"]]["oee"]
        rng = random.Random(hash(m["machine_id"]))
        # Forma de campana inversa: parte mas alto, baja al medio, recupera al final.
        for i in range(n_points):
            t = now - timedelta(minutes=(n_points - i) * 5)
            phase = i / n_points
            wave = 0.06 * (0.5 - abs(phase - 0.5))  # +/- 3 pts
            noise = rng.uniform(-0.04, 0.04)
            oee = max(0.0, min(1.0, base + wave + noise))
            rows.append({"ts": t, "machine_id": m["machine_id"], "oee": oee})
    return pd.DataFrame(rows)


def get_pareto(hours: int = 8) -> pd.DataFrame:
    rows = [{"cause": c, "events": int(mins / 1.5), "minutes": mins} for c, mins in PARETO]
    return pd.DataFrame(rows)


def get_last_state() -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    return pd.DataFrame([
        {"machine_id": "maquina01", "ts": now, "state": "RUN"},
        {"machine_id": "maquina02", "ts": now, "state": "RUN"},
        {"machine_id": "maquina03", "ts": now, "state": "DOWN"},
    ])


def get_recent_stops(minutes: int = 5) -> pd.DataFrame:
    return pd.DataFrame([
        {"machine_id": "maquina02", "cause": "MICROSTOP", "cnt": 4, "total_s": 240.0},
        {"machine_id": "maquina03", "cause": "BREAKDOWN", "cnt": 1, "total_s": 540.0},
    ])


def get_active_stop(machine_id: str) -> pd.DataFrame:
    if machine_id == "maquina03":
        return pd.DataFrame([{
            "cause": "BREAKDOWN",
            "ts": pd.Timestamp.now(tz="UTC") - pd.Timedelta(minutes=9),
            "duration_s": 540.0,
        }])
    return pd.DataFrame(columns=["cause", "ts", "duration_s"])
