""" Created in February 2026 taking over the scripts from comparison_report_utils but making it so general, that we can use it outside of the comparison tool"""
""" Andreas Henz, February 2026"""
""" WARNING: This script is not actively maintained, you can alsways use --no_plot to skip the plotting, if there are errors, many plots are very specific
to the application used for the original comparison tool paper... this can help you get inspiration. All data is saved before the plotting, so you can use the saved data to make your own plots."""

# basic imports
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import cmcrameri.cm as cmc
import matplotlib.colors as mcolors

def plot_individual_features_over_time(savefolder, distances, features, evaluation_timeframe, time_reference = 'b2k'):
    # height of figure is dependent on the amount of samples

    height = max(1, len(features) )
    # what about all the LIA position ages??
    from matplotlib.collections import LineCollection
    fig, ax = plt.subplots(figsize=(6.6, height/5))
    # plot the scores for each landform type
    plot_at = 0
    for i, row in features.iterrows():
        # following the current code in September 2026, adaptions possible for the future..
        if row.type_of_ages in ['TCN', 'lia_outline']:
            error_bar = [int(row['min_age']), int(row['max_age'])]
            mean_age = int((row['min_age'] + row['max_age']) / 2) # !! DO not take the recalc age, since this is not in BP
        elif row.type_of_ages in ['C14']:
            error_bar = [int(row['recal_min']), int(row['recal_max'])]
            mean_age = int((row['recal_max'] + row['recal_min']) / 2)
        elif row.type_of_ages in ['event_age']:
            error_bar = [int(row['e_age_min']), int(row['e_age_max'])]
            mean_age = int((row['e_age_max'] + row['e_age_min']) / 2)
        # landforms included now:
        elif row.type_of_ages in ['event_age_landform']:
            sample_year_or_publication_year = int(row['mean_s_yr'] if not pd.isna(row['mean_s_yr']) and row['mean_s_yr'] != '-' else row['mean_p_yr'])
            if time_reference == 'b2k':
                mean_age = int(row['e_age']) - (sample_year_or_publication_year - 2000) # !! make it b2k here.. because it is not BP so far
            else:
                mean_age = int(row['e_age']) - (sample_year_or_publication_year - 1950) # !! make it BP here.. because it is not BP so far
            error_bar = [mean_age - int(row['e_neg_err']), mean_age + int(row['e_pos_err'])]
        elif row.type_of_ages in ['14C_event_age']:
            error_bar = [int(row['e_age_max']), int(row['e_age_min'])]
            mean_age = int((row['e_age_max'] + row['e_age_min']) / 2)

        else:
            print(f"Unknown type {row.type_of_ages} for row {i}, skipping error bar plotting.")
            # AssertionError(f"Unknown type {row.type_of_ages} for row {i}, skipping error bar plotting.")

        # print(i, row['ID'], row['pc_cat'])

        # Assuming distances[i, :, 0] is your normalized score for each x

        norm_distances = np.sqrt(distances[i, :, 1]**2 + distances[i, :, 2]**2)  # shape: (n_x,)
        max_distance = 18000.0
        norm_distances = np.clip((1 - np.exp(-norm_distances / 2000)) / (1 - np.exp(-max_distance / 2000)), 0, 1)
        colors = cmc.bam_r(norm_distances)        # shape: (n_x, 4) (RGBA)
        widths = 6.0 - 4.0 * norm_distances           # shape: (n_x,)
        # print(i, "index for this landform")

        # x and y for each point
        x = distances[i, :, 0]             # shape: (n_x,)
        y = np.repeat(plot_at, len(x))                   # shape: (n_x,)

        # Create points array: (n_x, 2)
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        # Create segments: (n_x-1, 2, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        # Use all but the last color/width for the segments
        lc = LineCollection(segments, colors=colors[:], linewidths=widths[:])
        ax.add_collection(lc)
        # name is ID if not nan, otherwise site_ID (for event ages)
        name = row['ID']
        ax.text(error_bar[1]+200 ,plot_at, f"{name} - {row['pc_cat']}", fontsize=8, color='black',
                verticalalignment='center', horizontalalignment='left')
        
        # add an point with error bar for the time of min and max age and the point in the middle
        ax.errorbar(x=mean_age, y=plot_at, 
                    xerr=[[ np.abs(mean_age - error_bar[0]) ], [ np.abs(error_bar[1] - mean_age ) ] ],
                    fmt='o', color='black', ecolor='black', elinewidth=1.0, capsize=3)
        
        # add final score text to the right
        h_text = int(np.round(distances[i, -1, 1]))
        v_text = int(np.round(distances[i, -1, 2]))
        ax.text(x[-1]-500, plot_at, f"$\\leftrightarrow${h_text} $\\updownarrow${v_text} m", fontsize=8, color='black',
                verticalalignment='center', horizontalalignment='right')

        # add a fat point at the end with the color of the last score
        ax.scatter(x[-1], y[-1], color=colors[-1], s=40, edgecolors='none')

        plot_at += 1

        # continue

    # no y ticks
    ax.set_yticks([])
    ax.set_yticklabels([])
    if evaluation_timeframe is not None:
        ax.set_xlim(evaluation_timeframe[1], evaluation_timeframe[0]-4000)

    # we need to set a colorbar for the scores
    # sm = plt.cm.ScalarMappable(cmap=cmc.bam_r, norm=mcolors.Normalize(vmin=0, vmax=max_distance))
    # cbar = plt.colorbar(sm, ax=ax, orientation='vertical', fraction=0.02, pad=0.04)
    # cbar.set_label('Distance (m)', rotation=270, labelpad=10)
        
    ax.set_xlabel('Time')
    ax.set_ylabel('Individual datings')
    # make y label on the right side
    ax.yaxis.set_label_position("left")
    # x ticks go from evaluation_timeframe[1] to evaluation_timeframe[0] with steps of 1000 years
    if evaluation_timeframe is not None:
        ax.set_xticks(np.arange(evaluation_timeframe[0], evaluation_timeframe[1]+1, 2000))
        ax.set_xticklabels([f"{int(x)}" for x in ax.get_xticks()])
    # invert x axis
    ax.invert_xaxis()

    # no axis on top and left
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # logarithmic colorbar showing effective distance
    bar_ax = ax.inset_axes([0.86, 0.55, 0.08, 0.35])
    max_distance = 18000.0
    sm = plt.cm.ScalarMappable(cmap=cmc.bam_r, norm=mcolors.LogNorm(vmin=1.0, vmax=max_distance))
    sm.set_array([])
    cbar = plt.colorbar(sm, cax=bar_ax, orientation='vertical')
    cbar.set_label('Effective distance (m)', fontsize=8, rotation=270, labelpad=10)
    cbar.set_ticks([1, 100, 250, 500, 1000, 2000, 4000, 8000, 16000])
    cbar.set_ticklabels(['0 m', '100 m', '250 m', '500 m', '1000 m', '2000 m', '4000 m', '8000 m', '16000 m'])
    cbar.ax.tick_params(labelsize=8)
    # hide black boundaries of the colorbar
    cbar.outline.set_visible(False)

    # taper the visible colorbar so it is narrower at the top than at the  (from Microsoft Copilot, see)
    taper = plt.Polygon(
        [(0.0, 0.0), (1.0, 0.0), (0.60, 1.0), (0.40, 1.0)],
        closed=True,
        transform=bar_ax.transAxes,
        facecolor='none',
        edgecolor='black'
    )
    bar_ax.add_patch(taper)
    if cbar.solids is not None:
        cbar.solids.set_clip_path(taper)

    plt.savefig(f"{savefolder}/distances_over_time_individual_high-medium.svg", bbox_inches='tight', dpi=600)
    plt.close(fig)

