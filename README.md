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
