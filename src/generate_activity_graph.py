#!/usr/bin/env python3
"""
generate_activity_graph.py
--------------------------
Genera el gráfico de actividad (SVG estilo Chartist) a partir de los datos
editables en data/activity-data.json.

Reestructuración: antes el repositorio contenía únicamente el SVG final
(artefacto generado); ahora los datos, la lógica de generación y el artefacto
están separados en carpetas claras:

    data/   -> fuente de datos editable (JSON)
    src/    -> código generador (este archivo)
    dist/   -> artefactos intermedios
    raíz    -> activity-graph.svg (salida final, desplegada en GitHub Pages)

Uso:
    python3 src/generate_activity_graph.py
"""

import json
import math
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "activity-data.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "activity-graph.svg")

# ---------------------------------------------------------------------------
# Geometría del lienzo (idéntica a la del SVG original)
# ---------------------------------------------------------------------------
WIDTH = 1200
HEIGHT = 420
PLOT_LEFT = 90
PLOT_RIGHT = 1150
PLOT_TOP = 80
PLOT_BOTTOM = 350


def load_data(path=DATA_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def fmt(value):
    """Formatea números igual que Chartist (decimales largos para divisiones)."""
    if value == int(value) and abs(value) < 1e15:
        # Números 'redondos' se imprimen sin decimales
        return str(int(value))
    return repr(round(value, 14))


def scale_values(values, height_divisions=7):
    max_v = max(values) if values else 0
    high = max(max_v, 1)
    step = high / height_divisions
    scaled = [v / step for v in values]
    return scaled, high, step


def y_for(scaled_value):
    return PLOT_BOTTOM - scaled_value * ((PLOT_BOTTOM - PLOT_TOP) / 7.0)


def x_for(index, count):
    if count <= 1:
        return PLOT_LEFT
    return PLOT_LEFT + index * ((PLOT_RIGHT - PLOT_LEFT) / (count - 1))


def build_line_path(points):
    """Curva suave (Catmull-Rom -> Bézier cúbica), igual que Chartist.

    Chartist usa la tensión 1/6 pero, en los extremos, proyecta el punto
    'espejo' p0/p3 simétrico respecto al primer/último punto real
    (p0 = 2*p1 - p2 y p3 = 2*p2 - p4), en lugar de duplicar el punto final.
    """
    if not points:
        return ""
    d = [f"M{fmt(points[0][0])},{fmt(points[0][1])}"]
    n = len(points)
    for i in range(n - 1):
        p1 = points[i]
        p2 = points[i + 1]
        if i > 0:
            p0 = points[i - 1]
        else:  # proyección espeja del primero
            p0 = (2 * p1[0] - p2[0], 2 * p1[1] - p2[1])
        if i + 2 < n:
            p3 = points[i + 2]
        else:  # proyección espeja del último
            p3 = (2 * p2[0] - p1[0], 2 * p2[1] - p1[1])
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        d.append(
            f"C{fmt(c1x)},{fmt(c1y)},{fmt(c2x)},{fmt(c2y)},{fmt(p2[0])},{fmt(p2[1])}"
        )
    return "".join(d)


def render_svg(data):
    theme = data.get("theme", {})
    chart = data.get("chart", {})
    days = data["period"]["days"]
    values = data["series"]["contributions"]
    axis_x = chart.get("axisTitles", {}).get("x", "Days")
    axis_y = chart.get("axisTitles", {}).get("y", "Contributions")

    bg = theme.get("background", "#0a0e12")
    stroke = theme.get("stroke", "#000000")
    text_color = theme.get("textColor", "#5d417a")

    scaled, high, step = scale_values(values)
    count = len(days)
    points = [(x_for(i, count), y_for(s)) for i, s in enumerate(scaled)]

    # --- rejilla horizontal (líneas verticales de cada día) ---
    grids = []
    for i in range(count):
        x = fmt(x_for(i, count))
        grids.append(
            f'<line x1="{x}" x2="{x}" y1="{PLOT_TOP}" y2="{PLOT_BOTTOM}" '
            f'class="ct-grid ct-horizontal"></line>'
        )
    # --- rejilla vertical (niveles del eje Y) ---
    for div in range(8):
        y = fmt(PLOT_BOTTOM - div * ((PLOT_BOTTOM - PLOT_TOP) / 7.0))
        grids.append(
            f'<line y1="{y}" y2="{y}" x1="{PLOT_LEFT}" x2="{PLOT_RIGHT}" '
            f'class="ct-grid ct-vertical"></line>'
        )

    # --- paths de línea y área (igual que Chartist) ---
    line_d = build_line_path(points)
    # El área duplica la línea pero con los extremos anclados a la base del gráfico.
    if points:
        first_x, last_x = fmt(points[0][0]), fmt(points[-1][0])
        body = line_d[line_d.index("C"):] if "C" in line_d else ""
        area_d = (
            f"M{first_x},{fmt(PLOT_BOTTOM)}L{first_x},{fmt(PLOT_BOTTOM)}"
            + body
            + f"L{last_x},{fmt(PLOT_BOTTOM)}Z"
        )
    else:
        area_d = ""

    # --- puntos ---
    pts = []
    for (x, y), v in zip(points, values):
        pts.append(
            f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(x + 0.01)}" y2="{fmt(y)}" '
            f'class="ct-point" ct:value="{v}"></line>'
        )

    # --- etiquetas eje X ---
    labels = []
    slot = (PLOT_RIGHT - PLOT_LEFT) / max(count - 1, 1)
    for i, day in enumerate(days):
        x = fmt(x_for(i, count) - slot / 2 + 0.166666666666666)
        w = fmt(slot)
        labels.append(
            f'<text x="{x}" y="370" width="{w}" height="40" '
            f'class="ct-label ct-horizontal ct-end">{day}</text>'
        )
    # --- etiquetas eje Y ---
    for div in range(8):
        val = round(step * div)
        y = PLOT_BOTTOM - div * ((PLOT_BOTTOM - PLOT_TOP) / 7.0) - 4.5
        h = (PLOT_BOTTOM - PLOT_TOP) / 7.0
        labels.append(
            f'<text y="{fmt(y)}" x="80" height="{fmt(h)}" width="60" '
            f'class="ct-label ct-vertical ct-start">{val}</text>'
        )

    style = STYLE_TEMPLATE.replace("__TEXT_COLOR__", text_color)

    svg = f'''<svg
        width="{WIDTH}"
        height="{HEIGHT}"
        viewBox="0 0 {WIDTH} {HEIGHT}"
        fill="none"
        xmlns="http://www.w3.org/2000/svg">
            <rect xmlns="http://www.w3.org/2000/svg" data-testid="card_bg" id="cardBg"
            x="0" y="0" rx="9" height="100%" stroke="#E4E2E2" fill-opacity="1"
            width="100%" fill="{bg}" stroke-opacity="1" style="stroke:{stroke}; stroke-width:1;"/>

            <style>
{style}
            </style>

            <foreignObject x="0" y="0" width="{WIDTH}" height="50">
                <h1 xmlns="http://www.w3.org/1999/xhtml" class="header">

                </h1>
            </foreignObject>
            <svg xmlns:ct="http://gionkunz.github.com/chartist-js/ct" width="{WIDTH}" height="{HEIGHT}" class="ct-chart-line"><g class="ct-grids">{"".join(grids)}</g><g><g class="ct-series ct-series-a"><path d="{area_d}" class="ct-area"></path><path d="{line_d}" class="ct-line"></path>{"".join(pts)}</g></g><g class="ct-labels">{"".join(labels)}</g><text class="ct-axis-title ct-label" x="620" y="400" dominant-baseline="text-after-edge" text-anchor="middle">{axis_x}</text><text class="ct-axis-title ct-label" x="20" y="215" transform="rotate(-90, 20, 215)" dominant-baseline="hanging" text-anchor="middle">{axis_y}</text></svg>
    </svg>'''
    return svg


