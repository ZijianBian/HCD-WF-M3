#!/usr/bin/env python
"""
Generic Actor M3 Wrapper

Communication Pattern (MMSF micro-model):
    Actor: receive (F_INIT) -> compute -> send (O_F) within each reuse iteration
    Driver (macro-model): send (O_I) -> receive (S)
    
    MUSCLE3 automatically controls reuse: actor's reuse_instance() returns True
    as long as the driver keeps sending. When the driver exits, actors stop.
"""
import importlib
import logging
import os
import sys

import imas

from libmuscle import Instance, Message, KEEPS_NO_STATE_FOR_NEXT_USE
from ymmsl import Operator

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


def _create_ids(ids_name: str):
    """Create an IDS object by name."""
    if hasattr(imas, 'IDSFactory'):
        factory = imas.IDSFactory()
        return getattr(factory, ids_name)()
    elif hasattr(imas, ids_name):
        return getattr(imas, ids_name)()
    else:
        raise AttributeError(f"Cannot create IDS '{ids_name}': not found in imas module")


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


def main(actor_name, code_parameters_path=None):
    """Main entry point for the actor M3 wrapper."""
    print(f"[ActorWrapper] Starting {actor_name} as M3 component...", flush=True)
    
    actor_class, config = get_actor_class(actor_name)
    input_ids = config['input_ids']
    output_ids = config['output_ids']
    
    input_ports = [f"{ids}_in" for ids in input_ids]
    output_ports = [f"{ids}_out" for ids in output_ids]
    
    # Actor is the MICRO-MODEL: receives via F_INIT, sends via O_F
    # Driver is the MACRO-MODEL: sends via O_I, receives via S
    #
    # This tells MUSCLE3 the reuse relationship:
    #   Driver (O_I) ──> Actor (F_INIT)   [driver sends, actor receives to start]
    #   Actor  (O_F) ──> Driver (S)       [actor sends result, driver receives]
    #
    # MUSCLE3 will keep calling reuse_instance()=True on the actor as long
    # as the driver keeps sending on O_I. When the driver stops (exits its
    # reuse loop), the actor's reuse_instance() returns False.
    ports = {
        Operator.F_INIT: input_ports,    # Receive from driver at start of each reuse
        Operator.O_F: output_ports,      # Send to driver at end of each reuse
    }
    
    print(f"[ActorWrapper] Creating M3 Instance", flush=True)
    print(f"  F_INIT (recv): {input_ports}", flush=True)
    print(f"  O_F (send):    {output_ports}", flush=True)
    
    instance = Instance(ports, KEEPS_NO_STATE_FOR_NEXT_USE)
    
    # Get code_parameters from settings if not provided
    if code_parameters_path is None:
        try:
            code_parameters_path = instance.get_setting(f"{actor_name}.code_parameters", "str")
            print(f"[ActorWrapper] Got code_parameters from settings: {code_parameters_path}", flush=True)
        except KeyError:
            print(f"[ActorWrapper] No code_parameters in settings", flush=True)
    
    # Initialize actor
    print(f"[ActorWrapper] Instantiating {actor_name}...", flush=True)
    actor = actor_class()
    
    if config.get('has_code_parameters') and code_parameters_path:
        code_parameters = actor.get_code_parameters()
        code_parameters.parameters_path = code_parameters_path
        runtime_settings = actor.get_runtime_settings()
        actor.initialize(code_parameters=code_parameters, runtime_settings=runtime_settings)
    else:
        actor.initialize()
    
    print(f"[ActorWrapper] {actor_name} initialized", flush=True)
    
    # Main loop - one iteration per timestep
    # With F_INIT/O_F, MUSCLE3 controls reuse: reuse_instance() returns True
    # as long as the driver (macro-model) keeps sending on O_I ports.
    # When the driver exits its loop, reuse_instance() returns False here.
    while instance.reuse_instance():
        logging.info(f'#sync# {actor_name}: === New reuse iteration ===')
        print(f"[ActorWrapper] {actor_name}: Waiting for inputs...", flush=True)
        
        # ============ F_INIT: Receive all inputs ============
        input_data = {}
        timestamp = 0.0
        
        for i, ids_name in enumerate(input_ids):
            port_name = input_ports[i]
            logging.info(f'#sync# {actor_name}: Receiving {port_name}')
            
            msg = instance.receive(port_name)
            timestamp = msg.timestamp
            
            ids_obj = _create_ids(ids_name)
            ids_obj.deserialize(msg.data)
            input_data[ids_name] = ids_obj
            
            print(f"[ActorWrapper] {actor_name}: Received {ids_name} (t={msg.timestamp:.4f})", flush=True)
        
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
        
        # ============ O_F: Send all outputs ============
        for i, ids_name in enumerate(output_ids):
            port_name = output_ports[i]
            ids_obj = output_data[ids_name]
            
            if hasattr(ids_obj, 'time') and len(ids_obj.time) > 0:
                out_timestamp = float(ids_obj.time[-1])
            else:
                out_timestamp = timestamp
            
            logging.info(f'#sync# {actor_name}: Sending {port_name}')
            
            msg = Message(out_timestamp, data=ids_obj.serialize())
            instance.send(port_name, msg)
            
            print(f"[ActorWrapper] {actor_name}: Sent {ids_name} (t={out_timestamp:.4f})", flush=True)
        
        logging.info(f'#sync# {actor_name}: Iteration complete')
        print(f"[ActorWrapper] {actor_name}: Timestep complete", flush=True)
    
    # Finalize
    logging.info(f'#sync# {actor_name}: Finalizing')
    print(f"[ActorWrapper] {actor_name}: Finalizing...", flush=True)
    actor.finalize()
    print(f"[ActorWrapper] {actor_name}: Done", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python actor_m3_wrapper.py <actor_name> [code_parameters_path]")
        print(f"Available actors: {list(ACTOR_CONFIGS.keys())}")
        sys.exit(1)
    
    actor_name = sys.argv[1]
    code_parameters_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    main(actor_name, code_parameters_path)