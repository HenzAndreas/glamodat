"""Command-line entry point for evaluating one model-output folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from GLAMODAT.core.comparison_workflow import evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-output", required=True, help="Folder containing the model NetCDF output")
    parser.add_argument("--config", required=True, help="YAML comparison configuration")
    parser.add_argument("--no-plots", action="store_true", help="Skip result plots")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    horizontal, vertical, score, zero_fraction = evaluate(
        folder=args.model_output,
        parameter_file=args.config,
        create_plots=not args.no_plots,
    )
    print(f"Weighted horizontal distance: {horizontal}")
    print(f"Weighted vertical distance: {vertical}")
    print(f"Total weighted distance: {score}")
    print(f"Zero-distance feature fraction: {zero_fraction}")


if __name__ == "__main__":
    # sys.argv = [
    #     "run_comparison.py",
    #     "--model-output",
    #     "../paleoalps-extension/susten-run-paper-may/1/",
    #     "--config",
    #     "configs/params_comparison_tool_case_study.yaml",
    # ]
    main()
