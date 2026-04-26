"""Servicio que consume eventos MQTT, calcula OEE en streaming y persiste en TimescaleDB.

Suscribe a:  lmp/+/+/+/+/{cycle,stop,quality,state}
Cada minuto emite un snapshot de OEE por maquina.
"""

from __future__ import annotations

import json
import os
import signal
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg
from loguru import logger

from oee_engine import CycleEvent, MachineWindow, QualityEvent, StopEvent, now_utc


MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DB_DSN = os.getenv("DB_DSN", "postgresql://oee:oee@localhost:5432/oee")
SNAPSHOT_INTERVAL_S = int(os.getenv("SNAPSHOT_INTERVAL_S", "60"))

IDEAL_CYCLES = {
    "maquina01": 12.0,
    "maquina02": 8.0,
    "maquina03": 20.0,
}

windows: dict[str, MachineWindow] = {}
windows_lock = threading.Lock()


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def get_window(machine_id: str) -> MachineWindow:
    with windows_lock:
        if machine_id not in windows:
            windows[machine_id] = MachineWindow(
                machine_id=machine_id,
                ideal_cycle_s=IDEAL_CYCLES.get(machine_id, 12.0),
            )
        return windows[machine_id]


def on_message(client: mqtt.Client, userdata, msg) -> None:
    parts = msg.topic.split("/")
    if len(parts) < 6:
        return
    machine_id = parts[4]
    signal_name = parts[5]
    try:
        payload = json.loads(msg.payload.decode())
    except Exception as exc:
        logger.warning(f"Payload invalido en {msg.topic}: {exc}")
        return

    ts = parse_ts(payload.get("ts", now_utc().isoformat()))
    win = get_window(machine_id)

    # Persistir evento crudo.
    persist_event(ts, machine_id, signal_name, payload)

    if signal_name == "cycle":
        win.add_cycle(CycleEvent(
            ts=ts,
            duration_s=payload.get("duration_s", 0),
            ideal_cycle_s=payload.get("ideal_cycle_s", win.ideal_cycle_s),
        ))
    elif signal_name == "stop":
        ev = StopEvent(ts=ts, cause=payload["cause"], duration_s=payload["duration_s"])
        win.add_stop(ev)
        persist_stop(ts, machine_id, ev.cause, ev.duration_s, payload.get("alarm_code"))
    elif signal_name == "quality":
        win.add_quality(QualityEvent(ts=ts, good=bool(payload["good"])))


def persist_event(ts: datetime, machine_id: str, event_type: str, payload: dict) -> None:
    try:
        with psycopg.connect(DB_DSN, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO events (ts, machine_id, event_type, payload) VALUES (%s, %s, %s, %s)",
                (ts, machine_id, event_type, json.dumps(payload)),
            )
    except Exception as exc:
        logger.error(f"persist_event falló: {exc}")


def persist_stop(ts: datetime, machine_id: str, cause: str, dur: float, alarm: str | None) -> None:
    try:
        with psycopg.connect(DB_DSN, autocommit=True) as conn:
            conn.execute(
                "INSERT INTO stops (ts, machine_id, cause, duration_s, alarm_code) VALUES (%s, %s, %s, %s, %s)",
                (ts, machine_id, cause, dur, alarm),
            )
    except Exception as exc:
        logger.error(f"persist_stop falló: {exc}")


def snapshot_loop(stop_event: threading.Event) -> None:
    while not stop_event.wait(SNAPSHOT_INTERVAL_S):
        now = now_utc()
        with windows_lock:
            snaps = {mid: w.metrics(now) for mid, w in windows.items()}
        for machine_id, m in snaps.items():
            try:
                with psycopg.connect(DB_DSN, autocommit=True) as conn:
                    conn.execute(
                        """INSERT INTO oee_snapshots
                           (ts, machine_id, availability, performance, quality, oee, pieces_total, pieces_good)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (now, machine_id, m.availability, m.performance, m.quality, m.oee, m.pieces_total, m.pieces_good),
                    )
                logger.info(f"[{machine_id}] OEE={m.oee:.1%} (A={m.availability:.1%} P={m.performance:.1%} Q={m.quality:.1%})")
            except Exception as exc:
                logger.error(f"snapshot falló para {machine_id}: {exc}")


def wait_for_db() -> None:
    for _ in range(30):
        try:
            with psycopg.connect(DB_DSN) as conn:
                conn.execute("SELECT 1")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("TimescaleDB no responde")


def main() -> None:
    logger.info("Esperando TimescaleDB...")
    wait_for_db()
    logger.info("DB lista.")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="oee-processor")
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.subscribe("lmp/+/+/+/+/+", qos=0)
    client.loop_start()
    logger.info("Suscrito al UNS.")

    stop_event = threading.Event()
    snap_thread = threading.Thread(target=snapshot_loop, args=(stop_event,), daemon=True)
    snap_thread.start()

    signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: stop_event.set())
    stop_event.wait()

    logger.info("Cerrando procesador.")
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