def plot_combined_distances_over_time(folderpath, distances, features, evaluation_timeframe, time_label='years b2k'):
    # dynamically build index groups from available confidence and type values
    all_index = features.index.to_numpy()

    indices_to_plot = {'all': all_index}
    plot_kwargs = {'all': {'color': 'black', 'linewidth': 1.0, 'label': 'All'}}

    # confid_ra groups
    if 'confid_ra' in features.columns:
        confid_vals = [v for v in features['confid_ra'].dropna().unique()]
        # mapping for familiar names to nicer labels/colors
        confid_map = {
            'high': ('green', 'High Quality'),
            'medium': ('orange', 'Medium Quality'),
            'low': ('red', 'Low Quality')
        }
        for val in confid_vals:
            key = str(val)
            idx = features[features['confid_ra'] == val].index.to_numpy()
            indices_to_plot[key] = idx
            color, label = confid_map.get(val, (None, None))
            if color is None:
                color = None  # let matplotlib choose
                label = f"Confid: {val}"
            plot_kwargs[key] = {'color': color, 'linewidth': 1.0, 'label': label}

        # special combined high+medium weighted if both exist
        if 'high' in confid_vals and 'medium' in confid_vals:
            h_idx = indices_to_plot.get('high', np.array([], dtype=int))
            m_idx = indices_to_plot.get('medium', np.array([], dtype=int))
            weighted_index = np.concatenate((h_idx, m_idx))
            indices_to_plot['high-medium-weighted'] = weighted_index
            plot_kwargs['high-medium-weighted'] = {'color': 'darkgreen', 'linewidth': 2.0, 'linestyle': '--', 'label': 'High & Medium Quality (Weighted)', 'zorder': 10}

    # type groups
    if 'type' in features.columns:
        type_vals = [v for v in features['type'].dropna().unique()]
        type_map = {
            'TCN': ('blue', 'TCN'),
            'c14': ('lightgreen', 'C14'),
            'landform': ('gray', 'Landforms'),
            'TCN_event_age': ('cyan', 'TCN Event'),
            '14C_event_age': ('lightblue', '14C Event'),
            'lia_outline': ('purple', 'LIA Outlines')

        }
        for val in type_vals:
            key = str(val)
            idx = features[features['type'] == val].index.to_numpy()
            indices_to_plot[key] = idx
            color, label = type_map.get(val, (None, None))
            if color is None:
                color = None
                label = f"Type: {val}"
            plot_kwargs[key] = {'color': color, 'linewidth': 1.0, 'linestyle': '--', 'label': label}
    
    # print final meassage for all the distances
    print("Plotting combined scores over time for different landform types...")
    print("")

    # make a figure for each landform type
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.6, 10), sharex=True)
    # plot the scores for each landform type
    for landform_type, indices in indices_to_plot.items():
        # get the distances for the landform type
        tot_distances = np.sqrt(distances[indices, :, 1]**2 + distances[indices, :, 2]**2)
        num_landforms = np.sum(~np.isnan(tot_distances), axis=0)

        time = np.nanmean(distances[indices, :, 0], axis=0)

        if landform_type == 'high-medium-weighted':
            # we have to calculate the weighted score here
            spatial_weights = features.loc[indices, 'tot_weights'].values
            # Only consider weights where scores are not nan at each time step
            valid_mask = ~np.isnan(tot_distances)
            weighted_scores_sum = np.nansum(tot_distances * spatial_weights[:, None] * valid_mask, axis=0)
            weights_sum = np.nansum(spatial_weights[:, None] * valid_mask, axis=0)
            tot_score = np.divide(weighted_scores_sum, weights_sum, out=np.zeros_like(weighted_scores_sum), where=weights_sum != 0)
            print(f"Weighted medium to high Score: {np.nanmean(tot_score):.2f} (over {np.sum(~np.isnan(tot_distances), axis=0).max()} landforms at last time step)")

        else:
            tot_score = np.nanmean(tot_distances, axis=0, where=~np.isnan(tot_distances))  # Calculate mean scores over all landforms of this type
        # plot the scores using keyword arguments
        ax1.plot(time, tot_score, **plot_kwargs[landform_type])
        
        # number of non-nans to see how many landforms are contributing to the score
        num_landforms = np.sum(~np.isnan(tot_distances), axis=0)
        ax2.plot(time, num_landforms, **plot_kwargs[landform_type])

        print(f"{landform_type.capitalize()}: {np.nanmean(tot_score):.2f} (over {num_landforms.max()} landforms at last time step)")

    # give labels to axes
    ax1.set_ylabel('Distance (m)')
    ax2.set_ylabel('Number of Landforms')
    # time_label from the time convention of the run (years BP or years b2k)
    ax2.set_xlabel(f'Time ({time_label})')

    ax1.set_xlim(evaluation_timeframe[1], evaluation_timeframe[0])
    ax2.set_xlim(evaluation_timeframe[1], evaluation_timeframe[0])
    # make a grey line at 0 in both plots (distance and number of landforms)
    ax1.axhline(0, color='gray', linestyle='-', linewidth=0.5)
    ax2.axhline(0, color='gray', linestyle='-', linewidth=0.5)
    # # invert x axis
    # ax1.invert_xaxis()
    # ax2.invert_xaxis()

    # use plot kwargs to set the legend
    ax1.legend(loc='upper left', fontsize=10)
    ax2.legend(loc='upper left', fontsize=10)

    # save figure
    plt.savefig(f"{folderpath}/distances_over_time.svg", bbox_inches='tight', dpi=300)
    plt.close(fig)

