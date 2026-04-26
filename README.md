# OEE Andon ML

> Plataforma open-source para medir el **OEE en tiempo real** en planta, con
> captura automatica de datos via **MQTT / OPC UA**, **Andon digital** integrado
> y **modelos de Machine Learning** que detectan microparadas, sugieren causas
> y predicen el cierre del turno.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/dashboard-streamlit-ff4b4b.svg)](https://streamlit.io/)
[![MQTT](https://img.shields.io/badge/transport-MQTT%20%2F%20Sparkplug%20B-660066.svg)](https://mqtt.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/run-docker--compose-2496ed.svg)](docker-compose.yml)

---

## Por que existe este proyecto

En la mayoria de las PYMES de manufactura el OEE se calcula a mano: el
supervisor llena una planilla al final del turno y alguien lo pasa a un
Excel. El resultado llega tarde, los datos estan sesgados y las **microparadas
(la perdida mas grande de todas) son invisibles**.

`oee-andon-ml` propone una arquitectura abierta y de bajo costo para que
cualquier planta capture **el OEE real**, lo vea **hora por hora y maquina
por maquina** en una pantalla de produccion, y use **IA** para convertir el
KPI en una decision (no solo un reporte).

| Lo que hay hoy en internet                  | Lo que aporta este repo                                  |
|---------------------------------------------|----------------------------------------------------------|
| Calculadoras estaticas en Excel             | Calculo en streaming con TimescaleDB + MQTT              |
| Tutoriales que asumen entrada manual        | Captura via OPC UA / MQTT Sparkplug B / sensores ESP32   |
| Dashboards "bonitos" sin logica de decision | Pareto + TOC + simulador what-if + alertas predictivas   |
| Software MES caro y cerrado                 | 100% open source, Dockerizado, demo online en 1 clic     |
| Material en ingles                          | Documentacion y articulo en espanol                      |

---

## Caracteristicas principales

- **Captura automatica** de ciclos producidos, paradas y velocidad desde PLC
  (OPC UA), retrofit con ESP32 + sensor inductivo, o vision por computadora.
- **Unified Namespace** alineado a **ISA-95** sobre broker MQTT (Mosquitto).
- **Calculo de OEE en streaming** (Disponibilidad x Rendimiento x Calidad) con
  ventana movil por turno, dia y semana.
- **Pantalla de planta** con cabecera didactica que explica la formula OEE =
  Disponibilidad x Rendimiento x Calidad, semaforo por maquina, Pareto de
  causas en espanol y tendencia hora a hora.
- **Andon digital movil** (tablet) con **semaforos clickeables** (verde / amarillo
  / rojo) y panel contextual por estado: produccion en verde, microparadas en
  amarillo, **causa sugerida por ML** en rojo para cerrar la parada en 2 toques.
- **Modo demo** integrado en el Andon: un toggle fija un estado por maquina y
  un boton lanza el simulador durante N minutos sin necesidad de terminal.
- **4 modelos de ML integrados**:
  1. Deteccion de microparadas (Isolation Forest sobre serie de ciclos).
  2. Clasificacion de causa de parada (LightGBM sobre features contextuales).
  3. Forecast de OEE de cierre del turno (Prophet + LightGBM).
  4. Mantenimiento predictivo simple (regresion sobre vibracion / corriente).
- **Simulador realista** de planta con 3 maquinas para correr la demo sin
  hardware fisico.

---

## Arquitectura

```
                +------------------+
                |  PLC / CNC / IoT |  <-- OPC UA, Modbus, sensores ESP32
                +---------+--------+
                          |
                          v
                +------------------+
                | Edge Gateway /   |  Publica con tópicos ISA-95:
                | ESP32 + bridge   |  enterprise/site/area/line/machine/...
                +---------+--------+
                          |  MQTT (Sparkplug B)
                          v
                +------------------+
                |   Mosquitto      |  <-- Unified Namespace (UNS)
                +---------+--------+
                          |
        +-----------------+-----------------+
        |                 |                 |
        v                 v                 v
+--------------+  +----------------+  +------------------+
|  Procesador  |  |  Modelos ML    |  |   Andon movil    |
|  (FastAPI)   |  |  (scikit /     |  |   (Streamlit)    |
|  calcula OEE |  |   LightGBM /   |  |   +sugerencia ML |
|  y persiste  |  |   Prophet)     |  +------------------+
+------+-------+  +-------+--------+
       |                  |
       v                  v
+--------------+   +----------------+
| TimescaleDB  |-->|   Dashboard    | <-- pantalla de planta
| (eventos +   |   |   (Streamlit)  |     (TV 55", refresco 5s)
|  metricas)   |   |   + Plotly     |
+--------------+   +----------------+
```

---

## Estructura del repositorio

```
oee-andon-ml/
├── simulator/        Publisher MQTT que simula 3 maquinas reales
├── broker/           docker-compose, mosquitto.conf, init.sql Timescale
├── processor/        FastAPI: consume MQTT, calcula OEE, persiste
├── ml/
│   ├── notebooks/    Entrenamiento y EDA
│   ├── models/       Modelos serializados (.pkl)
│   └── data/         Datasets de ejemplo
├── dashboard/        Streamlit para pantalla de planta y supervisores
├── andon/            Streamlit mobile-friendly para operarios
├── docs/             Diagramas, guia de despliegue, datasheets
├── tests/            Pytest
├── scripts/          Utilidades CLI (cargar datos, entrenar, etc.)
├── docker-compose.yml
├── requirements.txt
├── PROJECT.md        Guia de trabajo + wireframe del articulo
└── README.md
```

---

## Quick start (demo en 5 minutos)

### Opcion A — Docker (recomendada)

Requisitos: Docker + Docker Compose.

```bash
git clone https://github.com/leanmasterpymes/oee-andon-ml.git
cd oee-andon-ml
docker compose up -d
```

Abrir en el navegador:

- **Pantalla de planta**: http://localhost:8501
- **Andon (tablet/celular)**: http://localhost:8502
- **Broker MQTT**: `localhost:1883` (cliente recomendado: MQTT Explorer)

El simulador empieza a publicar ciclos y paradas automaticamente. En 1-2
minutos el dashboard ya muestra OEE real.

Para detener: `docker compose down`. Para borrar datos: `docker compose down -v`.

### Opcion B — Instalacion nativa (sin Docker)

Util si Docker no esta disponible (por politicas IT, hardware limitado, edge
device). Probada en Ubuntu 24.04 / WSL 2.

```bash
# 1) Broker, base de datos y dependencias del sistema
sudo apt install -y mosquitto mosquitto-clients postgresql-common
curl -s https://packagecloud.io/install/repositories/timescale/timescaledb/script.deb.sh | sudo bash
sudo apt install -y timescaledb-2-postgresql-16 python3-venv

# 2) Habilitar TimescaleDB
echo "shared_preload_libraries = 'timescaledb'" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
sudo systemctl restart postgresql
sudo systemctl enable --now mosquitto postgresql

# 3) Base de datos y esquema
sudo -u postgres psql -c "CREATE USER oee WITH PASSWORD 'oee';"
sudo -u postgres psql -c "CREATE DATABASE oee OWNER oee;"
sudo -u postgres psql -d oee -c "CREATE EXTENSION timescaledb;"
sudo -u postgres psql -d oee < broker/init.sql

# 4) Entorno Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 5) Levantar los 4 servicios (4 terminales)
python simulator/main.py                                      # publica eventos al broker
python processor/main.py                                      # consume MQTT y calcula OEE
streamlit run dashboard/app.py --server.port 8501             # pantalla de planta
streamlit run andon/app.py --server.port 8502                 # andon mobile
```

Detalle paso a paso en [`docs/integration.md`](docs/integration.md).

---

## Calculo de OEE

```
OEE = Disponibilidad x Rendimiento x Calidad

Disponibilidad = Tiempo Operativo / Tiempo Planificado
Rendimiento    = (Tiempo Ciclo Ideal x Total Producido) / Tiempo Operativo
Calidad        = Piezas Buenas / Total Producido
```

Benchmark mundial (Nakajima): **OEE >= 85%** se considera *world-class*
(0.90 x 0.95 x 0.999). El promedio en manufactura discreta ronda 55-60%.

---

## Conexion a maquinas reales

| Tipo de equipo                  | Camino recomendado                                    |
|---------------------------------|-------------------------------------------------------|
| PLC moderno (S7-1500, CompactLogix) | Cliente OPC UA -> bridge a MQTT Sparkplug B       |
| PLC viejo (S7-300, sin Ethernet)| Modbus TCP via gateway (Moxa / Ewon) -> MQTT           |
| Maquina sin PLC                 | ESP32 + sensor inductivo en salida + clamp de corriente|
| Banda con piezas no detectables | Camara + YOLO ligero -> conteo a MQTT                  |

Detalle paso a paso en [`docs/integration.md`](docs/integration.md).

---

## Modelos de Machine Learning

| Modelo                  | Algoritmo                | Entrada                                | Salida                          |
|-------------------------|--------------------------|----------------------------------------|---------------------------------|
| Microparadas            | Isolation Forest         | Serie de gaps entre ciclos             | `is_microstop` (0/1) + score    |
| Clasificacion de causa  | LightGBM                 | hora, turno, maquina, alarma PLC, dur. | top-3 causas con probabilidad   |
| Forecast OEE turno      | Prophet + LightGBM stack | Historico OEE intra-turno              | OEE estimado al cierre + IC 95% |
| Mantenimiento predictivo| Regresion / XGBoost      | Vibracion, corriente, temperatura      | Horas restantes hasta probable falla |

Todos los modelos se entrenan con notebooks reproducibles en `ml/notebooks/`
y datasets sinteticos generados por el simulador para que cualquiera pueda
correrlos.

---

## Roadmap

- [x] Estructura inicial y stack Docker
- [x] Simulador de 3 maquinas con paradas realistas y duracion configurable
- [x] Procesador OEE en streaming + persistencia Timescale
- [x] Dashboard pantalla de planta con formula OEE y Pareto en espanol
- [x] Andon mobile con semaforos clickeables y panel contextual por estado
- [x] Modo demo + lanzador de simulacion integrados en el Andon
- [x] Instalacion nativa documentada (alternativa sin Docker)
- [ ] Modelo de microparadas (Isolation Forest)
- [ ] Modelo de clasificacion de causa (LightGBM)
- [ ] Modelo de forecast OEE turno (Prophet + LightGBM)
- [ ] Guia paso a paso para conectar PLC real (OPC UA)
- [ ] Demo en Streamlit Community Cloud
- [ ] Articulo publicado en LinkedIn + blog Leanmaster Pymes

---

## Stack tecnologico

- **Mensajeria**: Mosquitto (MQTT 3.1.1 / 5.0), Sparkplug B opcional
- **Edge**: paho-mqtt, asyncua (OPC UA), ESP32 (firmware referencia)
- **Backend**: FastAPI, SQLAlchemy, psycopg
- **Persistencia**: TimescaleDB (PostgreSQL + extension de series temporales)
- **ML**: scikit-learn, LightGBM, Prophet
- **Frontend**: Streamlit + Plotly + streamlit-autorefresh
- **Orquestacion**: Docker Compose

---

## Licencia

Distribuido bajo licencia MIT. Ver [`LICENSE`](LICENSE).

---

## Contacto

Proyecto desarrollado por **Leanmaster Pymes**.
Web: [leanmasterpymes.com](https://leanmasterpymes.com) — LinkedIn:
[Leanmaster Pymes](https://www.linkedin.com/company/leanmaster-pymes).
