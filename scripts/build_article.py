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
<title>De la planilla al tiempo real: medi el OEE de tu planta con MQTT, Andon digital y Machine Learning</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Como construir un sistema abierto y de bajo costo para medir el OEE en tiempo real, con captura automatica via MQTT/OPC UA, un Andon digital y modelos de Machine Learning.">
<meta name="author" content="Marlon Polanco — Leanmaster Pymes">
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
  <div class="kicker">Industria 4.0 · Lean · Ciencia de datos</div>
  <h1>De la planilla al tiempo real: medi el OEE de tu planta con MQTT, un Andon digital y Machine Learning</h1>
  <p class="lede">Como pase de un Excel mensual a un dashboard hora-por-hora con IA que avisa antes de cerrar el turno. Open source, en Python, listo para copiar.</p>
  <p class="meta">Lectura: 8–10 min · <span class="badge b-blue">Python</span> <span class="badge b-green">Open source</span> <span class="badge b-amber">PYME-friendly</span></p>
</header>

<h2>1 · El problema que veo en casi toda planta</h2>
<p>En la mayoria de las plantas que visito, el OEE se calcula <strong>los lunes a la mañana</strong> sobre lo que paso la semana pasada. Para entonces el problema ya costo plata, el operario olvido la mitad de las paradas y nadie puede hacer nada con el numero.</p>
<p>El patron se repite:</p>
<ul class="clean">
  <li>El operario digita lo que <em>recuerda</em>.</li>
  <li>Las microparadas — la mayor perdida oculta — <strong>nunca aparecen</strong>.</li>
  <li>Cuando llega el reporte, ya nadie puede actuar sobre el.</li>
</ul>
<p>Construi y abri en GitHub un sistema que ataca exactamente este problema. Te lo cuento abajo paso a paso.</p>

<h2>2 · Que es OEE y por que importa</h2>
<p>OEE (Overall Equipment Effectiveness) es el KPI estandar de manufactura para responder una pregunta simple: <em>"de todo el tiempo que mi linea podria producir, ¿que porcentaje aproveche realmente, bien y a la velocidad correcta?"</em>.</p>

<figure>{svg_oee_formula}<figcaption>OEE world-class segun Nakajima: 85.4% (0.90 × 0.95 × 0.999). Promedio en manufactura discreta: 55–60%.</figcaption></figure>

<table>
  <thead><tr><th>Nivel</th><th>OEE</th><th>Lectura</th></tr></thead>
  <tbody>
    <tr><td>World class</td><td>≥ 85%</td><td>Top 10% global</td></tr>
    <tr><td>Aceptable</td><td>60–85%</td><td>Mayoria de PYMES</td></tr>
    <tr><td>Bajo</td><td>&lt; 60%</td><td>Hay oportunidad enorme</td></tr>
  </tbody>
</table>

<h2>3 · El verdadero problema: los datos no llegan solos</h2>
<p>Calcular OEE es trivial. <strong>Conseguir datos limpios en tiempo real es el problema</strong>. Mientras dependamos del operario y de una planilla, el OEE va a llegar tarde, sesgado y sin las paradas chicas (que en muchas plantas representan hasta el 89% del downtime).</p>

<figure>{svg_manual_vs_auto}<figcaption>El salto no es en la formula, es en la captura.</figcaption></figure>

<h2>4 · La arquitectura propuesta</h2>
<p>Tres capas, todas open source y Dockerizadas:</p>

<figure>{svg_architecture}<figcaption>De PLC/sensor al dashboard. Mosquitto como Unified Namespace (UNS), TimescaleDB como historian, Streamlit como cara visible.</figcaption></figure>

<p><strong>Unified Namespace (UNS)</strong> en una frase: un broker MQTT donde toda la planta publica datos con tópicos jerarquicos alineados a <strong>ISA-95</strong>:</p>

<div class="formula">lmp/planta1/empaque/linea1/maquina01/cycle</div>

<p>Cualquier app (dashboard, Andon, modelo ML, Power BI, ERP) se conecta y lee. No hay integraciones punto a punto, no hay archivos planos, no hay corte por ruta. Y si despues queres ir a una planta multi-sitio con miles de puntos, simplemente sumas <strong>Sparkplug B</strong> arriba de MQTT.</p>

