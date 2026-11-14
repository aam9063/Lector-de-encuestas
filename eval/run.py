"""Evaluation harness entry point (ENC-17).

Will run a dataset of mutated synthetic articles through baselines B0-B4 and emit
metrics (false-accusation rate, recall, latency) as a table and a chart. Not
implemented yet: this placeholder only validates the CLI surface.
"""

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ficha Técnica evaluation harness")
    parser.add_argument("--dataset", default="eval", help="dataset directory")
    parser.add_argument("--baseline", default="B4", choices=["B0", "B1", "B2", "B3", "B4"])
    parser.add_argument("--split", default="test", choices=["dev", "test"])
    parser.parse_args(argv)
    print("eval: not implemented yet (ENC-17)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
