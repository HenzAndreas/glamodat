"""Helper for loading data from the params, databases or model outputs. 
"""



import yaml
import os
import numpy as np
import pandas as pd
import geopandas as gpd
from netCDF4 import Dataset

def load_yaml_parameters(parameter_file):
    try:
        with open(parameter_file, 'r', encoding='utf-8') as f:
            params = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Parameter file {parameter_file} not found. We are in this folder right now: {os.getcwd()}. Please check if the parameter file is in the correct folder.")
        raise AttributeError("Parameter file not found. Please check if the parameter file is in the correct folder.")
    return params

def read_nc_file_as_class(file, params):    
    '''Read a netCDF file and return it as a class instance'''

    class NetCDFData:
        def __init__(self, ds):
            # self.ds = ds
            # print availbale variables
            print('Available variables in the netCDF file:')
            for var in ds.variables:
                print(f' - {var}: {ds.variables[var].shape}')

            # Read out variables and assign as attributes if they exist
            for var in ['x', 'y', 'time', 'thk','icemargin', 'lasticecover', 'icefree_cummulative']:

                # for lasticecover, make sure to read it as (time in bp, y, x)
                if var == 'lasticecover':
                    setattr(self, var, ds.variables[var][:]) # negative is ice free, positive is ice free age
                    # add the value of the very first frame (from 0 to 1 topg norm) to make it differentiable
                    self.lasticecover += (self.lasticecover[0, :, :])

                # make time to t
                elif var == 'time':
                    setattr(self, 't', ds.variables[var][:])
                    # make sure the year is in the right format, using params year_format
                    if params.get('year_format') == '-BP':
                        self.t = -self.t # reverse the time array to be in ascending order and make it negative for BP
                    elif params.get('year_format') == '-b2k':
                        self.t = -self.t + 50.0 # 50 becuase b2k is 2000, and BP is 1950, so we need to add 50 years to convert from b2k to BP
                    else:
                        print(f"Warning: year_format {params.get('year_format')} not recognized. Assuming BP, but be sure to check if your model run is in BP or in another unit..")
                        self.t = -self.t
                    # check if we are going from old to young (big to small)$
                    check_time_order = np.diff(self.t)
                    if np.any(check_time_order > 0):
                        print("Warning: Time array is not in descending order (towards the present).")

                # normal cases ==================
                elif var in ds.variables:
                    setattr(self, var, ds.variables[var][:])
                else:
                    setattr(self, var, None)

            # check if topg, usurf should be present
            # check if any of these two are present:
            if 'topg' in ds.variables:
                setattr(self, 'topg', ds.variables['topg'][0, :, :])

            elif 'usurf' in ds.variables:
                setattr(self, 'usurf', ds.variables['usurf'][-1, :, :])
                self.topg = self.usurf - self.thk[-1, :, :]

            elif params.get('topg_file') and os.path.exists(params['topg_file']):
                # this means non of the topg or usurf are present, check as a last option if params has a file defined where we can find the topg
                topg_ds = Dataset(params['topg_file'], mode='r')
                try:
                    topg_var = topg_ds.variables['topg']
                except:
                    # take usurf and thk to calculate topg
                    usurf = topg_ds.variables['usurf'][:,:]
                    thk = topg_ds.variables['thk'][:,:]
                    topg_var = usurf - thk
                # also also the x and y from this file, as they might be different, if they are different, we should make they fitting if possible, try setting the topg to the same shape as x and y in self already
                topg_x = topg_ds.variables['x'][:]
                topg_y = topg_ds.variables['y'][:]
                # check if the x and y are the same as in self, if not, we need to interpolate the topg to the same grid as self.x and self.y
                if len(self.x) != len(topg_x) or len(self.y) != len(topg_y):
                    # check if min and max self.x are in topg_x and min max of self.y are in topg_y, then we can maybe just cut without interpolation
                    if (self.x.min() >= topg_x.min() and self.x.max() <= topg_x.max()) and (self.y.min() >= topg_y.min() and self.y.max() <= topg_y.max()):
                        # find the indices of topg_x and topg_y that are closest to self.x and self.y
                        x_indices = np.searchsorted(topg_x, self.x)
                        y_indices = np.searchsorted(topg_y, self.y)
                        # cut the topg_var to the same shape as self.x and self.y
                        topg_var_cut = topg_var[y_indices[0]:y_indices[-1]+1, x_indices[0]:x_indices[-1]+1]
                        # now check if the shapes are same, if not, we have a more difficult problem, we need to interpolate but we raise an error for now
                        if topg_var_cut.shape != (len(self.y), len(self.x)):
                            raise ValueError(f"Topography shape {topg_var_cut.shape} does not match the expected shape {(len(self.y), len(self.x))}. Interpolation is needed but not implemented.")
                    else:
                        raise ValueError(f"Topography x and y ranges do not cover the model x and y ranges. Interpolation is needed but not implemented.")
                else:
                    topg_var_cut = topg_var # is the right dimension and shape, we can use it directly

                setattr(self, 'topg', topg_var_cut[:, :])
                topg_ds.close()
            
            else:
                print("Warning: Neither 'topg' nor 'usurf' variables are present in the netCDF file, and no valid 'topg_file' is provided in parameters. Cannot determine topography.\n")
                print(f"Folder given was {params.get('folder_with_simulations')}, and topg_file was {params.get('topg_file')}. And we are in folder {os.getcwd()}. Please check if the topography file is present and correctly specified in the parameters.\n")
                raise ValueError("Neither 'topg' nor 'usurf' variables are present in the netCDF file, and no valid 'topg_file' is provided in parameters. Cannot determine topography.")

                # if thk is not available, set it to zero array (this is needed for plotting later, but actually only the cases for the synthetic case)
            if self.thk is None and self.lasticecover is not None:
                self.thk = np.zeros_like(self.lasticecover)
            
            # print available attributes
            print('Available attributes in the netCDF file:')



            self.dx = ds.variables['x'][1] - ds.variables['x'][0]

        def __getattr__(self, item):
            return getattr(self.ds, item)

    ds = Dataset(file, mode='r')

    state = NetCDFData(ds)

    output_nc_filename = params.get('output_nc_file', 'output.nc')  # default to output.nc if not specified
    output_nc_ts_filename = params.get('output_nc_ts_file', 'output_ts.nc')  # default to output_ts.nc if not specified

    # read also the output_ts.nc file in the same folder
    ts_file = file.replace(output_nc_filename, output_nc_ts_filename)
    try:
        ts_ds = Dataset(ts_file, mode='r')
        # Read out specific variables from output_ts.nc if they exist
        for var in ['vol', 'area', 'gi', 'ela', 'tas', 'tss', 'pr']:
            if var in ts_ds.variables:
                setattr(state, var, ts_ds.variables[var][:])
                print(f' - {var}: {ts_ds.variables[var].shape}')
    except FileNotFoundError:
        print(f"Optional file {ts_file} not found. Proceeding without it. Plotting will be limited.")

    # check if there is one single glacier history ice cover file to override lasticecover
    glacier_history_file = os.path.join(params.get('folder_with_simulations'), params.get('glacier_history_file'))  # default to most_extensive.nc if not specified

    # depending on where we started the script, we need to adjust the path, comparison_tool could be doubled with os.getcwd().endswith('comparison_tool')
    # if os.getcwd().endswith('comparison_tool'):
    #     most_extensive_file = os.path.join('most_extensive.nc')

    if os.path.exists(glacier_history_file):
        print(f"Glacier history ice cover file found: {glacier_history_file}. Overriding lasticecover variable.")
        with Dataset(glacier_history_file, 'r') as gh_ds:
            glacier_history = gh_ds.variables['glacier_history'][:]
        state.glacier_history = glacier_history

        # check if it has the same shape as lasticecover
        if glacier_history.shape != state.lasticecover.shape[1:]:
            raise ValueError(f"Glacier history ice cover shape {glacier_history.shape} does not match lasticecover shape {state.lasticecover.shape[1:]}.")

    else:
        raise FileNotFoundError(f"Glacier history ice cover file not found: {glacier_history_file}. Please provide this file to use the distance calculations.")

    # after all this code, there should now be variables for: lasticecover, thk, topg, x, y, t and glacier_history, check for that
    # find attributes:
    attributes = state.__dict__.keys()
    if not all(attribute in attributes for attribute in ['lasticecover', 'thk', 'topg', 'x', 'y', 't', 'glacier_history']):
        missing_attrs = [attribute for attribute in ['lasticecover', 'thk', 'topg', 'x', 'y', 't', 'glacier_history'] if attribute not in attributes]
        raise AttributeError(f"Missing attributes in state: {missing_attrs}. Please check the netCDF files.")
    
    return state

