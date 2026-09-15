#!/usr/bin/env python3

# Copyright (C) 2023 Andreas Henz (andreas.henz@geo.uzh.ch)
# Published under the GNU GPL (Version 3), check at the LICENSE file

# March 2024
# updated April 2024
# updated June 2025 and October/November 2025

# imports not standard to IGM
import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
import geopandas as gpd
import pandas as pd
import time

import numpy as np
import matplotlib.pyplot as plt
import time
# import tensorflow as tf # probably not needed for the comparison tool..
import yaml

# Data loading
from GLAMODAT.io.data_loader import load_yaml_parameters, read_nc_file_as_class, load_and_process_shapefiles

# Core Calculations
from GLAMODAT.core.weights_calculation import calculate_weights
from GLAMODAT.core.distance_calculation import process_features
from GLAMODAT.core.finalize_loading_features import finalize_loading_features
from GLAMODAT.core.checks_and_helping_functions import check_and_set_analysis_parameters, print_statements_of_run

# Saving data and features to file for later analysis and plots
from GLAMODAT.io.saving_features_and_data import save_features_and_distances

# plots
from GLAMODAT.visualisations.main_plots import do_all_plots



# ============================================================================================================================================================================

def prepare_data(model_output, parameter_file='comparison_tool.yaml'):
    """Prepare model output for downstream comparison analysis.

    Reads the configuration from a YAML parameter file, loads the NetCDF state for
    a given model output, sets the working directory, and derives the spatial
    extent needed for later spatial and temporal comparisons.

    Parameters
    ----------
    model_output : str
        Path to the model output NetCDF file.
    parameter_file : str
        YAML configuration file with data paths and analysis settings.
    """

    params = load_yaml_parameters(parameter_file)

    data_to_load = params.get('data_to_load')
    data_folder = params.get('data_folder')

    target_epsg = params.get('target_epsg', 32632)
    shapefiles = params.get('shapefiles', {})
    
    # name_of_column_in_be10_ages = 'Date_ID'

    file = os.path.join(model_output, params.get('output_nc_file'))
    state = read_nc_file_as_class(file, params)
    # get working folder from model_output
    state.working_folder = model_output
    extent = [min(state.x), max(state.x), min(state.y), max(state.y)]    

    timeframe = [state.t.min()+np.nanmax(state.icefree_cummulative), state.t.min()] # time frame from when we actually startet the heatmaps calculation
    timeframe_tool = [params.get('start_time'), params.get('end_time')]

    print(f"Extent of the model: {extent}. Time frame of the model: {timeframe}. Please check if that is right, could be that your model run is not in not in the desired time.. (BP (1950) or b2k (2000) or whatever...)  then you need to change the code...")

    load_and_process_shapefiles(params, data_to_load, data_folder, target_epsg, shapefiles, state, extent, timeframe_tool)

    finalize_loading_features(state)
    
    print("Data preparation done.") 

    return state, params


def analyse_data(state, params):

    number_of_features = len(state.features_to_score)

    check_and_set_analysis_parameters(state, params)

    process_features(state, params)

    # check if number of features matches the distance_array first dimension and the original features_to_score length
    assert state.distance_array.shape[0] == len(state.features_to_score), "Number of features in distance_array does not match features_to_score dataframe."
    assert number_of_features == len(state.features_to_score), "Total number of features does not match original number of features."

    # calculate weights for weighted scoring if needed
    calculate_weights(state, params)

    # plot the scores
    # create_report(state)
    save_features_and_distances(state)
    # assign last distance (metric distance and 10x elevation distance) to the features_to_score dataframe for easier plotting and reporting
    state.features_to_score['final_horizontal_distance'] = state.distance_array[:, -1, 0]
    state.features_to_score['final_vertical_distance'] = state.distance_array[:, -1, 1]
    # Save features_to_score to CSV
    state.features_to_score.to_csv(state.working_folder + '/features-to-score.txt', index=False)

    print_statements_of_run(state)

    # scoring after all time steps and features have been processed
    #
    # return mean distances, 
    elevation_factor_weight = params.get('elevation_factor_weight', 10.0)
    print("Calculating total weighted distances for scoring with elevation factor weight of ", elevation_factor_weight)
    horizontal_distances = state.distance_array[:, -1, 0]
    vertical_distances = state.distance_array[:, -1, 1]
    weighted_distances = np.sqrt(horizontal_distances**2 + (elevation_factor_weight * vertical_distances)**2)

    # check if weights need to be 1
    if np.sum(state.features_to_score['tot_weights']) != 1.0:
        print("Warning: Total weights do not sum to 1. Normalizing weights.")
        state.features_to_score['tot_weights'] = state.features_to_score['tot_weights'] / np.sum(state.features_to_score['tot_weights'])

    # Before making all toghether to a single score, also see how many features have a distance of 0
    weighted_distances = weighted_distances * state.features_to_score['tot_weights']
    weighted_distances = np.nansum(weighted_distances)
    weighted_horizontal_distances = np.nansum(horizontal_distances * state.features_to_score['tot_weights'].values)
    weighted_vertical_distances = np.nansum(vertical_distances * state.features_to_score['tot_weights'].values)
    # number of zero distances of features with weight > 0
    fraction_zero_distances = np.sum((horizontal_distances == 0) & (state.features_to_score['tot_weights'] > 0)) / np.sum(state.features_to_score['tot_weights'] > 0) * 100.0

    return weighted_horizontal_distances, weighted_vertical_distances, weighted_distances, fraction_zero_distances



def evaluate(folder, parameter_file, create_plots=True):
    model_output = os.path.join(folder)

    state, params = prepare_data(model_output=model_output, parameter_file=parameter_file)
    horizontal_distance, vertical_distance, final_score, fraction_zero_distances = analyse_data(state, params)
    end_time = params.get('end_time')
    start_time = params.get('start_time')
    if create_plots:
        do_all_plots(state.working_folder, evaluation_timeframe=[start_time, end_time], params=params)

    return horizontal_distance, vertical_distance, final_score, fraction_zero_distances # to minimize the function, num_zero_distances is only for high and mediuim quality ages!!

if __name__ == "__main__" and False:

    synthetic_case = True

    if synthetic_case:
        model_output = "test_database/test_run_1.0"
        parameter_file = "configs/params_comparison_tool_synthetic_case.yaml"
    else:
        # model_output = sys.argv[1] if len(sys.argv) > 1 else 'Lamare_simulations_for_AH_scoring/IGM_simulations/sim_0659/outputs/2026-07-09/16-58-20/output_ex.nc'
        model_output = sys.argv[1] if len(sys.argv) > 1 else 'susten-run-paper-may/1'
        parameter_file = sys.argv[2] if len(sys.argv) > 2 else 'comparison_tool/params_comparison_tool_case_study.yaml'

    # set current folder as working folder)
    # os.chdir("..")
    print(os.getcwd())

    state, params = prepare_data(model_output=model_output, parameter_file=parameter_file)

    horizontal_distances, vertical_distances, tot_weighted_distances, num_zero_distances = analyse_data(state, params)
    
    # here you could do the scoring, or we do it seperately..
    print("Total weighted distances (score to minimize): ", tot_weighted_distances)
    print("Number of features with horizontal distance of 0: ", num_zero_distances)
    start_time = params.get('start_time')
    end_time = params.get('end_time')
    do_all_plots(state.working_folder, evaluation_timeframe=[start_time, end_time], params=params)



