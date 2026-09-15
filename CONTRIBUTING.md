# Contributing

GLAMODAT is scientific research software. Contributions that improve
reproducibility, input validation, documentation, tests, or performance are
welcome.

## Before opening a change

```bash
conda activate glamodat
python -m compileall -q GLAMODAT scripts tests
python -m pytest -q
```

Keep tests independent of the external test database. Use temporary fixtures
for small NetCDF and GIS inputs. Do not add generated NetCDF, CSV, PNG, or
notebook output to the source repository.

For scientific changes, describe the changed assumption or scoring behavior and
identify the dataset or synthetic fixture used for validation. For data changes,
record provenance, license, source URL, and version.

## Pull requests

Please include:

- a concise description of the change;
- tests or a reproducible validation command;
- documentation updates when the user workflow changes; and
- provenance and licensing information for any new data.