def load_and_process_shapefiles(params, data_to_load, data_folder, target_epsg, shapefiles, state, extent, timeframe_tool):
    # define dataframes to save results into
    state.points = gpd.GeoDataFrame(columns=['geometry'], crs=f"EPSG:{target_epsg}") # empty geodataframe
    state.polygons = gpd.GeoDataFrame(columns=['geometry'], crs=f"EPSG:{target_epsg}") # empty geodataframe

    loaded_files = []

    for var in data_to_load:
        # if shapefiles[var] is not a string ending with shp, it is probably a folder with multiple shapefiles, so we need to load all of them, so add them to data_to_load and continue with the next var
        if not shapefiles[var].endswith('.shp'):
            folder_path = os.path.join(data_folder, shapefiles[var])
            if not os.path.isdir(folder_path):
                raise ValueError(f"Expected a folder for {var} at {folder_path}, but it does not exist.")
            # list all shapefiles in the folder and add them to data_to_load
            for file_name in os.listdir(folder_path):
                if file_name.endswith('.shp'):
                    new_var = f"{var}_{file_name.rsplit('.', 1)[0]}"
                    shapefiles[new_var] = os.path.join(shapefiles[var], file_name)
                    data_to_load.append(new_var)
            continue  # skip the rest of the loop for this var, as we have added new vars to data_to_load

        filepath = os.path.join(data_folder, shapefiles[var])

        loaded_files.append(filepath)

        # load data and check which format it is matching
        temp = gpd.read_file(filepath, encoding='utf-8')

        # give it to check the format and reproject it to the target_epsg
        temp = _check_and_reproject(temp, target_epsg=target_epsg)

        temp = _delete_outside_extent(state.working_folder, params, extent, gdf=temp)  # clip to model extent right away, and also ice mask if present

        temp = _delete_ambiguous_and_unqualified(temp)  # remove ambiguous and unqualified ages, because they are not useful for scoring

        type_of_ages = temp['type_of_ages'].iloc[0]

        is_point = temp.geometry.geom_type.isin(['Point'])
        temp = temp[is_point | ~is_point]

        temp = _give_age_bounds(gdf=temp, type_of_ages=type_of_ages, params=params)  # not the LIA, because this already has the age bounds

        temp = _delete_outside_time_frame(timeframe_tool, gdf=temp)  # clip to model time frame right away
        # define a new column which is the midpoint of the geometry, with points it is the same as geometry
        temp.loc[:, 'midpoint'] = temp.geometry.centroid

        # if confidence rating weights are 0, remove those ratings from scoring input (faster)
        confidence_rating_weights = params.get('confidence_rating_weights')
        zero_weight_ratings = {rating for rating, weight in confidence_rating_weights.items() if weight == 0}
        temp = temp[~temp['confid_ra'].isin(zero_weight_ratings)]

        if temp.geometry.geom_type.isin(['Point']).all():
            state.points = pd.concat([state.points, temp], ignore_index=True)
        else:
            state.polygons = pd.concat([state.polygons, temp], ignore_index=True)

    print(f"Loaded files: {loaded_files}.")