STYLE_TEMPLATE = """                body {
                    font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif;
                }
                .header {
                    font: 600 20px 'Segoe UI', Ubuntu, Sans-Serif;
                    text-align: center;
                    color: __TEXT_COLOR__;
                    margin-top: 20px;
                }
                svg {
                    font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif;
                    user-select: none;
                }

    .ct-label {
      fill: __TEXT_COLOR__;
      color: __TEXT_COLOR__;
      font-size: .75rem;
      line-height: 1;
    }

    .ct-grid-background,
    .ct-line {
      fill: none;
    }

    .ct-chart-bar .ct-label,
    .ct-chart-line .ct-label {
      display: block;
      display: -webkit-box;
      display: -moz-box;
      display: -ms-flexbox;
      display: -webkit-flex;
      display: flex;
    }

    .ct-label.ct-horizontal.ct-start {
      -webkit-box-align: flex-end;
      -webkit-align-items: flex-end;
      -ms-flex-align: flex-end;
      align-items: flex-end;
      -webkit-box-pack: flex-start;
      -webkit-justify-content: flex-start;
      -ms-flex-pack: flex-start;
      justify-content: flex-start;
      text-align: left;
      text-anchor: start;
    }

    .ct-label.ct-horizontal.ct-end {
      -webkit-box-align: flex-start;
      -webkit-align-items: flex-start;
      -ms-flex-align: flex-start;
      align-items: flex-start;
      -webkit-box-pack: flex-end;
      -webkit-justify-content: flex-end;
      -ms-flex-pack: flex-end;
      justify-content: flex-end;
      text-align: right;
      text-anchor: end;
    }

    .ct-vertical {
      -webkit-box-orient: vertical !important;
      -webkit-flex-direction: column !important;
      -ms-flex-direction: column !important;
      flex-direction: column !important;
      -webkit-box-pack: justify;
      -webkit-justify-content: space-between;
      -ms-flex-pack: justify;
      justify-content: space-between;
    }

    .ct-grid {
      stroke: rgba(0, 0, 0, 0.2);
      stroke-width: 1px;
      stroke-dasharray: 2px;
    }
    .ct-point {
      stroke-width: 10px;
      stroke-linecap: round;
      stroke: __TEXT_COLOR__;
    }

    .ct-line {
      stroke-width: 4px;
      stroke: __TEXT_COLOR__;
    }
    .ct-area {
      stroke: none;
      fill-width: 0;
      fill-opacity: 0.1;
      fill: __TEXT_COLOR__;
    }

        @keyframes dash {
            to {
                stroke-dashoffset: 0;
            }
        }

"""


def main():
    data = load_data()
    svg = render_svg(data)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"✔ Generado {os.path.relpath(OUTPUT_PATH, BASE_DIR)} "
          f"({len(svg)} bytes) desde data/activity-data.json")


if __name__ == "__main__":
    main()
