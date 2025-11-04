# HCD Workflow

[![Development Status](https://img.shields.io/badge/status-development-yellow.svg)](https://pypi.org/project/HCDWorkflow/)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-See%20LICENSE.md-blue.svg)](LICENSE.md)

Python-based Heating and Current Drive (H&CD) Workflow for ITER plasma simulations.

---

## 🚀 Quick Start

| Audience   | Recommended Setup                | Command/Script                        |
|------------|----------------------------------|---------------------------------------|
| **User**   | EasyBuild module (SDCC)          | `module load HCD-WF`                  |
| **User**   | SDCC Helper Script (SDCC)        | `./config_hcd_iter_sdcc.sh`           |
| **Developer** | SDCC Helper Script (SDCC)     | `./config_hcd_iter_sdcc.sh`           |
| **Developer** | Manual Setup (any system)     | See [Developer Setup](#developer-setup) |

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
./config_hcd_iter_sdcc.sh           # Uses default DD version (3.42.0)
./config_hcd_iter_sdcc.sh 4.0.0     # Use a different DD version if supported
# Optionally set ACTOR_FOLDER for local actors:
ACTOR_FOLDER=~/public/PYTHON_ACTORS ./config_hcd_iter_sdcc.sh
```

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

### 1. On ITER SDCC: Use the Helper Script (Recommended)

```bash
./config_hcd_iter_sdcc.sh
```
- Loads modules, sets up Python venv, installs all dependencies (including dev tools)

### 2. Manual Setup (Any System)

```bash
# Clone the repository
git clone ssh://git@git.iter.org/wf/hcd-wf.git
cd hcd-wf

# Create virtual environment
python -m venv devenv
source devenv/bin/activate

# Install in editable mode with dev dependencies
pip install -e "[dev]"

# Load required modules (SDCC only)
module load Tkinter matplotlib IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
```

### 3. Code Quality & Testing

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

### 4. Installing Custom Actors

```bash
cd actor_install
python actor_install.py --skipModules *.yml      # Install all actors
python actor_install.py --skipModules grayscale.yml  # Install specific actor
```

---

## Features

- **Multiple Execution Modes**: Console, GUI, batch, single time-slice
- **Flexible Actor System**: Easy integration of new physics codes
- **IMAS Integration**: Full compatibility with IMAS IDSes
- **Time-Loop Execution**: Automated multi-timepoint simulations
- **HPC Support**: SLURM batch job submission
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
├── tests/                 # Test data
├── ci-sdcc/               # CI/CD scripts
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

## Troubleshooting

- **Module import errors**: Load required IMAS modules: `module load IMAS-AL-Python`

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run code quality checks: `black`, `flake8`, `pylint`
4. Test your changes: `hcdslice_nogui -c tests/data/GRAYSCALE/`
5. Commit: `git commit -am "Add feature"`
6. Push: `git push origin feature/my-feature`
7. Create a Pull Request

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
