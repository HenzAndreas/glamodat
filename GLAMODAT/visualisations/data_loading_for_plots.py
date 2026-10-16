""" This script is for loading the data for the plots, it is not the same than loading for the comparison tool!"""

# imports
import os
import pandas as pd
import numpy as np
from netCDF4 import Dataset

from GLAMODAT.io.data_loader import clip_to_run_duration


# function to load the csv files and save it as df and tensor
def load_csv_as_df_and_tensor(csv_file_path):

    # Read the file and extract the metadata and data
    with open(csv_file_path, 'r') as file:
        lines = file.readlines()

    # there is an empty line somewhere, after which the data starts, we need to find that line and read the data from there
    data_start_line = None
    for i, line in enumerate(lines):
        if line.strip() == '':
            data_start_line = i + 1
            break


    # Extract metadata (lines before line 35)
    metadata = {}
    for line in lines[:data_start_line-1]:  # Adjust this if the data starts at a different line
        if ':' in line:
            key, value = line.strip().split(':', 1)
            metadata[key.strip()] = value.strip()
    # transform metadata to dataframe
    metadata_df = pd.DataFrame([metadata])
    # can we make values to numeric if possible?
    # define columns that should be numeric
    cols_to_numeric = ['latitude', 'longitude',
       'elevation', 'sample_yr', 'public_yr', 'r_exp_age', 'r_ext_err','min_age',
       'max_age', 'year', 'Year', 'recal_max',
       'recal_min', 'from_99.7', 'to_99.7', 'age_q16','age_q84','age_mean','score', 'icecover',
       'tot_weights', 'midpoint_x', 'midpoint_y', 'mean_s_yr', 'mean_p_yr', 'e_age', 'e_neg_err', 'e_pos_err', 'e_age_max', 'e_age_min']
    for col in cols_to_numeric:
        if col in metadata_df.columns:
            metadata_df[col] = metadata_df[col].str.strip()  # Remove leading/trailing whitespace
            metadata_df[col] = pd.to_numeric(metadata_df[col], errors='coerce')
    
    # make all age column to integers
    # Read the data starting from line 35, treating 'nan' as np.
    distances_df = pd.read_csv(csv_file_path, skiprows=data_start_line, na_values=['nan'])
    # eventually 32 skip rows for other files.. not sure if that is consistent or not..    
    # make a tensor float values out of the df
    distances_tensor = distances_df.values.astype(float)

    # Print metadata to verify
    # print("Metadata:", metadata_df.head())
    # print(distances_tensor.shape)
    return distances_tensor, metadata_df

def get_list_of_csv_files(folderpath):
    # get list of csv files in distance_per_feature
    distance_folder = os.path.join(folderpath, "distance_per_feature")
    if not os.path.exists(distance_folder):
        print(f"Folder {distance_folder} does not exist, skipping.")
        raise ValueError(f"Folder {distance_folder} does not exist.")
    csv_files = [f for f in os.listdir(distance_folder) if f.endswith('.csv')]
    return csv_files

def load_all_csv_files(folderpath):
    csv_files = get_list_of_csv_files(folderpath)
    all_data_tensor = np.array([])  # initialize an empty array to store all data tensors
    metadata_all = pd.DataFrame()  # initialize an empty list to store all metadata
    for csv_file in csv_files:
        csv_path = os.path.join(folderpath, "distance_per_feature", csv_file)
        distances, metadata = load_csv_as_df_and_tensor(csv_path)
        all_data_tensor = np.vstack([all_data_tensor, distances[np.newaxis, :, :]]) if all_data_tensor.size > 0 else distances[np.newaxis, :, :]
        metadata_all = pd.concat([metadata_all, metadata], ignore_index=True)

    metadata_all, all_data_tensor = sort_by_max_age(metadata_all, all_data_tensor)

    # make geometry column actually a geometry, not just a string
    from shapely import wkt
    metadata_all['geometry'] = metadata_all['geometry'].apply(wkt.loads)
    # also midpoint column should actually be a point geometry
    # metadata_all['midpoint'] = metadata_all.apply(lambda row: wkt.loads(f"POINT ({row['midpoint_x']} {row['midpoint_y']})") if not pd.isna(row['midpoint_x']) and not pd.isna(row['midpoint_y']) else None, axis

    return all_data_tensor, metadata_all

def sort_by_max_age(metadata, tensor):
    # sort the metadata by max_age and sort the tensor accordingly
    sorted_indices = np.argsort(metadata['max_age'])
    # reverse sorting
    sorted_indices = sorted_indices[::-1]
    sorted_metadata = metadata.iloc[sorted_indices].reset_index(drop=True)
    sorted_tensor = tensor[sorted_indices, :, :]
    return sorted_metadata, sorted_tensor

def load_topography_and_icecover(folderpath):
    # load net cdf file for the topography, last ice cover and time
    nc_file_path = os.path.join(folderpath, "output.nc")
    if not os.path.exists(nc_file_path):
        print(f"NetCDF file {nc_file_path} does not exist, skipping.")
        raise ValueError(f"NetCDF file {nc_file_path} does not exist.")
    
    dataset = Dataset(nc_file_path)
    print("Variables in the dataset:", dataset.variables.keys())
    try:
        topg = dataset.variables['topg'][-1, :, :] # topography at the last time step
    except: # topography not present, means we load last of usurf and last of thk and subtract
        usurf = dataset.variables['usurf'][-1, :, :]
        thk = dataset.variables['thk'][-1, :, :]
        topg = usurf - thk
    t = dataset.variables['time'][:]
    t = -t # convert to years before present
    # durations from before the run limited to the run duration + 1 yr (same as in the comparison tool)
    lasticecover = clip_to_run_duration(dataset.variables['lasticecover'][:], t)
    x = dataset.variables['x'][:]
    y = dataset.variables['y'][:]
    dataset.close()
    return topg, t, lasticecover, x, y

def load_output_ts_file(folderpath):
    # load the output_ts file for the forcing
    ts_file_path = os.path.join(folderpath, "output_ts.nc")
    if not os.path.exists(ts_file_path):
        print(f"Time series file {ts_file_path} does not exist")
        raise ValueError(f"Time series file {ts_file_path} does not exist.")
    
    dataset = Dataset(ts_file_path)
    time = -dataset.variables['time'][:]
    # print varuables in the dataset
    print("Variables in the time series dataset:", dataset.variables.keys())
    # look what exists, and take them, otherwise define "None" for the missing ones
    var_names = ['tss', 'tas', 'ela', 'pr']
    results = {}
    for var in var_names:
        try:
            results[var] = dataset.variables[var][:]
        except:
            results[var] = None
    dataset.close()

    return time, results['tss'], results['tas'], results['ela'], results['pr']