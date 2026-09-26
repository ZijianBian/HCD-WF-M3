# HCD Workflow

[![Development Status](https://img.shields.io/badge/status-development-yellow.svg)](https://pypi.org/project/HCDWorkflow/)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-See%20LICENSE.txt-blue.svg)](LICENSE.txt)

Python-based Heating and Current Drive (H&CD) Workflow for ITER plasma simulations.

---

## 🚀 Quick Start

| Audience   | Recommended Setup                | Command/Script                        |
|------------|----------------------------------|---------------------------------------|
| **User**   | EasyBuild module (SDCC)          | `module load HCD-WF`                  |
| **User**   | SDCC Helper Script (SDCC)        | `source config_hcd_iter_sdcc.sh`           |
| **Developer** | SDCC Helper Script (SDCC)     | `source config_hcd_iter_sdcc.sh`           |
| **Developer** | Manual Setup (any system)     | See [Developer Setup](#for-developers) |

---

## For Users

### 1. On ITER SDCC: Use the EasyBuild Module (Recommended)

```bash
module load HCD-WF
# Use the actors and DD version supplied by the installed module
hcd_nogui -c /path/to/config   # Run a simulation
hcd_gui                       # Launch the GUI
```

Installed modules may predate the MUSCLE3 support described below; use the documentation shipped with that release.

### 2. On ITER SDCC: Use the Helper Script (Alternative)

```bash
# From the repository root, select your installed DD 4.1.0 actors:
export ACTOR_FOLDER=/path/to/PYTHON_ACTORS
source config_hcd_iter_sdcc.sh
python -m pip install -e .        # One-time installation of this checkout
```

This script will:

- Load the DD 4.1.0 / Intel-2023b / MUSCLE3 0.8.0 runtime modules
- Create and activate the `devenv_dd410` virtual environment
- Use actors from `ACTOR_FOLDER`; it does not build actors or install Python packages by default

For Legacy actors built against DD 3.42.0, use `source config_hcd_iter_sdcc_3.42.0.sh` in a separate shell. See [Installation](docs/source/user/installation.rst) for details.

### 3. Example Commands

Use a saved case with matching actors and an accessible input database.

```bash
# Run a simulation (console)
hcd_nogui -c tests/data/GRAYSCALE/

# Run a simulation (GUI)
hcd_gui

# Submit a Legacy batch job using the site's submission setup
hcd_batch -n 4 -t 8 -e user@iter.org -q all -c my_config/

# Run the older single-slice diagnostic
hcdslice_nogui -c my_config/
```

`hcdslice_nogui` currently fixes the time at 320 s and does not store the returned outputs. For a configurable single slice with output storage, set `one_time_slice=1` in the XML and use `hcd_nogui`. The batch wrapper requires the site's `qsub` setup; see [Command reference](docs/source/reference/commands.rst).

### 4. Execution Modes (Source Checkout)

- **Legacy** calls the existing iWrap actors directly.
- **Hybrid** runs the iWrap workflow behind a MUSCLE3 interface.
- **Pure** connects the driver to native MUSCLE3 actors.

After preparing the environment above, run a saved configuration:

```bash
./run.sh legacy /path/to/config
./run.sh hybrid /path/to/config
./run.sh pure /path/to/config
```

Hybrid uses `topologies/hybrid.ymmsl`. Pure uses `topologies/pure.ymmsl` and keeps the actors selected in `input_workflow.xml`. Native actors must be installed separately; Rabbit uses `scripts/run_rabbit_m3.sh` for its GCC runtime. See [Execution modes](docs/source/user/execution_modes.rst) and [Actor installation](docs/source/developer/actor_installation.rst).

---

## For Developers

### 1. On ITER SDCC: Use the Helper Script (Recommended)

```bash
source config_hcd_iter_sdcc.sh
python -m pip install -e ".[dev]"
```

The helper prepares the runtime and virtual environment; the editable installation adds the project and development tools.

### 2. Manual Setup (Any System)

Prepare compatible IMAS and actor installations before creating the virtual environment. The SDCC module commands below are a Legacy DD 3.42.0 example; use the helper above for the MUSCLE3 stack.

```bash
# Clone the repository
git clone ssh://git@git.iter.org/wf/hcd-wf.git
cd hcd-wf

# Load required modules first (SDCC Legacy example)
module load Tkinter matplotlib Waveform-Cooker
module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0

# Create a virtual environment with access to module-provided packages
python -m venv --system-site-packages devenv
source devenv/bin/activate

# Install in editable mode with dev dependencies
python -m pip install -e ".[dev]"
```

### 3. Code Quality & Testing

```bash
# Format code
black --line-length 120 hcdworkflow/ gui/ tools/ workflow/

# Check style
flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow/

# Run linter
pylint --max-line-length=120 hcdworkflow/

# Run the single-slice diagnostic with compatible actors and input data
hcdslice_nogui -c tests/data/GRAYSCALE/

# Or use the SDCC CI script (loads modules and installs lint tools)
bash ci-sdcc/st05-staticanalysis.sh
```

To run the workflow integration tests using pytest:

1. Ensure you have pytest installed in your environment:
   ```bash
   pip install pytest
   ```
2. Run all tests:
   ```bash
   pytest tests/test_workflow.py
   ```
   Or run all tests in the directory:
   ```bash
   pytest tests/
   ```

These tests execute physics workflows and check their exit status. They require the matching actors and input databases; review each case's output run before execution. They do not compare numerical results.

### 4. Installing Custom Actors

```bash
cd actor_install
python actor_install.py --skipModules *.yml      # Run all supplied actor recipes
python actor_install.py --skipModules grayscale.yml  # Install specific actor
```

With `--skipModules`, load the dependencies required by each selected recipe first. These iWrap recipes do not provide every native MUSCLE3 actor; see [Actor installation](docs/source/developer/actor_installation.rst).

---

## Features

- **Multiple Execution Modes**: Console, GUI, batch, single time-slice
- **MUSCLE3 Support**: Hybrid iWrap workflow and Pure native actors
- **Flexible Actor System**: Easy integration of new physics codes
- **IMAS Integration**: Input and output through IMAS IDSes
- **Time-Loop Execution**: Automated multi-timepoint simulations
- **HPC Support**: Site-specific Legacy batch submission
- **Waveform Management**: Integration with Waveform Cooker
- **Modular Design**: Clean separation of workflow logic and physics codes

---

## Project Structure

```
hcd-wf/
├── hcdworkflow/           # Main workflow package
├── gui/                   # GUI components
├── tools/                 # Utility tools
├── workflow/              # Workflow wrapper
├── actor_install/         # Actor installation scripts
├── topologies/            # Hybrid and Pure MUSCLE3 templates
├── scripts/               # Rabbit GCC launcher
├── docs/                  # Handbook sources
├── tests/                 # Test data
├── ci-sdcc/               # CI/CD scripts
├── run.sh                 # Legacy / Hybrid / Pure launcher
├── hcd_gui                # GUI entry point
├── hcd_nogui              # Console entry point
├── hcdslice_nogui         # Single slice entry point
├── hcd_batch              # Batch submission script
├── pyproject.toml         # Project configuration
├── setup.cfg              # Tool configurations
└── README.md              # This file
```

---

## Configuration

The workflow is configured using a main XML file and optional YAML waveform files. These files define the simulation parameters, selected physics actors, and time-dependent waveforms.

### Main Configuration: `input_workflow.xml`

- This XML file is required in your configuration folder.
- It defines:
  - **Workflow parameters**: shot number, run numbers, time range, time step, etc.
  - **Actor selection**: which physics codes (actors) to use for each process (e.g., ECRH, ICRH, NBI).
  - **Database and output settings**: input/output locations and IMAS backends.

**Illustrative structure** (use the GUI to save a complete configuration):

```xml
<root>
  <workflow_parameters>
    <shot_nr>130012</shot_nr>
    <run_in>5</run_in>
    <run_out>6</run_out>
    <tbegin>30.0</tbegin>
    <tend>350.0</tend>
    <dt_required>20</dt_required>
  </workflow_parameters>
  <actor_selection>
    <main_process>
      <ECRH>
        <ec_wave_solver list="genray gray grayscale torbeam toray">4</ec_wave_solver>
      </ECRH>
      <ICRH>
        <ic_wave_solver list="cyrano tomcat pion lion">1</ic_wave_solver>
      </ICRH>
    </main_process>
  </actor_selection>
</root>
```

- The `list` attribute specifies available actors: `0` disables the process, `1` selects the first actor, and so on. The example selects Torbeam (`4`) and Cyrano (`1`).
- You can enable/disable actors and processes as needed for your simulation scenario.

### Waveform Files (YAML)

- Used for specifying time-dependent parameters for each heating/current drive system.
- Typical files:
  - `ec_waveforms.yaml` – ECRH waveforms
  - `ic_waveforms.yaml` – ICRH waveforms
  - `nbi_waveforms.yaml` – NBI waveforms
  - `lh_waveforms.yaml` – LHCD waveforms
- Place these files in your configuration folder if your simulation requires time-dependent input.

### Example Configuration Folder

A typical configuration folder (e.g., `tests/data/GRAY_PION`) contains:

- `input_workflow.xml` (main workflow definition)
- `ec_waveforms.yaml`, `ic_waveforms.yaml`, etc. (optional, for time-dependent scenarios)

You can run the workflow using:

```bash
hcd_nogui -c tests/data/GRAY_PION
hcdslice_nogui -c tests/data/GRAY_PION
```

---

### Runtime Dependencies

- IMAS-Python for DD4, or IMAS-AL-Python for the older DD3 installation
- MUSCLE3 for Hybrid and Pure modes
- Physics actor modules (GRAYSCALE, HCD_MERGERS, etc.)
- Tkinter (for GUI)
- matplotlib (for GUI plotting)

---

## Documentation

- [Confluence Documentation](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)
- [Handbook contents](docs/source/index.rst) and [Quickstart](docs/source/user/quickstart.rst)
- [Configuration reference](docs/source/reference/configuration.rst) and [Developer setup](docs/source/developer/setup.rst)
- Build locally from the repository root:

  ```bash
  python -m pip install -e ".[docs]"
  python -m sphinx -b html docs/source /tmp/hcdwf-handbook-preview
  # Open /tmp/hcdwf-handbook-preview/index.html in a browser
  ```

---

## Troubleshooting

- **Module import errors**: Use the helper matching your actor build (`config_hcd_iter_sdcc.sh` for DD4 or `config_hcd_iter_sdcc_3.42.0.sh` for Legacy DD3), and check `ACTOR_FOLDER`. See [Installation](docs/source/user/installation.rst).

---

## Legal

See [LICENSE.txt](LICENSE.txt) for details.

Copyright (c) 2019-2025, ITER Organization


## Links

- [Homepage](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)
- [Documentation](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)
- [Handbook](docs/source/index.rst)
- [Contributing](CONTRIBUTING.md)


---
