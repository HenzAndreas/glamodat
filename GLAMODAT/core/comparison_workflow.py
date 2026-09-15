"""Core single-run glacier-model comparison workflow."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from GLAMODAT.core.checks_and_helping_functions import (
    check_and_set_analysis_parameters,
    print_statements_of_run,
)
from GLAMODAT.core.distance_calculation import process_features
from GLAMODAT.core.finalize_loading_features import finalize_loading_features
from GLAMODAT.core.weights_calculation import calculate_weights
from GLAMODAT.io.data_loader import (
    load_and_process_shapefiles,
    load_yaml_parameters,
    read_nc_file_as_class,
)
from GLAMODAT.io.saving_features_and_data import save_features_and_distances
from GLAMODAT.visualisations.main_plots import do_all_plots


def prepare_data(model_output, parameter_file="comparison_tool.yaml"):
    """Load model output and evidence data for comparison analysis."""
    params = load_yaml_parameters(parameter_file)
    data_to_load = params.get("data_to_load")
    data_folder = params.get("data_folder")
    target_epsg = params.get("target_epsg", 32632)
    shapefiles = params.get("shapefiles", {})

    model_file = os.path.join(model_output, params.get("output_nc_file"))
    state = read_nc_file_as_class(model_file, params)
    state.working_folder = model_output
    extent = [min(state.x), max(state.x), min(state.y), max(state.y)]
    timeframe = [
        state.t.min() + np.nanmax(state.icefree_cummulative),
        state.t.min(),
    ]
    timeframe_tool = [params.get("start_time"), params.get("end_time")]

    print(
        f"Extent of the model: {extent}. Time frame of the model: {timeframe}. "
        "Please check that the model time format is correct."
    )
    load_and_process_shapefiles(
        params,
        data_to_load,
        data_folder,
        target_epsg,
        shapefiles,
        state,
        extent,
        timeframe_tool,
    )
    finalize_loading_features(state)
    print("Data preparation done.")
    return state, params


def analyse_data(state, params):
    """Process prepared features and return aggregate comparison metrics."""
    number_of_features = len(state.features_to_score)
    check_and_set_analysis_parameters(state, params)
    process_features(state, params)

    assert state.distance_array.shape[0] == len(state.features_to_score)
    assert number_of_features == len(state.features_to_score)

    calculate_weights(state, params)
    save_features_and_distances(state)
    state.features_to_score["final_horizontal_distance"] = state.distance_array[:, -1, 0]
    state.features_to_score["final_vertical_distance"] = state.distance_array[:, -1, 1]
    state.features_to_score.to_csv(
        os.path.join(state.working_folder, "features-to-score.txt"), index=False
    )
    print_statements_of_run(state)

    elevation_factor_weight = params.get("elevation_factor_weight", 10.0)
    horizontal_distances = state.distance_array[:, -1, 0]
    vertical_distances = state.distance_array[:, -1, 1]
    weighted_distances = np.sqrt(
        horizontal_distances**2
        + (elevation_factor_weight * vertical_distances) ** 2
    )

    total_weight = np.sum(state.features_to_score["tot_weights"])
    if total_weight != 1.0:
        print("Warning: Total weights do not sum to 1. Normalizing weights.")
        state.features_to_score["tot_weights"] /= total_weight

    weighted_distances = np.nansum(
        weighted_distances * state.features_to_score["tot_weights"]
    )
    weighted_horizontal_distances = np.nansum(
        horizontal_distances * state.features_to_score["tot_weights"].values
    )
    weighted_vertical_distances = np.nansum(
        vertical_distances * state.features_to_score["tot_weights"].values
    )
    positive_weights = state.features_to_score["tot_weights"] > 0
    fraction_zero_distances = (
        np.sum((horizontal_distances == 0) & positive_weights)
        / np.sum(positive_weights)
        * 100.0
    )

    return (
        weighted_horizontal_distances,
        weighted_vertical_distances,
        weighted_distances,
        fraction_zero_distances,
    )


def evaluate(folder, parameter_file, create_plots=True):
    """Prepare, analyse, and optionally plot one model-output folder."""
    state, params = prepare_data(folder, parameter_file)
    results = analyse_data(state, params)
    if create_plots:
        do_all_plots(
            state.working_folder,
            evaluation_timeframe=[params.get("start_time"), params.get("end_time")],
            params=params,
        )
    return results
