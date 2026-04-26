"""Andon mobile — botonera tactil para el operario.

- Vista de planta con semaforo (verde / amarillo / rojo) por maquina.
- Cada semaforo tiene boton para ver el detalle del estado.
- Panel contextual: produccion en verde, microparadas en amarillo, causa de parada en rojo.
- Sidebar con boton "Iniciar simulacion" para lanzar eventos al broker durante N minutos.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import paho.mqtt.publish as mqtt_publish
import streamlit as st
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
import demo_data  # noqa: E402

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DB_DSN = os.getenv("DB_DSN", "postgresql+psycopg://oee:oee@localhost:5432/oee")
MODEL_PATH = Path(os.getenv("MODEL_PATH", "/models/cause_classifier.pkl"))

CAUSES = ["BREAKDOWN", "SETUP", "MICROSTOP", "SLOW", "DEFECT", "STARTUP"]
CAUSE_LABEL = {
    "BREAKDOWN": "Averia",
    "SETUP":     "Cambio de formato",
    "MICROSTOP": "Microparada",
    "SLOW":      "Velocidad reducida",
    "DEFECT":    "Defecto de calidad",
    "STARTUP":   "Arranque",
}

STATE_GREEN = "VERDE"
STATE_YELLOW = "AMARILLO"
STATE_RED = "ROJO"

COLOR = {
    STATE_GREEN:  "#16a34a",
    STATE_YELLOW: "#eab308",
    STATE_RED:    "#dc2626",
}

LABEL = {
    STATE_GREEN:  "En marcha",
    STATE_YELLOW: "Atencion",
    STATE_RED:    "Detenida",
}

SUBTITLE = {
    STATE_GREEN:  "Produccion estable",
    STATE_YELLOW: "Microparadas frecuentes",
    STATE_RED:    "Requiere causa",
}

DEMO_STATUSES = {
    "maquina01": STATE_GREEN,
    "maquina02": STATE_YELLOW,
    "maquina03": STATE_RED,
}

st.set_page_config(page_title="Andon", layout="wide", page_icon="🚨")
st_autorefresh(interval=5000, key="andon-refresh")

engine = create_engine(DB_DSN, pool_pre_ping=True)


@st.cache_resource
def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _force_demo() -> bool:
    return os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")


def is_demo_mode() -> bool:
    return _force_demo() or not _db_available()


@st.cache_resource
def load_model():
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception:
            return None
    return None


@st.cache_data(ttl=4)
def get_machines() -> pd.DataFrame:
    if is_demo_mode():
        return demo_data.get_machines()
    return pd.read_sql("SELECT * FROM machines ORDER BY machine_id", engine)


@st.cache_data(ttl=4)
def get_last_state() -> pd.DataFrame:
    if is_demo_mode():
        return demo_data.get_last_state()
    q = text("""
        SELECT DISTINCT ON (machine_id)
            machine_id, ts, payload->>'state' AS state
        FROM events
        WHERE event_type = 'state'
        ORDER BY machine_id, ts DESC
    """)
    return pd.read_sql(q, engine)


@st.cache_data(ttl=4)
def get_recent_stops(minutes: int = 5) -> pd.DataFrame:
    if is_demo_mode():
        return demo_data.get_recent_stops(minutes)
    q = text("""
        SELECT machine_id, cause, COUNT(*) AS cnt, SUM(duration_s) AS total_s
        FROM stops
        WHERE ts > NOW() - (:m * INTERVAL '1 minute')
        GROUP BY machine_id, cause
    """)
    return pd.read_sql(q, engine, params={"m": minutes})


@st.cache_data(ttl=4)
def get_latest_oee() -> pd.DataFrame:
    if is_demo_mode():
        return demo_data.get_latest_oee()
    q = text("""
        SELECT DISTINCT ON (machine_id)
            machine_id, ts, availability, performance, quality, oee, pieces_total, pieces_good
        FROM oee_snapshots
        ORDER BY machine_id, ts DESC
    """)
    return pd.read_sql(q, engine)


@st.cache_data(ttl=4)
def get_active_stop(machine_id: str) -> pd.DataFrame:
    if is_demo_mode():
        return demo_data.get_active_stop(machine_id)
    q = text("""
        SELECT cause, ts, duration_s
        FROM stops
        WHERE machine_id = :m
        ORDER BY ts DESC
        LIMIT 1
    """)
    return pd.read_sql(q, engine, params={"m": machine_id})


def derive_status_real(machine_id: str, last_state: pd.DataFrame, recent: pd.DataFrame) -> str:
    state_row = last_state[last_state["machine_id"] == machine_id]
    state = state_row["state"].iloc[0] if not state_row.empty else "RUN"
    if state == "DOWN":
        return STATE_RED

    micro = recent[(recent["machine_id"] == machine_id) & (recent["cause"] == "MICROSTOP")]
    if not micro.empty and int(micro["cnt"].iloc[0]) >= 2:
        return STATE_YELLOW

    return STATE_GREEN


def render_light(col, machine: pd.Series, status: str, selected: bool) -> None:
    color = COLOR[status]
    label = LABEL[status]
    subtitle = SUBTITLE[status]
    border_w = "4px" if selected else "2px"
    glow = f"box-shadow: 0 0 18px {color};" if selected else ""
    with col:
        st.markdown(
            f"""
            <div style="background:#0f172a; border-radius:12px; padding:18px;
                        border:{border_w} solid {color}; text-align:center; {glow}">
                <div style="color:#94a3b8; font-size:13px; letter-spacing:1px;">
                    {machine['line'].upper()} · {machine['area'].upper()}
                </div>
                <div style="color:white; font-size:20px; font-weight:600; margin-top:4px;">
                    {machine['name']}
                </div>
                <div style="display:flex; justify-content:center; align-items:center;
                            margin:18px 0 14px 0;">
                    <div style="width:90px; height:90px; border-radius:50%;
                                background:{color};
                                box-shadow: 0 0 28px {color}, inset 0 0 18px rgba(255,255,255,0.18);">
                    </div>
                </div>
                <div style="color:{color}; font-size:22px; font-weight:700; letter-spacing:1px;">
                    {label.upper()}
                </div>
                <div style="color:#cbd5e1; font-size:12px; margin-top:6px; margin-bottom:8px;">
                    {subtitle}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Ver detalle — {machine['name']}",
                     key=f"sel_{machine['machine_id']}",
                     use_container_width=True,
                     type="primary" if selected else "secondary"):
            st.session_state.selected_machine = machine["machine_id"]
            st.rerun()


