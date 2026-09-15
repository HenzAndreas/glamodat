from pathlib import Path

import geopandas as gpd
import numpy as np
import yaml
from netCDF4 import Dataset
from shapely.geometry import Point

from GLAMODAT.core.comparison_workflow import prepare_data


def _write_model_output(path: Path) -> None:
    with Dataset(path, "w") as dataset:
        dataset.createDimension("time", 2)
        dataset.createDimension("y", 2)
        dataset.createDimension("x", 2)

        x = dataset.createVariable("x", "f8", ("x",))
        y = dataset.createVariable("y", "f8", ("y",))
        time = dataset.createVariable("time", "f8", ("time",))
        x[:] = [0.0, 1000.0]
        y[:] = [0.0, 1000.0]
        time[:] = [-50.0, 50.0]

        thickness = dataset.createVariable("thk", "f8", ("time", "y", "x"))
        last_ice_cover = dataset.createVariable(
            "lasticecover", "f8", ("time", "y", "x")
        )
        cumulative_ice_free = dataset.createVariable(
            "icefree_cummulative", "f8", ("time", "y", "x")
        )
        topography = dataset.createVariable("topg", "f8", ("time", "y", "x"))

        thickness[:] = np.ones((2, 2, 2))
        last_ice_cover[:] = np.zeros((2, 2, 2))
        cumulative_ice_free[:] = np.zeros((2, 2, 2))
        topography[:] = np.zeros((2, 2, 2))


def _write_glacier_history(path: Path) -> None:
    with Dataset(path, "w") as dataset:
        dataset.createDimension("y", 2)
        dataset.createDimension("x", 2)
        glacier_history = dataset.createVariable(
            "glacier_history", "f8", ("y", "x")
        )
        glacier_history[:] = np.ones((2, 2))


def _write_event_ages(path: Path) -> None:
    events = gpd.GeoDataFrame(
        {
            "ID": ["minimal-fixture-1"],
            "confid_ra": ["high"],
            "pc_cat": ["ice cover"],
            "pc_subcat": ["-"],
            "pc_time": ["-"],
            "e_age_min": [50.0],
            "e_age_max": [50.0],
        },
        geometry=[Point(0.0, 0.0)],
        crs="EPSG:32632",
    )
    events.to_file(path)


def test_prepare_data_with_minimal_fixture(tmp_path):
    model_output = tmp_path / "minimal-model-output"
    model_output.mkdir()
    _write_model_output(model_output / "output.nc")
    _write_glacier_history(model_output / "glacier_history.nc")
    _write_event_ages(model_output / "event_ages.shp")

    parameters = {
        "data_folder": str(model_output),
        "data_to_load": ["event_ages"],
        "shapefiles": {"event_ages": "event_ages.shp"},
        "target_epsg": 32632,
        "folder_with_simulations": str(model_output),
        "output_nc_file": "output.nc",
        "output_nc_ts_file": "output_ts.nc",
        "year_format": "-b2k",
        "glacier_history_file": "glacier_history.nc",
        "analyse_mask_file": str(model_output / "missing-mask.shp"),
        "start_time": 100.0,
        "end_time": 0.0,
        "analysis_frequency": 100.0,
        "output_saving_frequency": 10.0,
        "confidence_rating_weights": {"high": 1.0, "medium": 1.0, "low": 0.0},
    }
    parameter_file = tmp_path / "params.yaml"
    parameter_file.write_text(yaml.safe_dump(parameters), encoding="utf-8")

    state, loaded_parameters = prepare_data(
        model_output=str(model_output), parameter_file=str(parameter_file)
    )

    assert state.x.shape == (2,)
    assert state.y.shape == (2,)
    assert state.t.tolist() == [100.0, 0.0]
    assert state.lasticecover.shape == (2, 2, 2)
    assert state.glacier_history.shape == (2, 2)
    assert len(state.features_to_score) == 1
    assert state.features_to_score.iloc[0]["ID"] == "minimal-fixture-1"
    assert loaded_parameters["year_format"] == "-b2k"