"""Bind MUSCLE3 topologies to saved cases for the GUI and command-line launcher."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXECUTION_MODES = ("legacy", "hybrid", "pure")
DEFAULT_EXECUTION_MODE = "legacy"
_DEFAULT_YMMSL_FILES = {
    "hybrid": "topologies/hybrid.ymmsl",
    "pure": "topologies/pure.ymmsl",
}

# These are the direct-actor choices currently understood by the maintained
# Pure M3 drivers and topology templates.
_PURE_COMPONENT_SELECTIONS = {
    "torbeam": ("ec_wave_solver", 4),
    "cyrano": ("ic_wave_solver", 1),
    "fopla": ("ic_wave_fp", 2),
    "rabbit": ("nbi_fp", 1),
    "hcd2core_sources": ("fill_core_sources", 1),
}

_PURE_CODE_PARAMETER_FILES = {
    "torbeam": Path("ECRH/ec_wave_solver/input_torbeam.xml"),
    "cyrano": Path("ICRH/ic_wave_solver/input_cyrano.xml"),
    "fopla": Path("ICRH/ic_wave_fp/input_fopla.xml"),
    "rabbit": Path("NBI/nbi_fp/input_rabbit.xml"),
    "hcd2core_sources": Path("source/fill_core_sources/input_hcd2core_sources.xml"),
}

_KNOWN_DRIVER_SCRIPTS = (
    "workflow/workflow_driver.py",
    "hcdworkflow/hcd_workflow_m3.py",
    "hcdworkflow/workflow_driver_m3_pure.py",
    "scripts/run_rabbit_m3.sh",
)

_MODE_DRIVER_SCRIPTS = {
    "hybrid": {
        "workflow/workflow_driver.py",
        "hcdworkflow/hcd_workflow_m3.py",
    },
    "pure": {"hcdworkflow/workflow_driver_m3_pure.py"},
}

PathInput = str | os.PathLike


class LaunchConfigurationError(ValueError):
    """A selected launch mode or topology cannot safely be used."""


@dataclass(frozen=True)
class MuscleLaunchPlan:
    """The files generated for one Hybrid or Pure GUI launch."""

    mode: str
    configuration_directory: Path
    source_topology: Path
    run_directory: Path
    generated_topology: Path
    log_file: Path


def normalize_execution_mode(value: object) -> str:
    """Return a supported, lower-case execution mode."""

    if value is None:
        return DEFAULT_EXECUTION_MODE
    mode = str(value).strip().lower()
    if not mode:
        return DEFAULT_EXECUTION_MODE
    if mode not in EXECUTION_MODES:
        raise LaunchConfigurationError(
            "Unknown execution mode {!r}; choose one of {}.".format(value, ", ".join(EXECUTION_MODES))
        )
    return mode


def requires_ymmsl(mode: object) -> bool:
    """Whether a mode is launched by MUSCLE3 Manager."""

    return normalize_execution_mode(mode) != DEFAULT_EXECUTION_MODE


def repository_root(repository_root: PathInput | None = None) -> Path:
    """Locate the source-tree root that contains workflow entry points."""

    if repository_root is not None:
        return Path(repository_root).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def default_ymmsl_path(mode: object, repository_root_path: PathInput | None = None) -> Path | None:
    """Return the recommended bundled topology path for Hybrid or Pure."""

    normalized_mode = normalize_execution_mode(mode)
    filename = _DEFAULT_YMMSL_FILES.get(normalized_mode)
    if filename is None:
        return None
    return repository_root(repository_root_path) / filename


def _configuration_directory(config_directory: PathInput) -> Path:
    config_path = Path(config_directory).expanduser().resolve()
    input_file = config_path / "input_workflow.xml"
    if not input_file.is_file():
        raise LaunchConfigurationError(f"No input_workflow.xml found in configuration folder {config_path}.")
    return config_path


def selected_ymmsl_path(mode: object, topology_file: PathInput | None) -> Path | None:
    """Validate and normalize a user-selected yMMSL file."""

    if not requires_ymmsl(mode):
        return None
    if topology_file is None or not str(topology_file).strip():
        raise LaunchConfigurationError(f"{normalize_execution_mode(mode).title()} mode requires a yMMSL topology file.")

    path = Path(topology_file).expanduser().resolve()
    if path.suffix.lower() != ".ymmsl":
        raise LaunchConfigurationError(f"Topology file must have a .ymmsl extension: {path}")
    if not path.is_file():
        raise LaunchConfigurationError(f"Selected yMMSL file does not exist: {path}")
    if not os.access(str(path), os.R_OK):
        raise LaunchConfigurationError(f"Selected yMMSL file is not readable: {path}")
    return path


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise LaunchConfigurationError(
            "PyYAML is unavailable. Source config_hcd_iter_sdcc.sh and restart hcd_gui."
        ) from exc

    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise LaunchConfigurationError(f"Cannot read yMMSL file {path}: {exc}") from exc
    if not isinstance(content, dict):
        raise LaunchConfigurationError(f"yMMSL file {path} does not contain a mapping.")
    return content


def _write_yaml(path: Path, content: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise LaunchConfigurationError("PyYAML is unavailable.") from exc

    try:
        path.write_text(
            yaml.safe_dump(content, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
    except (OSError, yaml.YAMLError) as exc:
        raise LaunchConfigurationError(f"Cannot write yMMSL file {path}: {exc}") from exc


def _mapping(parent: dict[str, Any], name: str, source: Path) -> dict[str, Any]:
    value = parent.get(name)
    if not isinstance(value, dict):
        raise LaunchConfigurationError(f"Selected yMMSL file {source} has no {name} mapping.")
    return value


def _validate_topology_mode(topology: dict[str, Any], mode: str, source: Path) -> None:
    """Require the selected mode's drivers in implementations used by the model."""

    model = _mapping(topology, "model", source)
    components = _mapping(model, "components", source)
    implementations = _mapping(topology, "implementations", source)
    known_drivers = set().union(*_MODE_DRIVER_SCRIPTS.values())
    used_drivers = set()
    for component_name, component in components.items():
        implementation_name = component.get("implementation") if isinstance(component, dict) else None
        implementation = implementations.get(implementation_name) if isinstance(implementation_name, str) else None
        if not isinstance(implementation, dict):
            raise LaunchConfigurationError(f"Component {component_name} in {source} needs a defined implementation.")
        arguments = implementation.get("args", [])
        if not isinstance(arguments, list):
            raise LaunchConfigurationError(f"Implementation {implementation_name} in {source} needs an args list.")
        for argument in arguments:
            if not isinstance(argument, str):
                continue
            normalized = argument.replace("\\", "/")
            for script in known_drivers:
                if normalized == script or normalized.endswith("/" + script):
                    used_drivers.add(script)

    expected_drivers = _MODE_DRIVER_SCRIPTS[mode]
    if used_drivers != expected_drivers:
        raise LaunchConfigurationError(
            "Selected topology {} does not match {} mode: expected drivers {}; "
            "found {} in the model's active implementations.".format(
                source,
                mode,
                ", ".join(sorted(expected_drivers)),
                ", ".join(sorted(used_drivers)) or "none",
            )
        )


