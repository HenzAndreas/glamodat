"""Conversion of the evidence ages to min_age / max_age on the internal age scale (_give_age_bounds).

Internal scale: years before the present year of year_format (-b2k: 2000 CE, -bp: 1950 CE), positive into the past.
- TCN and event-age landforms: ages since sampling (or publication, if the sampling year is missing).
- 14C and event ages: (calibrated) years BP, i.e. before 1950.
"""

import math

import geopandas as gpd
import pytest
from shapely.geometry import Point

from GLAMODAT.io.data_loader import _give_age_bounds

B2K = {"year_format": "-b2k"}
BP = {"year_format": "-bp"}


def _gdf(**columns):
    n = len(next(iter(columns.values())))
    columns.setdefault("ID", [f"f{k}" for k in range(n)])
    columns.setdefault("pc_cat", ["ice free"] * n)
    return gpd.GeoDataFrame(columns, geometry=[Point(k, k) for k in range(n)], crs="EPSG:32632")


def _bounds(gdf):
    return list(zip(gdf["min_age"], gdf["max_age"]))


def test_tcn_sampling_year():
    """10000 +- 500 years before sampling in 2020 -> 2020 is 20 years after 2000 (b2k) / 70 after 1950 (BP)."""
    gdf = _gdf(r_exp_age=[10000.0], r_ext_err=[500.0], sample_yr=[2020.0], public_yr=[2023.0])
    assert _bounds(_give_age_bounds(gdf.copy(), "TCN", B2K)) == [(9480.0, 10480.0)]
    assert _bounds(_give_age_bounds(gdf.copy(), "TCN", BP)) == [(9430.0, 10430.0)]


def test_tcn_publication_year_if_no_sampling_year():
    gdf = _gdf(r_exp_age=[10000.0], r_ext_err=[500.0], sample_yr=[math.nan], public_yr=[2010.0])
    assert _bounds(_give_age_bounds(gdf, "TCN", B2K)) == [(9490.0, 10490.0)]


def test_tcn_error_if_no_sampling_and_no_publication_year():
    gdf = _gdf(r_exp_age=[10000.0], r_ext_err=[500.0], sample_yr=[math.nan], public_yr=[math.nan])
    with pytest.raises(ValueError, match="f0"):
        _give_age_bounds(gdf, "TCN", B2K)


def test_bedrock_exposure_uses_the_same_conversion():
    """Bedrock exposure: r_exp_age is the total exposure, converted the same way as the other TCN ages."""
    gdf = _gdf(r_exp_age=[8000.0], r_ext_err=[300.0], sample_yr=[2000.0], public_yr=[2005.0],
               pc_cat=["bedrock exposure"])
    assert _bounds(_give_age_bounds(gdf, "TCN", B2K)) == [(7700.0, 8300.0)]


@pytest.mark.parametrize("type_of_ages, columns", [
    ("C14", {"recal_min": [9000.0], "recal_max": [9500.0]}),
    ("event_age", {"e_age_min": [9000.0], "e_age_max": [9500.0]}),
])
def test_bp_ages(type_of_ages, columns):
    """14C and event ages are in years BP (before 1950): +50 years on the b2k scale, unchanged on the BP scale."""
    gdf = _gdf(**columns)
    assert _bounds(_give_age_bounds(gdf.copy(), type_of_ages, B2K)) == [(9050.0, 9550.0)]
    assert _bounds(_give_age_bounds(gdf.copy(), type_of_ages, BP)) == [(9000.0, 9500.0)]


def test_event_age_landform_sampling_and_publication_year():
    """Asymmetric errors (e_age - e_neg_err, e_age + e_pos_err); mean_s_yr, else mean_p_yr."""
    gdf = _gdf(e_age=[12000.0, 12000.0], e_neg_err=[300.0, 300.0], e_pos_err=[500.0, 500.0],
               mean_s_yr=[2010.0, math.nan], mean_p_yr=[2015.0, 2020.0])
    assert _bounds(_give_age_bounds(gdf, "event_age_landform", B2K)) == [(11690.0, 12490.0), (11680.0, 12480.0)]


def test_event_age_landform_error_if_no_year():
    gdf = _gdf(e_age=[12000.0], e_neg_err=[300.0], e_pos_err=[500.0], mean_s_yr=[math.nan], mean_p_yr=[math.nan])
    with pytest.raises(ValueError, match="f0"):
        _give_age_bounds(gdf, "event_age_landform", B2K)
