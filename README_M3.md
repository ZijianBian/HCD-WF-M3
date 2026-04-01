# HCD Workflow — MUSCLE3 Integration (`M3-develop`)

MUSCLE3-based execution modes for the ITER Heating and Current Drive workflow, enabling modular coupling of plasma physics actors.

## What Has Been Done

### Three Execution Modes

The workflow now supports three execution modes via a unified entry point (`wf_wrapper_m3.py`):

Mode            Flag / Command    Description
─────────────── ───────────────── ──────────────────────────────────────────────────
Traditional     m3_flag=0         All iWrap actors execute in-process.
                                  No MUSCLE3 involvement. Original behavior.

Hybrid M3       m3_flag=1         Two-component MUSCLE3 coupling:
                                  wf_wrapper_m3.py (macro) handles DB I/O and the time loop;
                                  hcd_workflow_m3.py (micro) runs iWrap actors in a separate process.
                                  IDS are exchanged via M3 conduits.

Direct M3       (planned)         Each physics actor (Torbeam, Cyrano, …) runs as an independent M3 micro model,
                                  coupled directly to a single macro driver.

### MUSCLE3 Hybrid Architecture

wf_wrapper_m3.py  (MACRO — one reuse_instance() containing the full time loop)
    ├── Opens input / output / machine databases
    ├── Reads IDS slices at each timestep
    ├── Sends IDS to micro via O_I ports ───────────┐
    ├── Receives updated IDS from micro via S ports │
    └── Writes results to output database           │
                                                    │
                    M3 conduits (serialized IDS)    │
                                                    │
hcd_workflow_m3.py  (MICRO — one reuse_instance() per timestep)
    ├── Receives IDS from macro via F_INIT ports ◄──┘
    ├── Calls HCDWorkflow.run()
    │     └── iWrap actors (Torbeam, Cyrano, FoPla, hcd2core_sources, …)
    │         execute internally — invisible to MUSCLE3
    └── Sends output IDS back to macro via O_F ports


## Quick Start

### Prerequisites

- **ITER SDCC environment** (modules: `IMAS-Python`, `IMAS-Fortran`, `IDStools`, `MUSCLE3`, `XMLlib`, `INTERPOS`, `Waveform-Cooker`)
- Python 3.x with `numpy`, `scipy`
- MUSCLE3 Python library (`libmuscle`)
- iWrap (from schneim's develop branch)
- Physics actors deployed in `ACTOR_FOLDER` (Torbeam, Cyrano, FoPla, etc.)

### Environment Setup

```bash
source config_hcd_iter_sdcc_m3.sh
```

This script:
1. Loads all required SDCC modules (`IMAS-Python`, `MUSCLE3`, etc.)
2. Sets up iWrap and Waveform Cooker paths
3. Configures `ACTOR_FOLDER` and `HCD_SANDBOX` in `PYTHONPATH`
4. Creates/activates a Python virtual environment (`devenv_m3`) with `muscle3` installed
5. Runs diagnostic checks (IMAS version, iWrap availability, actor folder contents)

### Input Data Preparation

Place your test configuration in a folder (e.g., `tests/m3_hybrid/`) containing:

- `input_workflow.xml` — workflow parameters (shot number, run numbers, database paths, time range, actor selection)
- `*_waveforms.yaml` — waveform cooker configurations (EC/IC launcher waveforms)
- Actor-specific XML configs (`input_torbeam.xml`, `input_cyrano.xml`, etc.)

## Running the Workflow

### Traditional Mode (No MUSCLE3)

```bash
# Via benchmark runner:
./run_benchmark.sh traditional
```

### Hybrid MUSCLE3 Mode

```bash
# Via MUSCLE3 manager:
muscle_manager --start-all test_hybrid_hcdwf.ymmsl

# Via benchmark runner:
./run_benchmark.sh hybrid
```

### Direct MUSCLE3 Mode *(Planned)*

```bash
./run_benchmark.sh direct
```

### Benchmark Runner

`run_benchmark.sh` provides a convenient wrapper for all modes:

```bash
./run_benchmark.sh [traditional|direct|hybrid]
```

It automatically:
- Creates a numbered output directory under `runs/` (e.g., `runs/run_hybrid_001/`)
- Captures stdout/stderr to `output.log`
- Moves MUSCLE3 output into the run directory
- Records run metadata (date, host, user, mode) in `run_config.txt`

## File Structure

```
hcd-wf-sandbox/
│
├── workflow/
│   └── wf_wrapper_m3.py          # Unified entry point (macro in M3 mode)
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
│   ├── workflow_executor.py       # Actor execution engine (iWrap integration)
│   ├── workflow_dbhelper.py       # Database connection helper
│   ├── workflow_globals_reader.py # Global configuration reader
│   └──....
├── tests/
│
├── test_hybrid_hcdwf.ymmsl        # MUSCLE3 hybrid mode configuration
├── config_hcd_iter_sdcc_m3.sh     # Environment setup script (SDCC)
├── run_benchmark.sh               # Benchmark runner (all 3 modes)
│
├── runs/                          # Auto-generated benchmark outputs
│   ├── run_traditional_001/
│   ├── run_hybrid_001/
│   │   ├── output.log
│   │   ├── run_config.txt
│   │   └── muscle3_output/
│   └── ...
```

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


