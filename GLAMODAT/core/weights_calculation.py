""" Script part for the weighting calculations of the GLAMODAT tool"""

# imports
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

def scaling_weights(weights, factor=2.0):
    """
    Scale weights so that the minimum is always 1 and the maximum is at most `factor`.

    The interpretation is intentionally direct:
      - factor = 1.0 -> all weights are exactly 1.0
      - factor = 2.0 -> all weights lie between 1.0 and 2.0
      - factor = 10.0 -> all weights lie between 1.0 and 10.0

    We do this by linearly stretching the original range to [1, factor].
    If all values are identical, they remain all 1.0.
    """
    weights = np.asarray(weights, dtype=float)

    if weights.size == 0:
        return weights

    min_weight = np.nanmin(weights)
    max_weight = np.nanmax(weights)

    if np.isnan(min_weight) or np.isnan(max_weight):
        return np.full_like(weights, np.nan, dtype=float)

    if np.isclose(min_weight, max_weight):
        return np.ones_like(weights, dtype=float)

    factor = float(factor)
    if factor < 1.0:
        factor = 1.0

    # Map the original range [min_weight, max_weight] onto [1.0, factor].
    # This guarantees min_weight -> 1.0 and max_weight -> factor.
    weights_scaled = 1.0 + (weights - min_weight) / (max_weight - min_weight) * (factor - 1.0)

    return weights_scaled

def calculate_weights(state, params):
    """
    Calculate a spatially weights based on the distance to a neighboring point, plus with confidence rating and time density. This is for feature weights, not for the weights in horizontal and vertical distances.
    """

    # here all the weights are taken from the params file. there are multiple possible weights
    confidence_rating_weights = params.get('confidence_rating_weights', {'high': 1.0, 'medium': 1.0, 'low': 0.0}) # basically the weights for the confidence ratings
    
    density_weight = params.get('density_weight', 2.0) # weight for the density distance

    # 1. get a first list of the weights using the confidence rating.
    # Zero-confidence features should not contribute to the density estimate,
    # but they must still remain in the output with a final weight of zero.
    confid_weights = state.features_to_score['confid_ra'].map(confidence_rating_weights).to_numpy(dtype=float)
    valid_mask = confid_weights > 0

    # 2. get a second list with weights for distance and time, but only use features that should be considered
    times = (state.features_to_score.min_age + state.features_to_score.max_age) / 2.0
    points = np.array([[point.x, point.y] for point in state.features_to_score.midpoint], dtype=float)

    spatial_weights = np.zeros_like(confid_weights, dtype=float)
    temporal_weights = np.zeros_like(confid_weights, dtype=float)
    spatio_temporal_weights = np.zeros_like(confid_weights, dtype=float)

    if valid_mask.sum() < 2:
        print("Not enough valid points to calculate density weights.")
        spatio_temporal_weights[valid_mask] = 1.0  # Assign a default weight of 1.0 to valid points
    else:
        valid_points = points[valid_mask]
        valid_times = times[valid_mask]

        # for testing
        # uniform distributed ponts
        # valid_points = np.random.uniform(low=0, high=1000, size=(100, 2))

        # # regular grid points
        # x = np.arange(0, 100, 10)
        # y = np.arange(0, 100, 10)
        # xx, yy = np.meshgrid(x, y)
        # valid_points = np.vstack([xx.ravel(), yy.ravel()])
        
        # # delete the points in the medium
        # new_points = np.concatenate((valid_points[:, :35], valid_points[:, 38:45]), axis=1)
        # new_points = np.concatenate((new_points, valid_points[:, 45:]),  axis=1)

        # valid_points = new_points
        bandwidth = 0.1
        # Perform kernel density estimation on the valid subset only.
        kde = gaussian_kde(valid_points.T, bw_method=bandwidth)
        kde_time = gaussian_kde(valid_times, bw_method=bandwidth)

        # Calculate the density for each valid point
        spatial_densities = kde(valid_points.T)
        temporal_densities = kde_time(valid_times)

        # Calculate weights as the inverse of the density
        spatial_weights_valid = 1 / (spatial_densities + 1e-10)
        temporal_weights_valid = 1 / (temporal_densities + 1e-10)

        spatial_weights_valid /= np.nanmax(spatial_weights_valid)
        temporal_weights_valid /= np.nanmax(temporal_weights_valid)

        # now make sure that the max_weight is at most the denisity_weidght times the min_weight, so if density weight is 1, then all weights are between 1 and 1, if density weight is 2, then all weights are between 1 and 2 etc.
        spatio_temporal_weights_valid = scaling_weights(spatial_weights_valid * temporal_weights_valid, factor=density_weight)

        spatial_weights[valid_mask] = spatial_weights_valid
        temporal_weights[valid_mask] = temporal_weights_valid
        spatio_temporal_weights[valid_mask] = spatio_temporal_weights_valid

    tot_weights = confid_weights * spatio_temporal_weights
    tot_weights[~valid_mask] = 0.0 # probably redundant.. but does not hurt..

    # normalize to make the sum of the weights equal to 1 among the valid entries.
    weight_total = np.nansum(tot_weights)
    if weight_total > 0:
        tot_weights /= weight_total

    # plot weights just to see for debugging
    plot_mask = valid_mask
    fig, axes = plt.subplots(3, 1, figsize=(10, 15))
    ax = axes[0]
    sc = ax.scatter(points[plot_mask, 0], points[plot_mask, 1], c=spatial_weights[plot_mask], cmap='viridis', s=spatial_weights[plot_mask] * 10000, alpha=0.5)
    ax.set_title('Spatial Weights')

    # add colorbar
    plt.colorbar(sc, ax=ax, label='Weight')

    # second plot is time weights
    ax = axes[1]
    sc = ax.scatter(times[plot_mask], temporal_weights[plot_mask], c=temporal_weights[plot_mask], cmap='viridis', s=temporal_weights[plot_mask] * 10000, alpha=0.5)
    ax.set_title('Time Weights')

    # plot the total scores
    ax = axes[2]
    sc = ax.scatter(points[plot_mask, 0], points[plot_mask, 1], c=tot_weights[plot_mask], cmap='viridis', s=tot_weights[plot_mask] * 10000, alpha=0.5)
    ax.set_title('Total Weights')
    # set x and y axis equal
    ax.set_aspect('equal', 'box')
    # Add colorbar
    plt.colorbar(sc, ax=ax, label='Total Weight')
    plt.tight_layout()
    # Save the figure
    plt.savefig(f"{params['folder_with_simulations']}spatial_weights.svg", bbox_inches='tight')
    plt.close()

    # add total weights to the features_to_score dataframe, only where the quality rating is high
    state.features_to_score['tot_weights'] = tot_weights