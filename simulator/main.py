"""Simulador de planta: publica eventos MQTT realistas para 3 maquinas.

Topicos (alineados a ISA-95):
    lmp/planta1/empaque/linea1/maquina01/cycle    -> ciclo terminado
    lmp/planta1/empaque/linea1/maquina01/stop     -> parada
    lmp/planta1/empaque/linea1/maquina01/quality  -> resultado de calidad
    lmp/planta1/empaque/linea1/maquina01/state    -> estado (run/idle/down)

Las paradas siguen la taxonomia Six Big Losses:
    BREAKDOWN, SETUP, MICROSTOP, SLOW, DEFECT, STARTUP
"""

from __future__ import annotations

import json
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from loguru import logger


MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
N_MACHINES = int(os.getenv("N_MACHINES", "3"))
SPEED = float(os.getenv("SIM_SPEED", "1.0"))  # 1.0 = tiempo real, 10.0 = 10x

CAUSES = {
    "BREAKDOWN": {"weight": 0.10, "min_s": 300, "max_s": 1800},
    "SETUP":     {"weight": 0.20, "min_s": 600, "max_s": 1500},
    "MICROSTOP": {"weight": 0.45, "min_s": 30,  "max_s": 180},
    "SLOW":      {"weight": 0.10, "min_s": 60,  "max_s": 600},
    "DEFECT":    {"weight": 0.10, "min_s": 0,   "max_s": 0},
    "STARTUP":   {"weight": 0.05, "min_s": 120, "max_s": 600},
}


@dataclass
class Machine:
    machine_id: str
    line: str = "linea1"
    area: str = "empaque"
    site: str = "planta1"
    enterprise: str = "lmp"
    ideal_cycle_s: float = 12.0     # 1 pieza cada 12s = 5/min = 300/h
    quality_rate: float = 0.97
    breakdown_lambda: float = 1 / 3600  # 1 falla/hora promedio
    state: str = "RUN"
    pieces_total: int = 0
    pieces_good: int = 0
    last_event_ts: float = field(default_factory=time.time)

    def topic(self, signal: str) -> str:
        return f"{self.enterprise}/{self.site}/{self.area}/{self.line}/{self.machine_id}/{signal}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def publish(client: mqtt.Client, topic: str, payload: dict) -> None:
    client.publish(topic, json.dumps(payload), qos=0, retain=False)
    logger.debug(f"-> {topic} {payload}")


def pick_cause() -> str:
    causes = list(CAUSES.keys())
    weights = [CAUSES[c]["weight"] for c in causes]
    return random.choices(causes, weights=weights, k=1)[0]


def simulate_machine(client: mqtt.Client, m: Machine) -> None:
    """Bucle de eventos para una maquina. Genera ciclos y, ocasionalmente, paradas."""
    publish(client, m.topic("state"), {"ts": now_iso(), "state": "RUN"})

    while True:
        # ¿Falla aleatoria?
        if random.random() < m.breakdown_lambda * m.ideal_cycle_s:
            cause = "BREAKDOWN"
        elif random.random() < 0.02:  # microparada cada ~50 ciclos
            cause = "MICROSTOP"
        elif random.random() < 0.005:  # cambio de formato esporadico
            cause = "SETUP"
        else:
            cause = None

        if cause:
            stop_dur = random.uniform(CAUSES[cause]["min_s"], CAUSES[cause]["max_s"])
            m.state = "DOWN"
            publish(client, m.topic("state"), {"ts": now_iso(), "state": "DOWN"})
            publish(client, m.topic("stop"), {
                "ts": now_iso(),
                "cause": cause,
                "duration_s": round(stop_dur, 1),
                "alarm_code": f"A{random.randint(100, 999)}" if cause == "BREAKDOWN" else None,
            })
            logger.info(f"[{m.machine_id}] STOP {cause} {stop_dur:.0f}s")
            time.sleep(stop_dur / SPEED)
            m.state = "RUN"
            publish(client, m.topic("state"), {"ts": now_iso(), "state": "RUN"})
            continue

        # Ciclo normal con jitter en la velocidad
        cycle_dur = m.ideal_cycle_s * random.uniform(0.95, 1.20)
        time.sleep(cycle_dur / SPEED)

        m.pieces_total += 1
        good = random.random() < m.quality_rate
        if good:
            m.pieces_good += 1

        publish(client, m.topic("cycle"), {
            "ts": now_iso(),
            "duration_s": round(cycle_dur, 2),
            "ideal_cycle_s": m.ideal_cycle_s,
        })
        publish(client, m.topic("quality"), {
            "ts": now_iso(),
            "good": good,
            "total": m.pieces_total,
            "good_total": m.pieces_good,
        })


def make_machines(n: int) -> list[Machine]:
    presets = [
        Machine(machine_id="maquina01", ideal_cycle_s=12.0, quality_rate=0.97),
        Machine(machine_id="maquina02", ideal_cycle_s=8.0,  quality_rate=0.95, line="linea1"),
        Machine(machine_id="maquina03", ideal_cycle_s=20.0, quality_rate=0.99, line="linea2"),
    ]
    return presets[:n]


def main() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="oee-simulator")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()
    logger.info(f"Conectado al broker {MQTT_HOST}:{MQTT_PORT}")

    machines = make_machines(N_MACHINES)
    logger.info(f"Simulando {len(machines)} maquinas a {SPEED}x")

    # Hilos por maquina via threading nativo
    import threading
    threads = []
    for m in machines:
        t = threading.Thread(target=simulate_machine, args=(client, m), daemon=True)
        t.start()
        threads.append(t)

    # Espera de senial de termino
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()

    logger.info("Cerrando simulador")
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
