# HCD Workflow

[![Development Status](https://img.shields.io/badge/status-development-yellow.svg)](https://pypi.org/project/HCDWorkflow/)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-See%20LICENSE.md-blue.svg)](LICENSE.md)

Python-based Heating and Current Drive (H&CD) Workflow for ITER plasma simulations,with MUSCLE3 integration for modular multi-scale coupling of physics actors.

---

## 🚀 Quick Start

Audience     Setup                          Command
──────────── ────────────────────────────── ──────────────────────────────────────
User         EasyBuild module (SDCC)        module load HCD-WF
User         Default helper (DD 4.1.0)      source config_hcd_iter_sdcc.sh
Developer    Legacy helper (DD 3.42.0)      source config_hcd_iter_sdcc_3.42.0.sh
Developer    Manual Setup (any system)      See "Developer Setup" below

---

## Execution Modes

The workflow supports three execution modes via a unified entry point (`workflow/wf_wrapper.py`):

```
Mode            Flag / Command    Description
─────────────── ───────────────── ──────────────────────────────────────────────────────
Legacy          m3_flag=0         All iWrap actors execute in-process.
                                  No MUSCLE3 involvement. Original behavior.

Hybrid M3       m3_flag=1         Two-component MUSCLE3 coupling:
                                  wf_wrapper.py (macro) handles DB I/O and the
                                  time loop; hcd_workflow_m3.py (micro) runs
                                  iWrap actors in a separate process.
                                  IDS are exchanged via M3 conduits.

Pure M3         (under            Each physics actor (Torbeam, Cyrano, …) runs
                development)      as an independent M3 micro model, coupled
                                  directly to a single macro driver.
                                  Not yet runnable from this branch.
```

### MUSCLE3 Hybrid Architecture

```
wf_wrapper.py     (MACRO — one reuse_instance() containing the full time loop)
    ├── Opens input / output / machine databases
    ├── Reads IDS slices at each timestep
    ├── Sends IDS to micro via O_I ports ────────────┐
    ├── Receives updated IDS from micro via S ports  │
    └── Writes results to output database            │
                                                     │
                    M3 conduits (serialized IDS)     │
                                                     │
hcd_workflow_m3.py  (MICRO — one reuse_instance() per timestep)
    ├── Receives IDS from macro via F_INIT ports ◄───┘
    ├── Calls HCDWorkflow.run()
    │     └── iWrap actors (Torbeam, Cyrano, FoPla, hcd2core_sources, …)
    │         execute internally — invisible to MUSCLE3
    └── Sends output IDS back to macro via O_F ports
```
---

## For Users

### 1. On ITER SDCC: Use the EasyBuild Module (Recommended)

```bash
module load HCD-WF
# All dependencies and actors are loaded automatically
hcd_nogui -c <config_folder>   # Run a simulation
hcd_gui                       # Launch the GUI
```

### 2. On ITER SDCC: Use the Helper Script (Alternative)

```bash
source config_hcd_iter_sdcc.sh           # Default: latest DD (4.1.0) + MUSCLE3
source config_hcd_iter_sdcc_3.42.0.sh    # Legacy DD 3.42.0 stack (no MUSCLE3)
# Optionally set ACTOR_FOLDER for local actors:
ACTOR_FOLDER=~/public/PYTHON_ACTORS source config_hcd_iter_sdcc.sh
```

The default script loads the IMAS-Python 2.x stack with DD 4.1.0, sets up MUSCLE3, iWrap, the Waveform Cooker, and creates a devenv virtual environment. The _3.42.0 variant loads the legacy IMAS-AL-Python 5.x stack with DD 3.42.0 for compatibility with older test cases and JINTRAC coupling.

This script will:
- Load all required modules (unless `ACTOR_FOLDER` is set)
- Create and activate the `devenv` virtual environment
- Install the project and all development dependencies

### 3. Example Commands

```bash
# Run a simulation (console)
hcd_nogui -c tests/data/GRAYSCALE/

# Run a simulation (GUI)
hcd_gui

# Submit a batch job
hcd_batch -n 4 -t 8 -e user@iter.org -q all -c my_config/

# Run a single time slice (test)
hcdslice_nogui -c my_config/
```

---

## For Developers

### SDCC Setup (DD 4.1.0, default)

```bash
source config_hcd_iter_sdcc.sh
```

This script loads the latest IMAS stack and sets up MUSCLE3:
1. Loads `IMAS-Python`, `IMAS-Fortran`, `IDStools`, `MUSCLE3`, `XMLlib`, `INTERPOS`
2. Sets up iWrap (develop branch) and Waveform Cooker paths
3. Configures `ACTOR_FOLDER` and `HCD_SANDBOX` in `PYTHONPATH`
4. Creates a dedicated virtual environment (`devenv`) with `muscle3` installed
5. Runs diagnostic checks (IMAS version, iWrap availability, actor folder)

### SDCC Setup (DD 3.42.0, legacy)

```bash
source config_hcd_iter_sdcc_3.42.0.sh
```

For backward compatibility with the legacy IMAS-AL-Python 5.x stack and DD 3.42.0 actor builds (e.g. for JINTRAC coupling tests under `tests/data/`). Creates a separate `devenv_3.42.0` virtual environment so the two stacks do not interfere.

### Manual Setup (SDCC, without helper script)

```bash
git clone ssh://git@git.iter.org/wf/hcd-wf.git
cd hcd-wf

# Load IMAS stack (must be first)
module purge
module load IMAS-Python IMAS-Fortran IDStools

# Load MUSCLE3 and core tools
module load MUSCLE3 XMLlib INTERPOS

# Waveform Cooker
module load Waveform-Cooker/1.6.0-GCCcore-13.2.0

# iWrap (develop branch)
export PATH=/home/ITER/schneim/public/git/iwrap/bin:$PATH
export PYTHONPATH=/home/ITER/schneim/public/git/iwrap/python:$PYTHONPATH

# Actor and sandbox paths
export ACTOR_FOLDER=/home/ITER/<user>/public/PYTHON_ACTORS
export PYTHONPATH=$ACTOR_FOLDER:$PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

# Create virtual environment
python3 -m venv devenv --system-site-packages
source devenv/bin/activate
pip install muscle3
pip install -e .
```

### Code Quality & Testing

```bash
# Format code
black --line-length 120 hcdworkflow/ gui/ tools/ workflow/
# Check style
flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow/
# Run linter
pylint --max-line-length=120 hcdworkflow/
# Run tests
hcdslice_nogui -c tests/data/GRAYSCALE/
# Or use the CI script
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

These tests will execute the workflow commands for various configurations and check for successful completion.

### Installing Custom Actors (No-Muscle3)

```bash
cd actor_install
python actor_install.py --skipModules *.yml      # Install all actors
python actor_install.py --skipModules grayscale.yml  # Install specific actor
```

---

## Features

- **Multiple Execution Modes**: Console, GUI, batch, single time-slice, and MUSCLE3 hybrid
- **MUSCLE3 Integration**: Modular multi-scale coupling via macro/micro architecture
- **Flexible Actor System**: Easy integration of new physics codes (Torbeam, Cyrano, FoPla, …)
- **IMAS Integration**: Full compatibility with IMAS IDSes, IMAS-Python 2.x, DD 4.0.0/4.1.0
- **Smart DD Conversion**: Automatic Data Dictionary version handling with manual fix-ups
- **Time-Loop Execution**: Automated multi-timepoint simulations
- **HPC Support**: SLURM batch job submission
- **Waveform Management**: Integration with Waveform Cooker
- **Benchmark Runner**: Automated run management with numbered output directories
---

## Configuration

The workflow is configured using a main XML file and optional YAML waveform files. These files define the simulation parameters, selected physics actors, and time-dependent waveforms.

### Main Configuration: `input_workflow.xml`
- This XML file is required in your configuration folder.
- It defines:
  - **Workflow parameters**: shot number, run numbers, time range, time step, etc.
  - **Actor selection**: which physics codes (actors) to use for each process (e.g., ECRH, ICRH, NBI).
  - **Database and output settings** (if needed).

**Example structure:**
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
        <ec_wave_solver list="genray gray grayscale torbeam toray">3</ec_wave_solver>
      </ECRH>
      <ICRH>
        <ic_wave_solver list="pion cyrano tomcat lion">1</ic_wave_solver>
      </ICRH>
    </main_process>
  </actor_selection>
</root>
```
- The `list` attribute specifies available actors; the value (e.g., `3`) selects which one to use (0-based index).
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
- IMAS-AL-Python
- Physics actor modules (GRAYSCALE, HCD_MERGERS, etc.)
- Tkinter (for GUI)
- matplotlib (for GUI plotting)

---

## Documentation

- [Confluence Documentation](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)
- Build locally:
  ```bash
  cd docs
  pip install -e ".[docs]"
  make html
  # Open docs/build/html/index.html in browser
  ```
---

## Running the Workflow

Prereq: `source config_hcd_iter_sdcc.sh` once per shell session.

### Legacy Mode (No MUSCLE3)

```bash
./run.sh legacy
```

### Hybrid MUSCLE3 Mode

```bash
# Via MUSCLE3 manager:
muscle_manager --start-all test_hybrid_hcdwf.ymmsl

# Via runner:
./run.sh hybrid
```

### Pure MUSCLE3 Mode

Pure mode (each physics actor as an independent M3 micro model) is under active
development on a separate branch and is not runnable from this branch. The
`./run.sh pure` stub will print a notice and exit.

### Runner

`run.sh` provides a convenient wrapper for all modes:

```bash
./run.sh [legacy|hybrid|pure]   # default: hybrid
```

It automatically:
- Creates a numbered output directory under `runs/` (e.g., `runs/run_hybrid_001/`)
- Captures stdout/stderr to `output.log`
- Moves MUSCLE3 output into the run directory
- Records run metadata (date, host, user, mode) in `run_config.txt`


## File Structure

hcd-wf-sandbox/
│
├── workflow/
│   └── wf_wrapper.py              # Unified entry point (legacy + M3 macro)
│                                  #   - Database setup & I/O
│                                  #   - Time loop management
│                                  #   - DD version conversion & fix-ups
│                                  #   - IMAS compatibility layer
│
├── hcdworkflow/
│   ├── hcd_workflow.py            # Original HCDWorkflow class (shared by all modes)
│   ├── hcd_workflow_m3.py         # MUSCLE3 micro model
│   │                              #   - Receives IDS via F_INIT ports
│   │                              #   - Calls HCDWorkflow.run()
│   │                              #   - Sends results via O_F ports
│   ├── workflow_executor.py       # Actor execution
│   ├── workflow_dbhelper.py       # Database connection helper
│   ├── workflow_globals_reader.py # Global configuration reader
│   └── ...
│
├── gui/                           # GUI components
├── tools/                         # Utility tools
├── actor_install/                 # Actor installation scripts
│
├── tests/                         # Test data and configs
│
├── test_hybrid_hcdwf.ymmsl        # MUSCLE3 hybrid mode configuration
├── config_hcd_iter_sdcc.sh        # Environment setup (default: DD 4.1.0 + MUSCLE3)
├── config_hcd_iter_sdcc_3.42.0.sh # Environment setup (legacy: DD 3.42.0)
├── run.sh                         # Runner for legacy/hybrid (pure mode is WIP)
│
├── runs/                          # Auto-generated run outputs
│   ├── run_legacy_001/
│   ├── run_hybrid_001/
│   │   ├── output.log
│   │   ├── run_config.txt
│   │   └── muscle3_output/
│   └── ...
│
├── hcd_gui                        # GUI entry point
├── hcd_nogui                      # Console entry point
├── hcdslice_nogui                 # Single slice entry point
├── hcd_batch                      # Batch submission script
├── pyproject.toml                 # Project configuration
├── setup.cfg                      # Tool configurations
└── README.md                      # This file

---
## M3 Port Mapping Reference

### Macro → Micro (O_I → F_INIT)

| Port | IDS | Description |
|------|-----|-------------|
| `equilibrium_out/in` | `equilibrium` | Plasma equilibrium (with b_field fix-ups) |
| `core_profiles_out/in` | `core_profiles` | Plasma profiles (Te, ne, Ti, …) |
| `workflow_out/in` | `workflow` | Workflow control parameters |
| `ec_launchers_out/in` | `ec_launchers` | EC system configuration |
| `ic_antennas_out/in` | `ic_antennas` | IC antenna configuration |
| `core_sources_out/in` | `core_sources` | Heating sources (input from previous step) |
| `distributions_out/in` | `distributions` | Particle distribution functions |
| `distribution_sources_out/in` | `distribution_sources` | Distribution source terms |

### Micro → Macro (O_F → S)

| Port | IDS | Description |
|------|-----|-------------|
| `core_sources_out/in` | `core_sources` | Computed heating sources |
| `waves_out/in` | `waves` | Wave propagation results |
| `core_profiles_out/in` | `core_profiles` | Updated plasma profiles |
| `distributions_out/in` | `distributions` | Updated distribution functions |

---

## License

See [LICENSE.md](LICENSE.md) for details.

## Authors

ITER Organization

## Links

- [Homepage](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)
- [Documentation](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)
- [Source Code](https://git.iter.org/projects/IMAS/repos/hcd-wf)

## Support

For support and questions:
- Open an issue on the ITER JIRA
- Contact the ITER HCD Workflow development team
- Refer to the Confluence documentation


---
