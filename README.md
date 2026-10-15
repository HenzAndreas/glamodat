# GLAMODAT

GLAMODAT compares transient palaeo glacier-model simulations with dated geomorphological and
and geochronological evidence. It is designed for glacier-model researchers and
geomorphologists who want to evaluate the spatial and temporal agreement between
modelled ice histories and mapped or dated landscape evidence.

The tool calculates horizontal and vertical distances between evidence features
and matching model grid cells, applies configurable confidence and density
weights, and produces summary scores and diagnostic plots.

> Status: research software under active development. The associated
> publication is in preparation.

## Links

- Publication: `PUBLICATION_LINK_TO_BE_ADDED`
- Review test database: `TEST_DATABASE_REVIEW_LINK_TO_BE_ADDED`
- Permanent test database archive: `ZENODO_LINK_TO_BE_ADDED`
- Citation metadata: [CITATION.cff](CITATION.cff)

## Repository layout

```text
GLAMODAT/
├── GLAMODAT/       reusable data-loading, scoring, and plotting modules
├── scripts/        single-run, batch, preprocessing, and helper commands
├── configs/        YAML configuration examples
├── tests/          small archive-independent automated tests
├── docs/           detailed usage and data documentation
├── archive/        local historical material, ignored by Git
└── test_database/  large external example data, ignored by Git
```

The large test database is intentionally separate from the source repository.
The automated tests create small temporary inputs and do not require it.

## Installation

GLAMODAT currently uses Python and scientific geospatial packages. Conda is
recommended because it provides reliable NetCDF and geospatial binaries:

```bash
conda create -n glamodat python=3.11
conda activate glamodat
python -m pip install -r requirements-dev.txt
```

An existing compatible environment can be used instead. Verify the selected
interpreter before running the tool:

```bash
python --version
which python
```

Python 3.10 or newer is recommended.

## Quick start

Run the archive-independent test suite:

```bash
python -m pytest -q
```

Evaluate one model-output folder:

```bash
python scripts/run_comparison.py \
  --model-output /path/to/model-run \
  --config configs/params_comparison_tool_case_study.yaml \
  --no-plots
```

Remove `--no-plots` when diagnostic figures are wanted. The model folder must
contain the NetCDF file named by `output_nc_file` in the YAML configuration.

Evaluate multiple model folders:

```bash
python scripts/run_batch_comparison.py \
  --input /path/to/model-runs \
  --config /path/to/parameters.yaml \
  --results results/comparison_results.csv \
  --no-plots
```

Build a shared glacier-history field before evaluation:

```bash
python scripts/build_glacier_history.py \
  --input /path/to/model-runs \
  --runs run-001 run-002 run-003 \
  --output /path/to/glacier_history.nc \
  --preview /path/to/glacier_history.png
```

All commands support `--help`. Full command documentation, including VS Code
debugging, is in [docs/USAGE.md](docs/USAGE.md).

## Inputs

A model output normally contains:

- `x(x)` and `y(y)` spatial axes;
- `time(time)`;
- `thk(time, y, x)`;
- `lasticecover(time, y, x)`;
- `icefree_cummulative(time, y, x)`; and
- either `topg(time, y, x)` or `usurf(time, y, x)`.

Evidence is supplied as GeoPandas-readable GIS data, commonly shapefiles, with
fields appropriate to the evidence type. Event-age point data use fields such
as `ID`, `confid_ra`, `pc_cat`, `pc_subcat`, `pc_time`, `e_age_min`, and
`e_age_max`. Coordinate reference systems and time conventions must be declared
correctly in the YAML configuration.

### Time convention

GLAMODAT compares model and evidence on one internal time scale of **ages**:
positive years before a "present" year, growing into the past. Two settings
define it:

- `year_format` sets the present year: `-b2k` = years before 2000 CE,
  `-bp` = years before 1950 CE (case-insensitive). `start_time` and `end_time`
  are given on this scale, with `start_time` the older one.
- `model_year_ce_at_t0` is the calendar year (CE) at model time t = 0, i.e. the
  model time is t = year CE − `model_year_ce_at_t0`. Use 2000 for IGM runs with
  t = 0 in 2000 CE and 1950 for runs that count in negative years BP. If it is
  missing, GLAMODAT assumes 1950 (the behaviour of earlier versions) and prints a
  warning.

Model frames are converted with age = present year − `model_year_ce_at_t0` − t.
Example: with `year_format: -b2k` and `model_year_ce_at_t0: 2000`, the model frame
t = −400 (1600 CE) has the age 400 b2k.

Evidence ages are converted to the same scale:

| Evidence type | Fields | Read as |
|---|---|---|
| event ages | `e_age_min`, `e_age_max` | years BP (1950) |
| ¹⁴C | `recal_min`, `recal_max` | calibrated years BP (1950) |
| TCN | `r_exp_age` ± `r_ext_err` | years before the sampling year (`sample_yr`, else `public_yr`, else 2024) |
| dated landforms | `e_age` − `e_neg_err` / + `e_pos_err` | years before `mean_s_yr`, else `mean_p_yr`, else 2000 |

Further rules:

- `start_time` and `end_time` should be output frames of the model. The
  closest frame within half of `output_saving_frequency` is accepted (with a
  warning); otherwise GLAMODAT stops with an error.
- A feature is used only if its **whole** age window [min_age, max_age] lies
  between `start_time` and `end_time`. The number of features removed by this
  rule is printed.
- Ice margins and moraines match if the cell was last ice-covered at a time
  inside the age window. Ice that covers the feature after the young end of the
  window (an overshoot) is scored with the distance at the time of maximum ice
  thickness at the feature. Ice that goes beyond the feature and back within the
  window is not penalised.
- A mismatch between `model_year_ce_at_t0` and the model output shifts model and
  evidence against each other without any error. Check the printed line
  "Time convention: …" and the time frame of the model at the start of a run.

See [docs/DATA_AND_REPRODUCIBILITY.md](docs/DATA_AND_REPRODUCIBILITY.md) for
input details, provenance, data licensing, and the external test database.

## Outputs

A comparison run can produce:

- per-feature distance files;
- aggregate weighted distance metrics;
- feature tables; and
- diagnostic plots and maps.

Generated NetCDF, CSV, PNG, and notebook files are ignored by default by git.

## Scientific and software status

The scoring conventions, input schema, and command-line interface are still
being refined alongside the publication. 

## License and citation

The source code is released under the GNU General Public License, version 3 or
later. See [LICENSE](LICENSE). Please use [CITATION.cff](CITATION.cff) and add
the publication citation once the manuscript is accepted.

## Development checks

Run the tests before submitting changes:

```bash
python -m pytest -q
```
