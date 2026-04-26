# CLAUDE.md — guia interna del proyecto

Este documento es la **brujula del repositorio** para cualquier sesion futura
de trabajo (humana o asistida por IA). Incluye:

1. Contexto y objetivo de negocio.
2. Decisiones de arquitectura ya tomadas.
3. Convenciones de codigo y datos.
4. **Wireframe del articulo de LinkedIn** (la pieza publica que justifica el
   repo).
5. Backlog priorizado para el MVP.

---

## 1. Contexto

- **Autor**: Manuel Antonio Perez Ogando (Leanmaster Pymes). Ingeniero industrial,
  maestria en gestion estrategica para el desarrollo de software, certificado
  Power BI, profesor de Investigacion de Operaciones, especialista en
  procesos.
- **Objetivo de negocio**: ganar visibilidad en LinkedIn (empresas, contactos,
  reclutadores) demostrando capacidad de combinar **ingenieria industrial +
  ciencia de datos + ingenieria de software**.
- **Cadencia editorial**: un articulo semanal con su repo publico.
- **Audiencia**: gerentes de planta, jefes de mantenimiento, jefes de
  produccion, consultores lean, reclutadores tech-industria.

## 2. Decisiones de arquitectura (ya cerradas)

- **Mensajeria**: MQTT (Mosquitto) como columna vertebral. Sparkplug B es
  opcional pero documentado.
- **Topic design**: ISA-95 -> `enterprise/site/area/line/machine/<signal>`.
- **Persistencia**: TimescaleDB (no Influx) por SQL estandar y por que la
  mayoria de los lectores conoce PostgreSQL.
- **Backend**: FastAPI (suscriptor MQTT + API REST minima).
- **Frontend**: Streamlit (rapido de iterar y de demostrar). Si en el futuro
  se necesita TV-grade, migrar a Grafana o Next.js.
- **ML**: scikit-learn / LightGBM / Prophet. Nada de deep learning para el MVP.
- **Despliegue**: Docker Compose local + Streamlit Community Cloud para la
  demo publica.
- **Idioma del codigo**: comentarios en espanol cuando aporten contexto de
  negocio; nombres de variables y funciones en ingles.

## 3. Convenciones

- **Tópicos MQTT**: minusculas, separados por `/`. Ej.:
  `lmp/planta1/empaque/linea2/maquina03/cycle`.
- **Payload**: JSON UTF-8 con campos `ts` (ISO 8601 UTC), `value`, `quality`
  (`good|bad|uncertain`), `unit` opcional.
- **Codigos de causa de parada**: alineados a las **Six Big Losses** (TPM):
  `BREAKDOWN`, `SETUP`, `MICROSTOP`, `SLOW`, `DEFECT`, `STARTUP`. Mantener
  esta taxonomia estable en toda la app.
