""" The holy script for distance calculation.. 
This script is the main script for the distance calculation, 
"""

# imports
import os
import numpy as np
import pandas as pd
from shapely import Point

from GLAMODAT.core.distance_calculation_debug_plots import plot_checked_cells
from GLAMODAT.core.distance_calculation_debug_plots import plot_ice_thickness_through_time


def _frame_index(model_times, wanted_time, name, tolerance):
    """Index of the model frame closest to wanted_time (same time scale as model_times).

    Raises a clear error if no frame is within `tolerance` years, and warns if the closest frame is not exact.
    """
    index = int(np.argmin(np.abs(model_times - wanted_time)))
    offset = abs(model_times[index] - wanted_time)
    if offset > tolerance:
        raise ValueError(f"{name} = {wanted_time} has no model frame within {tolerance} years (closest frame: "
                         f"{model_times[index]}, model frames from {model_times.max()} to {model_times.min()}). "
                         f"Check {name}, output_saving_frequency and the time convention (year_format, "
                         f"model_year_ce_at_t0).")
    if offset > 0:
        print(f"Warning: {name} = {wanted_time} is not a model frame; the closest frame {model_times[index]} is used.")
    return index


def process_features(state, params):

    number_of_features = len(state.features_to_score)

    # find start index and end index for the time steps; start_time / end_time should be output frames, the closest
    # frame is accepted within half an output interval
    tolerance = 0.5 * state.output_saving_frequency
    start_index_model = _frame_index(state.t, state.start_time, "start_time", tolerance)
    end_index_model = _frame_index(state.t, state.end_time, "end_time", tolerance)

    times = state.t[start_index_model:end_index_model+1:int(state.analysis_frequency/state.output_saving_frequency)]

    # We need now to add a np.array with the actuall scores (over time), there are as many scores and time steps as there are available in the model
    state.distance_array = np.nan * np.ones((number_of_features, len(times), 3))

    # find indices of these categories
    counter = 0    

    # we go through every feature, start analysing when the time is at or just after the min_age. Then we calculate the distance at this time step.
    # later, if conditions change, for example the ice margin moves, we can update the distances, but we do not have to check when the ice thickness is anyways "better" than at the min_age.
    # "Better" means, for example, if it should stay ice free, it should stay ice free, if it is ice covered, it should stay ice covered.
    for index, row in state.features_to_score.iterrows():
        horizontals = np.full(len(times), np.nan)
        verticals = np.full(len(times), np.nan)

        print(f"Processing feature {counter+1} of {number_of_features} (index {index}).")
        counter += 1

        ti_comp = np.where(times <= row.min_age)[0][0]
        ti_model = np.where(state.t == times[ti_comp])[0][0]  # this is the index of the time step at or just after the min_age

            # cummulative exposure and cummulative ice cover can only be evaluated at the last time step, so we set ti_start_model to the last
        ti_model = end_index_model if row.pc_cat in ['bedrock exposure', 'ice cover'] else ti_model
        ti_comp = np.where(times <= state.t[ti_model])[0][0]  # also only update the last time step for this..

            # analyse it here right away
        horizontal, vertical, sign_lastice = _calculate_distance(state, ti_model, row)

        row['icecover'] = sign_lastice  # update icecover status in features_to_score dataframe

            # for ice margins we have to check once where the ice margin was at the moment when the boulder should have been deposited, after that we only have to check if the icefree status did not change
        if row.pc_cat in ['ice margin', 'ice free', 'rockfall deposit', 'moraine', 'rockglacier', 'peatbog', 'ice cover']:
                # if this feature is matching at this time step, we need later on to check if the ice free status is actually staying ice free
            coords = np.array(row.midpoint.coords[0])

            i, j = int(np.round((coords[0] - min(state.x)) / state.dx)), int(np.round((coords[1] - min(state.y)) / state.dx))
                # we need to check this feature at every time step later on
            ice_thickness_through_time = state.thk[ti_model:end_index_model+1, j, i]

                # we have to fill in all distances and would override it later if needed
            horizontals[ti_comp:] = horizontal
            verticals[ti_comp:] = vertical
                # ice cover is anyway only looked at at the end of the time period.. So that is ok? - we do not need to look at other time steps, because we only evaluate the distance at the last time step, because this is the only time step where we can be sure that the feature was actually ice covered, and we do not have to check if it was ice free before, because only the cummulative ice cover counts (since the last big glaciation, for example YD or LGM), depending on location.
            if row.pc_cat == 'ice cover':
                if np.all(ice_thickness_through_time > 0):
                #         # if it is always ice covered, we can just fill in the rest with the distance value
                    pass  # horizontals and verticals are already filled with zeros or the distance value
                else:
                    plot_ice_thickness_through_time(working_dir=state.working_folder, times=state.t[ti_model:end_index_model+1], ice_thickness_through_time=ice_thickness_through_time, id=row.ID, row_index=index, feature_type=row.pc_cat, year_format=params.get('year_format'))
                        # if it is not always ice covered, we have to check at which time step it becomes ice free and fill in the distances from there on
                    print(f"This feature {row['ID']} - {row['pc_cat']} is not always ice covered, but we anyways have therefore a mismatch at age {state.t[ti_model]} with a distance of {horizontal} m.")
                        # # for the score, we calculate the distance when there was the least ice
                        # least_ice_index = np.argmin(state.vol[ti_model:end_index_model+1]) + int(ti_model)

                        # horizontal, vertical, sign_lastice = calculate_distance(state, least_ice_index, row)
                        # # if no ice before and this distance is not worse than before, we keep the old distance
                        # if row['icecover'] == -1.0 and horizontal <= horizontals[0]:
                        #     horizontal = horizontals[0]
                        #     vertical = verticals[0]
                        # # fill up horizontals and verticals from here and further with the new distances
                        # horizontals[int((least_ice_index - ti_start_model)/step):] = [horizontal]*(len(horizontals) - int((least_ice_index - ti_start_model)/step))
                        # verticals[int((least_ice_index - ti_start_model)/step):] = [vertical]*(len(verticals) - int((least_ice_index - ti_start_model)/step))

            else:
                current_ice_thickness = state.thk[ti_model, j, i]
                    
                    # if there is a very special case, where we have an ice free date that is later ice covered, we only evaluate the distance at the min_age time
                if row.pc_cat == 'ice free' and row.pc_subcat == 'ice retreat/readvance' and np.any(ice_thickness_through_time > 0):
                        # if it is ice free at the min_age time, but later on becomes ice covered, we only evaluate the distance at the min_age time, because this is the only time step where we can be sure that the feature was actually ice free
                    pass  # horizontals and verticals are already filled with zeros or the distance value
                elif row.pc_cat == 'ice free' and row.pc_subcat == 'ice retreat/readvance' and np.any(ice_thickness_through_time == 0):
                    print(f"Warning: This feature {row['ID']} - {row['pc_cat']} has a retreat/readvance time perspective, but it is ice free at the min_age time and later is not ice covered anymore, so there is a to short ice extent later.. however, will not go into the objective evaluation.")

                else: # for all other cases, it should not be ice covered later on.
                        # if everything is zero, we can just fill in the rest with zeros
                    if np.all(ice_thickness_through_time == 0):
                        pass  # horizontals and verticals are already filled with zeros or the distance value

                    else:           
                        plot_ice_thickness_through_time(working_dir=state.working_folder, times=state.t[ti_model:end_index_model+1], ice_thickness_through_time=ice_thickness_through_time, id=row.ID, row_index=index, feature_type=row.pc_cat, year_format=params.get('year_format'))
                            
                        method = "look only twice per feature"   # like this, one feature is maximal looked at twice...                      
                        if method == "look at all time steps that have more ice": # this is the time consuming version, that was implemented first, that is why it is also hardcoded here.. you really need to look into the code if you want to have the full details
                            for time_frame in times[ti_comp+1:]:
                                future_ti_comp = np.where(times == time_frame)[0][0]
                                future_ti_model = np.where(state.t == time_frame)[0][0]
                                future_ice_thickness = state.thk[future_ti_model, j, i]
                                    # check if ice free status changed
                                if future_ice_thickness <= current_ice_thickness:
                                        # ice free status did not change, keep the same distances
                                    pass
                                else:
                                        # ice free status changed, recalculate distances
                                    horizontal, vertical, sign_lastice = _calculate_distance(state, future_ti_model, row)

                                        # if no ice before and this distance is not worse than before, we keep the old distance
                                    if row['icecover'] == -1.0 and horizontal <= horizontals[-1]:
                                        horizontal = horizontals[-1]
                                        vertical = verticals[-1]
                                        
                                        # row['icecover'] = sign_lastice  # update icecover status in features_to_score dataframe

                                        # fill up horizontals and verticals from here and further with the new distances
                                    horizontals[future_ti_comp+1:] = [horizontal]*(len(horizontals) - future_ti_comp - 1)
                                    verticals[future_ti_comp+1:] = [vertical]*(len(verticals) - future_ti_comp - 1)
                                    current_ice_thickness = future_ice_thickness
                        else:
                                # index of the most ice
                            most_ice_index = np.argmax(ice_thickness_through_time) + int(ti_model)
                            horizontal, vertical, sign_lastice = _calculate_distance(state, most_ice_index, row)
                                
                                # what comparison tool time is that? Here it could be not very exact, because we only save with the comparison tool resolution, not the model resolution...
                            ti_most_ice_comp = np.where(times <= state.t[most_ice_index])[0][0]

                                # fill up horiontals and verticals from here and further with the new distances
                            horizontals[ti_most_ice_comp:] = [horizontal]*(len(horizontals) - ti_most_ice_comp)
                            verticals[ti_most_ice_comp:] = [vertical]*(len(verticals) - ti_most_ice_comp)

                        # now we have the full list of horizontals and verticals from ti to end_index
                    horizontals = np.array(horizontals)
                    verticals = np.array(verticals)

        elif row.pc_cat in ['bedrock exposure']:
                # for bedrock exposure, we only evaluate the distance at the last time step, because this is the only time step where we can be sure that the feature was actually exposed, and we do not have to check 
                # if it was ice free before, because only the cummulative exposure counts (since the last big glaciation, for example YD or LGM), depending on location.
            horizontals[ti_comp:] = horizontal
            verticals[ti_comp:] = vertical
        else:
            raise ValueError(f"paleo context {row.pc_cat} not recognized.")
        
            # vectorised fill from ti to end_index
        state.distance_array[index, :, 0] = horizontals
        state.distance_array[index, :, 1] = verticals
        state.distance_array[index, :, 2] = times


