""" This script contains checks and helping functions for the comparison tool"""

# imports
import numpy as np

def check_and_set_analysis_parameters(state, params):

    state.start_time = params.get('start_time')
    state.end_time = params.get('end_time')
    state.analysis_frequency = params.get('analysis_frequency')
    state.output_saving_frequency = params.get('output_saving_frequency')

    # go through the time steps from start_time to end_time and first check if they are inside the time of the model
    t_model_start = state.t.max()
    t_model_end = state.t.min()
    if state.start_time > t_model_start or state.end_time < t_model_end:
        print(f"Warning: start_time {state.start_time} or end_time {state.end_time} is outside the model time range ({t_model_start}, {t_model_end}). Keep in mind to check time format of output and dataset input. Returning nan for continuing evaluation..")

    # second check, that analyis_frequency is not smaller than output_saving_frequency
    if state.analysis_frequency < state.output_saving_frequency:
        print(f"Warning: analysis_frequency {state.analysis_frequency} is smaller than output_saving_frequency {state.output_saving_frequency}. This could lead to problems, because we do not have enough time steps to analyse. Please change the parameters in the comparison_tool.yaml file.")
        return np.nan


def print_statements_of_run(state):
    # print median distance horizontal and vertical
    print("--------------------------------")
    print("Mean horizontal distance: ", np.round(np.nanmean(state.distance_array[:, -1, 0])), "m. With a median of ", np.round(np.nanmedian(state.distance_array[:, -1, 0])), "m.   ")
    print("Mean vertical distance: ", np.round(np.nanmean(state.distance_array[:, -1, 1])), "m. With a median of ", np.round(np.nanmedian(state.distance_array[:, -1, 1])), "m.   ")
    # mean distance without weighting
    mean_distance = np.nanmean(np.sqrt(state.distance_array[:, -1, 0]**2 + state.distance_array[:, -1, 1]**2))
    print("Mean distance without weighting: ", np.round(mean_distance), "m.   ")
    print("--------------------------------")
    # also print number of features that have a distance of 0
    print("Number of features with horizontal distance of 0: ", np.sum(state.distance_array[:, -1, 0] == 0))
