import subprocess
import sys
import os
import pytest

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    return result

@pytest.mark.parametrize("cli_cmd", [
    "hcd_nogui -c tests/data/DT_baseline_example",
    "hcd_nogui -c tests/data/EC_IC_NBI",
    "hcd_nogui -c tests/data/FOPLA_TEST",
    "hcd_nogui -c tests/data/GRAYSCALE",
    "hcdslice_nogui -c tests/data/DT_baseline_example",
    "hcdslice_nogui -c tests/data/EC_IC_NBI",
    "hcdslice_nogui -c tests/data/FOPLA_TEST",
    "hcdslice_nogui -c tests/data/GRAYSCALE",
])
def test_workflow_commands(cli_cmd):
    result = run_command(cli_cmd)
    assert result.returncode == 0, f"Command failed: {cli_cmd}\n{result.stderr}"