def _calculate_distance(state, ti, row):
    """
    Calculate a distance to a fitting grid cell from the glacier model output.
    
    """
    # save current timestep
    lasticecover = state.lasticecover[ti]
    cumicefree = state.icefree_cummulative[ti]
    glacier_history = state.glacier_history
    thk = state.thk[ti]
    usurf = state.topg + thk
    current_t = state.t[ti]

    geometry = row['geometry']

    # check if geometry is point or polygon or multippolygon
    if geometry.geom_type == 'Point':
        # If it's a point, we can directly use the coordinates
        coords = np.array(geometry.coords[0])

        i, j = int(np.round((coords[0] - min(state.x)) / state.dx)), int(np.round((coords[1] - min(state.y)) / state.dx))

        return _distance_for_point(current_t, i, j, state, lasticecover, cumicefree, usurf, row, glacier_history) # early return for point geometries
    
    elif geometry.geom_type in ['Polygon', 'MultiPolygon']:
        # Generate points in the polygon
        points_to_test = _generate_points_in_polygon(geometry, state.dx)

    elif geometry.geom_type in ['MultiLineString', 'LineString']:
        # Generate points along the lines
        points_to_test = _generate_points_on_lines(geometry, state.dx)

    else:
        raise ValueError(f"Unsupported geometry type: {geometry.geom_type}")    

    # for small polygons or lines we might not generate any points, then we fallback to the centroid of that landform
    if not points_to_test:
        print(f"No points generated for geometry type {geometry.geom_type}.")
        points_to_test = [Point(geometry.centroid.x, geometry.centroid.y, 0)]  # Fallback to centroid if no points generated


    
    horizontal_distances = []
    vertical_distances = []

    for point in points_to_test:
        coords = np.array(point.coords[0])
        # if coords is 3d, take only the x and y
        if len(coords) == 3:
            coords = coords[:2]
        i, j = int(np.round((coords[0] - min(state.x)) / state.dx)), int(np.round((coords[1] - min(state.y)) / state.dx))
        # print(i, j, coords)
        # Calculate the score for this point
        horizontal_distance, vertical_distance, sign_last_ice = _distance_for_point(current_t, i, j, state, lasticecover,cumicefree , usurf, row, glacier_history)
        horizontal_distances.append(horizontal_distance)
        vertical_distances.append(vertical_distance)

        mean_horizontal_distance = np.nanmean(horizontal_distances)
        mean_vertical_distance = np.nanmean(vertical_distances)

    # id = row['ID']
    # # make a txt file with the id as name, then the current time  as the first line with the time and then all the horizontal distances (not the vertical ones for now)
    # with open(f'distances_{id}.txt', 'a') as f:
    #     zeile = [current_t] + ['horizontal'] + horizontal_distances + ['vertical:'] + vertical_distances
    #     f.write(','.join(map(str, zeile)) + '\n')

    return mean_horizontal_distance, mean_vertical_distance, np.sign(sign_last_ice) # return the mean horizontal and vertical distance, and the sign of the last ice (positive for ice cover, negative for ice free)

