"""Output of the harness: a Markdown table and a self-contained SVG chart.

The chart plots the false-accusation rate against latency (section 11.4): "same or
better criterion, much faster and more repeatable". Baselines marked unavailable
(B1/B2) appear in the table with their reason and are left out of the chart rather
than drawn with invented points.
"""

from ficha_tecnica.evaluation.metrics import MetricValue
from ficha_tecnica.evaluation.rows import HarnessReport

_TABLE_HEADER = (
    "baseline",
    "falsa acusación",
    "(n)",
    "recall omisiones",
    "en revisar",
    "M4",
    "M5",
    "calibración",
    "estabilidad",
    "p50 ms",
    "p95 ms",
    "casos",
)

#: What each baseline is, for the table footer (copia de la CLI en español).
_SCORER = {
    "B0": "solo reglas y expresiones regulares",
    "B1": "LLM de NaN como juez, sin razonamiento",
    "B2": "LLM de NaN como juez con razonamiento alto",
    "B3": "reglas + Clef, una sola lectura",
    "B4": "reglas + Clef con segunda lectura enfocada",
}


def _percent(metric: MetricValue) -> str:
    return "—" if metric.value is None else f"{metric.value * 100:.2f} %"


def _plain(metric: MetricValue | None) -> str:
    if metric is None or metric.value is None:
        return "—"
    return f"{metric.value:.3f}"


def _number(value: int | None) -> str:
    return "—" if value is None else str(value)


def render_table(report: HarnessReport) -> str:
    """Markdown table of the run, the leak counter and the run's caveats."""
    lines = [
        "| " + " | ".join(_TABLE_HEADER) + " |",
        "|" + "|".join("---" for _ in _TABLE_HEADER) + "|",
    ]
    for row in report.rows:
        if row.unavailable_reason is not None:
            lines.append(
                f"| {row.baseline} | unavailable ({row.unavailable_reason}) | — | — | — "
                f"| — | — | — | — | — | — | 0 |"
            )
            continue
        lines.append(
            f"| {row.baseline} | {_percent(row.false_accusation)} "
            f"| ({row.false_accusation.numerator}/{row.false_accusation.denominator}) "
            f"| {_percent(row.omission_recall)} | {_percent(row.review_fraction)} "
            f"| {_plain(row.m4)} | {_plain(row.m5)} | {_plain(row.ece)} "
            f"| {_plain(row.stability)} | {_number(row.latency_p50_ms)} "
            f"| {_number(row.latency_p95_ms)} | {row.case_count} |"
        )

    lines.append("")
    lines.append(f"Fugas del saneador: **{report.leak_count}** (objetivo: 0).")
    if report.notes:
        lines.append("")
        for note in report.notes:
            lines.append(f"> {note}")
    lines.append("")
    lines.append(
        "Sistemas: "
        + "; ".join(f"{row.baseline}: {_SCORER.get(row.baseline, '?')}" for row in report.rows)
        + "."
    )
    return "\n".join(lines)


def _x(value: float, max_x: float) -> float:
    return 70.0 + value / max_x * 520.0 if max_x else 70.0


def _y(value: float) -> float:
    return 350.0 - min(max(value, 0.0), 1.0) * 280.0


def render_chart_svg(report: HarnessReport) -> str:
    """False-accusation rate (y) against p50 latency (x), one labelled point per baseline.

    Self-contained SVG: no dependency is added, and no baseline without a measurement
    is drawn.
    """
    max_x = float(max((row.latency_p50_ms or 0) for row in report.rows) or 1.0) * 1.15
    parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 640 420">',
        '<rect width="640" height="420" fill="white"/>',
        '<text x="20" y="34" font-size="18" font-family="sans-serif">'
        "Falsa acusación frente a latencia (p50)</text>",
        '<line x1="70" y1="350" x2="590" y2="350" stroke="#333"/>',
        '<line x1="70" y1="350" x2="70" y2="50" stroke="#333"/>',
        '<text x="330" y="380" text-anchor="middle" font-size="13" '
        'font-family="sans-serif">latencia p50 (ms)</text>',
        '<text x="24" y="200" text-anchor="middle" font-size="13" font-family="sans-serif" '
        'transform="rotate(-90 24 200)">falsa acusación (%)</text>',
    ]
    points = [
        row
        for row in report.rows
        if row.unavailable_reason is None
        and row.false_accusation.value is not None
        and row.latency_p50_ms is not None
    ]
    for row in points:
        x = _x(float(row.latency_p50_ms or 0), max_x)
        y = _y(row.false_accusation.value or 0.0)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#1a5276"/>')
        parts.append(
            f'<text x="{x + 8:.1f}" y="{y - 8:.1f}" font-size="13" font-family="sans-serif">'
            f"{row.baseline}</text>"
        )
    if not points:
        parts.append(
            '<text x="200" y="200" font-size="13" font-family="sans-serif">'
            "sin puntos medibles</text>"
        )
    parts.append("</svg>")
    return "\n".join(parts)
