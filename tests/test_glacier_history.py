from pathlib import Path

import numpy as np
from netCDF4 import Dataset

from scripts.build_glacier_history import build_glacier_history, find_compromise_glacier_history


def _write_model_run(path: Path, last_ice_cover: np.ndarray) -> None:
    with Dataset(path, "w") as dataset:
        dataset.createDimension("time", 2)
        dataset.createDimension("y", last_ice_cover.shape[0])
        dataset.createDimension("x", last_ice_cover.shape[1])
        variable = dataset.createVariable("lasticecover", "f8", ("time", "y", "x"))
        topography = dataset.createVariable("topg", "f8", ("time", "y", "x"))
        variable[0, :, :] = 0.0
        variable[1, :, :] = last_ice_cover
        topography[:] = 0.0


def test_glacier_history_scales_final_frame(tmp_path):
    model_file = tmp_path / "output.nc"
    _write_model_run(model_file, np.array([[2.0, 4.0], [6.0, 8.0]]))

    history = find_compromise_glacier_history(model_file)

    np.testing.assert_allclose(history, [[-1.0, -1.0 / 3.0], [1.0 / 3.0, 1.0]])


def test_build_glacier_history_writes_netcdf_and_preview(tmp_path):
    input_folder = tmp_path / "runs"
    run_folder = input_folder / "run-a"
    run_folder.mkdir(parents=True)
    _write_model_run(run_folder / "output.nc", np.array([[0.0, 1.0], [2.0, 3.0]]))
    output_nc = tmp_path / "results" / "glacier_history.nc"
    output_png = tmp_path / "results" / "glacier_history.png"

    build_glacier_history(input_folder, ["run-a"], output_nc, output_png)

    assert output_nc.exists()
    assert output_png.exists()
    with Dataset(output_nc) as dataset:
        assert dataset.variables["glacier_history"].shape == (2, 2)
