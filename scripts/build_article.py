"""Genera articulo HTML standalone (todos los recursos embebidos).

Toma SVGs de docs/diagrams y PNGs de docs/images, los inyecta inline /
base64 y escribe docs/articulo.html — autocontenido y sin huellas externas.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGRAMS = ROOT / "docs" / "diagrams"
IMAGES = ROOT / "docs" / "images"
OUT = ROOT / "docs" / "articulo.html"


def load_svg_inner(path: Path) -> str:
    txt = path.read_text(encoding="utf-8")
    # Quita la declaracion XML si la tuviera y devuelve el <svg>...</svg>.
    txt = re.sub(r"<\?xml[^?]*\?>", "", txt).strip()
    return txt


def png_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    svg = {p.stem: load_svg_inner(p) for p in DIAGRAMS.glob("*.svg")}
    img = {p.stem: png_b64(p) for p in IMAGES.glob("*.png")}

    html = ARTICLE_TEMPLATE.format(
        svg_oee_formula=svg["oee_formula"],
        svg_manual_vs_auto=svg["manual_vs_auto"],
        svg_architecture=svg["architecture"],
        svg_esp32=svg["esp32_retrofit"],
        svg_dashboard=svg["dashboard_mockup"],
        svg_andon=svg["andon_mockup"],
        svg_andon_flow=svg["andon_flow"],
        png_microstop=img["microstop_hist"],
        png_forecast=img["forecast_shift"],
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"Articulo escrito en {OUT}  ({len(html):,} bytes)")


ARTICLE_TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Del Excel al tiempo real: medición automatizada del OEE con MQTT, Andon digital y Machine Learning</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Arquitectura abierta y de bajo costo para medir el OEE en tiempo real mediante captura automatizada con MQTT/OPC UA, un sistema Andon digital y modelos de Machine Learning aplicados a la mejora operativa.">
<meta name="author" content="Manuel Antonio Pérez Ogando — Leanmaster Pymes">
<style>
  :root {{
    --ink:#0f172a; --soft:#475569; --bg:#ffffff; --surface:#f8fafc;
    --accent:#0ea5e9; --green:#16a34a; --amber:#eab308; --red:#dc2626;
    --purple:#7c3aed; --border:#e2e8f0;
    --radius:12px; --maxw:880px;
    --mono: ui-monospace, SFMono-Regular, "JetBrains Mono", Consolas, monospace;
  }}
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; padding:0; background:var(--bg); color:var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
    line-height:1.65; font-size:17px; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:var(--maxw); margin:0 auto; padding:48px 22px 96px; }}
  header.hero {{ padding:32px 0 28px; border-bottom:1px solid var(--border); margin-bottom:32px; }}
  .kicker {{ color:var(--accent); text-transform:uppercase; letter-spacing:1.5px; font-weight:700; font-size:13px; }}
  h1 {{ font-size:38px; line-height:1.15; margin:8px 0 16px; letter-spacing:-0.02em; }}
  h2 {{ font-size:26px; margin-top:48px; margin-bottom:14px; letter-spacing:-0.01em; }}
  h3 {{ font-size:19px; margin-top:30px; margin-bottom:8px; }}
  p {{ margin: 0 0 16px; }}
  .lede {{ font-size:19px; color:var(--soft); margin: 8px 0 20px; }}
  .meta {{ color:var(--soft); font-size:14px; }}
  a {{ color: var(--accent); text-decoration: none; border-bottom:1px solid transparent; }}
  a:hover {{ border-bottom-color: var(--accent); }}
  figure {{ margin:24px 0; }}
  figure svg, figure img {{ width:100%; height:auto; display:block; border:1px solid var(--border); border-radius:var(--radius); background:#fff; }}
  figcaption {{ color:var(--soft); font-size:14px; text-align:center; margin-top:8px; }}
  .grid-2 {{ display:grid; grid-template-columns: 1fr 1fr; gap:18px; }}
  @media (max-width:720px) {{ .grid-2 {{ grid-template-columns:1fr; }} h1{{font-size:30px;}} }}
  .callout {{ background:#fef9c3; border-left:5px solid var(--amber); padding:14px 18px; border-radius:8px; margin:24px 0; }}
  .callout strong {{ color:#854d0e; }}
  blockquote.pull {{ font-size:24px; line-height:1.4; color:var(--ink); border-left:4px solid var(--accent);
    padding:14px 22px; margin:32px 0; background:var(--surface); border-radius:8px; font-style:italic; }}
  table {{ width:100%; border-collapse:collapse; margin:18px 0; font-size:15px; }}
  th, td {{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); vertical-align:top; }}
  th {{ background:var(--surface); font-weight:700; }}
  pre {{ background:#0f172a; color:#e2e8f0; padding:18px 20px; border-radius:var(--radius); overflow-x:auto;
    font-family: var(--mono); font-size:14px; line-height:1.55; }}
  code {{ font-family: var(--mono); font-size:0.92em; background:var(--surface); padding:1px 6px; border-radius:4px; }}
  pre code {{ background:transparent; padding:0; }}
  .formula {{ font-family: var(--mono); background: var(--surface); padding:14px 18px;
    border-radius:8px; border:1px dashed var(--border); }}
  ul.clean {{ padding-left:20px; }}
  ul.clean li {{ margin-bottom:6px; }}
  .cta {{ background: linear-gradient(135deg, #0ea5e9 0%, #7c3aed 100%); color:#fff;
    padding:28px 28px; border-radius:var(--radius); margin-top:48px; }}
  .cta h2 {{ color:#fff; margin-top:0; }}
  .cta a {{ color:#fff; border-bottom:1px solid rgba(255,255,255,0.5); }}
  footer.byline {{ margin-top:64px; padding-top:24px; border-top:1px solid var(--border);
    color:var(--soft); font-size:14px; display:flex; justify-content:space-between; flex-wrap:wrap; gap:12px; }}
  .badge {{ display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600; }}
  .b-green {{ background:#dcfce7; color:#166534; }}
  .b-blue  {{ background:#dbeafe; color:#1e3a8a; }}
  .b-amber {{ background:#fef3c7; color:#854d0e; }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <div class="kicker">Industria 4.0 · Lean Manufacturing · Ciencia de datos</div>
  <h1>Del Excel al tiempo real: medición automatizada del OEE con MQTT, Andon digital y Machine Learning</h1>
  <p class="lede">Una arquitectura abierta, replicable y de bajo costo para que cualquier planta industrial deje de calcular su OEE en planillas mensuales y empiece a operarlo hora por hora, con apoyo de modelos predictivos.</p>
  <p class="meta">Lectura estimada: 8–10 minutos · <span class="badge b-blue">Python</span> <span class="badge b-green">Open source</span> <span class="badge b-amber">Orientado a PYMES</span></p>
</header>

<h2>1 · El problema operativo que se repite en la mayoría de las plantas</h2>
<p>En la mayoría de las plantas industriales que he visitado, el OEE se calcula <strong>los lunes por la mañana</strong> a partir de los datos de la semana anterior. Para ese momento el problema ya generó un costo, el operario ha olvidado el detalle de la mitad de las paradas y la información ya no permite tomar decisiones correctivas oportunas.</p>
<p>El patrón suele ser el mismo:</p>
<ul class="clean">
  <li>El operario registra únicamente lo que <em>recuerda</em> al cierre del turno.</li>
  <li>Las microparadas, que constituyen la mayor pérdida oculta, <strong>no quedan documentadas</strong>.</li>
  <li>El reporte llega cuando la oportunidad de mejora ya se perdió.</li>
</ul>
<p>Para responder a esta situación desarrollé un sistema de código abierto, disponible en GitHub, que aborda el problema desde la captura del dato hasta la decisión en planta. A continuación presento la propuesta y su arquitectura.</p>

<h2>2 · Qué es el OEE y por qué es relevante</h2>
<p>El OEE (<em>Overall Equipment Effectiveness</em>) es el indicador estándar de manufactura para responder una pregunta concreta: <em>del tiempo total que una línea podría producir, ¿qué porcentaje se aprovecha efectivamente, con la calidad esperada y a la velocidad nominal?</em></p>

<figure>{svg_oee_formula}<figcaption>OEE de clase mundial según Nakajima: 85.4% (0.90 × 0.95 × 0.999). Promedio observado en manufactura discreta: 55–60%.</figcaption></figure>

<table>
  <thead><tr><th>Nivel</th><th>OEE</th><th>Interpretación</th></tr></thead>
  <tbody>
    <tr><td>Clase mundial</td><td>≥ 85%</td><td>Top 10% de la industria a nivel global</td></tr>
    <tr><td>Aceptable</td><td>60–85%</td><td>Rango habitual en la mayoría de las PYMES</td></tr>
    <tr><td>Bajo</td><td>&lt; 60%</td><td>Margen significativo de mejora operativa</td></tr>
  </tbody>
</table>

<h2>3 · El problema de fondo: los datos no se generan solos</h2>
<p>Calcular el OEE es matemáticamente trivial. <strong>El verdadero desafío es disponer de datos confiables en tiempo real.</strong> Mientras la captura dependa del operario y de una planilla manual, el indicador llegará tarde, sesgado y sin las paradas menores, las cuales en muchas plantas pueden representar hasta el 89% del tiempo total de inactividad.</p>

<figure>{svg_manual_vs_auto}<figcaption>El salto cualitativo no está en la fórmula, sino en el modo de captura.</figcaption></figure>

<h2>4 · Arquitectura propuesta</h2>
<p>La solución se compone de tres capas, todas basadas en software libre y desplegables mediante Docker:</p>

<figure>{svg_architecture}<figcaption>Del PLC o sensor hasta el tablero ejecutivo. Mosquitto opera como Unified Namespace (UNS), TimescaleDB como <em>historian</em> y Streamlit como capa de visualización.</figcaption></figure>

<p>El concepto de <strong>Unified Namespace (UNS)</strong> puede resumirse así: un broker MQTT central en el que toda la planta publica datos mediante tópicos jerárquicos alineados al estándar <strong>ISA-95</strong>:</p>

<div class="formula">lmp/planta1/empaque/linea1/maquina01/cycle</div>

<p>Cualquier aplicación, ya sea el tablero de planta, el Andon, los modelos de Machine Learning, Power BI o el ERP, se conecta al broker y consume la información. Esto elimina las integraciones punto a punto, los archivos planos y los procesos por lotes. Si en el futuro la solución escala a un entorno multisitio con miles de puntos, basta con incorporar <strong>Sparkplug B</strong> sobre la misma capa MQTT.</p>

<h2>5 · Cómo conectar máquinas reales, incluso las de generaciones anteriores</h2>

<table>
  <thead><tr><th>Tipo de equipo</th><th>Camino recomendado</th></tr></thead>
  <tbody>
    <tr><td>PLC moderno (S7-1500, CompactLogix)</td><td>Cliente OPC UA con puente hacia MQTT Sparkplug B</td></tr>
    <tr><td>PLC anterior (S7-300, sin Ethernet)</td><td>Modbus TCP a través de un gateway (Moxa, Ewon) hacia MQTT</td></tr>
    <tr><td>Máquina sin PLC</td><td>ESP32 con sensor inductivo en la salida (aprox. USD 50)</td></tr>
    <tr><td>Banda con piezas difíciles de detectar</td><td>Cámara con modelo YOLO ligero para conteo, publicado a MQTT</td></tr>
  </tbody>
</table>

<figure>{svg_esp32}<figcaption>Retrofit IIoT de bajo costo: sensor, microcontrolador ESP32 y MQTT, sin necesidad de modificar el PLC original.</figcaption></figure>

<div class="callout"><strong>Recomendación práctica:</strong> con una inversión menor a USD 50 es posible adaptar una máquina antigua y comenzar a leer ciclos de manera automática, sin licenciamiento, sin contratos anuales y sin depender de un integrador externo.</div>

<h2>6 · Cálculo del OEE en <em>streaming</em></h2>
<p>El procesador se suscribe al broker, mantiene una <strong>ventana móvil de 60 minutos</strong> por máquina y recalcula los tres componentes (A · P · Q) ante cada evento recibido. El núcleo del motor luce de la siguiente manera:</p>

<pre><code>def metrics(self, now):
    self.trim(now)

    planned_s        = self.minutes * 60
    unplanned_down_s = sum(s.duration_s for s in self.stops if s.cause != "STARTUP")
    operating_s      = max(planned_s - unplanned_down_s, 0)

    pieces_total = len(self.cycles)
    pieces_good  = sum(1 for q in self.quality if q.good)

    availability = operating_s / planned_s
    performance  = (pieces_total * self.ideal_cycle_s) / operating_s
    quality      = pieces_good / pieces_total if pieces_total else 1.0

    return availability * performance * quality
</code></pre>

<p>Cada minuto se persiste una instantánea en TimescaleDB (<em>hypertable</em> sobre PostgreSQL). Esto habilita consultas SQL estándar, integración directa con Power BI y la construcción de tableros o reportes posteriores sin necesidad de duplicar la capa de datos.</p>

<h2>7 · La pantalla de planta</h2>
<p>La pantalla principal de planta se diseña bajo la <strong>regla de los cinco segundos</strong>: cualquier persona que pase frente al televisor debe poder identificar el estado operativo de la planta en menos de cinco segundos.</p>

<figure>{svg_dashboard}<figcaption>Vista para televisor de planta: tarjetas con semáforo, OEE actual, meta y delta, tendencia de las últimas ocho horas y diagrama de Pareto de causas en vivo.</figcaption></figure>

<h2>8 · El Andon digital sobre <em>tablet</em></h2>
<p>Cuando una máquina permanece detenida más de dos minutos, una <em>tablet</em> ubicada en la zona de trabajo emite una alerta. El operario visualiza <strong>las tres causas más probables</strong>, sugeridas por un modelo de Machine Learning y ordenadas por probabilidad. La confirmación se realiza con un solo toque.</p>

<div class="grid-2">
  <figure>{svg_andon}<figcaption>Aplicación Andon móvil desarrollada en Streamlit. El operario no requiere escribir texto.</figcaption></figure>
  <figure>{svg_andon_flow}<figcaption>Flujo operativo: detectar, alertar, sugerir, confirmar y retroalimentar el modelo.</figcaption></figure>
</div>

<blockquote class="pull">Lo que no se mide en tiempo real, se termina justificando al final del turno.</blockquote>

<h2>9 · El rol del Machine Learning en la solución</h2>
<p>Los modelos de ML cumplen <strong>cuatro funciones concretas</strong> dentro del sistema; cada una responde a un problema operativo claramente identificado:</p>

<table>
  <thead><tr><th>Modelo</th><th>Algoritmo</th><th>Aporte operativo</th></tr></thead>
  <tbody>
    <tr><td>Detección de microparadas</td><td>Isolation Forest</td><td>Identifica paradas no reportadas por el operario</td></tr>
    <tr><td>Clasificación de causas</td><td>LightGBM</td><td>Sugiere las tres causas más probables para confirmación en un toque</td></tr>
    <tr><td>Pronóstico de OEE de turno</td><td>Regresión con <em>bootstrap</em> de residuos</td><td>Anticipa el cierre del turno a media jornada</td></tr>
    <tr><td>Mantenimiento predictivo</td><td>XGBoost o regresión</td><td>Anticipa fallas a partir de vibración y consumo eléctrico</td></tr>
  </tbody>
</table>

<p>El siguiente extracto corresponde al clasificador de causas que alimenta al Andon:</p>

<pre><code>features = ["machine_id", "hour", "shift", "alarm_code", "stop_duration_s"]
model = LGBMClassifier(n_estimators=300, learning_rate=0.05, class_weight="balanced")
model.fit(X_train, y_train)

# Las 3 causas mas probables que iran a la tablet del operario
proba = model.predict_proba(X_new)
top3  = sorted(zip(model.classes_, proba[0]), key=lambda p: -p[1])[:3]
</code></pre>

<p>Entrenado sobre un conjunto sintético realista, el modelo alcanza un <strong>83% de exactitud (<em>accuracy</em>)</strong>, con un 100% en la categoría BREAKDOWN y por encima del 90% en MICROSTOP. En producción el desempeño mejora de manera incremental, ya que cada confirmación del operario funciona como nuevo dato de entrenamiento.</p>

<h3>Microparadas: la pérdida que rara vez aparece en los reportes</h3>
<p>Las microparadas, esos intervalos de 30 a 90 segundos sin producción que el operario no suele documentar, constituyen la mayor pérdida oculta de OEE en planta. Un modelo de Isolation Forest aplicado sobre la serie de tiempos entre ciclos las identifica de manera automática:</p>

<figure><img alt="Histograma de tiempos entre ciclos con la zona anómala marcada en rojo" src="data:image/png;base64,{png_microstop}"><figcaption>Todo intervalo que se aleje del patrón normal se clasifica como microparada y se incorpora al OEE real, sin requerir intervención humana.</figcaption></figure>

<h3>Pronóstico del cierre del turno</h3>
<p>A mitad de jornada, el modelo proyecta el cierre del turno con una banda de incertidumbre del 95%. De este modo, un KPI tradicionalmente <em>post-mortem</em> se transforma en una alerta accionable:</p>

<figure><img alt="OEE observado y pronóstico hasta el final del turno con banda de incertidumbre" src="data:image/png;base64,{png_forecast}"><figcaption>"De mantenerse las condiciones actuales, el turno cerrará en 78%. Para alcanzar la meta es necesario recuperar 8 piezas adicionales por hora."</figcaption></figure>

<h2>10 · Resultados esperables</h2>
<p>Las cifras siguientes corresponden a referencias públicas del sector (HiveMQ, EMQ, TEEPTRAK y casos documentados) cuando la arquitectura se implementa con disciplina:</p>
<ul class="clean">
  <li><strong>Mejora promedio de OEE entre 15% y 25%</strong> luego de implementar conectividad OPC UA / MQTT correctamente.</li>
  <li><strong>Reducción del tiempo de respuesta a paradas cercana al 60%</strong> con la incorporación del Andon digital.</li>
  <li><strong>Dos o tres causas concentran entre el 70% y el 89%</strong> del tiempo de inactividad (Pareto), por lo que focalizar allí las acciones de mejora ofrece el mayor retorno.</li>
  <li>Las microparadas suelen ser <strong>el mayor componente de pérdida en el factor Rendimiento</strong>, y solo se hacen visibles con captura automatizada.</li>
</ul>

<h2>11 · Cómo probar el sistema (cinco minutos)</h2>
<p>El código completo está publicado en GitHub bajo licencia MIT. El único requisito es disponer de Docker:</p>
<pre><code>git clone https://github.com/leanmasterpymes/oee-andon-ml
cd oee-andon-ml
docker compose up -d
</code></pre>
<p>Una vez levantado el <em>stack</em>, los puntos de acceso son:</p>
<ul class="clean">
  <li><strong>Pantalla de planta:</strong> <code>http://localhost:8501</code></li>
  <li><strong>Andon móvil:</strong> <code>http://localhost:8502</code></li>
  <li><strong>Broker MQTT:</strong> <code>localhost:1883</code></li>
</ul>
<p>El simulador comienza a publicar datos de tres máquinas de manera inmediata; en menos de dos minutos el OEE ya se visualiza en pantalla.</p>

<div class="cta">
  <h2>Si este contenido le resultó útil</h2>
  <p>⭐ Marque el repositorio en GitHub para darle visibilidad.<br>
  💬 Comparta el artículo con su responsable de producción o de mantenimiento; el sistema puede evaluarse en una sola jornada.<br>
  📩 Si desea adaptar la solución a su planta o integrarla a sus PLC, está abierto el canal de mensajes directos.</p>
</div>

<footer class="byline">
  <div>
    <strong>Manuel Antonio Pérez Ogando</strong> — Ingeniero industrial, MSc en Gestión Estratégica para el Desarrollo de Software · Profesor de Investigación de Operaciones · Especialista en mapeo, análisis y mejora de procesos · Certificado en Power BI.
  </div>
  <div>Leanmaster Pymes · Entrega de la serie semanal sobre ciencia de datos aplicada a la productividad empresarial.</div>
</footer>

</div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
