"""Dashboard pantalla de planta — vista TV.

Refresco cada 5s. Muestra:
- Tarjetas por maquina con semaforo, OEE, meta y delta.
- Pareto de causas de parada (top 6).
- Tendencia OEE hora-por-hora del turno en curso.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh


DB_DSN = os.getenv("DB_DSN", "postgresql+psycopg://oee:oee@localhost:5432/oee")
TARGET_OEE = 0.85

CAUSE_LABEL = {
    "BREAKDOWN": "Averia",
    "SETUP": "Cambio de formato",
    "MICROSTOP": "Microparada",
    "SLOW": "Velocidad reducida",
    "DEFECT": "Defecto",
    "STARTUP": "Arranque",
}

st.set_page_config(page_title="OEE en tiempo real", layout="wide", page_icon="📊")
st_autorefresh(interval=5000, key="planta-refresh")

engine = create_engine(DB_DSN, pool_pre_ping=True)


@st.cache_data(ttl=4)
def get_machines() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM machines ORDER BY machine_id", engine)


@st.cache_data(ttl=4)
def get_latest_oee() -> pd.DataFrame:
    q = text("""
        SELECT DISTINCT ON (machine_id)
            machine_id, ts, availability, performance, quality, oee, pieces_total, pieces_good
        FROM oee_snapshots
        ORDER BY machine_id, ts DESC
    """)
    return pd.read_sql(q, engine)


@st.cache_data(ttl=4)
def get_oee_trend(hours: int = 8) -> pd.DataFrame:
    q = text("""
        SELECT ts, machine_id, oee
        FROM oee_snapshots
        WHERE ts > NOW() - (:hrs * INTERVAL '1 hour')
        ORDER BY ts
    """)
    return pd.read_sql(q, engine, params={"hrs": hours})


@st.cache_data(ttl=4)
def get_pareto(hours: int = 8) -> pd.DataFrame:
    q = text("""
        SELECT cause, COUNT(*) AS events, SUM(duration_s)/60 AS minutes
        FROM stops
        WHERE ts > NOW() - (:hrs * INTERVAL '1 hour')
        GROUP BY cause
        ORDER BY minutes DESC
    """)
    return pd.read_sql(q, engine, params={"hrs": hours})


def color_for(oee: float, target: float = TARGET_OEE) -> str:
    if oee >= target:
        return "#16a34a"  # verde
    if oee >= target * 0.75:
        return "#eab308"  # ambar
    return "#dc2626"      # rojo


def render_card(col, machine: pd.Series, oee_row: pd.Series | None) -> None:
    with col:
        oee_val = oee_row["oee"] if oee_row is not None else 0.0
        a = oee_row["availability"] if oee_row is not None else 0.0
        p = oee_row["performance"] if oee_row is not None else 0.0
        q = oee_row["quality"] if oee_row is not None else 0.0
        target = machine["target_oee"]
        c = color_for(oee_val, target)

        st.markdown(
            f"""
            <div style="border-left: 8px solid {c}; padding: 12px 18px; background:#0f172a;
                        border-radius: 8px; margin-bottom: 8px;">
                <div style="color:#94a3b8; font-size:14px;">{machine['line'].upper()} · {machine['area'].upper()}</div>
                <div style="color:white; font-size:22px; font-weight:600;">{machine['name']}</div>
                <div style="color:{c}; font-size:46px; font-weight:700; margin-top:4px;">{oee_val:.0%}</div>
                <div style="color:#cbd5e1; font-size:13px;">Meta: {target:.0%} · Δ {(oee_val-target)*100:+.1f} pts</div>
                <div style="margin-top:10px; color:#e2e8f0; font-size:13px;">
                    D {a:.0%} · R {p:.0%} · C {q:.0%}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def header() -> None:
    now = datetime.now(timezone.utc).astimezone()
    hour = now.hour
    if 6 <= hour < 14:
        turno = "Turno mañana"
    elif 14 <= hour < 22:
        turno = "Turno tarde"
    else:
        turno = "Turno noche"

    st.markdown(
        """
        <div style="background:#0f172a; padding:18px 22px; border-radius:10px; margin-bottom:18px;
                    border-left:6px solid #0ea5e9;">
            <div style="color:#e2e8f0; font-size:22px; font-weight:700; margin-bottom:4px;">
                Cálculo del OEE en tiempo real
            </div>
            <div style="color:#f1f5f9; font-size:30px; font-weight:600; letter-spacing:1px;
                        font-family: 'Courier New', monospace; margin:6px 0 12px 0;">
                OEE = Disponibilidad × Rendimiento × Calidad
            </div>
            <div style="display:flex; gap:24px; color:#cbd5e1; font-size:14px; flex-wrap:wrap;">
                <div><b style="color:#38bdf8;">Disponibilidad (D)</b>: tiempo en marcha sobre tiempo planificado.</div>
                <div><b style="color:#38bdf8;">Rendimiento (R)</b>: piezas reales sobre piezas teóricas a velocidad ideal.</div>
                <div><b style="color:#38bdf8;">Calidad (C)</b>: piezas buenas sobre piezas totales producidas.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([3, 2, 1])
    c1.markdown("### Planta 1 — Empaque")
    c2.markdown(f"#### {turno}")
    c3.markdown(f"#### {now:%H:%M:%S}")


def main() -> None:
    header()

    machines = get_machines()
    oee = get_latest_oee().set_index("machine_id")

    cols = st.columns(len(machines))
    for col, (_, m) in zip(cols, machines.iterrows()):
        row = oee.loc[m["machine_id"]] if m["machine_id"] in oee.index else None
        render_card(col, m, row)

    st.markdown("---")
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Tendencia OEE — ultimas 8 horas")
        trend = get_oee_trend(hours=8)
        if not trend.empty:
            fig = px.line(trend, x="ts", y="oee", color="machine_id",
                          labels={"oee": "OEE", "ts": "Hora", "machine_id": "Maquina"})
            fig.add_hline(y=TARGET_OEE, line_dash="dash", line_color="#16a34a",
                          annotation_text=f"Meta {TARGET_OEE:.0%}")
            fig.update_yaxes(tickformat=".0%", range=[0, 1])
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Esperando datos del procesador...")

    with right:
        st.subheader("Pareto de causas (8h)")
        pareto = get_pareto(hours=8)
        if not pareto.empty:
            pareto["causa"] = pareto["cause"].map(CAUSE_LABEL).fillna(pareto["cause"])
            pareto["acum_pct"] = pareto["minutes"].cumsum() / pareto["minutes"].sum() * 100
            fig = go.Figure()
            fig.add_bar(x=pareto["causa"], y=pareto["minutes"], name="Minutos",
                        marker_color="#dc2626")
            fig.add_scatter(x=pareto["causa"], y=pareto["acum_pct"], name="% acum.",
                            yaxis="y2", mode="lines+markers", line=dict(color="#0ea5e9"))
            fig.update_layout(
                yaxis=dict(title="Minutos"),
                yaxis2=dict(title="% acumulado", overlaying="y", side="right",
                            range=[0, 110], ticksuffix="%"),
                height=380, margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=-0.2),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin paradas registradas todavia.")


if __name__ == "__main__":
    main()
else:
    main()
