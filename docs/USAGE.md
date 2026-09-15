# Usage

GLAMODAT compares transient palaeo glacier-model output with dated geomorphological and
geochronological evidence. The commands below assume that the repository root
is the current directory and that the right Conda environment is active with the installed dependencies.

## Install the dependencies

The current research environment uses Conda because NetCDF and geospatial
packages are easier to install there:

```bash
conda create -n glamodat python=3.11
conda activate glamodat
python -m pip install -r requirements-dev.txt
```

An existing environment with the same dependencies, can also be
used or named how you want...

## Run the tests

The tests create small temporary NetCDF, YAML, and GIS inputs. They do not need
the large test database:

```bash
python -m pytest -q
```

## Single model run from the command line

```bash
python scripts/run_comparison.py \
  --model-output /path/to/model-run \
  --config configs/params_comparison_tool_case_study.yaml \
  --no-plots
```

Remove `--no-plots` to generate the configured result plots. The model folder
must contain the configured `output.nc` file and any other files referenced by
the YAML configuration.

The command reports weighted horizontal distance, weighted vertical distance,
total weighted distance, and the percentage of positively weighted features
with zero horizontal distance.

## Batch processing

Evaluate every folder below an input directory containing the configured NetCDF
filename:

```bash
python scripts/run_batch_comparison.py \
  --input /path/to/model-runs \
  --config /path/to/parameters.yaml \
  --results results/comparison_results.csv \
  --no-plots
```

Use `--output-file output_ex.nc` when model runs use another filename. The batch
command does not delete existing output files.

## Build a glacier-history field

Some workflows use one common glacier-history field for all model runs. Build
it before evaluation:

```bash
python scripts/build_glacier_history.py \
  --input /path/to/model-runs \
  --runs run-001 run-002 run-003 \
  --output /path/to/glacier_history.nc \
  --preview /path/to/glacier_history.png
```

Set `glacier_history_file` in the comparison configuration to the resulting
file. The input runs must contain `output.nc` with `lasticecover`; `topg` is
optional.

## Resample flowlines

Convert a flowline shapefile into regularly spaced coordinate text files:

```bash
python scripts/resample_flowline.py \
  --input /path/to/flowlines.shp \
  --output /path/to/flowlines-40m \
  --interval 40 \
  --minimum-distance 25
```

The shapefile must contain an `id` field and line geometries.

## VS Code debugging

Open the repository in VS Code, select the interpreter containing the GLAMODAT
dependencies, and create a launch configuration with the script path
`scripts/run_comparison.py`. Supply the same arguments as the command-line
example in the `args` list:

```json
{
  "name": "GLAMODAT single run",
  "type": "debugpy",
  "request": "launch",
  "program": "${workspaceFolder}/scripts/run_comparison.py",
  "args": [
    "--model-output", "/path/to/model-run",
    "--config", "${workspaceFolder}/configs/params_comparison_tool_case_study.yaml",
    "--no-plots"
  ],
  "console": "integratedTerminal"
}
```

For library-level debugging, import `prepare_data`, `analyse_data`, or
`evaluate` from `scripts.comparison_tool` and place breakpoints in those
functions.

## Configuration

The YAML configuration defines model files, evidence files, coordinate reference
system, time convention, analysis interval, and scoring weights. Paths are
currently interpreted relative to the working directory unless they are
absolute. Keep model and evidence data outside the source repository when they
are large or confidential.
