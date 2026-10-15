# intermediate plots for debugging the distance calculation, quite important...

import os
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors
import cmcrameri.cm as cmc

def plot_checked_cells(workingdir, last_ice_pad, checked_cells, dx, Date_ID, current_t, min_age, max_age, palcontext, pc_time, condition_met, distance):
    # check if file already exists, then do not plot again

    # if os.path.exists(f'{workingdir}/checked_cells_{Date_ID}.png'):
    #     return
    
    custom_cmap = get_cmap_for_icecover()

    vmin = np.nanmin(last_ice_pad)
    vmax = np.nanmax(last_ice_pad)
    # depending on what is absolute values bigger, take this as vmax
    if abs(vmin) > abs(vmax):
        vmax = abs(vmin)
    else:
        vmin = -abs(vmax)

    fig, ax = plt.subplots(figsize=(8, 6))
    cax = ax.imshow(last_ice_pad, cmap=custom_cmap, origin='lower', vmin=vmin, vmax=vmax)

    # white contour line for last_ice_pad = 0
    contour = ax.contour(last_ice_pad, levels=[0], colors='white', linewidths=1, origin='lower')

    fig.colorbar(cax, ax=ax, label='Last Ice Cover (years)')
    path_x = [cell[1] for cell in checked_cells]
    path_y = [cell[0] for cell in checked_cells]
    ax.plot(path_x, path_y, color='red', marker='o', linestyle='-', linewidth=2, markersize=1, label='Path Taken')
    
    # plot start and end points
    ax.text(path_x[0], path_y[0], 'Start', color='white', fontsize=12, fontweight='bold')
    ax.text(path_x[-1], path_y[-1], 'End', color='white', fontsize=12, fontweight='bold')
    
    ax.set_title(f'Path of Cells for ID {Date_ID}\nTime: {current_t}, Age Range: [{min_age}, {max_age}], Palcontext: {palcontext}, Tperspect: {pc_time}, Matching condition found: {condition_met}\nHorizontal Distance: {np.round(distance[0], 0)} m, Vertical Distance: {np.round(distance[1], 0)} m')
    ax.set_xlabel('Grid Cell X')
    ax.set_ylabel('Grid Cell Y')
    ax.legend()

    # check if folder checked_cells exists, if not create it
    if not os.path.exists(f"{workingdir}/checked_cells"):
        os.makedirs(f"{workingdir}/checked_cells")

    plt.savefig(f'{workingdir}/checked_cells/checked_cells_{Date_ID}_{current_t}.png', bbox_inches='tight')
    plt.close()


def plot_ice_thickness_through_time(working_dir, times, ice_thickness_through_time, id, row_index, feature_type, year_format):
    import matplotlib.pyplot as plt

    # change x-axis time name depending on year_format (case-insensitive, as in data_loader.get_time_convention)
    year_format = str(year_format).strip().lower()
    if year_format == '-bp':
        x_label = 'Time (years BP (before 1950 CE))'
    elif year_format == '-b2k':
        x_label = 'Time (years b2k (before 2000 CE))'
    else:
        x_label = 'Time (years)'
        print(f"Unknown year_format: {year_format}. Using default x-axis label.")

    plt.figure(figsize=(10, 6))
    plt.plot(times, ice_thickness_through_time)
    # invert x axis
    plt.gca().invert_xaxis()
    plt.xlabel(x_label)
    plt.ylabel('Ice Thickness (m)')
    plt.title(f'This site ID {id} (type {feature_type}) has an ice thickness evolution that is not matching.')
    plt.grid()

    # make directory for icethickness plots if it does not exist
    if not os.path.exists(f"{working_dir}/ice_thickness_plots"):
        os.makedirs(f"{working_dir}/ice_thickness_plots")

    plt.savefig(f'{working_dir}/ice_thickness_plots/ice_thickness_{id}_row{row_index}.png')
    plt.close()

    # total score for gree labels
def get_cmap_for_icecover(n=256):
    """
    Return a ListedColormap suitable for ice-cover/deglacial-age plotting.
    Creates a diverging-like colormap using cmcrameri.lisbon_r with a white middle.
    """
    mid = n // 2
    cmap = mcolors.ListedColormap(np.zeros((n, 4)))
    lower_count = mid
    upper_count = n - mid - 1

    if lower_count > 0:
        cmap.colors[:lower_count] = cmc.lisbon_r(np.linspace(0.05, 0.5, lower_count))
    if upper_count > 0:
        cmap.colors[mid + 1:] = cmc.lisbon_r(np.linspace(0.5, 0.95, upper_count))

    cmap.colors[mid] = np.array([1.0, 1.0, 1.0, 1.0])  # white center
    return cmap

