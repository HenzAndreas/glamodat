"""Small synthetic-grid tests for the neighbourhood search in _distance_for_point (via _calculate_distance), and for
process_features (first evaluation, re-evaluation at the frame with the most ice).

Each test checks one thing: if the feature cell does not match, does the search go in the right direction
(towards or away from the ice), skip the cells that do not match, and stop at the first cell that matches for the
right reason?

Grid (same for all tests):
- 13 rows x 21 columns, dx = 1000 m, feature in the centre cell (row 6, column 10).
- One valley along row 6: the glacier lies to the east. glacier_history (which steers the search) rises towards the
  glacier along row 6 and is flat (0) on the sides, so the search stays on row 6 and the distances are exact
  (one cell = 1000 m).
- With dx = 1000 the search window is +-5 cells (max_search_distance 5000 m), so the padded search window starts at
  row 1 / column 5, not at the grid corner. This also tests the index conversion back to the full grid.
- topg rises 10 m per column, no ice thickness -> vertical distance = 10 m per column.
- Model frames at ages 11100, 11050, 11000; the evaluated frame is 11000. Window [11040, 11540].
  lasticecover is given per column (the same in every row): negative = ice free since |value| years,
  positive = ice covered since value years (seen from the frame).
"""

import numpy as np
import pandas as pd
import pytest
from shapely import Point
from types import SimpleNamespace

import GLAMODAT.core.distance_calculation as dc

N_ROWS, N_COLS = 13, 21
ROW, COL = 6, 10            # feature cell (full grid)
DX = 1000.0
PAD_ROW0, PAD_COL0 = 1, 5   # where the padded search window starts in the full grid (ROW-5, COL-5)
TIMES = np.array([11100.0, 11050.0, 11000.0])
NOW, BEFORE = 2, 1          # frame index of 11000 (evaluated) and 11050 (youngest frame inside the window)
MIN_AGE, MAX_AGE = 11040.0, 11540.0
PENALTY = 5000              # max_search_distance in _distance_for_point


def _columns(values, default):
    """Row of length N_COLS: `values` = {column: lasticecover}, all other columns = default."""
    row = np.full(N_COLS, float(default))
    for column, value in values.items():
        row[column] = value
    return row


def _state(now, before=None):
    """Synthetic state. now / before: lasticecover per column at frame 11000 / 11050 (before defaults to now)."""
    before = now if before is None else before
    return _make_state(TIMES, [now, before, now][::-1])  # frames 11100 (unused), 11050, 11000


def _make_state(times, lasticecover_rows, thk_at_feature=None, analysis_frequency=100.0):
    """Synthetic state from one lasticecover row (per column, same in every row) per model frame.
    thk_at_feature: ice thickness at the feature cell per frame (0 everywhere else)."""
    lasticecover = np.stack([np.tile(row, (N_ROWS, 1)) for row in lasticecover_rows])
    thk = np.zeros_like(lasticecover)
    if thk_at_feature is not None:
        thk[:, ROW, COL] = thk_at_feature

    glacier_history = np.zeros((N_ROWS, N_COLS))
    glacier_history[ROW, :] = np.arange(N_COLS) - COL   # higher towards the glacier (east), only along the valley

    return SimpleNamespace(
        t=np.asarray(times, dtype=float), lasticecover=lasticecover, icefree_cummulative=np.zeros_like(lasticecover),
        thk=thk, topg=np.tile(10.0 * np.arange(N_COLS), (N_ROWS, 1)),
        glacier_history=glacier_history, x=DX * np.arange(N_COLS), y=DX * np.arange(N_ROWS), dx=DX,
        analysis_frequency=analysis_frequency, working_folder=".")


def _row(pc_cat, pc_time="-"):
    return {"geometry": Point(COL * DX, ROW * DX), "min_age": MIN_AGE, "max_age": MAX_AGE,
            "pc_cat": pc_cat, "pc_time": pc_time, "ID": "test", "site_ID": "test"}


@pytest.fixture
def search_path(monkeypatch):
    """Record the cells the search checked (full-grid (row, column)) instead of plotting them."""
    paths = []

    def record(workingdir, last_ice_pad, checked_cells, *args, **kwargs):
        paths.append([(j + PAD_ROW0, i + PAD_COL0) for j, i in checked_cells])

    monkeypatch.setattr(dc, "plot_checked_cells", record)
    return paths


def _run(state, row, first_evaluation=True):
    horizontal, vertical, sign = dc._calculate_distance(state, NOW, row, first_evaluation=first_evaluation)
    return float(horizontal), float(vertical), float(sign)


def _columns_checked(path):
    assert all(j == ROW for j, _ in path), f"search left the valley row: {path}"
    return [i for _, i in path]


def test_feature_cell_matches_no_search(search_path):
    """Ice margin passed the feature at 11300 (inside the window) -> match at the feature, no search at all."""
    state = _state(now=_columns({COL: -300}, default=-2000))
    assert _run(state, _row("ice margin")) == (0.0, 0.0, -1.0)
    assert search_path == []