def plot_last_frame_with_icecover_over_time(folderpath, start_time, end_time, params):

    from archive.comparison_tool_plot_glacier_history_maps import plot_glacier_history_maps

    # only the last one, which means the end_time
    # start_time = end_time + 100.0 # we take a 100 year window for the last frame, so we can see the ice cover at the end of the simulation
    plot_glacier_history_maps(folderpath, start_time, end_time, 100.0, params) # only one time frame here.. can be changed, but you need to know what you are doing, because this map plots are long to generate.
 

def plot_forcing(folderpath, evaluation_timeframe):

    time, summertemp, annualtemp, ela, precip = load_output_ts_file(folderpath)

    if summertemp is None or annualtemp is None or ela is None or precip is None:
        print("One or more forcing variables are missing in the output_ts.nc file. Skipping forcing plot.")
        return

    fig, ax = plt.subplots(3, 1, figsize=(6.6, 10.0), sharex=True)
    # plot the temperature forcing and precipitation forcing in one figure state.tas for temperature and state.pr for precipitation
    ax[0].plot(time, summertemp, color='red', label='Summer Temperature (°C)')
    # add annual temperature as a dashed line
    # ax[0].plot(time, annualtemp, color='red', linestyle='--', label='Annual Temperature (°C)')
    ax[0].set_ylabel('Temperature (°C) at 1000 m a.s.l.')
    ax[0].legend(loc='upper left')
    # set y axis that temperature curve is a bit higher than precipitation curve
    ax[0].set_ylim(np.nanmin(summertemp) - 5, np.nanmax(summertemp) +1)
    ax[0].grid(True, axis='x', linestyle='--', linewidth=0.5, alpha=0.5)
    
    # left y axis for precipitation
    ax_2 = ax[0].twinx()
    ax_2.set_ylabel('Precipitation (mm/year)')
    ax_2.plot(time, precip, color='blue', label='Precipitation (mm/year)')
    # set ax limits that precipitation curve is a bit lower than temperature curve
    ax_2.set_ylim(np.nanmin(precip), np.nanmax(precip) + 200)
    ax_2.legend(loc='upper right')

    ax[1].plot(time, ela, color='green', label='ELA (m a.s.l.)', linestyle='-')
    ax[1].set_xlabel('Years BP')
    ax[1].set_ylabel('ELA (m a.s.l.)')
    ax[1].legend(loc='upper left')
    # add a vertical grid
    ax[1].grid(True, axis='x', linestyle='--', linewidth=0.5 , alpha=0.5)

    # make an A and B label for the two subplots
    ax[0].text(-0.1, 1.05, '(a)', transform=ax[0].transAxes, fontsize=16, va='top', ha='right')
    ax[1].text(-0.1, 1.05, '(b)', transform=ax[1].transAxes, fontsize=16, va='top', ha='right')
    ax[2].text(-0.1, 1.05, '(c)', transform=ax[2].transAxes, fontsize=16, va='top', ha='right')

    # make a third subplot with annual temperature and summer temperture, in two different axis
    ax_3 = ax[2].twinx()
    ax[2].plot(time, annualtemp, color='red', label='Annual Temperature (°C)', linestyle='--')
    ax[2].set_xlabel('Years BP')
    ax[2].set_ylabel('Annual Temperature (°C) at 1000 m a.s.l.')
    ax[2].legend(loc='upper left')
    # add a vertical grid
    ax[2].grid(True, axis='x', linestyle='--', linewidth=0.5 , alpha=0.5)

    ax_3.plot(time, summertemp, color='red', label='Summer Temperature (°C)', linestyle='-')
    ax_3.set_ylabel('Summer Temperature (°C) at 1000 m a.s.l.')
    ax_3.legend(loc='upper right')

    # ax_4 = ax[1].twinx()
    # # add glacial area on the right y axis
    # total_area_region = (state.x.max() - state.x.min()) * (state.y.max() - state.y.min()) / 1e6  # Convert to km²
    # area_relative = (state.area / total_area_region) * 100  # Normalize to percentage
    # ax_4.set_ylabel('Glacial Area (%)')
    # ax_4.set_ylim(-2, 102)
    # label = 'Glacial Area (%) of Region'
    # ax_4.set_ylim(0,101)  # Set limits to show percentage
    # if False:
        # normalize to LIA percentage
        # lia_fraction = 0.263 # hard coded for Meiental region
        # print("pay attention, for this second part of the plot, the lia fraction is hard-coded for the region of analysis")
        # area_relative = (area_relative / lia_fraction)   # Normalize to LIA percentage
        # ax_4.set_ylabel('Glacial Area (1 = LIA area)')
        # ax_4.set_ylim(0, 300)  # Set limits to show percentage
        # label = 'Glacial Area % (100 = LIA area)'
    
    # ax_4.plot(state.t, area_relative, color='purple', label=label)

    # invert all x axis
    ax[0].invert_xaxis()
    ax[1].invert_xaxis()
    ax[2].invert_xaxis()
    ax_3.invert_xaxis()
    ax_2.invert_xaxis()
    # ax_4.invert_xaxis()

    # set all x lims  to starting time
    ax[0].set_xlim(evaluation_timeframe[1], evaluation_timeframe[0])
    ax[1].set_xlim(evaluation_timeframe[1], evaluation_timeframe[0])
    ax[2].set_xlim(evaluation_timeframe[1], evaluation_timeframe[0])
    ax_2.set_xlim(evaluation_timeframe[1], evaluation_timeframe[0])
    ax_3.set_xlim(evaluation_timeframe[1], evaluation_timeframe[0])
    # ax_4.set_xlim(state.start_time_bp, state.end_time)
    
    # ax_4.legend(loc='upper right')
    # ax_4.invert_yaxis()  # Invert y-axis for glacial area

    # save plot
    plt.savefig(f"{folderpath}/forcing_plot.svg", bbox_inches='tight')

