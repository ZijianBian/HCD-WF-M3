#!/usr/bin/env python
"""
Generic Actor M3 Wrapper (Vector Port / Bundle Mode)

Communication Pattern (MMSF micro-model):
    Actor (micro):  receive bundle (F_INIT) -> unpack -> compute -> pack -> send bundle (O_F)
    Driver (macro): pack bundle -> send (O_I) -> receive (S) -> unpack bundle

    Each message is a bundled dict: {ids_name: serialized_bytes, ...}
    packed via msgpack for efficient binary transfer.

    MUSCLE3 automatically controls reuse: actor's reuse_instance() returns True
    as long as the driver keeps sending. When the driver exits, actors stop.

Instance Configuration (from ymmsl settings):
    actor_wrapper[i].actor_name:       Name of the physics actor (e.g., "torbeam")
    actor_wrapper[i].process_name:     Workflow process name (e.g., "ec_wave_solver")
    actor_wrapper[i].code_parameters:  Path to code parameters XML file

NOTE on ports:
    The actor_wrapper side has SCALAR ports (no '[]' suffix in Instance()).
    The vector nature is on the hcd_workflow (macro) side.
    Each actor_wrapper instance sees only its own single slot.
"""
import importlib
import json
import logging
import os
import sys

import imas

from libmuscle import Instance, Message, KEEPS_NO_STATE_FOR_NEXT_USE
from ymmsl import Operator

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

# msgpack for efficient binary bundling of multiple IDS
MSGPACK_AVAILABLE = False
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    print("[ActorWrapper] Warning: msgpack not available, falling back to json", file=sys.stderr)


# =============================================================================
# Bundle Serialization Helpers
# =============================================================================

def _pack_bundle(bundle_dict):
    """Pack a dict of {ids_name: bytes} into a single bytes payload."""
    if MSGPACK_AVAILABLE:
        return msgpack.packb(bundle_dict, use_bin_type=True)
    else:
        import base64
        json_dict = {k: base64.b64encode(v).decode('ascii') for k, v in bundle_dict.items()}
        return json.dumps(json_dict).encode('utf-8')


def _unpack_bundle(data):
    """Unpack a bytes payload back into a dict of {ids_name: bytes}."""
    if MSGPACK_AVAILABLE:
        return msgpack.unpackb(data, raw=True)
    else:
        import base64
        json_dict = json.loads(data.decode('utf-8'))
        return {k: base64.b64decode(v) for k, v in json_dict.items()}


def _create_ids(ids_name: str):
    """Create an IDS object by name."""
    if hasattr(imas, 'IDSFactory'):
        factory = imas.IDSFactory()
        return getattr(factory, ids_name)()
    elif hasattr(imas, ids_name):
        return getattr(imas, ids_name)()
    else:
        raise AttributeError(f"Cannot create IDS '{ids_name}': not found in imas module")


# =============================================================================
# Actor Configuration Registry
# =============================================================================

ACTOR_CONFIGS = {
    'torbeam': {
        'module': 'torbeam.actor',
        'class': 'torbeam',
        'input_ids': ['equilibrium', 'core_profiles', 'ec_launchers'],
        'output_ids': ['waves'],
        'has_code_parameters': True,
    },
    'hcd2core_sources': {
        'module': 'hcd2core_sources.actor',
        'class': 'hcd2core_sources',
        'input_ids': ['distributions', 'distribution_sources', 'waves', 'core_profiles'],
        'output_ids': ['core_sources'],
        'has_code_parameters': True,
    },
    'hcd2core_profiles': {
        'module': 'hcd2core_profiles.actor',
        'class': 'hcd2core_profiles',
        'input_ids': ['equilibrium', 'core_profiles', 'core_sources'],
        'output_ids': ['core_profiles'],
        'has_code_parameters': True,
    },
}


def get_actor_class(actor_name):
    """Dynamically import and return the actor class."""
    if actor_name not in ACTOR_CONFIGS:
        raise ValueError(f"Unknown actor: {actor_name}. Available: {list(ACTOR_CONFIGS.keys())}")

    config = ACTOR_CONFIGS[actor_name]
    module = importlib.import_module(config['module'])
    actor_class = getattr(module, config['class'])
    return actor_class, config


# =============================================================================
# Main Entry Point
# =============================================================================

