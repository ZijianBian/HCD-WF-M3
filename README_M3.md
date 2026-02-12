
# HCD-Workflow_M3 Hybrid

This document describes how to run the HCD-Workflow coupled with the Torbeam and hcd2core_sources actors using MUSCLE3 under the IMAS-Python DD 4.0.0 environment.

---------------------------------------------------------------------------------------------

## Quick Start

### 1. Configure Environment for hcd-wf-m3

Run the setup script once to prepare everything:

```
module purge
chmod +x config_hcd_iter_sdcc_m3.sh
source config_hcd_iter_sdcc_m3.sh
```
  Note: This script will create a virtual environment in devenv_m3 and generate run_env.sh and run_benchmark.sh.


### 2. Run benchmark

```bash
# Return to hcd-wf-sandbox root
./run_benchmark.sh hybrid
```

Output will be in `./runs/run_hybrid_001/`, `./runs/run_hybrid_002/`, etc. Check instances/torbeam/stdout.txt for physics output.

---

## File Structure

```
hcd-wf/
├── config_hcd_iter_sdcc_m3.sh           # One-time setup script
├── run_env_hybrid.sh                 # loads modules + venv
├── run_benchmark.sh           # Auto-generated: runs workflow with MUSCLE3
├── hcdworkflow                  
  ├── workflow_driver_m3.py      # Main orchestrator
  ├── ...
├── runs/
├── test_hybrid_hcdwf.ymmsl         # MUSCLE3 configuration
└── tests/m3_hybrid/                # Test datasets
```