"""Check _condition_met_for_palcontext (and the special case "last change after the window") against the case
table palcontext_cases.txt, the same way _distance_for_point combines them: normal rule OR special case.

Every line of the table is one test. Add new cases to the table, not here.
"""

import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from GLAMODAT.core.distance_calculation import (_condition_met_for_palcontext, _is_special_case_change_after_window,
                                                _special_case_condition)

CASES_FILE = Path(__file__).with_name("palcontext_cases.txt")
COLUMNS = ["case_id", "group", "pc_cat", "pc_time", "min_age", "max_age", "current_t",
           "last_ice", "cum_icefree", "t_before", "last_ice_before", "expected", "explanation"]
KNOWN_ISSUE = "KNOWN ISSUE:"


def _number(value):
    """'-' means 'not used by this category' -> NaN (any use of it would make the comparison False)."""
    return math.nan if value == "-" else float(value)


def _read_cases():
    """Read the "|"-separated table; '#' lines and empty lines are skipped."""
    cases = []
    for line_number, line in enumerate(CASES_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # split only up to the last column, so the explanation may contain "|"
        values = [value.strip() for value in line.split("|", len(COLUMNS) - 1)]
        if len(values) != len(COLUMNS):
            raise ValueError(f"{CASES_FILE.name}:{line_number}: expected {len(COLUMNS)} columns, got {len(values)}")
        cases.append(SimpleNamespace(**dict(zip(COLUMNS, values))))
    return cases


def _case_params():
    params = []
    for case in _read_cases():
        marks = []
        if KNOWN_ISSUE in case.explanation:
            reason = case.explanation.split(KNOWN_ISSUE, 1)[1].strip()
            marks.append(pytest.mark.xfail(reason=reason, strict=True))
        params.append(pytest.param(case, id=case.case_id, marks=marks))
    return params


@pytest.mark.parametrize("case", _case_params())
def test_condition_met_for_palcontext(case):
    current_t, last_ice = _number(case.current_t), _number(case.last_ice)
    min_age, max_age = _number(case.min_age), _number(case.max_age)

    result = _condition_met_for_palcontext(
        current_t=current_t,
        last_ice=last_ice,
        cum_icefree=_number(case.cum_icefree),
        min_age=min_age,
        max_age=max_age,
        palcontext=case.pc_cat,
        pc_time=case.pc_time,
    )
    # special case: only possible when the case gives the earlier frame (t_before, last_ice_before)
    if case.t_before != "-" and _is_special_case_change_after_window(current_t, last_ice, min_age, case.pc_cat, case.pc_time):
        result = result or _special_case_condition(_number(case.t_before), _number(case.last_ice_before),
                                                   min_age, max_age, case.pc_cat, case.pc_time)

    assert bool(result) == (case.expected == "True"), case.explanation