def test_ice_margin_too_early_searches_towards_the_ice(search_path):
    """Model margin passed the feature too early (ice free since 12000) -> search towards the ice (east).

    Column 11: ice free since 11700 (still too early), column 12: since 11400 (inside the window) -> match 2 cells east.
    """
    state = _state(now=_columns({COL: -1000, 11: -700, 12: -400, 13: -100}, default=-2000))
    assert _run(state, _row("ice margin")) == (2000.0, 20.0, -1.0)
    assert _columns_checked(search_path[0]) == [10, 11, 12]


def test_ice_margin_still_ice_covered_searches_away_from_the_ice(search_path):
    """Feature still ice covered (model margin not far enough back) -> search away from the ice (west).

    Column 9: still ice covered, column 8: ice free since 11100 (inside the window) -> match 2 cells west.
    """
    state = _state(now=_columns({COL: 200, 9: 50, 8: -100}, default=-2000))
    assert _run(state, _row("ice margin")) == (2000.0, 20.0, -1.0)
    assert _columns_checked(search_path[0]) == [10, 9, 8]


def test_icefree_longterm_skips_cell_deglaciated_after_the_window(search_path):
    """Long-term deglaciation, feature still ice covered -> search away from the ice (west).

    Column 9 is ice free, but only since 11020 (after min_age) -> no match, column 8 (since 11100) -> match.
    """
    state = _state(now=_columns({COL: 200, 9: -20, 8: -100}, default=-2000))
    assert _run(state, _row("ice free", "long-term deglaciation")) == (2000.0, 20.0, -1.0)
    assert _columns_checked(search_path[0]) == [10, 9, 8]


def test_ice_cover_feature_ice_free_searches_towards_the_ice(search_path):
    """Ice cover, feature ice free -> search towards the ice (east).

    Column 11 is ice covered, but only since 11020 (after min_age) -> no match, column 12 (since 11300) -> match.
    """
    state = _state(now=_columns({COL: -100, 11: 20, 12: 300}, default=-2000))
    assert _run(state, _row("ice cover")) == (2000.0, 20.0, 1.0)
    assert _columns_checked(search_path[0]) == [10, 11, 12]


def test_special_case_found_at_neighbour_cell(search_path):
    """SPECIAL CASE at a neighbour cell: column 11 is ice free only since 11010 at frame 11000 (last change after the
    window), but at frame 11050 it was ice free since 11300 (margin passed inside the window) -> match 1 cell east.
    Column 12 would match with the normal rule (2 cells east). The window-frame value is only set in column 11, so a
    wrong index conversion (padded instead of full grid) would read another column and not find it.
    """
    now = _columns({COL: -1000, 11: -10, 12: -300, 13: 100}, default=-2000)
    before = _columns({11: -250}, default=-2000)
    state = _state(now=now, before=before)
    assert _run(state, _row("ice margin")) == (1000.0, 10.0, -1.0)
    assert _columns_checked(search_path[0]) == [10, 11]


def test_special_case_not_used_at_later_evaluation(search_path):
    """Same grid as above, but not the first evaluation (a re-evaluation at the frame with the most ice): the special
    case must not apply -> column 11 skipped, match in column 12.
    """
    now = _columns({COL: -1000, 11: -10, 12: -300, 13: 100}, default=-2000)
    before = _columns({11: -250}, default=-2000)
    state = _state(now=now, before=before)
    assert _run(state, _row("ice margin"), first_evaluation=False) == (2000.0, 20.0, -1.0)
    assert _columns_checked(search_path[0]) == [10, 11, 12]


def test_ice_margin_jumped_over_from_inside_the_ice(search_path):
    """Feature still ice covered -> search away from the ice (west). Column 9 is ice free, but since 12500 (far too
    early, no age match). The ice sign changed between the feature and column 9: the search jumped over the (sharp)
    ice margin, which counts as a match (the grid is too coarse to resolve the margin) -> 1000 m."""
    state = _state(now=_columns({COL: 200, 9: -1500}, default=-3000))
    assert _run(state, _row("ice margin")) == (1000.0, 10.0, -1.0)
    assert _columns_checked(search_path[0]) == [10, 9]


def test_ice_margin_jumped_over_from_outside_the_ice(search_path):
    """Feature deglaciated far too early -> search towards the ice (east). Column 11 is ice free since 11800 (still too
    early), column 12 is ice covered (no age match for an ice margin, but the sign changed) -> jumped over the ice
    margin -> match at 2000 m."""
    state = _state(now=_columns({COL: -1000, 11: -800, 12: 300}, default=-3000))
    assert _run(state, _row("ice margin")) == (2000.0, 20.0, 1.0)
    assert _columns_checked(search_path[0]) == [10, 11, 12]


