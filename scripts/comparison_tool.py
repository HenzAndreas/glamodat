"""VS Code debug harness for the core GLAMODAT comparison workflow.

Use ``scripts/run_comparison.py`` for normal command-line execution. Edit the
paths below when launching this file with the VS Code debugger.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from GLAMODAT.core.comparison_workflow import evaluate


MODEL_OUTPUT = "../paleoalps-extension/susten-run-paper-may/1/"
PARAMETER_FILE = "configs/params_comparison_tool_case_study.yaml"
CREATE_PLOTS = True


def main():
    """Run one comparison using the paths configured above."""
    results = evaluate(
        folder=MODEL_OUTPUT,
        parameter_file=PARAMETER_FILE,
        create_plots=CREATE_PLOTS,
    )
    print("Weighted horizontal distance:", results[0])
    print("Weighted vertical distance:", results[1])
    print("Total weighted distance:", results[2])
    print("Zero-distance feature fraction:", results[3])
    return results


if __name__ == "__main__":
    main()
