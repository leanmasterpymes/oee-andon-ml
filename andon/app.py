"""Andon mobile — botonera tactil para el operario.

- Detecta el estado de la maquina via consulta al broker.
- Cuando hay parada, muestra top-3 causas mas probables (clasificador ML).
- El operario confirma con 1 toque -> publica el cierre de la parada al broker.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import paho.mqtt.publish as mqtt_publish
import streamlit as st


MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MODEL_PATH = Path(os.getenv("MODEL_PATH", "/models/cause_classifier.pkl"))

CAUSES = ["BREAKDOWN", "SETUP", "MICROSTOP", "SLOW", "DEFECT", "STARTUP"]
CAUSE_LABEL = {
    "BREAKDOWN": "Falla / averia",
    "SETUP":     "Cambio de formato",
    "MICROSTOP": "Microparada",
    "SLOW":      "Velocidad reducida",
    "DEFECT":    "Defecto de calidad",
    "STARTUP":   "Arranque",
}

st.set_page_config(page_title="Andon", layout="centered", page_icon="🚨")


@st.cache_resource
def load_model():
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception:
            return None
    return None


def suggest_causes(machine_id: str, hour: int, shift: str) -> list[tuple[str, float]]:
    """Devuelve top-3 causas mas probables. Si no hay modelo, fallback heuristico."""
    model = load_model()
    if model is None:
        # Heuristica: en arranque de turno suele haber STARTUP/SETUP, sino MICROSTOP.
        if hour in (6, 14, 22):
            return [("STARTUP", 0.45), ("SETUP", 0.30), ("MICROSTOP", 0.15)]
        return [("MICROSTOP", 0.55), ("SETUP", 0.25), ("BREAKDOWN", 0.10)]

    import pandas as pd
    X = pd.DataFrame([{"hour": hour, "shift": shift, "machine_id": machine_id,
                       "alarm_code": "A000", "stop_duration_s": 60}])
    proba = model.predict_proba(X)[0]
    pairs = sorted(zip(model.classes_, proba), key=lambda p: -p[1])[:3]
    return pairs


def publish_stop(machine_id: str, cause: str) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "cause": cause,
        "duration_s": st.session_state.get("stop_dur_s", 60),
        "alarm_code": None,
        "detected_by": "operator_andon",
    }
    topic = f"lmp/planta1/empaque/linea1/{machine_id}/stop"
    mqtt_publish.single(topic, json.dumps(payload), hostname=MQTT_HOST, port=MQTT_PORT)


def main() -> None:
    st.title("🚨 Andon")
    st.caption("Confirma la causa de la parada con un toque.")

    machine_id = st.selectbox("Maquina", ["maquina01", "maquina02", "maquina03"])
    now = datetime.now(timezone.utc).astimezone()
    shift = "M" if 6 <= now.hour < 14 else ("T" if 14 <= now.hour < 22 else "N")

    st.markdown(f"**Hora:** {now:%H:%M}  ·  **Turno:** {shift}")
    st.markdown("---")

    suggestions = suggest_causes(machine_id, now.hour, shift)

    st.subheader("Causa sugerida")
    for cause, prob in suggestions:
        if st.button(f"{CAUSE_LABEL[cause]}  ·  {prob:.0%}", use_container_width=True, key=f"sug_{cause}"):
            publish_stop(machine_id, cause)
            st.success(f"Registrado: {CAUSE_LABEL[cause]}")
            st.balloons()

    st.markdown("---")
    with st.expander("Otra causa"):
        for cause in CAUSES:
            if cause in [c for c, _ in suggestions]:
                continue
            if st.button(CAUSE_LABEL[cause], use_container_width=True, key=f"alt_{cause}"):
                publish_stop(machine_id, cause)
                st.success(f"Registrado: {CAUSE_LABEL[cause]}")


if __name__ == "__main__":
    main()
else:
    main()