def test_no_match_in_search_area_gives_penalty(search_path):
    """Everything deglaciated far too early -> search towards the ice (east) until the edge of the search area,
    no match -> penalty distance, and the search only went east."""
    state = _state(now=_columns({}, default=-2000))
    horizontal, vertical, _ = _run(state, _row("ice margin"))
    assert (horizontal, vertical) == (PENALTY, PENALTY)
    columns = _columns_checked(search_path[0])
    assert columns[0] == COL and columns == sorted(columns) and len(columns) > 1


# ---------------------------------------------------------------------------------------------------------------------
# process_features: model output every 50 years, analysis every 100 years.
#   model frames   11100  11050  11000  10950  10900   (index 0..4)
#   analysis       11100         11000         10900   (distance_array columns 0..2)
# Window [11040, 11540] -> first evaluation at 11000 (model index 2, analysis column 1); youngest frame inside the
# window is 11050. If the feature gets ice later, it is re-evaluated at the model frame with the most ice.
# ---------------------------------------------------------------------------------------------------------------------

PF_TIMES = [11100.0, 11050.0, 11000.0, 10950.0, 10900.0]


def _process(state, pc_cat, pc_time="-"):
    row = _row(pc_cat, pc_time)
    row["midpoint"] = row["geometry"]
    state.features_to_score = pd.DataFrame([row])
    state.start_time, state.end_time = PF_TIMES[0], PF_TIMES[-1]
    state.output_saving_frequency = 50.0
    dc.process_features(state, {"year_format": "-b2k"})
    return state.distance_array[0, :, 0], state.distance_array[0, :, 1]   # horizontal, vertical per analysis frame


@pytest.fixture
def no_thickness_plot(monkeypatch):
    monkeypatch.setattr(dc, "plot_ice_thickness_through_time", lambda *args, **kwargs: None)


def test_process_features_readvance_at_first_frame_is_penalised(search_path, no_thickness_plot):
    """Ice margin passed the feature at 11300 (frame 11050), ice came back at 11020 and is still there at 11000 with
    the most ice of the run there. First evaluation: special case -> match. But then the re-evaluation at the frame
    with the most ice (the same frame 11000) must not use the special case: the feature is ice covered, the search goes
    away from the ice (west) and finds column 9 (ice free since 11100) -> 1000 m from 11000 on.
    """
    background = _columns({}, default=-2000)
    frames = [background,
              _columns({COL: -250}, default=-2000),            # 11050: margin passed at 11300
              _columns({COL: 20, 9: -100}, default=-2000),     # 11000: ice again since 11020
              _columns({COL: -30}, default=-2000),             # 10950: ice free again
              _columns({COL: -80}, default=-2000)]             # 10900
    state = _make_state(PF_TIMES, frames, thk_at_feature=[0, 0, 50, 0, 0])
    horizontal, vertical = _process(state, "ice margin")
    np.testing.assert_array_equal(horizontal, [np.nan, 1000.0, 1000.0])
    # vertical: surface at the feature = topg 100 + 50 m ice, at column 9 = 90 -> 60 m
    np.testing.assert_array_equal(vertical, [np.nan, 60.0, 60.0])


def test_process_features_advance_gone_before_first_frame_is_a_match(search_path, no_thickness_plot):
    """Same, but the small advance after the window is gone again at 11000 (ice free since 11010) and no ice later:
    special case at the first evaluation -> match, no re-evaluation -> 0 from 11000 on."""
    background = _columns({}, default=-2000)
    frames = [background,
              _columns({COL: -250}, default=-2000),            # 11050: margin passed at 11300
              _columns({COL: -10}, default=-2000),             # 11000: ice free again since 11010
              _columns({COL: -60}, default=-2000),
              _columns({COL: -110}, default=-2000)]
    state = _make_state(PF_TIMES, frames, thk_at_feature=[0, 0, 0, 0, 0])
    horizontal, vertical = _process(state, "ice margin")
    np.testing.assert_array_equal(horizontal, [np.nan, 0.0, 0.0])
    assert search_path == []


def test_process_features_most_ice_between_analysis_frames(search_path, no_thickness_plot):
    """Long-term deglaciation, match at 11000. A readvance has its most ice at 10950, a model frame between the
    analysis frames: that exact frame is evaluated (column 9 matches there -> 1000 m), not 10900 (where only
    column 8 would match -> 2000 m). Stored from the next analysis frame (10900) on."""
    background = _columns({}, default=-2000)
    frames = [background,
              _columns({COL: -250}, default=-2000),
              _columns({COL: -300}, default=-2000),            # 11000: ice free since 11300 -> match
              _columns({COL: 20, 9: -500}, default=-2000),     # 10950: ice again since 10970; column 9 ice free since 11450
              _columns({COL: -10, 9: -50}, default=-2000)]     # 10900: column 9 only since 10950 (too young)
    state = _make_state(PF_TIMES, frames, thk_at_feature=[0, 0, 0, 30, 0])
    horizontal, vertical = _process(state, "ice free", "long-term deglaciation")
    np.testing.assert_array_equal(horizontal, [np.nan, 0.0, 1000.0])