## internal helper function for data_loader.py

def _check_and_reproject(gdf, target_epsg=32632):
    """
    Check if the GeoDataFrame is in the target EPSG and reproject if necessary.
    """
    if gdf.crs.to_epsg() != target_epsg:
        gdf = gdf.to_crs(epsg=target_epsg)
        print(f"Reprojected GeoDataFrame to EPSG:{target_epsg}")
    else:
        print(f"GeoDataFrame is already in EPSG:{target_epsg}")
    """
    Assign a single ID, from either date ID or site ID
    """
        # Either identifier is valid; use ID internally for consistency.
    if 'ID' not in gdf.columns and 'date_ID' in gdf.columns:
        gdf = gdf.rename(columns={'date_ID': 'ID'})
    elif 'ID' not in gdf.columns and 'site_ID' in gdf.columns:
        gdf = gdf.rename(columns={'site_ID': 'ID'})

    """
    check the data, based on the names that are present in the columns.
    """
    # if the age column is called r_exp_age, we are sure that we are treating TCN ages, so when this is present, go to TCN samples
    if 'r_exp_age' in gdf.columns:
        type_of_ages='TCN'
        gdf = _check_ages_shp(gdf, type_of_ages) # they are always expected to be point data, so we can check for that
    # if there the age column is called recalc_max or e_age_max we are surely treating point C14 ages or event ages, so when this is present, go to C14 samples
    elif 'recal_max' in gdf.columns:
        type_of_ages='C14'
        gdf = _check_ages_shp(gdf, type_of_ages) # they are always expected to be point data, so we can check for that
    elif 'e_age_max' in gdf.columns:
        type_of_ages='event_age'
        gdf = _check_ages_shp(gdf, type_of_ages) # they are always expected to be point data, so we can check for that
    # the last option is, that the age is e_age with e_pos_err and e_neg_err, which is the case for event ages from TCN ages, which are any kind of polygon, lines or points, so we can check for that
    elif 'e_age' in gdf.columns and 'e_pos_err' in gdf.columns and 'e_neg_err' in gdf.columns:
        type_of_ages='event_age_landform'
        gdf = _check_landforms_shp(gdf, type_of_ages) # they can be any kind of geometry, so we can check for that
    else:
        # give a good error message, what was checked, what was not found and what is expected
        print("Error: The provided GeoDataFrame does not match any known age type.")
        print(f"Columns found: {gdf.columns.tolist()}")
        print("Expected columns for TCN: ['r_exp_age']")
        print("Expected columns for C14 (event ages): ['recal_max'] or ['e_age_max']")
        print("Expected columns for event ages (TCN): ['e_age'], ['e_pos_err'], ['e_neg_err']")
        print("Expected columns for event ages (landforms): ['e_age'], ['e_pos_err'], ['e_neg_err']")
        raise ValueError("The provided GeoDataFrame does not match any known age type. Please check the columns and ensure they match one of the expected formats.")

    gdf = _check_all_categories_right(gdf)

    return gdf

