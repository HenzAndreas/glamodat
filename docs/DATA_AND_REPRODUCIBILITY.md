# Data and reproducibility

## Source repository

The GitHub repository contains the GLAMODAT source code, configurations,
tests, and documentation. Large model outputs and generated products are
excluded by `.gitignore`.

## Test database

The complete test database is intentionally distributed separately because it
contains large NetCDF outputs and generated research products.

- Review download: `TEST_DATABASE_REVIEW_LINK_TO_BE_ADDED`
- Permanent archive: `ZENODO_LINK_TO_BE_ADDED`

Until those links are available, the automated tests use small temporary
fixtures and do not require the external database.

## Publication

The associated manuscript is in preparation.

- Publication link: `PUBLICATION_LINK_TO_BE_ADDED`

Update this document and `CITATION.cff` when a DOI or review link is available.

## Input data responsibility

Users must confirm the license and provenance of their glacier-model outputs,
shapefiles, age compilations, and derived products. GLAMODAT's GPL-3.0-or-later
license applies to the source code only; it does not automatically relicense
third-party scientific data.

## NetCDF model requirements

A model output file normally contains:

- `x(x)` and `y(y)` spatial axes
- `time(time)`
- `thk(time, y, x)`
- `lasticecover(time, y, x)`
- `icefree_cummulative(time, y, x)`
- either `topg(time, y, x)` or `usurf(time, y, x)`

A separate glacier-history file contains `glacier_history(y, x)` or equivalent
2-D dimensions with the same spatial shape.

## Evidence data

Evidence is read through GeoPandas. The exact fields depend on the evidence type,
but event-age point data use fields such as `ID`, `confid_ra`, `pc_cat`,
`pc_subcat`, `pc_time`, `e_age_min`, and `e_age_max`, plus a geometry and CRS.
The default example configuration uses EPSG:32632; users must set the CRS to
match their data and model grid.

## Release checklist

Before a public release:

- replace all placeholder links in this document, the README, and `CITATION.cff`;
- confirm licenses for every external data product;
- publish the large test database with a versioned DOI or review archive;
- record the exact model-output and evidence-data versions used in the paper;
- run the tests in a clean environment;
- review generated files and confirm they are not accidentally committed.
