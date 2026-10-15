"""Saving data and features to file for later analysis and plots"""

import os
import pandas as pd
import numpy as np


def save_features_and_distances(state):
        # Open a new NetCDF file

    subfolder = state.working_folder + "/distance_per_feature"
    os.makedirs(subfolder, exist_ok=True)

    # Clear the subfolder if it already exists and is not empty
    for filename in os.listdir(subfolder):
        file_path = os.path.join(subfolder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

    # Iterate over each feature to score
    for i in range(len(state.features_to_score)):
        feature = state.features_to_score.iloc[i]
        feature_id = feature["ID"] if not pd.isna(feature["ID"]) else feature["site_ID"]

        # Create a list to store the metadata and scores
        lines = []

        # Add metadata as comments or header lines
        for key, value in feature.items():
            lines.append(f"{key}: {value}")
            # remove any string that is \n or \r or \t from the value, as this can cause issues with the csv format
            lines[-1] = lines[-1].replace('\n', '').replace('\r', '').replace('\t', '')

        # add two seperate for midpoint_x and midpoint_y
        lines.append(f"midpoint_x: {feature.midpoint.x}")
        lines.append(f"midpoint_y: {feature.midpoint.y}")

        # Add an empty line to separate metadata from data
        lines.append("")

        # Add the time and score columns
        # time unit from the time convention of the run (years BP or years b2k), see data_loader.get_time_convention
        time_label = getattr(state, 'time_label', 'years')
        lines.append(f"time ({time_label}),horizontal_distance (m),vertical_distance (m)")

        # Add the score data
        distance_data = state.distance_array[i, :]  # Assuming score_array is 2D: (horizontal distance, vertical distance, time)
        for t in range(distance_data.shape[0]):
            lines.append(f"{distance_data[t, 2]}, {distance_data[t, 0]}, {distance_data[t, 1]}")  # time, horizontal distance, vertical distance

        # Write to CSV
        csv_filename = os.path.join(subfolder, f"{i}_{feature_id}.csv")
        with open(csv_filename, 'w') as f:
            f.write('\n'.join(lines))

        print(f"Saved distances for feature {feature_id} to {csv_filename}")

