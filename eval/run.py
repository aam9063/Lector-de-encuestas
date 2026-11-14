"""Punto de entrada del harness de evaluación (ENC-17).

CLI fina: delega todo en ``ficha_tecnica.evaluation``. El número de casos está acotado
por ``--limit``, pequeño por defecto porque cada caso de B3/B4 puede lanzar varias
llamadas a la API. B0 no necesita proveedor; B3/B4 usan el proveedor configurado, y si
no hay clave de NaN corre con el mock y lo dice en el informe en lugar de fingir
resultados reales.

Uso::

    py eval/run.py --limit 6 --baseline B4
    py eval/run.py --limit 3 --baseline B0

Salida: tabla Markdown en stdout y gráfica SVG autónoma escrita en ``--chart``.
"""

import argparse
import asyncio
from pathlib import Path

DEFAULT_LIMIT = 6
DEFAULT_CHART = Path(__file__).resolve().parent / "chart.svg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Harness de evaluación de la ficha técnica (baselines B0-B4)",
    )
    parser.add_argument(
        "--baseline",
        default="B4",
        choices=["B0", "B1", "B2", "B3", "B4"],
        help="baseline a medir (por defecto B4, el sistema completo)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="número máximo de casos (pequeño por defecto: cada caso cuesta llamadas)",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["dev", "test"],
        help="partición del corpus a medir (test por defecto)",
    )
    parser.add_argument(
        "--chart",
        default=str(DEFAULT_CHART),
        help="ruta del SVG de falsa acusación frente a latencia",
    )
    return parser


async def run(args: argparse.Namespace) -> str:
    """Run one baseline and return the printed report. Never touches the network
    unless a NaN key is configured."""
    from ficha_tecnica.evaluation import run_harness

    notes: list[str] = []
    provider = None
    provider_name = "mock"

    if args.baseline in ("B3", "B4"):
        from ficha_tecnica.api.app import build_provider

        provider, client, provider_name = build_provider()
        if provider_name == "mock":
            notes.append(
                "provider: mock (sin clave de NaN configurada; la medición no es "
                "representativa del sistema real)"
            )
        try:
            report = await run_harness(
                (args.baseline,),
                split=args.split,
                limit=args.limit,
                provider=provider,
                provider_name=provider_name,
                notes=tuple(notes),
            )
        finally:
            if client is not None:
                await client.aclose()
    else:
        report = await run_harness(
            (args.baseline,),
            split=args.split,
            limit=args.limit,
            notes=tuple(notes),
        )

    chart_path = Path(args.chart)
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_text(report.chart, encoding="utf-8")
    return f"{report.table}\n\n[grafica] escrita en {chart_path}\n"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = asyncio.run(run(args))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