def _check_ages_shp(geo, type_of_ages):
    """
    Check if all needed columns are in shapefile
    """
    # save list of invalid geometries
    invalid_geometries = []    

    needed_columns_both_types = ['ID', 'confid_ra', 'pc_cat', 'pc_subcat', 'pc_time', 'geometry']
    needed_columns_TCN_ages = ['sample_yr', 'public_yr', 'r_exp_age', 'r_ext_err']
    needed_columns_C14_ages = ['recal_max', 'recal_min']
    needed_columns_event_ages = ['e_age_max', 'e_age_min']

        # FOR Synthetic case only, we have a different color (glength_po), which gives us the position of the the point along the glacer length. This is added if it is in geo
    if 'glength_po' in geo.columns:
        geo['glength_po'] = pd.to_numeric(geo['glength_po'], errors='coerce')
        needed_columns_both_types.append('glength_po') 

    for col in needed_columns_both_types:
        if col not in geo.columns:
            invalid_geometries.append((col, 'is missing'))

    if type_of_ages == 'TCN':
        needed_columns = needed_columns_both_types + needed_columns_TCN_ages
        for col in needed_columns:
            if col not in geo.columns:
                invalid_geometries.append((col, 'is missing'))
    elif type_of_ages == 'C14':
        needed_columns = needed_columns_both_types + needed_columns_C14_ages
        for col in needed_columns:
            if col not in geo.columns:
                invalid_geometries.append((col, 'is missing'))
    elif type_of_ages == 'event_age':
        needed_columns = needed_columns_both_types + needed_columns_event_ages
        for col in needed_columns:
            if col not in geo.columns:
                invalid_geometries.append((col, 'is missing'))

    # make sure to keep only the needed columns
    geo = geo[needed_columns].copy()

    for idx, geom in enumerate(geo['geometry']):
        if geom is None or geom.is_empty or geom.geom_type != 'Point':
            invalid_geometries.append((geo.loc[idx, 'ID'], geom.geom_type if geom else 'None or Empty point (no geometry)'))

    if invalid_geometries:
        raise AssertionError(f"Invalid ages found: {invalid_geometries}")
        
    else:
        print(f'Checking ages {type_of_ages} --> shapefile is correct.')

    # numberic columns are after the first 6 columns, so we convert to numerics
    for col in geo.columns[6:]:
        geo.loc[:, col] = pd.to_numeric(geo[col], errors='coerce')

    # for this set all values in a new column type_of_ages to the type_of_ages, so we can use it later for filtering
    geo.loc[:, 'type_of_ages'] = type_of_ages

    return geo