def main(actor_name_override=None, code_parameters_override=None):
    """
    Main entry point for the actor M3 wrapper.

    In vector port mode:
    - Ports are SCALAR: F_INIT: ['actor_input'], O_F: ['actor_output']
      (no '[]' suffix — the vector nature is on the macro side only)
    - Each actor_wrapper instance sees only its own single connection
    - actor_name and config come from MUSCLE3 instance settings
    - All input IDS are received as a single bundled message
    - All output IDS are sent as a single bundled message
    """
    # === 1. Create M3 Instance with scalar ports ===
    # No '[]' here — each actor_wrapper instance has a single scalar port.
    # The macro side (hcd_workflow) has vector ports with slots.
    ports = {
        Operator.F_INIT: ['actor_input'],     # Receive bundled inputs from driver
        Operator.O_F:    ['actor_output'],     # Send bundled outputs to driver
    }

    print(f"[ActorWrapper] Creating M3 Instance", flush=True)
    print(f"  F_INIT (recv): ['actor_input']", flush=True)
    print(f"  O_F (send):    ['actor_output']", flush=True)

    instance = Instance(ports, KEEPS_NO_STATE_FOR_NEXT_USE)

    # === 2. Get actor configuration from MUSCLE3 settings ===
    # These come from the ymmsl: actor_wrapper[i].actor_name, etc.
    if actor_name_override:
        actor_name = actor_name_override
    else:
        actor_name = instance.get_setting("actor_name", "str")

    process_name = "unknown"
    try:
        process_name = instance.get_setting("process_name", "str")
    except KeyError:
        pass

    if code_parameters_override:
        code_parameters_path = code_parameters_override
    else:
        try:
            code_parameters_path = instance.get_setting("code_parameters", "str")
        except KeyError:
            code_parameters_path = None

    print(f"[ActorWrapper] Configuration from settings:", flush=True)
    print(f"  actor_name:      {actor_name}", flush=True)
    print(f"  process_name:    {process_name}", flush=True)
    print(f"  code_parameters: {code_parameters_path}", flush=True)

    # === 3. Load and initialize the physics actor ===
    actor_class, config = get_actor_class(actor_name)
    input_ids = config['input_ids']
    output_ids = config['output_ids']

    print(f"[ActorWrapper] Instantiating {actor_name}...", flush=True)
    print(f"  Expected inputs:  {input_ids}", flush=True)
    print(f"  Expected outputs: {output_ids}", flush=True)

    actor = actor_class()

    if config.get('has_code_parameters') and code_parameters_path:
        code_parameters = actor.get_code_parameters()
        code_parameters.parameters_path = code_parameters_path
        runtime_settings = actor.get_runtime_settings()
        actor.initialize(code_parameters=code_parameters, runtime_settings=runtime_settings)
    else:
        actor.initialize()

    print(f"[ActorWrapper] {actor_name} initialized successfully", flush=True)

    # === 4. Main reuse loop ===
    # With F_INIT/O_F, MUSCLE3 controls reuse: reuse_instance() returns True
    # as long as the driver (macro-model) keeps sending on O_I ports.
    # When the driver exits its loop, reuse_instance() returns False here.
    iteration = 0
    while instance.reuse_instance():
        iteration += 1
        logging.info(f'#sync# {actor_name}: === Reuse iteration {iteration} ===')
        print(f"[ActorWrapper] {actor_name}: Iteration {iteration} - waiting for input bundle...", flush=True)

        # ============ F_INIT: Receive bundled input ============
        msg = instance.receive('actor_input')
        timestamp = msg.timestamp
        bundle = _unpack_bundle(msg.data)

        print(f"[ActorWrapper] {actor_name}: Received bundle (t={timestamp:.4f}, "
              f"{len(bundle)} IDS, {len(msg.data)} bytes)", flush=True)

        # Unpack each IDS from the bundle
        input_data = {}
        for ids_name in input_ids:
            # Handle both str and bytes keys (msgpack may return bytes keys)
            ids_name_key = ids_name
            if len(bundle) > 0 and isinstance(list(bundle.keys())[0], bytes):
                ids_name_key = ids_name.encode('utf-8')

            if ids_name_key not in bundle:
                print(f"[ActorWrapper] WARNING: {ids_name} not found in bundle! "
                      f"Available keys: {list(bundle.keys())}", flush=True)
                # Create empty IDS as fallback
                input_data[ids_name] = _create_ids(ids_name)
                continue

            ids_obj = _create_ids(ids_name)
            ids_obj.deserialize(bundle[ids_name_key])
            input_data[ids_name] = ids_obj
            print(f"[ActorWrapper] {actor_name}: Unpacked {ids_name}", flush=True)

        # ============ Run physics ============
        logging.info(f'#sync# {actor_name}: Running physics code')
        print(f"[ActorWrapper] {actor_name}: Running actor at t={timestamp:.4f}...", flush=True)

        input_args = [input_data[ids] for ids in input_ids]
        result = actor.run(*input_args)

        if len(output_ids) == 1:
            output_data = {output_ids[0]: result}
        else:
            output_data = dict(zip(output_ids, result))

        print(f"[ActorWrapper] {actor_name}: Actor completed", flush=True)

        # ============ O_F: Send bundled output ============
        output_bundle = {}
        out_timestamp = timestamp  # default

        for ids_name in output_ids:
            ids_obj = output_data[ids_name]

            if hasattr(ids_obj, 'time') and len(ids_obj.time) > 0:
                out_timestamp = float(ids_obj.time[-1])

            output_bundle[ids_name] = ids_obj.serialize()
            print(f"[ActorWrapper] {actor_name}: Packed {ids_name} into output bundle", flush=True)

        packed = _pack_bundle(output_bundle)

        logging.info(f'#sync# {actor_name}: Sending output bundle')
        instance.send('actor_output', Message(out_timestamp, data=packed))

        print(f"[ActorWrapper] {actor_name}: Sent output bundle "
              f"(t={out_timestamp:.4f}, {len(output_ids)} IDS, {len(packed)} bytes)", flush=True)

        logging.info(f'#sync# {actor_name}: Iteration {iteration} complete')

    # === 5. Finalize ===
    logging.info(f'#sync# {actor_name}: Finalizing')
    print(f"[ActorWrapper] {actor_name}: Finalizing after {iteration} iterations...", flush=True)
    actor.finalize()
    print(f"[ActorWrapper] {actor_name}: Done", flush=True)


if __name__ == "__main__":
    # Support both modes:
    #   1. Settings-based (preferred): python actor_m3_wrapper.py
    #      -> actor_name comes from MUSCLE3 instance settings
    #   2. CLI override: python actor_m3_wrapper.py <actor_name> [code_parameters_path]
    #      -> for testing/debugging
    actor_name_override = None
    code_parameters_override = None

    if len(sys.argv) >= 2:
        actor_name_override = sys.argv[1]
        print(f"[ActorWrapper] CLI override: actor_name={actor_name_override}", flush=True)
    if len(sys.argv) >= 3:
        code_parameters_override = sys.argv[2]
        print(f"[ActorWrapper] CLI override: code_parameters={code_parameters_override}", flush=True)

    main(actor_name_override, code_parameters_override)