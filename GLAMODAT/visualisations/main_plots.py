""" This is the script to run plots, also directly from here, or from the main comparison tool scirpt..
here you can change what plots should be made at the end of each run"""

import os
import yaml

from GLAMODAT.visualisations.data_loading_for_plots import load_all_csv_files
from GLAMODAT.io.data_loader import get_time_convention
from GLAMODAT.visualisations.plots_scripts import plot_forcing, plot_individual_features_over_time, plot_combined_distances_over_time, plot_last_frame_with_icecover_over_time


def do_all_plots(folderpath, evaluation_timeframe, params):

    print("Creating plots... \n")
    print("This may take a while but this plotting function is not necessary to run the comparison tool, as it uses the saved output, which is already created by the comparison tool. At this point of the code. \n")

    distances_tensor, metadata = load_all_csv_files(folderpath)
    # plot_forcing(folderpath, evaluation_timeframe=evaluation_timeframe)
    plot_individual_features_over_time(folderpath, distances_tensor, metadata, evaluation_timeframe)
    plot_combined_distances_over_time(folderpath, distances_tensor, metadata, evaluation_timeframe,
                                      time_label=get_time_convention(params)[2])

if __name__ == "__main__":
    # example usage
    # run_folder = 'comparison_tool/test_database'
    # folder_id = 'test_run_0.0'
    run_folder = 'susten-run-paper-may'
    folder_id = '1'
    folderpath = os.path.join(run_folder, folder_id)

    distances_tensor, metadata = load_all_csv_files(folderpath)

    # plot_forcing(folderpath, evaluation_timeframe=(-80.0, 14000))
    plot_individual_features_over_time(folderpath, distances_tensor, metadata, evaluation_timeframe=(-80.0, 14000))
    plot_combined_distances_over_time(folderpath, distances_tensor, metadata, evaluation_timeframe=(-80.0, 14000))

    print("All plots created and saved in the folder.")