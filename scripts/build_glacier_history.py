"""Build a glacier-history NetCDF from several model output folders."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

# repository root on the path, so the GLAMODAT package can be imported when this file is run as a script
repository_root = Path(__file__).resolve().parents[1]
if str(repository_root) not in sys.path:
    sys.path.insert(0, str(repository_root))

from GLAMODAT.io.data_loader import clip_to_run_duration

def find_compromise_glacier_history(nc_file_path: Path, variable_name: str = "lasticecover"):
    """Extract the final ice-cover frame and scale it to [-1, 1]."""
    with Dataset(nc_file_path, "r") as dataset:
        if variable_name not in dataset.variables:
            raise KeyError(f"Variable {variable_name!r} is not present in {nc_file_path}")
        last_ice_cover = dataset.variables[variable_name][-1, :, :]
        model_time = dataset.variables["time"][:]
    # durations from before the run (e.g. +-99000 yr from the heatmaps start) limited to the run duration + 1 yr, so
    # the scaling to [-1, 1] below is not dominated by them
    last_ice_cover = clip_to_run_duration(last_ice_cover[np.newaxis], model_time[[0, -1]])[-1]

    shifted = last_ice_cover - np.min(last_ice_cover)
    maximum = np.max(shifted)
    if maximum == 0:
        return np.zeros_like(shifted, dtype=np.float32)
    return (2.0 * shifted / maximum - 1.0).astype(np.float32)


def build_glacier_history(input_folder: Path, runs: list[str], output_nc: Path, output_png: Path) -> None:
    """Combine the final ice-cover frame from each named run."""
    summed_history = None
    bedrock = None
    for run in runs:
        model_file = input_folder / run / "output.nc"
        history = find_compromise_glacier_history(model_file)
        summed_history = history if summed_history is None else summed_history + history
        if bedrock is None:
            with Dataset(model_file, "r") as dataset:
                if "topg" in dataset.variables:
                    bedrock = dataset.variables["topg"][0, :, :]

    if summed_history is None:
        raise ValueError("At least one model run is required")
    if bedrock is not None:
        summed_history = summed_history + 0.0001 * bedrock

    output_nc.parent.mkdir(parents=True, exist_ok=True)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    with Dataset(output_nc, "w", format="NETCDF4") as dataset:
        dataset.createDimension("lat", summed_history.shape[0])
        dataset.createDimension("lon", summed_history.shape[1])
        variable = dataset.createVariable("glacier_history", "f4", ("lat", "lon"))
        variable[:] = summed_history

    plt.imsave(output_png, summed_history, cmap="coolwarm", origin="lower")
    print(f"Saved glacier history to {output_nc}")
    print(f"Saved preview map to {output_png}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Folder containing model-run folders")
    parser.add_argument("--runs", nargs="+", required=True, help="Run folder names")
    parser.add_argument("--output", type=Path, required=True, help="Output glacier-history NetCDF")
    parser.add_argument("--preview", type=Path, required=True, help="Output preview image")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    build_glacier_history(args.input, args.runs, args.output, args.preview)


if __name__ == "__main__":
    # for testing you can run this script directly also here, if you give the input here (hard coded into the file...)
    # sys.argv = [
    #     "build_glacier_history.py",
    #     "--input",
    #     "test_database",
    #     "--runs",
    #     "test_run_1.0",
    #     "test_run_0.5",
    #     "test_run_0.25",
    #     "--output",
    #     "glacier_history.nc",
    #     "--preview",
    #     "summed_glacier_history.png",
    # ]
    main()