def _check_landforms_shp(geo, type_of_ages):
    """
    Check if all needed columns are in landforms shapefile, event ages should already be attributed in the shapefile with a different script or use a Database
    """
    # confid_ra could be named confid_no and consist of a text with high and medium and low in it.. we take the higest word available
            # if confid_no in column, rename it to confid_ra and take the first word (high, medium or low) for consistency with the other ages, if it exists
    if 'confid_no' in geo.columns:
        geo.rename(columns={'confid_no': 'confid_ra'}, inplace=True)
        geo['confid_ra'] = geo['confid_ra'].apply(lambda x: next((word for word in str(x).split() if word.lower() in ['high', 'medium', 'low']), str(x).split()[0] if isinstance(x, str) else x))

    # only mean_s_yr and mean_p_yr are needed for landforms, one of them is enough
    if 'mean_s_yr' not in geo.columns and 'mean_p_yr' not in geo.columns:
        raise ValueError("At least one of 'mean_s_yr' or 'mean_p_yr' must be present in the landforms shapefile.")

    needed_columns = ['ID','confid_ra','pc_cat','geometry', 'e_age', 'e_pos_err', 'e_neg_err']
    for col in needed_columns:
        if col not in geo.columns:
            raise ValueError(f'Column {col} is missing in landforms shapefile.')

    for geom in geo['geometry']:
        if geom.geom_type not in ['Point','Polygon', 'LineString','LineString Z', 'MultiLineString', 'MultiPolygon']:
            raise ValueError(f'Geometry type is not tested in this version of the comparison tool. Found: {geom.geom_type}.')

    # if pc_subcat and pc_time are not present, we can add them as empty columns, as they are not needed for landforms
    if 'pc_subcat' not in geo.columns:
        geo['pc_subcat'] = ''
    if 'pc_time' not in geo.columns:
        geo['pc_time'] = ''

    # numberics of number columns
    for col in ['e_age', 'e_pos_err', 'e_neg_err', 'mean_s_yr', 'mean_p_yr']:
        if col in geo.columns:
            geo.loc[:, col] = pd.to_numeric(geo[col], errors='coerce')

    # for this set all values in a new column type_of_ages to the type_of_ages, so we can use it later for filtering
    geo.loc[:, 'type_of_ages'] = type_of_ages

    print(f'Checking landforms {type_of_ages} --> shapefile is correct.')

    return geo
        
