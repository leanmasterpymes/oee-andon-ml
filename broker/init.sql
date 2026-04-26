-- Esquema base para el procesador OEE.
-- Compatible con TimescaleDB (PostgreSQL + extension series temporales).

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Cada evento crudo recibido por MQTT.
CREATE TABLE IF NOT EXISTS events (
    ts          TIMESTAMPTZ      NOT NULL,
    machine_id  TEXT             NOT NULL,
    event_type  TEXT             NOT NULL,   -- cycle | stop | quality | state
    payload     JSONB            NOT NULL
);
SELECT create_hypertable('events', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS events_machine_idx ON events (machine_id, ts DESC);

-- Paradas materializadas (una fila por evento de stop).
CREATE TABLE IF NOT EXISTS stops (
    ts          TIMESTAMPTZ      NOT NULL,
    machine_id  TEXT             NOT NULL,
    cause       TEXT             NOT NULL,   -- BREAKDOWN, SETUP, MICROSTOP, SLOW, DEFECT, STARTUP
    duration_s  DOUBLE PRECISION NOT NULL,
    alarm_code  TEXT,
    detected_by TEXT             NOT NULL DEFAULT 'sensor'  -- sensor | operator | ml
);
SELECT create_hypertable('stops', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS stops_machine_idx ON stops (machine_id, ts DESC);

-- Snapshot de OEE por maquina y minuto (lo escribe el procesador).
CREATE TABLE IF NOT EXISTS oee_snapshots (
    ts            TIMESTAMPTZ      NOT NULL,
    machine_id    TEXT             NOT NULL,
    availability  DOUBLE PRECISION NOT NULL,
    performance   DOUBLE PRECISION NOT NULL,
    quality       DOUBLE PRECISION NOT NULL,
    oee           DOUBLE PRECISION NOT NULL,
    pieces_total  INTEGER          NOT NULL,
    pieces_good   INTEGER          NOT NULL
);
SELECT create_hypertable('oee_snapshots', 'ts', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS oee_snap_machine_idx ON oee_snapshots (machine_id, ts DESC);

-- Catalogo de maquinas (parametros maestros).
CREATE TABLE IF NOT EXISTS machines (
    machine_id     TEXT PRIMARY KEY,
    name           TEXT,
    line           TEXT,
    area           TEXT,
    ideal_cycle_s  DOUBLE PRECISION NOT NULL,
    target_oee     DOUBLE PRECISION DEFAULT 0.85
);

INSERT INTO machines (machine_id, name, line, area, ideal_cycle_s, target_oee) VALUES
    ('maquina01', 'Empacadora 1', 'linea1', 'empaque', 12.0, 0.85),
    ('maquina02', 'Empacadora 2', 'linea1', 'empaque',  8.0, 0.85),
    ('maquina03', 'Etiquetadora', 'linea2', 'empaque', 20.0, 0.85)
ON CONFLICT (machine_id) DO NOTHING;