def _condition_met_for_palcontext(current_t, last_ice, cum_icefree, min_age, max_age, palcontext, pc_time, jumped_over_icemargin=False):
    if palcontext in ['ice margin', 'moraine']:
        return (min_age-current_t <= -last_ice) * ( -last_ice <= max_age-current_t) or jumped_over_icemargin
    elif palcontext == 'ice free':
        if pc_time == 'ice-free interval':
            return (max_age-current_t <= -last_ice) or (min_age-current_t <= abs(last_ice)) # min age, because inside the uncertainty we accept everything
        else:
            # This was before, now we only call icefree "moment" when we have the very specific time, namely current_t is min_age
                # if current_t < min_age:
                #     return True
            return (max_age-current_t <= -last_ice) or (min_age-current_t <= abs(last_ice)) # min age, because inside the uncertainty we accept everything

    elif palcontext == 'ice cover':
        return (min_age-current_t <= last_ice) and (last_ice > 0.0)
        # elif pc_time == 'moment':
        #     return (min_age <= last_ice) * (last_ice <= max_age)
    elif palcontext == 'bedrock exposure':
        return cum_icefree >= min_age
    elif palcontext in ['rockfall deposit', 'peatbog', 'rock glacier', 'other']:
        return (max_age-current_t <= -last_ice) or (min_age-current_t <= abs(last_ice)) # must be icefree since max age, but can be icefree since longer, because we do not have an upper bound on the age of formation of these landforms, only a lower bound, which is the max age
    else:
        print(f"Unknown palcontext: {palcontext}")
    return False

