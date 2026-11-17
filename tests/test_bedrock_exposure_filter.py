"""Bedrock exposure is only evaluated for runs that end at the present (end_time <= 0); otherwise it is removed."""

import geopandas as gpd
from shapely.geometry import Point

from GLAMODAT.io.data_loader import _delete_bedrock_exposure_if_not_present


def _features():
    return gpd.GeoDataFrame(
        {"ID": ["be-1", "if-1", "be-2"], "pc_cat": ["bedrock exposure", "ice free", "bedrock exposure"]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)], crs="EPSG:32632")


def test_run_until_present_keeps_bedrock_exposure():
    kept = _delete_bedrock_exposure_if_not_present((15000.0, 0.0), _features())
    assert kept["ID"].tolist() == ["be-1", "if-1", "be-2"]


def test_run_not_until_present_removes_bedrock_exposure(capsys):
    kept = _delete_bedrock_exposure_if_not_present((15000.0, 5000.0), _features())
    assert kept["ID"].tolist() == ["if-1"]
    assert "2 features removed" in capsys.readouterr().out
