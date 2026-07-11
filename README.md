# HCD Workflow

[![Development Status](https://img.shields.io/badge/status-development-yellow.svg)](https://pypi.org/project/HCDWorkflow/)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-See%20LICENSE.md-blue.svg)](LICENSE.md)

Python-based Heating and Current Drive (H&CD) Workflow for ITER plasma simulations, with MUSCLE3 integration for modular multi-scale coupling of physics actors.

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

The workflow supports four execution modes. Legacy and Hybrid use the shared
entry point `workflow/workflow_driver.py`; Pure M3 uses
`hcdworkflow/workflow_driver_m3_pure.py` because it wires the macro driver
directly to individual M3 actor executables.

```
Mode            Flag / Command    Description
─────────────── ───────────────── ──────────────────────────────────────────────────────
Legacy          m3_flag=0         All iWrap actors execute in-process.
                                  No MUSCLE3 involvement. Original behavior.

Hybrid M3       m3_flag=1         Two-component MUSCLE3 coupling:
                                  workflow_driver.py (macro) handles DB I/O and the
                                  time loop; hcd_workflow_m3.py (micro) runs
                                  iWrap actors in a separate process.
                                  IDS are exchanged via M3 conduits.

Pure M3         yMMSL             Actor-level MUSCLE3 coupling:
                                  workflow_driver_m3_pure.py talks directly to
                                  M3 actor executables such as torbeam_m3.exe
                                  and cyrano_m3.exe. The maintained baseline is
                                  `hcdwf_pure_m3.ymmsl`.

Pure + Rabbit   yMMSL             Extends Pure M3 with the external GCC Rabbit
                                  NBI actor. The topology is
                                  `hcdwf_pure_rabbit_m3.ymmsl`.
```

### MUSCLE3 Hybrid Architecture

```
workflow_driver.py     (MACRO — one reuse_instance() containing the full time loop)
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

### Pure M3 Architecture

```
workflow_driver_m3_pure.py  (MACRO — database I/O and time loop)
    ├── torbeam_m3.exe
    ├── cyrano_m3.exe
    ├── merge_waves_m3.exe
    ├── rabbit_m3.exe  (optional GCC process)
    └── hcd2core_sources_m3.exe
```

Pure M3 is the direct actor-coupling path. ``hcdwf_pure_m3.ymmsl`` is the
maintained no-Rabbit baseline. ``hcdwf_pure_rabbit_m3.ymmsl`` adds Rabbit, but
its NBI waveform and Rabbit code parameters are deliberately local and must be
provided under ``tests/m3_pure_rabbit``. The Pure driver supports EC-only,
IC-only, and combined operation without imposing an EC/IC output order.
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

Use this environment only for legacy, non-MUSCLE3 runs. It is not intended for
Hybrid M3 or Pure M3 yMMSL cases.

```bash
source config_hcd_iter_sdcc_3.42.0.sh

# Console entry point:
hcd_nogui -c tests/data/GRAYSCALE

# Equivalent direct driver call:
python workflow/workflow_driver.py tests/data/GRAYSCALE 0
```

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

# iWrap (optional local develop checkout)
export HCDWF_IWRAP_ROOT=/path/to/iwrap
export PATH=$HCDWF_IWRAP_ROOT/bin:$PATH
export PYTHONPATH=$HCDWF_IWRAP_ROOT/python:$PYTHONPATH

# Actor and sandbox paths
export ACTOR_FOLDER=/path/to/PYTHON_ACTORS
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

- **Multiple Execution Modes**: Console, GUI, batch, single time-slice, Legacy, Hybrid M3, and Pure M3
- **MUSCLE3 Integration**: Modular multi-scale coupling via macro/micro architecture
- **Pure M3 Actor Coupling**: Direct macro-to-actor M3 execution through a single maintained Pure yMMSL topology
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
A typical configuration folder (e.g., `tests/data/GRAYSCALE`) contains:
- `input_workflow.xml` (main workflow definition)
- `ec_waveforms.yaml`, `ic_waveforms.yaml`, etc. (optional, for time-dependent scenarios)

You can run the workflow using:
```bash
hcd_nogui -c tests/data/GRAYSCALE
hcdslice_nogui -c tests/data/GRAYSCALE
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

For current M3 development runs, source the DD 4.1.0 helper once per shell
session:

```bash
source config_hcd_iter_sdcc.sh
```

### Legacy Mode, DD 4.1.0 Smoke Case

```bash
./run.sh legacy
```

### Legacy Compatibility Mode, DD 3.42.0

Use this path when you need the older IMAS-AL-Python 5.x / DD 3.42.0 stack,
for example for legacy actor builds, old `tests/data/` cases, or JINTRAC
coupling checks.

```bash
source config_hcd_iter_sdcc_3.42.0.sh
hcd_nogui -c tests/data/GRAYSCALE

# Or call the driver directly:
python workflow/workflow_driver.py tests/data/GRAYSCALE 0
```

Do not use the DD 3.42.0 environment for `./run.sh hybrid`, `./run.sh pure`,
`./run.sh pure-rabbit`, or `muscle_manager --start-all ...`; those paths are
for the DD 4.1.0/MUSCLE3 environment.

### Hybrid MUSCLE3 Mode

```bash
# Via MUSCLE3 manager:
muscle_manager --start-all hcdwf_hybrid_m3.ymmsl

# Via runner:
./run.sh hybrid
```

### Pure MUSCLE3 Mode

Pure mode runs each selected physics actor as an independent M3 micro model.
The default runner uses `hcdwf_pure_m3.ymmsl`, the maintained no-Rabbit
actor-level topology.

```bash
# Via MUSCLE3 manager:
muscle_manager --start-all hcdwf_pure_m3.ymmsl

# Via runner:
./run.sh pure
```

Pure yMMSL files:

- `hcdwf_pure_m3.ymmsl`: Torbeam, Cyrano, merge_waves, and
  hcd2core_sources baseline.
- `hcdwf_pure_rabbit_m3.ymmsl`: adds Rabbit distributions and
  distribution_sources. It requires a local `tests/m3_pure_rabbit` case and
  `$ACTOR_FOLDER/rabbit/rabbit_m3.exe`.

Rabbit is compiled with GCC and must not be loaded into the main Intel HCD
shell. `tools/run_rabbit_m3_gcc_2023b.sh` switches the module stack inside the
Rabbit child process while keeping the MUSCLE3 0.8/DD 4.1.0 wire contract.

```bash
./run.sh pure-rabbit
# or, after providing the local Rabbit case:
muscle_manager --start-all hcdwf_pure_rabbit_m3.ymmsl
```

### Runner

`run.sh` provides a convenient wrapper for all modes:

```bash
./run.sh [legacy|hybrid|pure|pure-rabbit]   # default: hybrid
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
│   ├── workflow_driver.py        # Unified entry point (legacy + Hybrid M3 macro)
│                                  #   - Database setup & I/O
│                                  #   - Time loop management
│                                  #   - DD version conversion & fix-ups
│                                  #   - IMAS compatibility layer
│   ├── ids_prep.py               # IDS preparation and DD compatibility helpers
│   └── wf_wrapper.py             # Backward-compatible shim; not the main driver
│
├── hcdworkflow/
│   ├── hcd_workflow.py            # Original HCDWorkflow class (shared by all modes)
│   ├── hcd_workflow_m3.py         # MUSCLE3 micro model
│   │                              #   - Receives IDS via F_INIT ports
│   │                              #   - Calls HCDWorkflow.run()
│   │                              #   - Sends results via O_F ports
│   ├── workflow_driver_m3_pure.py # Pure M3 macro driver for direct actor coupling
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
├── hcdwf_hybrid_m3.ymmsl          # MUSCLE3 Hybrid configuration
├── hcdwf_pure_m3.ymmsl            # Pure M3 baseline configuration
├── hcdwf_pure_rabbit_m3.ymmsl     # Pure M3 + external Rabbit topology
├── config_hcd_iter_sdcc.sh        # Environment setup (default: DD 4.1.0 + MUSCLE3)
├── config_hcd_iter_sdcc_3.42.0.sh # Environment setup (legacy: DD 3.42.0)
├── run.sh                         # Runner for all four execution modes
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

### Hybrid Macro → Micro (O_I → F_INIT)

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

### Hybrid Micro → Macro (O_F → S)

| Port | IDS | Description |
|------|-----|-------------|
| `core_sources_out/in` | `core_sources` | Computed heating sources |
| `waves_out/in` | `waves` | Wave propagation results |
| `core_profiles_out/in` | `core_profiles` | Updated plasma profiles |
| `distributions_out/in` | `distributions` | Updated distribution functions |

Pure M3 uses actor-specific ports defined in `hcdwf_pure_m3.ymmsl` and
`hcdwf_pure_rabbit_m3.ymmsl`.

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
