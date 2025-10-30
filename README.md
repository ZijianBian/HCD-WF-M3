# HCD Workflow

[![Development Status](https://img.shields.io/badge/status-production-green.svg)](https://pypi.org/project/HCDWorkflow/)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-See%20LICENSE.md-blue.svg)](LICENSE.md)

Python-based Heating and Current Drive (H&CD) Workflow for ITER plasma simulations.

## Overview

HCD Workflow is a comprehensive workflow management system designed to orchestrate various heating and current drive simulation codes for ITER tokamak plasma physics analysis. It provides integration for:

- **ECRH** (Electron Cyclotron Resonance Heating): GRAY, GRAYSCALE, TORBEAM, TORAY, GENRAY
- **ICRH** (Ion Cyclotron Resonance Heating): CYRANO, TOMCAT, PION, LION
- **NBI** (Neutral Beam Injection): NEMO, BBNBI, ASCOT, SPOT, RISK, NBISIM
- **LHCD** (Lower Hybrid Current Drive): LHCD-METIS
- **Post-processing**: HCD2CORE_SOURCES, HCD2CORE_PROFILES, Mergers

## Quick Start

### For Users (Recommended)

If you just want to run simulations, use the pre-installed EasyBuild module:

```bash
# Load the workflow module
module load HCD-WF

# All dependent actors will be automatically loaded along with other dependencies
# Loads mandatory actors
module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0

# Loads main actors for your simulation:
# EC: GRAYSCALE, GRAY, TORBEAM, TORAY, GENRAY
# IC: CYRANO, FoPla, StixReDist, TOMCAT
# NBI: NEMO, NBISIM, RISK, SPOT
# Other: RELAX, SMART, FPSIM

# Example: Loads GRAYSCALE for EC heating
module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0

# Optional: suppress verbose warnings
export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1

# Run a simulation
hcd_nogui -c tests/data/GRAYSCALE/

# Or use the GUI
hcd_gui
```

### For Developers

If you need to modify or develop the workflow:

```bash
# Clone the repository
git clone ssh://git@git.iter.org/wf/hcd-wf.git
cd hcd-wf

# Setup Python environment
module load Python
python -m venv devenv
source devenv/bin/activate

# Install in editable mode
pip install -e .

# Load required modules
module load Tkinter
module load matplotlib
module load waveform-cooker
module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0

# Load actor modules (available at /work/imas/etc/modules/all)
module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
module load HCD2CORE_SOURCES/1.2.0-intel-2023b-DD-3.42.0
module load HCD2CORE_PROFILES/1.1.0-intel-2023b-DD-3.42.0
module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
# Load additional actors as needed (see /work/imas/etc/modules/all)

# Run tests
hcd_nogui -c tests/data/GRAYSCALE/
```

## Features

- **Multiple Execution Modes**: Console, GUI, batch, single time-slice
- **Flexible Actor System**: Easy integration of new physics codes
- **IMAS Integration**: Full compatibility with IMAS IDSes
- **Time-Loop Execution**: Automated multi-timepoint simulations
- **HPC Support**: SLURM batch job submission
- **Waveform Management**: Integration with Waveform Cooker
- **Modular Design**: Clean separation of workflow logic and physics codes

## Commands

### `hcd_gui`
Interactive graphical interface for workflow configuration and execution.

```bash
hcd_gui
```

### `hcd_nogui`
Console-based workflow execution with time-loop.

```bash
hcd_nogui -c <configuration_folder>
```

### `hcdslice_nogui`
Execute workflow for a single time slice (useful for testing).

```bash
hcdslice_nogui -c <configuration_folder>
```

### `hcd_batch`
Submit workflow as a batch job to SLURM scheduler.

```bash
hcd_batch -n <nproc> -t <hours> -e <email> -q <queue> -c <config_folder>
```

Example:
```bash
hcd_batch -n 1 -t 2 -e user@iter.org -q all -c tests/data/GRAYSCALE/
```

## Documentation

Full documentation is available at:
- [Confluence Page](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)

Build documentation locally:

```bash
cd docs
pip install -e ".[docs]"
make html
# Open docs/build/html/index.html in browser
```

## Installation Methods

### Method 1: EasyBuild Module (Users)

```bash
module load HCD-WF
```

This is the recommended method for users who just want to run simulations.

### Method 2: pip install (Developers)

```bash
# From source
git clone ssh://git@git.iter.org/wf/hcd-wf.git
cd hcd-wf
pip install .

# Or in editable mode for development
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

### Method 3: Build from source

```bash
# Build distribution
python -m build

# Install the wheel
pip install dist/HCDWorkflow-<version>-py3-none-any.whl
```

## Configuration

### Basic Configuration

The main configuration file is `input_workflow.xml`:

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
    </main_process>
  </actor_selection>
</root>
```

### Waveform Files

Create YAML waveform files for time-dependent parameters:
- `ec_waveforms.yaml` - ECRH waveforms
- `ic_waveforms.yaml` - ICRH waveforms  
- `nbi_waveforms.yaml` - NBI waveforms
- `lh_waveforms.yaml` - LHCD waveforms

## Project Structure

```
hcd-wf/
├── hcdworkflow/           # Main workflow package
│   ├── hcd_workflow.py    # Main workflow logic
│   ├── workflow_driver.py # Time-loop driver
│   ├── workflow_executor.py # Actor execution
│   └── global_configuration/ # Default configs
├── gui/                   # GUI components
├── tools/                 # Utility tools
├── workflow/              # Workflow wrapper
├── actor_install/         # Actor installation scripts
├── tests/                 # Test data
├── ci-sdcc/              # CI/CD scripts
├── hcd_gui               # GUI entry point
├── hcd_nogui             # Console entry point
├── hcdslice_nogui        # Single slice entry point
├── hcd_batch             # Batch submission script
├── pyproject.toml        # Project configuration
├── setup.cfg             # Tool configurations
└── README.md             # This file
```

## Requirements

- Python >= 3.8
- lxml >= 4.6.0
- numpy >= 1.20.0
- pyparsing >= 2.4.0
- python-dateutil >= 2.8.0
- pyyaml >= 5.4.0
- six >= 1.15.0

### Runtime Dependencies

- IMAS-AL-Python (ITER Integrated Modelling & Analysis Suite)
- Physics actor modules (GRAYSCALE, HCD_MERGERS, etc.)
- Tkinter (for GUI)
- matplotlib (for GUI plotting)

## Development

### Setup Development Environment

```bash
# Clone and setup
git clone ssh://git@git.iter.org/wf/hcd-wf.git
cd hcd-wf
git checkout develop

# Create virtual environment
module load Python
python -m venv devenv
source devenv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Load required modules
module load Tkinter matplotlib
module load IMAS-AL-Python/5.4.0-intel-2023b-DD-3.42.0
module load GRAYSCALE/1.1.0-intel-2023b-DD-3.42.0
module load HCD_MERGERS/1.0.0-intel-2023b-DD-3.42.0
```

### Code Quality

Run static analysis:

```bash
# Format code
black --line-length 120 hcdworkflow/ gui/ tools/ workflow/

# Check style
flake8 --max-line-length=120 --ignore=E203,W503 hcdworkflow/

# Run linter
pylint --max-line-length=120 hcdworkflow/

# Or use the CI script
bash ci-sdcc/st05-staticanalysis.sh
```

### Installing Custom Actors

For testing actors under development:

```bash
cd actor_install

# Install all actors
python actor_install.py --skipModules *.yml

# Install specific actor
python actor_install.py --skipModules grayscale.yml
```

## Examples

### Example 1: ECRH Simulation

```bash
module load HCD-WF
export IMAS_AL_DISABLE_OBSOLESCENT_WARNING=1
hcd_nogui -c tests/data/GRAYSCALE/
```

### Example 2: Batch Job

```bash
module load HCD-WF
hcd_batch -n 4 -t 8 -e user@iter.org -q all -c my_config/

# Monitor job
squeue -u $USER
tail -f auto_batch_*.o<jobid>
```

### Example 3: Interactive GUI

```bash
module load HCD-WF
hcd_gui
# Use GUI to configure and run workflow
```

### Example 4: Single Time Slice Test

```bash
module load HCD-WF
hcdslice_nogui -c my_config/
```

## Troubleshooting

### Common Issues

**KeyError: 'equilibrium_solver'**
- Solution: Ensure all processes in the algorithm are configured in your XML

**NameError: name 'logger' is not defined**
- This is a known issue in `hcdslice_nogui`, will be fixed in next release

**Module import errors**
- Solution: Load required IMAS modules: `module load IMAS-AL-Python`

**Permission denied on batch submission**
- Solution: Check SLURM partition name with `sinfo`

### Getting Help

- Check the [Confluence documentation](https://confluence.iter.org/pages/viewpage.action?pageId=252217231)
- Review the `/docs` folder for detailed guides
- Contact ITER HCD Workflow team

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run code quality checks: `black`, `flake8`, `pylint`
4. Test your changes: `hcdslice_nogui -c tests/data/GRAYSCALE/`
5. Commit: `git commit -am "Add feature"`
6. Push: `git push origin feature/my-feature`
7. Create a Pull Request

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
