"""Motor de OEE en ventana movil.

OEE = Disponibilidad x Rendimiento x Calidad

  Disponibilidad = (Tiempo planificado - tiempo de paradas no planificadas)
                   / Tiempo planificado
  Rendimiento    = (Tiempo ciclo ideal x piezas totales) / Tiempo operativo
  Calidad        = piezas buenas / piezas totales
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class CycleEvent:
    ts: datetime
    duration_s: float
    ideal_cycle_s: float


@dataclass
class StopEvent:
    ts: datetime
    cause: str
    duration_s: float


@dataclass
class QualityEvent:
    ts: datetime
    good: bool


@dataclass
class OEEMetrics:
    availability: float
    performance: float
    quality: float
    oee: float
    pieces_total: int
    pieces_good: int


@dataclass
class MachineWindow:
    """Ventana movil de eventos para una maquina."""

    machine_id: str
    minutes: int = 60
    ideal_cycle_s: float = 12.0
    cycles: deque[CycleEvent] = field(default_factory=deque)
    stops: deque[StopEvent] = field(default_factory=deque)
    quality: deque[QualityEvent] = field(default_factory=deque)

    def trim(self, now: datetime) -> None:
        cutoff = now - timedelta(minutes=self.minutes)
        for buf in (self.cycles, self.stops, self.quality):
            while buf and buf[0].ts < cutoff:
                buf.popleft()

    def add_cycle(self, ev: CycleEvent) -> None:
        self.cycles.append(ev)

    def add_stop(self, ev: StopEvent) -> None:
        self.stops.append(ev)

    def add_quality(self, ev: QualityEvent) -> None:
        self.quality.append(ev)

    def metrics(self, now: datetime) -> OEEMetrics:
        self.trim(now)

        planned_s = self.minutes * 60
        unplanned_down_s = sum(s.duration_s for s in self.stops if s.cause != "STARTUP")
        operating_s = max(planned_s - unplanned_down_s, 0)

        pieces_total = len(self.cycles)
        pieces_good = sum(1 for q in self.quality if q.good)
        # Si la calidad llega por evento separado, asumir 1 buena por ciclo si no hay quality.
        if pieces_total > 0 and not self.quality:
            pieces_good = pieces_total

        availability = operating_s / planned_s if planned_s else 0.0
        ideal_total_s = pieces_total * self.ideal_cycle_s
        performance = (ideal_total_s / operating_s) if operating_s > 0 else 0.0
        performance = min(performance, 1.0)  # Capear en 1.0 (no se puede ir mas rapido que ideal)
        quality = (pieces_good / pieces_total) if pieces_total > 0 else 1.0

        oee = availability * performance * quality
        return OEEMetrics(
            availability=availability,
            performance=performance,
            quality=quality,
            oee=oee,
            pieces_total=pieces_total,
            pieces_good=pieces_good,
        )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
