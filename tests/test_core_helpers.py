import numpy as np

from GLAMODAT.core.weights_calculation import scaling_weights
from archive.scoring_utils import score_based_on_distance


def test_scaling_weights_maps_range_to_requested_factor():
    scaled = scaling_weights([2.0, 4.0, 6.0], factor=3.0)

    np.testing.assert_allclose(scaled, [1.0, 2.0, 3.0])


def test_scaling_weights_returns_ones_for_constant_values():
    scaled = scaling_weights([5.0, 5.0, 5.0], factor=10.0)

    np.testing.assert_allclose(scaled, [1.0, 1.0, 1.0])


def test_score_decreases_with_distance():
    scores = [score_based_on_distance(distance) for distance in (0.0, 500.0, 1000.0)]

    assert scores[0] == 1.0
    assert scores[0] > scores[1] > scores[2] > 0.0