def _distance_for_point(current_t, i, j, state, lasticecover, cumicefree, usurf, row, glacier_history):
    # Find the closest point in the state

    # check if this cell agrees
    last_ice = lasticecover[j, i]
    cum_ice = cumicefree[j, i]
    elevation = usurf[j, i]

    min_age = row['min_age']
    max_age = row['max_age']

    palcontext = row['pc_cat']
    pc_time = row['pc_time']
    pc_subcat = row['pc_subcat']

    # differentiate the different palcontext types with different functions
    
    # check if last ice in inbetween the min and max age
    if _condition_met_for_palcontext(current_t, last_ice, cum_ice, min_age, max_age, palcontext, pc_time): # returns True or False for a single point
        return 0.0, 0.0, np.sign(last_ice) # full match

    else:
    # we look for a bigger section, if any of the ages match, so i-1 to i+1 and j-1 to j+1, and increase the 1 
        # define maximum horizontal and vertical distance
        max_search_distance = 5000  # maximum horizontal distance we search for a matching cell
        horizontal_distance = max_search_distance # penalty values
        vertical_distance = max_search_distance # penalty values

        id = row['ID'] if not pd.isna(row['ID']) else row['site_ID']

        # for some very specific cases, we want to find the icemargin, but this one is very sharp, so we would not hit it with the gradient search and therefore
        # need to find it with a switch of sign of last ice
        jumped_over_icemargin = False
        sign_of_last_ice = np.sign(last_ice)

        
        grid_cells_to_search = int(max_search_distance // state.dx)
        # extract pad (padding with max distance)
        last_ice_pad = lasticecover[max(j-grid_cells_to_search, 0):min(j+grid_cells_to_search+1, lasticecover.shape[0]),
                    max(i-grid_cells_to_search, 0):min(i+grid_cells_to_search+1, lasticecover.shape[1])]
        cum_ice_pad = cumicefree[max(j-grid_cells_to_search, 0):min(j+grid_cells_to_search+1, cumicefree.shape[0]),
                    max(i-grid_cells_to_search, 0):min(i+grid_cells_to_search+1, cumicefree.shape[1])]
        usurf_pad = usurf[max(j-grid_cells_to_search, 0):min(j+grid_cells_to_search+1, usurf.shape[0]),
                max(i-grid_cells_to_search, 0):min(i+grid_cells_to_search+1, usurf.shape[1])]
        glacier_history_pad = glacier_history[max(j-grid_cells_to_search, 0):min(j+grid_cells_to_search+1, glacier_history.shape[0]),
                    max(i-grid_cells_to_search, 0):min(i+grid_cells_to_search+1, glacier_history.shape[1])]
        x_pad = state.x[max(i-grid_cells_to_search, 0):min(i+grid_cells_to_search+1, state.x.shape[0])]
        y_pad = state.y[max(j-grid_cells_to_search, 0):min(j+grid_cells_to_search+1, state.y.shape[0])]

        starting_i = i - max(i - grid_cells_to_search, 0)
        starting_j = j - max(j - grid_cells_to_search, 0)
        assert last_ice == last_ice_pad[starting_j, starting_i], "Starting cell does not match."
        cell_j = starting_j
        cell_i = starting_i

        cells_checked = [( cell_j, cell_i )]

        # if we are looking for the ice margin and are outside the ice, we have to go towards the ice (higher values of last ice)
        if palcontext in ['ice margin', 'moraine'] and last_ice < current_t - min_age:
            search_for_higher_values = -1.0
        # if ice cover is not fullfilled, it means we have not enough ice, so we have to go towards the ice (higher values of last ice), otherwise we have too much ice, which means we have still a fit with the ice cover age
        elif palcontext == 'ice cover':
            search_for_higher_values = -1.0
        else:
            search_for_higher_values = 1.0

        # we look at the cells around the starting cell, in increasing distance
        for distance in range(1, grid_cells_to_search*2):

            # Recursive function to find the next cell to check
            new_cell_j, new_cell_i = _propose_next_cell(glacier_history_pad.copy(), cell_j, cell_i, cells_checked, search_for_higher_values)
            if new_cell_j is None or new_cell_i is None:
                print("Reached boundary of the search area or no more cells to check.")
                break

            cell_j, cell_i = new_cell_j, new_cell_i
            cells_checked.append((cell_j, cell_i))

            last_ice = last_ice_pad[cell_j, cell_i]
            # print(distance, last_ice)
            # check if we jumped over an icemargin
            if np.sign(last_ice) != sign_of_last_ice:
                jumped_over_icemargin = True
            if _condition_met_for_palcontext(current_t, last_ice, cum_ice_pad[cell_j, cell_i], min_age, max_age, palcontext, pc_time, jumped_over_icemargin):
                ii = cell_i - starting_i  # offset from center
                jj = cell_j - starting_j
                new_horizontal_distance = np.sqrt(ii**2 + jj**2) * state.dx
                new_vertical_distance = abs(usurf_pad[cell_j, cell_i] - elevation)

                plot_checked_cells(state.working_folder, last_ice_pad, cells_checked, state.dx, id, current_t, min_age, max_age, palcontext, pc_time, condition_met=True, distance=[new_horizontal_distance, new_vertical_distance])

                return new_horizontal_distance, new_vertical_distance, np.sign(last_ice)  # give back the distances found
            
        
        # if we reach here, no matching cell was found
        condition_met = False
        distance = [horizontal_distance, vertical_distance]

        # # save checked cells but the real coordinates, not the padded and not the indices
        # checked_cells_real_coords = [(state.x[cell_i], state.y[cell_j]) for cell_j, cell_i in cells_checked]
        # # save as txt
        # with open(f'{state.working_folder}/checked_cells/checked_cells_{id}_{current_t}.txt', 'w') as f:
        #     for cell in checked_cells_real_coords:
        #         f.write(f"{int(cell[0])}, {int(cell[1])}\n")
        
        plot_checked_cells(state.working_folder, last_ice_pad, cells_checked, state.dx, id, current_t, min_age, max_age, palcontext, pc_time, condition_met, distance)
        return horizontal_distance, vertical_distance, sign_of_last_ice

# get all cells around with 1 and look for the lowest value
def _propose_next_cell(pad, cell_j, cell_i, cells_checked, search_for_higher_values=1.0):
    """
    Propose the next cell to check based on the minimum value in the neighborhood.
    If the proposed cell is already checked, recursively propose a new one.
    """
    # if all are checked, return None
    
    if np.mean(pad[cell_j-1:cell_j+2, cell_i-1:cell_i+2]) == 100000 * search_for_higher_values:
        return None, None
    

    slice_2d = pad[cell_j-1:cell_j+2, cell_i-1:cell_i+2]* search_for_higher_values                    
    min_indices = np.unravel_index(np.argmin(slice_2d, axis=None), slice_2d.shape)

    di = min_indices[1] - 1
    dj = min_indices[0] - 1
    
    new_cell_j = cell_j + dj
    new_cell_i = cell_i + di

    # Avoid going over the boundary
    if new_cell_j < 2 or new_cell_j >= pad.shape[0]-1 or new_cell_i < 2 or new_cell_i >= pad.shape[1]-1:
        return None, None

    # If the cell is already checked, propose a new one
    if (new_cell_j, new_cell_i) in cells_checked:
        pad[new_cell_j, new_cell_i] = 100000 * search_for_higher_values # Set to a high value to avoid picking it again
        return _propose_next_cell(pad, cell_j, cell_i, cells_checked, search_for_higher_values=search_for_higher_values)

    return new_cell_j, new_cell_i

def _generate_points_in_polygon(polygon, grid_spacing):
    # Get the bounds of the polygon
    min_x, min_y, max_x, max_y = polygon.bounds

    # Generate grid points within the bounding box
    x_coords = np.arange(min_x, max_x, grid_spacing)
    y_coords = np.arange(min_y, max_y, grid_spacing)
    grid_points = [Point(x, y) for x in x_coords for y in y_coords]

    # Filter points that are inside the polygon
    points_in_polygon = [point for point in grid_points if polygon.contains(point)]

    # make sure we have not more than points in polygon
    points_in_polygon = _sample_for_largest_distance_points(points_in_polygon, num_points=10)

    return points_in_polygon

def _generate_points_on_lines(geometry, grid_spacing):
    points_on_lines = []

    if geometry.geom_type == 'LineString':
        geometries = [geometry]
    elif geometry.geom_type == 'MultiLineString':
        geometries = list(geometry.geoms)

    for line in geometries:
        length = line.length
        num_points = int(length / grid_spacing)
        for i in range(num_points + 1):
            point = line.interpolate(i * grid_spacing)
            points_on_lines.append(point)
    
    points_on_lines = _sample_for_largest_distance_points(points_on_lines, num_points=10)

    return points_on_lines

def _sample_for_largest_distance_points(points, num_points=10):
    # we sample the points furthest away from each other, these are the points with the highest distance to their nearest neighbor, we do this until we have num_points points left
    while len(points) > num_points:
        distances = np.array([[point.distance(other) for other in points] for point in points])
        np.fill_diagonal(distances, np.inf)  # Ignore self-distance
        nearest_distances = np.min(distances, axis=1)
        index_to_remove = np.argmin(nearest_distances)
        points.pop(index_to_remove)

    return points