def suggest_causes(machine_id: str, hour: int, shift: str) -> list[tuple[str, float]]:
    model = load_model()
    if model is None:
        if hour in (6, 14, 22):
            return [("STARTUP", 0.45), ("SETUP", 0.30), ("MICROSTOP", 0.15)]
        return [("MICROSTOP", 0.55), ("SETUP", 0.25), ("BREAKDOWN", 0.10)]

    X = pd.DataFrame([{"hour": hour, "shift": shift, "machine_id": machine_id,
                       "alarm_code": "A000", "stop_duration_s": 60}])
    proba = model.predict_proba(X)[0]
    pairs = sorted(zip(model.classes_, proba), key=lambda p: -p[1])[:3]
    return pairs


def publish_stop(machine_id: str, cause: str) -> None:
    """Publica al broker MQTT. En entornos sin broker (Streamlit Cloud) ignora silenciosamente."""
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "cause": cause,
        "duration_s": st.session_state.get("stop_dur_s", 60),
        "alarm_code": None,
        "detected_by": "operator_andon",
    }
    topic = f"lmp/planta1/empaque/linea1/{machine_id}/stop"
    try:
        mqtt_publish.single(topic, json.dumps(payload), hostname=MQTT_HOST, port=MQTT_PORT)
    except Exception:
        # Sin broker (entorno demo en cloud): el evento se registra solo en memoria/UI.
        pass