def _replace_configuration_reference(value: Any, original: str, replacement: str) -> Any:
    """Replace exact configuration paths and paths rooted below them."""

    if isinstance(value, dict):
        return {key: _replace_configuration_reference(item, original, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_configuration_reference(item, original, replacement) for item in value]
    if isinstance(value, str):
        original_clean = original.rstrip("/")
        if value == original_clean:
            return replacement
        if original_clean and value.startswith(original_clean + "/"):
            return replacement + value[len(original_clean) :]
    return value


def _rewrite_driver_script_paths(topology: dict[str, Any], root: Path, source: Path) -> None:
    """Make bundled entry points independent of Manager's CWD."""

    implementations = _mapping(topology, "implementations", source)
    for implementation in implementations.values():
        if not isinstance(implementation, dict):
            continue
        args = implementation.get("args")
        if not isinstance(args, list):
            continue
        for index, argument in enumerate(args):
            if not isinstance(argument, str):
                continue
            normalized_argument = argument.replace("\\", "/")
            for script in _KNOWN_DRIVER_SCRIPTS:
                if normalized_argument == script or normalized_argument.endswith("/" + script):
                    args[index] = str(root / script)
                    break


def _actor_selections(config_path: Path) -> dict[str, int]:
    try:
        root = ET.parse(str(config_path / "input_workflow.xml")).getroot()
    except (OSError, ET.ParseError) as exc:
        raise LaunchConfigurationError(f"Cannot read input_workflow.xml in {config_path}: {exc}") from exc

    actor_selection = root.find("actor_selection")
    if actor_selection is None:
        raise LaunchConfigurationError("input_workflow.xml has no actor_selection section.")

    selections: dict[str, int] = {}
    for element in actor_selection.iter():
        if "list" not in element.attrib:
            continue
        try:
            selections[element.tag] = int((element.text or "").strip())
        except ValueError as exc:
            raise LaunchConfigurationError(f"Actor selection {element.tag} is not an integer index.") from exc
    return selections


def _select_pure_components(topology: dict[str, Any], selections: dict[str, int], source: Path) -> None:
    """Remove disabled direct actors from a reusable Pure topology template."""

    model = _mapping(topology, "model", source)
    components = _mapping(model, "components", source)
    disabled = {
        component for component, (process, _) in _PURE_COMPONENT_SELECTIONS.items() if selections.get(process, 0) == 0
    }
    if selections.get("ec_wave_solver", 0) != 4 or selections.get("ic_wave_solver", 0) != 1:
        disabled.add("merge_waves")

    removed_implementations = {
        components.pop(component)["implementation"] for component in disabled if component in components
    }
    used_implementations = {component["implementation"] for component in components.values()}
    implementations = _mapping(topology, "implementations", source)
    for implementation in removed_implementations - used_implementations:
        implementations.pop(implementation, None)

    def is_disabled(reference: str) -> bool:
        return reference.split(".", 1)[0].split("[", 1)[0] in disabled

    conduits = _mapping(model, "conduits", source)
    for sender, receiver in list(conduits.items()):
        if is_disabled(sender):
            del conduits[sender]
        elif isinstance(receiver, list):
            remaining = [endpoint for endpoint in receiver if not is_disabled(endpoint)]
            if remaining:
                conduits[sender] = remaining
            else:
                del conduits[sender]
        elif is_disabled(receiver):
            del conduits[sender]

    for name in ("resources", "settings"):
        if name not in topology:
            continue
        mapping = _mapping(topology, name, source)
        for key in list(mapping):
            if is_disabled(key):
                del mapping[key]


def _validate_pure_topology(topology: dict[str, Any], selections: dict[str, int], source: Path) -> None:
    """Require direct actors wired in yMMSL to match GUI actor selection."""

    model = _mapping(topology, "model", source)
    components = _mapping(model, "components", source)
    mismatches: list[str] = []

    for component, (process, required_index) in _PURE_COMPONENT_SELECTIONS.items():
        topology_enabled = component in components
        gui_enabled = selections.get(process, 0) == required_index
        if topology_enabled != gui_enabled:
            expected_actor = "selected" if topology_enabled else "not selected"
            mismatches.append(f"{component} must be {expected_actor} in GUI ({process})")

    torbeam_enabled = "torbeam" in components
    cyrano_enabled = "cyrano" in components
    merge_waves_enabled = "merge_waves" in components
    if merge_waves_enabled and not (torbeam_enabled and cyrano_enabled):
        mismatches.append("merge_waves requires both torbeam and cyrano")
    if torbeam_enabled and cyrano_enabled and not merge_waves_enabled:
        mismatches.append("torbeam plus cyrano requires merge_waves")
    if "rabbit" in components and "fopla" in components:
        mismatches.append("Rabbit and FoPla cannot be connected in the same Pure topology")
    if "fopla" in components and not cyrano_enabled:
        mismatches.append("FoPla requires Cyrano in Pure mode")

    direct_processes = set(process for process, _ in _PURE_COMPONENT_SELECTIONS.values())
    for process, selected_index in selections.items():
        if selected_index == 0:
            continue
        if process in direct_processes:
            allowed_indexes = {
                required_index
                for selected_process, required_index in _PURE_COMPONENT_SELECTIONS.values()
                if selected_process == process
            }
            if selected_index in allowed_indexes:
                continue
            mismatches.append(f"{process}={selected_index} is not supported by this Pure topology")
            continue
        mismatches.append(f"{process}={selected_index} has no direct actor in this Pure topology")

    if mismatches:
        raise LaunchConfigurationError(
            "Pure topology and GUI actor selection do not match:\n- "
            + "\n- ".join(mismatches)
            + "\nChoose a matching yMMSL file or change the actor selection before running."
        )


def _rewrite_pure_code_parameters(topology: dict[str, Any], config_path: Path, source: Path) -> None:
    """Bind known direct-actor code parameters to the saved GUI case."""

    settings = _mapping(topology, "settings", source)
    components = _mapping(_mapping(topology, "model", source), "components", source)
    unknown_code_parameters = [
        setting
        for setting in settings
        if setting.endswith(".code_parameters") and setting.split(".", 1)[0] not in _PURE_CODE_PARAMETER_FILES
    ]
    missing_code_parameters: list[Path] = []
    # Bind every selected actor, even when a custom template omits its setting.
    for component in components:
        relative_path = _PURE_CODE_PARAMETER_FILES.get(component)
        if relative_path is None:
            continue
        code_parameters = config_path / relative_path
        if not code_parameters.is_file():
            missing_code_parameters.append(code_parameters)
            continue
        settings[component + ".code_parameters"] = str(code_parameters)

    errors: list[str] = []
    if unknown_code_parameters:
        errors.append("unrecognized code-parameter settings: " + ", ".join(unknown_code_parameters))
    if missing_code_parameters:
        errors.append(
            "missing saved GUI code-parameter files: " + ", ".join(str(path) for path in missing_code_parameters)
        )
    if errors:
        raise LaunchConfigurationError("Cannot prepare Pure topology; " + "; ".join(errors) + ".")


def materialize_ymmsl(
    mode: object,
    config_directory: PathInput,
    source_topology: PathInput,
    destination: PathInput,
    repository_root_path: PathInput | None = None,
) -> Path:
    """Create a topology copy tied to one saved GUI configuration.

    For Pure, remove disabled direct actors from the template, then require
    the remaining graph to agree with the saved actor selections. Unsupported
    selections and missing selected actors fail before MUSCLE3 starts.
    """

    normalized_mode = normalize_execution_mode(mode)
    if not requires_ymmsl(normalized_mode):
        raise LaunchConfigurationError("Legacy mode does not use a yMMSL file.")

    config_path = _configuration_directory(config_directory)
    source_path = selected_ymmsl_path(normalized_mode, source_topology)
    assert source_path is not None
    destination_path = Path(destination).expanduser().resolve()
    topology = _load_yaml(source_path)
    _validate_topology_mode(topology, normalized_mode, source_path)
    settings = _mapping(topology, "settings", source_path)
    source_configuration = settings.get("config_folder_path")
    if not isinstance(source_configuration, str) or not source_configuration.strip():
        raise LaunchConfigurationError(
            f"Selected yMMSL file {source_path} needs settings.config_folder_path so GUI can bind "
            "the saved configuration."
        )

    if normalized_mode == "pure":
        selections = _actor_selections(config_path)
        _select_pure_components(topology, selections, source_path)
        _validate_pure_topology(topology, selections, source_path)

    topology = _replace_configuration_reference(topology, source_configuration, str(config_path))
    settings = _mapping(topology, "settings", source_path)
    settings["config_folder_path"] = str(config_path)
    _rewrite_driver_script_paths(topology, repository_root(repository_root_path), source_path)
    if normalized_mode == "pure":
        _rewrite_pure_code_parameters(topology, config_path, source_path)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    _write_yaml(destination_path, topology)
    return destination_path


def prepare_muscle_launch(
    mode: object,
    config_directory: PathInput,
    source_topology: PathInput,
    repository_root_path: PathInput | None = None,
) -> MuscleLaunchPlan:
    """Create an isolated run directory and derived topology for MUSCLE3."""

    normalized_mode = normalize_execution_mode(mode)
    if not requires_ymmsl(normalized_mode):
        raise LaunchConfigurationError("Legacy mode does not use MUSCLE3 Manager.")

    config_path = _configuration_directory(config_directory)
    source_path = selected_ymmsl_path(normalized_mode, source_topology)
    assert source_path is not None
    run_root = config_path / ".hcd_gui_runs"
    run_root.mkdir(parents=True, exist_ok=True)
    run_directory = Path(tempfile.mkdtemp(prefix=normalized_mode + "_", dir=str(run_root)))
    generated_topology = run_directory / "configuration.ymmsl"
    materialize_ymmsl(
        normalized_mode,
        config_path,
        source_path,
        generated_topology,
        repository_root_path,
    )
    (run_directory / "topology_source.txt").write_text(
        f"source_topology={source_path}\nconfiguration_directory={config_path}\nmode={normalized_mode}\n",
        encoding="utf-8",
    )
    return MuscleLaunchPlan(
        mode=normalized_mode,
        configuration_directory=config_path,
        source_topology=source_path,
        run_directory=run_directory,
        generated_topology=generated_topology,
        log_file=run_directory / "manager.log",
    )


def muscle_manager_command(plan: MuscleLaunchPlan, manager: str = "muscle_manager") -> list[str]:
    """Return a non-shell Manager command for a prepared launch."""

    return [
        manager,
        "--run-dir",
        str(plan.run_directory),
        "--start-all",
        str(plan.generated_topology),
    ]


def launch_muscle(
    mode: object,
    config_directory: PathInput,
    source_topology: PathInput,
    repository_root_path: PathInput | None = None,
    manager: str = "muscle_manager",
) -> tuple[MuscleLaunchPlan, Any]:
    """Prepare and start Hybrid/Pure in the background, without a shell."""

    if shutil.which(manager) is None:
        raise LaunchConfigurationError(f"Cannot find {manager!r}. Source config_hcd_iter_sdcc.sh and restart hcd_gui.")

    plan = prepare_muscle_launch(mode, config_directory, source_topology, repository_root_path)
    environment = os.environ.copy()
    environment.pop("MUSCLE_CONFIGURATION", None)
    environment.pop("MUSCLE_INSTANCE", None)
    try:
        with plan.log_file.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                muscle_manager_command(plan, manager),
                cwd=str(repository_root(repository_root_path)),
                env=environment,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
    except OSError as exc:
        raise LaunchConfigurationError(f"Cannot start MUSCLE3 Manager: {exc}") from exc
    return plan, process
