"""
Gráficos SVG generados en el servidor. Sin librerías de cliente: cada
gráfico es SVG inline, se estiliza con las variables CSS del sitio y se
anima por CSS. Reutilizable por cualquier proyecto.

    from core.charts import bar_chart, sparkline
    svg = bar_chart([{"label": "Ene", "value": 805685, "caption": "6 casos"}, ...])
"""

from __future__ import annotations

from html import escape


def _round(x, n=1):
    return round(float(x), n)


def bar_chart(points, *, value_fmt=None, unit="", height=210):
    """Barras verticales con etiqueta de valor arriba y rótulo abajo.

    points: lista de dicts {label, value, caption?}.
    value_fmt: función valor -> texto para la etiqueta superior.
    """
    if not points:
        return ""
    if value_fmt is None:
        value_fmt = lambda v: f"{v:,.0f}"

    W = 760
    H = height
    pad_l, pad_r, pad_top, pad_bot = 8, 8, 34, 38
    plot_h = H - pad_top - pad_bot
    n = len(points)
    slot = (W - pad_l - pad_r) / n
    bar_w = min(slot * 0.46, 64)

    vals = [max(0.0, float(p["value"])) for p in points]
    vmax = max(vals) or 1.0
    baseline_y = pad_top + plot_h

    parts = [
        f'<svg class="svg-bars" viewBox="0 0 {W} {H}" '
        f'width="100%" preserveAspectRatio="xMidYMid meet" role="img">'
    ]
    # baseline
    parts.append(
        f'<line x1="{pad_l}" y1="{baseline_y:.1f}" x2="{W - pad_r}" '
        f'y2="{baseline_y:.1f}" stroke="var(--line)" stroke-width="1"/>'
    )

    for i, p in enumerate(points):
        v = vals[i]
        bh = (v / vmax) * plot_h
        cx = pad_l + i * slot + slot / 2
        x = cx - bar_w / 2
        y = baseline_y - bh
        delay = f"{i * 0.05:.2f}s"

        parts.append(
            f'<rect class="bar" x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{bh:.1f}" rx="4" fill="var(--ink)" '
            f'style="animation-delay:{delay}">'
            f'<title>{escape(str(p["label"]))}: {escape(value_fmt(v))}</title></rect>'
        )
        # valor arriba
        parts.append(
            f'<text x="{cx:.1f}" y="{y - 9:.1f}" text-anchor="middle" '
            f'class="bar-val">{escape(value_fmt(v))}</text>'
        )
        # rótulo mes
        parts.append(
            f'<text x="{cx:.1f}" y="{H - 20:.1f}" text-anchor="middle" '
            f'class="bar-lab">{escape(str(p["label"]))}</text>'
        )
        # caption opcional
        if p.get("caption"):
            parts.append(
                f'<text x="{cx:.1f}" y="{H - 6:.1f}" text-anchor="middle" '
                f'class="bar-cap">{escape(str(p["caption"]))}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def sparkline(values, *, width=240, height=56):
    """Línea de tendencia compacta con área y punto final."""
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        return ""

    pad = 6
    W, H = width, height
    vmin, vmax = min(vals), max(vals)
    span = (vmax - vmin) or 1.0
    step = (W - 2 * pad) / (len(vals) - 1)

    def xy(i, v):
        x = pad + i * step
        y = pad + (1 - (v - vmin) / span) * (H - 2 * pad)
        return x, y

    pts = [xy(i, v) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = (
        f"{pad:.1f},{H - pad:.1f} "
        + line
        + f" {pts[-1][0]:.1f},{H - pad:.1f}"
    )
    ex, ey = pts[-1]

    return (
        f'<svg class="svg-spark" viewBox="0 0 {W} {H}" width="100%" '
        f'preserveAspectRatio="none" role="img">'
        f'<polygon class="spark-area" points="{area}" fill="var(--ink)" opacity="0.06"/>'
        f'<polyline class="spark-line" points="{line}" fill="none" '
        f'stroke="var(--ink)" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
        f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.2" fill="var(--ink)"/>'
        f"</svg>"
    )