def _give_age_bounds(gdf, type_of_ages, params):
    """
    Add min_age and max_age columns to the GeoDataFrame based on existing age data.
    """
    min_ages = []
    max_ages = []

    year_format = params.get('year_format')  # Default to AD if not specified
    if year_format == '-b2k':
        year_of_present = 2000
    elif year_format == '-bp':
        year_of_present = 1950
    else:
        raise ValueError(f"Unknown year format: {year_format}. Supported formats are '-b2k' and '-bp'.")

    if type_of_ages == 'TCN':
        for i, item in gdf.iterrows():

            if item['pc_cat'] == 'bedrock exposure': # must be total bedrock exposure.. take the r_exp_age as total age of exposure in the processing
                min_ages.append(item['r_exp_age']-item['r_ext_err'])
                max_ages.append(item['r_exp_age']+item['r_ext_err']) # is actually not really the age, but total bedrock exposure, will be handled later like this

            else:
                min_ages.append(item['r_exp_age'] - item['r_ext_err'])
                max_ages.append(item['r_exp_age'] + item['r_ext_err'])

            # make BP out of age since sampling
            year_of_sampling = item['sample_yr'] if not pd.isna(item['sample_yr']) else item['public_yr']
            if pd.isna(year_of_sampling):
                year_of_sampling = 2024
            # change all min ages and max ages to years before present (present = 1950)
            min_ages[-1] = year_of_present - year_of_sampling + min_ages[-1]
            max_ages[-1] = year_of_present - year_of_sampling + max_ages[-1]

    elif type_of_ages == 'C14':
        # columns are directly min_ and max ages, 
        for i, item in gdf.iterrows():
            min_ages.append(item['recal_min'])
            max_ages.append(item['recal_max'])

            # ussually this is cal BP, we still change to the year, if it is BP, it is already fine..
            min_ages[-1] = (year_of_present-1950) + min_ages[-1]
            max_ages[-1] = (year_of_present-1950) + max_ages[-1]
    
    elif type_of_ages == 'event_age':
        for i, item in gdf.iterrows():

            min_ages.append(item['e_age_min'])
            max_ages.append(item['e_age_max'])

            # usually in BP, so if age formate is different, change
            min_ages[-1] = (year_of_present-1950) + min_ages[-1]
            max_ages[-1] = (year_of_present-1950) + max_ages[-1]
    
    elif type_of_ages == 'event_age_landform':
        # use e_age and e_pos_err and e_neg_err to calculate min and max ages
        for i, item in gdf.iterrows():
            min_ages.append(item['e_age'] - item['e_neg_err'])
            max_ages.append(item['e_age'] + item['e_pos_err'])

            # year of sampling
            # get the number in the column orig_ref, if there is a number, otherwise take 2000
            year_of_sampling = 2000
            
            # take sample year (mean_s_yr) if is nan, take the publication year (mean_p_yr) if is nan, otherwise take 2000
            if 'mean_s_yr' in gdf.columns and not pd.isna(item['mean_s_yr']):
                year_of_sampling = int(item['mean_s_yr'])
            elif 'mean_p_yr' in gdf.columns and not pd.isna(item['mean_p_yr']):
                year_of_sampling = int(item['mean_p_yr'])
            else:
                print(f"Warning: No sampling year or publication year available for {item['ID']}. Using default year of 2000 for age conversion to years before present.")

            # change all min ages and max ages to years before present (present = 1950)
            min_ages[-1] = year_of_present - year_of_sampling + min_ages[-1]
            max_ages[-1] = year_of_present - year_of_sampling + max_ages[-1]

    else:
        raise ValueError("type_of_ages not known. Use 'TCN', 'C14', 'event_age' or 'event_age_landform'.")

    # check if lengths are correct
    if len(min_ages) != len(gdf) or len(max_ages) != len(gdf):
        raise ValueError("Length of min_ages or max_ages does not match length of GeoDataFrame. Check the palcontext and paleo context time (pc_time) values.")
    gdf['min_age'] = min_ages
    gdf['max_age'] = max_ages

    return gdf