def panel_verde(machine: pd.Series, oee_row) -> None:
    st.success(f"✅ **{machine['name']}** trabaja con normalidad. No requiere intervencion del operario.")
    if oee_row is None:
        st.info("Esperando datos de produccion del procesador...")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("OEE actual", f"{oee_row['oee']:.0%}",
              f"{(oee_row['oee']-machine['target_oee'])*100:+.1f} pts vs meta")
    c2.metric("Piezas producidas", f"{int(oee_row['pieces_total'])}")
    c3.metric("Piezas buenas", f"{int(oee_row['pieces_good'])}",
              f"{(oee_row['pieces_good']/max(oee_row['pieces_total'],1)):.1%} aprob.")
    c4.metric("Meta de OEE", f"{machine['target_oee']:.0%}")

    st.markdown("##### Componentes del OEE")
    d1, d2, d3 = st.columns(3)
    d1.metric("Disponibilidad", f"{oee_row['availability']:.0%}")
    d2.metric("Rendimiento",    f"{oee_row['performance']:.0%}")
    d3.metric("Calidad",        f"{oee_row['quality']:.0%}")


def panel_amarillo(machine: pd.Series, oee_row, recent: pd.DataFrame) -> None:
    st.warning(
        f"⚠️ **{machine['name']}** acumula varias microparadas en los ultimos 5 minutos. "
        "La maquina sigue produciendo, pero la eficiencia esta cayendo. Conviene revisar la linea."
    )

    micro = recent[(recent["machine_id"] == machine["machine_id"]) & (recent["cause"] == "MICROSTOP")]
    cnt = int(micro["cnt"].iloc[0]) if not micro.empty else 0
    total_s = float(micro["total_s"].iloc[0]) if not micro.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Microparadas (5 min)", cnt)
    c2.metric("Tiempo perdido", f"{total_s/60:.1f} min")
    c3.metric("OEE actual", f"{oee_row['oee']:.0%}" if oee_row is not None else "—")

    st.markdown("##### Si vas a registrar la causa de las microparadas:")
    cols = st.columns(3)
    options = ["MICROSTOP", "SLOW", "DEFECT"]
    for col, code in zip(cols, options):
        if col.button(CAUSE_LABEL[code], use_container_width=True, key=f"yel_{code}"):
            publish_stop(machine["machine_id"], code)
            st.success(f"Registrado: {CAUSE_LABEL[code]} en {machine['machine_id']}")


def panel_rojo(machine: pd.Series, hour: int, shift: str) -> None:
    active = get_active_stop(machine["machine_id"])
    cause_now = active["cause"].iloc[0] if not active.empty else "?"
    ts_now = active["ts"].iloc[0] if not active.empty else None

    st.error(
        f"⛔ **{machine['name']}** esta detenida. Confirma la causa para que el sistema "
        "registre la parada y aprenda de ella."
    )
    if ts_now is not None:
        elapsed = datetime.now(timezone.utc) - ts_now.to_pydatetime()
        st.caption(
            f"Ultima parada detectada: {CAUSE_LABEL.get(cause_now, cause_now)}  "
            f"·  hace {int(elapsed.total_seconds())}s"
        )

    suggestions = suggest_causes(machine["machine_id"], hour, shift)

    st.subheader("Causa sugerida")
    for cause, prob in suggestions:
        if st.button(f"{CAUSE_LABEL[cause]}  ·  {prob:.0%}",
                     use_container_width=True, key=f"sug_{cause}"):
            publish_stop(machine["machine_id"], cause)
            st.success(f"Registrado: {CAUSE_LABEL[cause]} en {machine['machine_id']}")
            st.balloons()

    with st.expander("Otra causa"):
        sugg_codes = {c for c, _ in suggestions}
        for cause in CAUSES:
            if cause in sugg_codes:
                continue
            if st.button(CAUSE_LABEL[cause],
                         use_container_width=True, key=f"alt_{cause}"):
                publish_stop(machine["machine_id"], cause)
                st.success(f"Registrado: {CAUSE_LABEL[cause]} en {machine['machine_id']}")


def sim_is_alive() -> bool:
    pid = st.session_state.get("sim_pid")
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_simulation(minutes: int) -> None:
    if sim_is_alive():
        return
    duration_s = int(minutes * 60)
    env = os.environ.copy()
    env["SIM_DURATION_S"] = str(duration_s)
    env["SIM_SPEED"] = env.get("SIM_SPEED", "20.0")
    env["MQTT_HOST"] = MQTT_HOST
    env["MQTT_PORT"] = str(MQTT_PORT)
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "simulator" / "main.py")],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    st.session_state.sim_pid = proc.pid
    st.session_state.sim_until = time.time() + duration_s