def plot_all_landforms_with_ages(state, background_topography=False):
    import matplotlib.pyplot as plt
    import numpy as np
    from shapely.plotting import patch_from_polygon
    from matplotlib.patches import Polygon as MplPolygon

    fig, ax = plt.subplots(figsize=(20, 12.2))
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    
    # give a faint topography background in black-white
    ax.imshow(state.topg, cmap='gray', alpha=0.5, extent=[min(state.x), max(state.x), min(state.y), max(state.y)], origin='lower')

    # Normalize the mean_age column for the color map
    norm = mcolors.Normalize(vmin=state.polygons['age_mean'].min(), vmax=state.polygons['age_mean'].max())
    cmap = cm.viridis


    # for variable in params.daco_AlpICE_data:
    for landform in state.polygons['geometry'].unique(): 
            
        # plot the landforms, depending on the type (polygon or point)
        if state.polygons[state.polygons['geometry'] == landform].iloc[0]['geometry'].geom_type in ['Polygon', 'MultiPolygon']:
            landforms = state.polygons[state.polygons['geometry'] == landform]
            landforms.plot(
            ax=ax,
            linewidth=5.0,
            alpha=0.9,
            color=landforms['age_mean'].apply(
            lambda x: cmap(norm(x)) if not pd.isna(x) else 'lightgray'
            )
            )
            
            # label the landforms with the age and the 2sigma
            for i, row in landforms.iterrows():
                if not pd.isna(row['age_mean']):
                    ax.text(row['geometry'].centroid.x, row['geometry'].centroid.y, f"{row['ID']} \n {row['age_mean']:.0f} (+ {row['age_q16']:.0f} - {row['age_q84']:.0f})", fontsize=10)
                
        elif state.polygons[state.polygons['geometry'] == landform].iloc[0]['geometry'].geom_type in ['LineString', 'MultiLineString']:
            landforms = state.polygons[state.polygons['geometry'] == landform]
            landforms.plot(
            ax=ax,
            linewidth=5.0,
            alpha=0.9,
            color=landforms['age_mean'].apply(
            lambda x: cmap(norm(x)) if not pd.isna(x) else 'lightgray'
            )
            )
            
            # label the landforms with the age and the 2sigma
            for i, row in landforms.iterrows():
                if not pd.isna(row['age_mean']):
                    ax.text(row['geometry'].centroid.x, row['geometry'].centroid.y, f"{row['ID']} \n {row['age_mean']:.0f} (+ {row['age_q16']:.0f} - {row['age_q84']:.0f})", fontsize=10)
            
        elif state.polygons[state.polygons['geometry'] == landform].iloc[0]['geometry'].geom_type == 'Point':
            if 'r_exp_age' not in landforms.columns:
                landforms['r_exp_age'] = (landforms['max_age']-landforms['min_age'])/2
                landforms['r_ext_err'] = np.abs(landforms['r_exp_age']-landforms['min_age'])

            landforms.plot(
            ax=ax,
            color=landforms['r_exp_age'].apply(lambda x: cmap(norm(x))),
            markersize=70,  # Bigger marker size
            marker='*',
            edgecolor='black',
            linewidth=0.5  # Thinner edge line width
            )
            
            # add the dates for the ages as text, but in a different color
            for i, row in landforms.iterrows():
                ax.text(row['geometry'].x, row['geometry'].y, f"{row['ID']} \n {row['r_exp_age']:.0f} ± {row['r_ext_err']}", fontsize=10, color='red')
                
    # add the colorbar for the ages
    cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax)
    cbar.set_label('Mean Age (years)', rotation=270, labelpad=15)
    cbar.ax.text(1.5, 0.5, f"min age = {int(state.polygons['age_mean'].min())}\nmax age = {int(state.polygons['age_mean'].max())}", rotation=0, ha='center', va='center', fontsize=12)
                
    # set axes equal
    ax.set_aspect('equal', 'box')
    
    # add an easy scale bar, basically showing two grid cells length at the bottom
    # Add a scale bar in the lower-left corner of the actual coordinates
    x_min, y_min = min(state.x), min(state.y)
    length = 10 * state.dx
    ax.plot([x_min + state.dx, x_min + length + state.dx], [y_min + state.dx, y_min + state.dx], color='black', linewidth=5)
    ax.text(x_min + state.dx, y_min + state.dx, f'{length:.0f} m', fontsize=10, ha='left', va='bottom')

    # ax.text(1, 0.5, f'{length} m', fontsize=15, ha='center', va='center')
    # add a title
    
    # save figure
    plt.savefig('loaded_landforms_with_ages.png')
    
    # close and delete the figure
    plt.close()
    # delete the plot
    del fig, ax

