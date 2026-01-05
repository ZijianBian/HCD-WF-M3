
# HCD-Workflow_M3(v0.1) + Torbeam (MUSCLE3) Benchmark

This document describes how to run the HCD-Workflow coupled with the Fortran Torbeam kernel using MUSCLE3 under the IMAS DD 4.0.0 environment.


## What DONE
This is a MUSCLE3-based refactor of the HCD workflow system. The original monolithic wrapper/driver has been split into:

- **`workflow_driver_m3.py`**: Orchestrates the simulation (time-stepping, data I/O, actor coordination)
- **`workflow_actor_m3.py`**: Generic wrapper for physics codes (TORBEAM, GRAY, etc.)

The driver reads IMAS data, broadcasts it to actors via MUSCLE3, collects results, and writes to output database.

*Key Features:*
- **DD 4.0.0 Compatibility:** The driver handles explicit data version conversion.
- **Direct Coupling:** Uses Native Fortran MUSCLE3 bindings for high performance.

---------------------------------------------------------------------------------------------

## Quick Start

### 1. Configure Environment for hcd-wf-m3

Run the setup script once to prepare everything:

```
module purge
chmod +x config_hcd_m3.sh
source config_hcd_m3.sh
```
  Note: This script will create a virtual environment in devenv_m3 and generate run_env.sh and run_benchmark.sh.


### 2. Configure for torbeam-m3 (DD v4.0.0)
 under branch * feature/imas-python
```
cd /path/to/your/torbeam/tests/test_imas/
source config_sdcc.sh 
source ci-sdcc/st01-build-code.sh 
source ci-sdcc/st02-build-actor.sh 
make torbeam_m3.exe
```

### 3. Configuration Check
Before running, open test_torbeam_fortran.ymmsl and ensure the executable path points to your compiled binary:

implementations:
  torbeam_fortran_impl:
    executable: /YOUR/PATH/TO/torbeam/tests/test_imas/build/bin/torbeam_m3.exe


### 4. Run benchmark

```bash
# Return to hcd-wf-sandbox root
./run_benchmark.sh
```

Output will be in `run_test/test001/`, `run_test/test002/`, etc. Check instances/torbeam/stdout.txt for physics output.

---

## File Structure

```
hcd-wf/
├── config_hcd_m3.sh           # One-time setup script
├── run_env.sh                 # Auto-generated: loads modules + venv
├── run_benchmark.sh           # Auto-generated: runs workflow with MUSCLE3
├── hcdworkflow                  
  ├── workflow_driver_m3.py      # Main orchestrator
  ├── workflow_actor_m3.py       # Generic actor wrapper
  ├── ...
├── run_test
  ├──test001
  ├──test002
├── test_torbeam_fortran.ymmsl         # MUSCLE3 configuration
└── tests/m3_benchmark/                # Test datasets
```