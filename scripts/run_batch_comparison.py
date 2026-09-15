"""Evaluate many model-output folders with one configuration."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

try:
    from scripts.comparison_tool import evaluate
except ModuleNotFoundError:
    from comparison_tool import evaluate


def find_model_folders(input_folder: Path, output_nc_file: str) -> Iterable[Path]:
    """Yield unique folders containing the configured model output file."""
    seen = set()
    for model_file in sorted(input_folder.rglob(output_nc_file)):
        folder = model_file.parent.resolve()
        if folder not in seen:
            seen.add(folder)
            yield folder


def run_batch(
    input_folder: Path,
    parameter_file: Path,
    results_file: Path,
    output_nc_file: str,
    create_plots: bool,
) -> None:
    """Evaluate every model folder below ``input_folder`` and save CSV results."""
    folders = list(find_model_folders(input_folder, output_nc_file))
    results_file.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for folder in folders:
        print(f"Evaluating {folder}")
        horizontal, vertical, score, zero_fraction = evaluate(
            folder=str(folder),
            parameter_file=str(parameter_file),
            create_plots=create_plots,
        )
        rows.append(
            {
                "model_folder": str(folder),
                "horizontal_distance": horizontal,
                "vertical_distance": vertical,
                "weighted_score": score,
                "zero_distance_fraction": zero_fraction,
            }
        )

    with results_file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys() if rows else ["model_folder"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} results to {results_file}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Folder containing model runs")
    parser.add_argument("--config", type=Path, required=True, help="YAML comparison configuration")
    parser.add_argument("--results", type=Path, required=True, help="Output CSV file")
    parser.add_argument("--output-file", default="output.nc", help="Model NetCDF filename")
    parser.add_argument("--no-plots", action="store_true", help="Skip result plots")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_batch(args.input, args.config, args.results, args.output_file, not args.no_plots)


if __name__ == "__main__":
    # sys.argv = [
    #     "run_batch_comparison.py",
    #     "--input",
    #     "test_database",
    #     "--config",
    #     "configs/params_comparison_tool_synthetic_case.yaml",
    #     "--results",
    #     "batch_results.csv",
    #     "--output-file",
    #     "output.nc",
    # ]
    main()