# !!!!!!!!! needs update because it has still the state variable.. !!!!!!!!!!!!!!!!!!!
def plot_icemargins_with_landforms(state, save_fig=True, show_fig=False):
    # here we plot the ice marings from the model, together with the landforms on top and also the datings that are in the category ice margin
    fig, ax = plt.subplots(figsize=(10, 6.6))
    # plot the topgraphy as background
    ax.imshow(state.topg, cmap='gray', extent=[state.x.min(), state.x.max(), state.y.min(), state.y.max()], origin='lower')
    # plot the ice margins at last time step
    time_index = -1  # last time step
    icemargin = state.icemargin[time_index]
    icemargin = np.where(icemargin > 1, icemargin, np.nan)  # set zeros to nan for better plotting

    im = ax.imshow(icemargin, cmap=cmc.buda, alpha=0.7, extent=[state.x.min(), state.x.max(), state.y.min(), state.y.max()], 
                   origin='lower',
                   vmin=0, vmax=200)

    cbar = plt.colorbar(im, ax=ax, orientation='vertical', fraction=0.02, pad=0.04)
    cbar.set_label('Ice Margin Residence Time (years)', rotation=270, labelpad=10)

    # plot the landforms that are of type ice margin
    ice_margin_landforms = state.features_to_score[state.features_to_score['pc_cat'] == 'icemargin']
    ax.scatter(ice_margin_landforms['midpoint'].apply(lambda p: p.x), ice_margin_landforms['midpoint'].apply(lambda p: p.y), color='blue', s=50, edgecolors='black', label='Ice Margin Landforms')

    # save figure
    if save_fig:
        plt.savefig(f"{state.working_folder}/icemargins_with_landforms.svg", bbox_inches='tight')