<h2>5 · Como conectar maquinas reales (incluso las viejas)</h2>

<table>
  <thead><tr><th>Tipo de equipo</th><th>Camino recomendado</th></tr></thead>
  <tbody>
    <tr><td>PLC moderno (S7-1500, CompactLogix)</td><td>Cliente OPC UA → bridge a MQTT Sparkplug B</td></tr>
    <tr><td>PLC viejo (S7-300, sin Ethernet)</td><td>Modbus TCP via gateway (Moxa / Ewon) → MQTT</td></tr>
    <tr><td>Maquina sin PLC</td><td>ESP32 + sensor inductivo en la salida (~USD 50)</td></tr>
    <tr><td>Banda con piezas no detectables</td><td>Camara + YOLO ligero → conteo a MQTT</td></tr>
  </tbody>
</table>

<figure>{svg_esp32}<figcaption>Retrofit IIoT de bajo costo: sensor + ESP32 + MQTT. Sin tocar el PLC original.</figcaption></figure>

<div class="callout"><strong>Tip:</strong> con menos de USD 50 retrofiteamos una maquina vieja y empezamos a leer ciclos automaticamente. Sin licencia, sin contrato anual, sin esperar al integrador.</div>

<h2>6 · El calculo en streaming</h2>
<p>El procesador escucha el broker, mantiene una <strong>ventana movil de 60 minutos</strong> por maquina y recalcula A · P · Q en cada evento. Asi se ve el corazon del motor:</p>

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

<p>Cada minuto se persiste un snapshot en TimescaleDB (hypertable de PostgreSQL). Eso permite consultas SQL estandar, integracion directa con Power BI y la posibilidad de montar dashboards o reportes a futuro sin reinventar la rueda.</p>

<h2>7 · La pantalla de planta</h2>
<p>El TV de planta esta diseñado bajo la <strong>regla de los 5 segundos</strong>: cualquiera que pase frente a la pantalla debe entender el estado de la planta en menos de 5 segundos.</p>

<figure>{svg_dashboard}<figcaption>Vista TV: tarjetas con semaforo + OEE + meta + delta · tendencia 8h · Pareto de causas en vivo.</figcaption></figure>

<h2>8 · El Andon digital en la tablet</h2>
<p>Cuando una maquina queda detenida mas de 2 minutos, una tablet en la zona de trabajo vibra. El operario ve <strong>las 3 causas mas probables</strong> sugeridas por un modelo de ML, ordenadas por probabilidad. Confirma con un toque y listo.</p>

<div class="grid-2">
  <figure>{svg_andon}<figcaption>App Andon mobile (Streamlit). El operario nunca escribe.</figcaption></figure>
  <figure>{svg_andon_flow}<figcaption>Flujo: detectar → alertar → sugerir → confirmar → reentrenar.</figcaption></figure>
</div>

<blockquote class="pull">Lo que no se mide en tiempo real, se justifica al final del turno.</blockquote>

<h2>9 · Donde entra el Machine Learning</h2>
<p>El ML no esta ahi para vender humo. Cumple <strong>4 funciones concretas</strong>, cada una resuelve un dolor real:</p>

<table>
  <thead><tr><th>Modelo</th><th>Algoritmo</th><th>Que aporta</th></tr></thead>
  <tbody>
    <tr><td>Microparadas</td><td>Isolation Forest</td><td>Detecta paradas que el operario no reporta</td></tr>
    <tr><td>Causa de parada</td><td>LightGBM</td><td>Sugiere top-3 causas → 1 toque para confirmar</td></tr>
    <tr><td>Forecast OEE turno</td><td>Regresion + bootstrap</td><td>Avisa a media mañana como va a cerrar el turno</td></tr>
    <tr><td>Mantenimiento predictivo</td><td>XGBoost / regresion</td><td>Anticipa fallas a partir de vibracion / corriente</td></tr>
  </tbody>
</table>

<p>Asi se ve el clasificador de causas que alimenta el Andon (extracto):</p>

