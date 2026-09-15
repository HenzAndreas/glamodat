from pathlib import Path

import yaml

from GLAMODAT.io.data_loader import load_yaml_parameters
from scripts.run_batch_comparison import find_model_folders


def test_load_yaml_parameters_reads_fixture_configuration(tmp_path):
    parameter_file = tmp_path / "parameters.yaml"
    parameter_file.write_text(
        yaml.safe_dump({"year_format": "-b2k", "analysis_frequency": 100.0}),
        encoding="utf-8",
    )

    parameters = load_yaml_parameters(parameter_file)

    assert parameters == {"year_format": "-b2k", "analysis_frequency": 100.0}


def test_find_model_folders_discovers_only_matching_outputs(tmp_path):
    first = tmp_path / "run-a"
    second = tmp_path / "nested" / "run-b"
    first.mkdir()
    second.mkdir(parents=True)
    (first / "output.nc").touch()
    (second / "output.nc").touch()
    (tmp_path / "not-a-run.txt").touch()

    folders = list(find_model_folders(tmp_path, "output.nc"))

    assert set(folders) == {first.resolve(), second.resolve()}