- **Tiempo**: todo en UTC en la base; la UI convierte a hora local de planta.
- **No** dejar rastros de herramientas de asistencia (firmas tipo "generated
  with X", co-author tags, comentarios "TODO IA") ni en commits ni en
  codigo publico.

## 4. Wireframe del articulo

> Este es el wireframe **acabado** que pediste. Cuando llegue el momento de
> escribir el articulo, seguir esta estructura. Cada bloque indica si lleva
> formula, codigo, imagen o diagrama.

### 4.0 Datos generales

- **Titulo (LinkedIn / blog)**:
  *De la planilla al tiempo real: medi el OEE de tu planta con MQTT, un
  Andon digital y Machine Learning (open source, en Python)*
- **Subtitulo / hook**:
  *Como pase de un Excel mensual a un dashboard hora-por-hora con IA que te
  avisa antes de cerrar el turno.*
- **Tiempo de lectura objetivo**: 8-10 minutos.
- **Tono**: profesional, cercano, sin jerga innecesaria. Cada vez que aparezca
  un termino tecnico (Sparkplug B, TOC, Isolation Forest), explicarlo en una
  linea.
- **CTA final**: link al repo + invitacion a probar la demo en 1 clic + DM
  abierta para implementarlo.

### 4.1 Apertura — el dolor (texto, ~150 palabras)

- Anecdota: *"En la mayoria de las plantas que visito, el OEE se calcula los
  lunes a la manana sobre lo que paso la semana pasada. Para entonces, el
  problema ya costo plata."*
- Tres frases punzantes:
  - El operario digita lo que recuerda.
  - Las microparadas (la perdida mas grande) **nunca aparecen**.
  - Cuando llega el numero, ya nadie puede actuar.
- Promesa del articulo: vamos a montar un sistema **abierto, barato y en
  tiempo real** que cualquier planta pueda copiar.

**Imagen sugerida**: foto real de una pizarra con planilla manual de
produccion (banco de imagenes, atribuir). Va arriba del titulo.

### 4.2 Que es OEE y por que importa (texto + formula + tabla)

- 4 lineas explicando el indicador con lenguaje llano.
- **Formula (bloque destacado)**:
  ```
  OEE = Disponibilidad x Rendimiento x Calidad
  ```
- **Tabla** con benchmark mundial:

  | Nivel       | OEE     | Lectura                    |
  |-------------|---------|----------------------------|
  | World class | >= 85%  | Top 10% global (Nakajima)  |
  | Aceptable   | 60-85%  | Mayoria de PYMES           |
  | Bajo        | < 60%   | Hay oportunidad enorme     |

- **Imagen / diagrama**: barra horizontal con los 3 componentes (D/P/Q)
  multiplicandose. Hacer SVG simple en `docs/diagrams/oee_formula.svg`.

### 4.3 El problema real: los datos no llegan solos (texto + diagrama)

- Explicar las 3 fuentes de perdida de datos:
  1. Lo que el operario no anota.
  2. Lo que anota mal.
  3. Lo que llega tarde.
- Introducir la idea: *"Si la maquina ya sabe lo que hace, ¿por que se lo
  estamos preguntando al humano?"*
- **Diagrama 1**: planilla manual vs. captura automatica
  (`docs/diagrams/manual_vs_auto.svg`). Dos columnas con iconos.

### 4.4 La arquitectura propuesta (diagrama + texto)

- **Diagrama 2** — el central del articulo, debe ser limpio y claro
  (`docs/diagrams/architecture.svg` o exportar a PNG):
  ```
  PLC / sensores -> Edge (ESP32 / OPC UA) -> MQTT (UNS) -> Procesador
  -> TimescaleDB -> Dashboard / Andon / Modelos ML
  ```
- Explicar **Unified Namespace** en 3 frases: un broker MQTT donde toda la
  planta publica datos con tópicos jerarquicos (ISA-95) y donde cualquier
  app se conecta a leer.
- Mencionar **Sparkplug B** como capa opcional para empresas grandes.

### 4.5 Como conectar maquinas reales (tabla + foto + tip)

- **Tabla** de 4 filas (PLC moderno, PLC viejo, sin PLC, sin contador
  digital) con la solucion recomendada para cada caso. Mismo contenido que
  esta en el README.
- **Foto / imagen referencial**: ESP32 con sensor inductivo conectado a la
  salida de una maquina (foto de banco, atribuir; o screenshot del
  esquematico en Fritzing).
- **Tip destacado** (callout): *"Con menos de USD 50 se retrofitea una
  maquina vieja sin tocar el PLC."*

### 4.6 Calculo en streaming (bloque de codigo + explicacion)

- Mostrar el corazon del procesador: una funcion de ~25 lineas que escucha
  MQTT y actualiza OEE en ventana movil.
- **Bloque de codigo** (Python):
  ```python
  # processor/oee_engine.py (extracto)
  def update_oee(machine_id: str, event: CycleEvent) -> OEEMetrics:
      window = state.get_window(machine_id, minutes=60)
      window.append(event)

      operating_time = window.duration - window.unplanned_downtime
      ideal_time = window.total_count * window.ideal_cycle_time

      availability = operating_time / window.planned_time
      performance  = ideal_time / operating_time if operating_time else 0
      quality      = window.good_count / window.total_count if window.total_count else 0

      return OEEMetrics(availability, performance, quality)
  ```
- 3 frases explicando: *ventana movil*, *unplanned downtime* y por que
  recalcular en cada evento es barato.

### 4.7 La pantalla de planta (mockup + descripcion)

- **Imagen tipo screenshot** del dashboard real en Streamlit
  (`docs/images/dashboard_planta.png`, capturar cuando este listo). Si
  todavia no esta, hacer un mockup en Figma / Excalidraw.
- Layout descrito:
  - Cabecera didactica con la formula `OEE = Disponibilidad x Rendimiento x
    Calidad` y una linea explicando cada componente (D / R / C). Esto cumple
    doble funcion: pedagogica para visitantes y de marca para el articulo.
  - Linea de turno y hora (planta, turno actual, hora).
  - Grid con una tarjeta por maquina (semaforo + OEE + delta vs meta + D/R/C).
  - Panel inferior: Pareto de causas (etiquetas en espanol: Averia,
    Microparada, Cambio de formato, etc.) + tendencia OEE hora a hora.
- Explicar la **regla de los 5 segundos**: cualquiera que pase frente al TV
  debe entender el estado de planta en 5s.

### 4.8 El Andon en la tablet (mockup + flujo)

- **Imagen** de la app movil (`docs/images/andon_tablet.png`).
- Layout actual del Andon:
  - Tres **semaforos clickeables** (uno por maquina) — verde "En marcha",
    amarillo "Atencion" (microparadas frecuentes), rojo "Detenida". Click en
    cualquiera abre el panel de detalle.
  - **Panel contextual** segun el estado de la maquina seleccionada:
    - Verde: KPIs de produccion del turno (OEE, piezas, calidad) y los 3
      componentes (Disponibilidad / Rendimiento / Calidad).
    - Amarillo: cantidad de microparadas en los ultimos 5 min, tiempo
      perdido, OEE actual y botones rapidos para registrar la causa.
    - Rojo: alerta + tiempo desde la ultima parada + **top-3 causas
      sugeridas por ML** + opcion "Otra causa" en expander.
  - **Sidebar con lanzador de simulacion**: el lector del articulo puede
    apretar "▶ Iniciar simulacion (3 min)" y ver eventos llegar al broker
    sin abrir terminal. Tambien hay un toggle "Modo demo" que fija
    1 verde / 1 amarillo / 1 rojo para que la captura del articulo muestre
    los tres estados.
- **Diagrama de flujo** del Andon:
  ```
  Maquina detenida > 2 min  -->  Tablet alerta operario
                                       |
                                       v
                          ML sugiere top-3 causas mas probables
                                       |
                                       v
                Operario confirma con 1 toque  -->  Evento al broker
  ```
  (`docs/diagrams/andon_flow.svg`)
- Resaltar: *el operario no escribe nada, solo confirma*. Eso es lo que
  hace que el dato sea limpio.

### 4.9 Donde entra Machine Learning (texto + tabla + 1 bloque)

- Tabla con los 4 modelos (la misma del README).
- **Bloque de codigo corto** mostrando el clasificador de causas:
  ```python
  # ml/notebooks/01_cause_classifier.py (extracto)
  features = ["hour", "shift", "machine_id", "alarm_code", "stop_duration_s"]
  X = df[features]
  y = df["cause_code"]

  model = LGBMClassifier(n_estimators=300, learning_rate=0.05)
  model.fit(X_train, y_train)

  # Top-3 causas mas probables que iran al Andon
  proba = model.predict_proba(X_new)
  top3 = np.argsort(proba, axis=1)[:, -3:][:, ::-1]
  ```
- Explicar como las **microparadas** se detectan con Isolation Forest
  comparando el gap entre ciclos contra el patron normal.
- **Imagen / chart**: histograma de gaps con la zona "anomala" marcada
  (generar con matplotlib y guardar en `docs/images/microstop_hist.png`).

### 4.10 Forecast del cierre del turno (chart + impacto)

- **Imagen**: chart de Plotly con OEE real hasta la hora actual + banda de
  prediccion hasta el final del turno (`docs/images/forecast_shift.png`).
- 3 lineas: *"a las 10:00 ya sabes que vas a cerrar en 62%, todavia podes
  recuperar 8 piezas/hora si actuas ahora"*.

### 4.11 Resultados esperados (numeros + cita)

- **Numeros del sector** (citar fuentes en el articulo final):
  - 15-25% mejora promedio de OEE tras conectividad OPC UA bien hecha.
  - 60% reduccion de tiempo de respuesta a paradas con Andon digital.
  - Hasta 89% del downtime concentrado en 2-3 causas (Pareto).
- **Cita destacada** (pull quote de gran tamano):
  *"Lo que no se mide en tiempo real, se justifica al final del turno."*

### 4.12 Como probarlo (comando + link)

- Bloque corto:
  ```bash
  git clone https://github.com/leanmasterpymes/oee-andon-ml
  cd oee-andon-ml
  docker compose up -d
  ```
- Link al repo, link a la demo en Streamlit Cloud, link al post de LinkedIn.

### 4.13 Cierre + CTA (texto corto, ~80 palabras)

- *"Este es el primero de una serie semanal donde voy a mostrar como la
  ciencia de datos se baja del paper a la planta."*
- CTA triple:
  - **Estrella el repo** si te resulto util.
  - **Comentale a tu jefe de planta** que lo pruebe.
  - **Mandame DM** si queres implementarlo en tu empresa.
- Firma con perfil + LinkedIn.

### 4.14 Inventario visual del articulo (resumen)

| #  | Tipo                | Donde se usa                     | Archivo destino                          |
|----|---------------------|----------------------------------|------------------------------------------|
| 1  | Foto banco          | Apertura (planilla manual)       | (link inline, atribuir)                  |
| 2  | Diagrama SVG        | Formula OEE                      | `docs/diagrams/oee_formula.svg`          |
| 3  | Diagrama SVG        | Manual vs automatico             | `docs/diagrams/manual_vs_auto.svg`       |
| 4  | Diagrama SVG/PNG    | Arquitectura general             | `docs/diagrams/architecture.svg`         |
| 5  | Foto / esquematico  | ESP32 + sensor                   | `docs/images/esp32_retrofit.png`         |
| 6  | Bloque codigo       | Funcion `update_oee`             | inline                                   |
| 7  | Screenshot          | Dashboard pantalla planta        | `docs/images/dashboard_planta.png`       |
| 8  | Screenshot          | Andon mobile                     | `docs/images/andon_tablet.png`           |
| 9  | Diagrama flujo SVG  | Andon + ML                       | `docs/diagrams/andon_flow.svg`           |
| 10 | Tabla + bloque cod. | 4 modelos ML                     | inline                                   |
| 11 | Chart matplotlib    | Histograma microparadas          | `docs/images/microstop_hist.png`         |
| 12 | Chart Plotly        | Forecast OEE turno               | `docs/images/forecast_shift.png`         |
| 13 | Pull quote          | Cierre seccion resultados        | inline                                   |
| 14 | Bloque codigo bash  | Quick start                      | inline                                   |

## 5. Backlog priorizado para el MVP

Orden sugerido de implementacion (estado al 2026-04-26):

1. [x] **Simulador** (`simulator/`) — eventos realistas, parametrizable por
   `SIM_SPEED` y `SIM_DURATION_S` para autodetenerse.
2. [x] **Esquema Timescale + procesador** (`broker/init.sql`, `processor/`)
   — eventos crudos, paradas materializadas y snapshots de OEE por minuto.
3. [x] **Dashboard pantalla** (`dashboard/`) — header con formula OEE y
   componentes APQ en espanol, tarjetas D/R/C, Pareto traducido y tendencia.
4. [x] **Andon mobile** (`andon/`) — semaforos clickeables, panel contextual
   por estado, modo demo y lanzador de simulacion integrado.
5. [x] **Convencion de etiquetas en espanol para la UI** (codigos internos
   y MQTT siguen en ingles).
6. [x] **Instalacion nativa documentada** (sin Docker) en `README.md`.
7. [ ] **Modelo de clasificacion de causa** (`ml/notebooks/01_*.ipynb`) y
   carga real en el Andon (hoy usa heuristica fallback).
8. [ ] **Modelo de microparadas** (`ml/notebooks/02_*.ipynb`).
9. [ ] **Modelo de forecast OEE turno** (`ml/notebooks/03_*.ipynb`).
10. [ ] **Guia OPC UA real** (`docs/integration.md`).
11. [ ] **Despliegue demo Streamlit Cloud**.
12. [ ] **Articulo + post LinkedIn + cross-post blog Leanmaster Pymes**.

## 6. Recursos consultados

- HiveMQ — Unified Namespace (UNS) Essentials.
- EMQ — Incorporating Unified Namespace with ISA-95.
- Lean Production / OEE.com — formulas y benchmark world class.
- TEEPTRAK — Six Big Losses.
- MDPI — Cumulative and Rolling Horizon Prediction of OEE with ML.
- Factbird — Micro-stops automatic tracking.
- PyImageSearch — Predictive Maintenance with Isolation Forest.
- ACM — Deep Learning-Powered Intelligent Andon.
- Kai Waehner — OPC UA + MQTT + Kafka trinity.

(Las URLs completas se citan en el articulo publicado, no aca.)