def stop_simulation() -> None:
    pid = st.session_state.get("sim_pid")
    if not pid:
        return
    try:
        os.kill(pid, 15)
    except OSError:
        pass
    st.session_state.sim_pid = None
    st.session_state.sim_until = None


def render_sidebar() -> bool:
    with st.sidebar:
        st.markdown("### Configuracion")
        demo_mode = st.toggle("Modo demo (1 verde · 1 amarillo · 1 rojo)", value=True,
                              help="Util para capturas. Apagado, usa el estado real de las maquinas.")

        # El lanzador de simulacion solo aparece si hay broker MQTT y BD locales
        # (es decir, no en Streamlit Cloud). En cloud queda oculto.
        if not is_demo_mode():
            st.markdown("---")
            st.markdown("### Simulacion")
            st.caption("Lanza eventos de planta al broker durante el tiempo elegido. Util para probar la app sin sensores reales.")

            if sim_is_alive():
                remaining = max(0, int(st.session_state.get("sim_until", 0) - time.time()))
                mm, ss = divmod(remaining, 60)
                st.success(f"▶ Simulacion corriendo — quedan {mm:02d}:{ss:02d}")
                if st.button("⏹ Detener simulacion", use_container_width=True):
                    stop_simulation()
                    st.rerun()
            else:
                minutes = st.selectbox("Duracion", [1, 3, 5, 10], index=1,
                                       format_func=lambda x: f"{x} min")
                if st.button("▶ Iniciar simulacion", use_container_width=True, type="primary"):
                    start_simulation(minutes)
                    st.rerun()
        else:
            st.markdown("---")
            st.info(
                "Estas en la **demo publica**. Los datos son sinteticos para que puedas "
                "probar la interfaz sin conectarte a una planta real."
            )

    return demo_mode


def main() -> None:
    st.markdown(
        """
        <div style="background:#0f172a; padding:14px 20px; border-radius:10px;
                    border-left:6px solid #ef4444; margin-bottom:14px;">
            <div style="color:#f1f5f9; font-size:22px; font-weight:700;">🚨 Andon — Estado de planta</div>
            <div style="color:#cbd5e1; font-size:13px;">
                Verde: produccion estable · Amarillo: requiere atencion · Rojo: detenida — confirmar causa.
                Toca el boton bajo cada semaforo para ver el detalle.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    demo_mode = render_sidebar()

    machines = get_machines()
    last_state = get_last_state()
    recent = get_recent_stops(minutes=5)
    oee_df = get_latest_oee().set_index("machine_id")

    statuses: dict[str, str] = {}
    for _, m in machines.iterrows():
        mid = m["machine_id"]
        if demo_mode and mid in DEMO_STATUSES:
            statuses[mid] = DEMO_STATUSES[mid]
        else:
            statuses[mid] = derive_status_real(mid, last_state, recent)

    if "selected_machine" not in st.session_state or st.session_state.selected_machine not in statuses:
        red = [m for m, s in statuses.items() if s == STATE_RED]
        yellow = [m for m, s in statuses.items() if s == STATE_YELLOW]
        st.session_state.selected_machine = red[0] if red else (yellow[0] if yellow else list(statuses.keys())[0])

    selected = st.session_state.selected_machine

    cols = st.columns(len(machines))
    for col, (_, m) in zip(cols, machines.iterrows()):
        render_light(col, m, statuses[m["machine_id"]], selected=(m["machine_id"] == selected))

    st.markdown("---")

    machine = machines[machines["machine_id"] == selected].iloc[0]
    status = statuses[selected]

    now = datetime.now(timezone.utc).astimezone()
    shift = "M" if 6 <= now.hour < 14 else ("T" if 14 <= now.hour < 22 else "N")
    st.caption(f"Detalle de **{machine['name']}** — Hora: {now:%H:%M}  ·  Turno: {shift}")

    oee_row = oee_df.loc[selected] if selected in oee_df.index else None

    if status == STATE_GREEN:
        panel_verde(machine, oee_row)
    elif status == STATE_YELLOW:
        panel_amarillo(machine, oee_row, recent)
    else:
        panel_rojo(machine, now.hour, shift)


if __name__ == "__main__":
    main()
else:
    main()
