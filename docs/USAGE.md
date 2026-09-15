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

## VS Code debugging

Using the VS Code Python Debugger extension from debugpy, you can set breakpoints in the script and run comparison_tool.py or run_comparison_tool.py in debug mode (usually F5 or manually clicking on debug button.) This allows you to step through the code, inspect variables along the way, and understand the flow of the program step by step.
Make sure to set the correct working directory and provide the necessary command-line arguments, which you can write directly in the python file for debugging purposes.

## Configuration

The YAML configuration defines model files, evidence files, coordinate reference
system, time convention, analysis interval, and scoring weights. Paths are
currently interpreted relative to the working directory unless they are
absolute. Keep model and evidence data outside the source repository when they
are large or confidential.