<pre><code>features = ["machine_id", "hour", "shift", "alarm_code", "stop_duration_s"]
model = LGBMClassifier(n_estimators=300, learning_rate=0.05, class_weight="balanced")
model.fit(X_train, y_train)

# Top-3 causas que iran a la tablet del operario
proba = model.predict_proba(X_new)
top3  = sorted(zip(model.classes_, proba[0]), key=lambda p: -p[1])[:3]
</code></pre>

<p>El modelo entrenado sobre datos sinteticos realistas alcanza <strong>83% de accuracy</strong> con 100% en BREAKDOWN y &gt;90% en MICROSTOP. En produccion mejora aun mas porque cada confirmacion del operario lo reentrena.</p>

<h3>Microparadas: el OEE que nadie te muestra</h3>
<p>Las microparadas — esos 30/60/90 segundos sin pieza que nadie reporta — son la mayor perdida oculta de OEE en planta. Un Isolation Forest sobre la serie de gaps entre ciclos las marca solo:</p>

<figure><img alt="Histograma de gaps entre ciclos con la zona anomala marcada en rojo" src="data:image/png;base64,{png_microstop}"><figcaption>Cualquier gap fuera del patron normal se marca como microparada y se incluye en el OEE real, sin requerir intervencion del operario.</figcaption></figure>

<h3>Forecast del cierre del turno</h3>
<p>A media mañana, el modelo proyecta como va a terminar el turno con una banda de incertidumbre del 95%. Eso convierte un KPI <em>post-mortem</em> en una alerta accionable:</p>

<figure><img alt="OEE observado y forecast hasta el final del turno con banda de incertidumbre" src="data:image/png;base64,{png_forecast}"><figcaption>"Si nada cambia, vas a cerrar en 78%. Para llegar a la meta necesitas recuperar 8 piezas/hora a partir de ahora."</figcaption></figure>

<h2>10 · Resultados esperados</h2>
<p>Numeros tipicos del sector cuando esta arquitectura entra bien implementada (citados por HiveMQ, EMQ, TEEPTRAK y casos publicados):</p>
<ul class="clean">
  <li><strong>15–25% de mejora promedio de OEE</strong> tras conectividad OPC UA / MQTT bien hecha.</li>
  <li><strong>60% de reduccion del tiempo de respuesta</strong> a paradas con Andon digital.</li>
  <li><strong>2–3 causas concentran el 70–89%</strong> del downtime (Pareto), por lo que enfocar mejora ahi rinde mucho mas.</li>
  <li>Las microparadas suelen representar <strong>el mayor componente perdido</strong> de Performance, y solo se ven con captura automatica.</li>
</ul>

<h2>11 · Como probarlo (5 minutos)</h2>
<p>Todo el codigo esta abierto en GitHub bajo licencia MIT. Solo necesitas Docker:</p>
<pre><code>git clone https://github.com/leanmasterpymes/oee-andon-ml
cd oee-andon-ml
docker compose up -d
</code></pre>
<p>Despues abris:</p>
<ul class="clean">
  <li><strong>Pantalla de planta:</strong> <code>http://localhost:8501</code></li>
  <li><strong>Andon mobile:</strong> <code>http://localhost:8502</code></li>
  <li><strong>Broker MQTT:</strong> <code>localhost:1883</code></li>
</ul>
<p>El simulador empieza a publicar datos de 3 maquinas inmediatamente. En menos de 2 minutos ya tenes OEE en pantalla.</p>

<div class="cta">
  <h2>Si te resulto util</h2>
  <p>⭐ Estrellame el repo en GitHub. Le hace mas visible al resto.<br>
  💬 Compartilo con tu jefe de produccion o de mantenimiento — esto se prueba en una tarde.<br>
  📩 Si queres llevarlo a tu planta y necesitas ayuda para integrarlo a tus PLC, mandame DM.</p>
</div>

<footer class="byline">
  <div>
    <strong>Marlon Polanco</strong> — Ingeniero industrial, MSc Gestion Estrategica de Software · Profesor de Investigacion de Operaciones · Especialista en procesos · Power BI certified.
  </div>
  <div>Leanmaster Pymes · Articulo de la serie semanal de ciencia de datos para productividad empresarial.</div>
</footer>

</div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