def _check_all_categories_right(gdf):
    """
    Check if all categories are right, for pc_cat, pc_subcat and pc_time
    """
    # check if pc_cat is in the right categories
    valid_pc_cat = ['ice free', 'ice cover', 'bedrock exposure', 'ice margin', 'ambiguous', '-']
    if not gdf['pc_cat'].isin(valid_pc_cat).all():
        invalid_categories = gdf.loc[~gdf['pc_cat'].isin(valid_pc_cat), 'pc_cat'].unique()
        raise ValueError(f"Invalid pc_cat categories found: {invalid_categories}. Valid categories are: {valid_pc_cat}")

    # check if pc_subcat is in the right categories
    valid_pc_subcat = ['-','','ice advance','ice retreat','ice retreat/readvance']
    if not gdf['pc_subcat'].isin(valid_pc_subcat).all():
        invalid_categories = gdf.loc[~gdf['pc_subcat'].isin(valid_pc_subcat), 'pc_subcat'].unique()
        raise ValueError(f"Invalid pc_subcat categories found: {invalid_categories}. Valid categories are: {valid_pc_subcat}")

    # check if pc_time is in the right categories
    valid_pc_time = ['', '-', 'long-term deglaciation', 'ice-free interval']
    if not gdf['pc_time'].isin(valid_pc_time).all():
        invalid_categories = gdf.loc[~gdf['pc_time'].isin(valid_pc_time), 'pc_time'].unique()
        raise ValueError(f"Invalid pc_time categories found: {invalid_categories}. Valid categories are: {valid_pc_time}")

    valid_confid_ra = ['high', 'medium', 'low', 'unqualified', 'unaccepted']
    if not gdf['confid_ra'].isin(valid_confid_ra).all():
        invalid_categories = gdf.loc[~gdf['confid_ra'].isin(valid_confid_ra), 'confid_ra'].unique()
        raise ValueError(f"Invalid confid_ra categories found: {invalid_categories}. Valid categories are: {valid_confid_ra}")

    return gdf

# delete all columns outside the given extent
def _delete_outside_extent(working_folder, params, extent, gdf):
    # load an anlyse mask, where dates should not be evaluated. That can be the ice mask file or any other shapefile...
    icemask_file = params.get('analyse_mask_file')
    if os.path.exists(icemask_file):
        print(f"Found analyse mask file {icemask_file}. Using it to filter the ages.")
        icemask = gpd.read_file(icemask_file)
        
        # Ensure both are in the same CRS
        icemask = icemask.to_crs(gdf.crs)
        # if icemask is inverted, we have to invert it here again to plot the things outside the polygon
        if params.get('ice_mask_inverted', True):
            # invert the icemask polygon to get the area outside the polygon
            from shapely.geometry import box
            from shapely.ops import unary_union

            # Create a bounding box that covers the entire area of interest
            bounding_box = box(extent[0], extent[2], extent[1], extent[3])

            # Invert the icemask polygon by subtracting it from the bounding box
            inverted_mask = bounding_box.difference(unary_union(icemask.geometry))
            icemask = gpd.GeoDataFrame(geometry=[inverted_mask], crs=icemask.crs)
        
        if 'geometry' in icemask.columns and icemask.geometry.geom_type.isin(['Polygon', 'MultiPolygon']).any():
            
            # For all geometries, keep only those that do NOT intersect the ice mask
            gdf = gpd.sjoin(gdf, icemask[['geometry']], how="left", predicate="intersects")
            gdf = gdf[gdf["index_right"].isna()].drop(columns="index_right")


    else:
        print(f"Warning: analyse mask file {icemask_file} not found. Proceeding")

    # Still delete all rows outside the given extent, just in case there are some left after the ice mask filtering, or if there is no ice mask
    gdf = gdf.cx[extent[0]:extent[1], extent[2]:extent[3]]
    
    return gdf

def _delete_outside_time_frame(time_frame, gdf):
    """
    Delete all rows in the GeoDataFrame that are outside the time frame defined by the state's t values.
    """
    # time frame that should be analysed, e.g., (min_time, max_time) in years
    time_frame = time_frame  # e.g., (min_time, max_time)

    gdf = gdf[(gdf['min_age'] >= time_frame[1]) & (gdf['max_age'] <= time_frame[0])]
    
    return gdf

def _delete_ambiguous_and_unqualified(gdf):
    """
    Delete all rows in the GeoDataFrame that have pc_cat as 'ambiguous' or confid_ra as 'unqualified'.
    """
    gdf = gdf[(gdf['pc_cat'] != 'ambiguous') & (gdf['confid_ra'] != 'unqualified') & (gdf['confid_ra'] != 'unaccepted')]

    # and - in these columns..
    gdf = gdf[(gdf['pc_cat'] != '-')]

    # check if gdf is empty after filtering, if so, raise an error
    if gdf.empty:
        raise ValueError("All rows have been filtered out due to ambiguous or unqualified categories. Please check the input data.")
    
    return gdf