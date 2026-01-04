import sys
import os
import imas
import numpy as np
from libmuscle import Instance, Message
from ymmsl import Operator

from hcdworkflow.workflow_actor import WorkflowActor


def inspect_ids_content(name, obj):
    """Helper to peek inside the IDS."""
    info = []
    try:
        if hasattr(obj, 'time') and obj.time is not None:
            t = obj.time
            size = t.size if hasattr(t, 'size') else len(t)
            if size > 0:
                info.append(f"Time=[{t[0]:.4f}...] (len={size})")
            else:
                info.append("Time=[] (EMPTY!)")
        else:
            info.append("No 'time' attribute")

        if "equilibrium" in name and hasattr(obj, 'time_slice'):
            info.append(f"Slices={len(obj.time_slice)}")
        elif "ec_launchers" in name and hasattr(obj, 'beam'):
            info.append(f"Beams={len(obj.beam)}")
        elif "core_profiles" in name and hasattr(obj, 'profiles_1d'):
            info.append(f"Profiles={len(obj.profiles_1d)}")
    except Exception as e:
        info.append(f"Inspection failed: {e}")
    
    return ", ".join(info)


def deserialize_ids_dict(serialized_dict):
    """Deserialize IDS dictionary."""
    restored_objects = {}
    for key, data_bytes in serialized_dict.items():
        if hasattr(imas, key):
            cls = getattr(imas, key)
            obj = cls()
            if hasattr(obj, 'deserialize'):
                try:
                    obj.deserialize(data_bytes)
                    restored_objects[key] = obj
                except Exception as e:
                    print(f"[Actor Warning] deserialize() failed for {key}: {e}", file=sys.stderr)
            else:
                try:
                    obj.put_transfer(data_bytes)
                    restored_objects[key] = obj
                except Exception as e:
                    print(f"[Actor Warning] put_transfer() failed for {key}: {e}", file=sys.stderr)
        else:
            restored_objects[key] = data_bytes
    return restored_objects


def dump_ec_launchers(ec_obj, filename):
    """Dump ec_launchers to file for comparison with original version."""
    with open(filename, 'w') as f:
        f.write(f"time: {ec_obj.time}\n")
        f.write(f"time type: {type(ec_obj.time)}\n")
        if hasattr(ec_obj.time, 'shape'):
            f.write(f"time shape: {ec_obj.time.shape}\n")
            f.write(f"time dtype: {ec_obj.time.dtype}\n")
        
        f.write(f"n_beams: {len(ec_obj.beam)}\n")
        f.write(f"ids_properties.homogeneous_time: {ec_obj.ids_properties.homogeneous_time}\n")
        
        for i, b in enumerate(ec_obj.beam):
            if i > 10: break  # Only first few beams
            
            f.write(f"\n{'='*50}\n")
            f.write(f"=== Beam {i} ===\n")
            f.write(f"{'='*50}\n")
            
            f.write(f"name: {b.name}\n")
            
            # Mode
            if hasattr(b.mode, 'data'):
                f.write(f"mode.data: {b.mode.data}\n")
            else:
                f.write(f"mode: {b.mode}\n")
            
            # Helper to dump signal
            def dump_sig(node, name):
                if node is None or not hasattr(node, 'data'):
                    f.write(f"{name}: N/A\n")
                    return
                d = node.data
                if isinstance(d, memoryview):
                    d = np.array(d)
                f.write(f"{name}.data:\n")
                f.write(f"  type: {type(node.data)}\n")
                f.write(f"  shape: {d.shape if hasattr(d, 'shape') else 'N/A'}\n")
                f.write(f"  dtype: {d.dtype if hasattr(d, 'dtype') else 'N/A'}\n")
                f.write(f"  values: {d}\n")
                if hasattr(d, 'flags'):
                    f.write(f"  C_CONTIGUOUS: {d.flags['C_CONTIGUOUS']}\n")
                    f.write(f"  F_CONTIGUOUS: {d.flags['F_CONTIGUOUS']}\n")
                
                # Time
                if hasattr(node, 'time'):
                    t = node.time
                    f.write(f"{name}.time: {t}\n")
                else:
                    f.write(f"{name}.time: (no attr)\n")
            
            # Dump all fields
            if hasattr(b, 'frequency'):
                dump_sig(b.frequency, "frequency")
            if hasattr(b, 'power_launched'):
                dump_sig(b.power_launched, "power_launched")
            
            if hasattr(b, 'launching_position'):
                lp = b.launching_position
                if hasattr(lp, 'r'): dump_sig(lp.r, "launching_position.r")
                if hasattr(lp, 'z'): dump_sig(lp.z, "launching_position.z")
                if hasattr(lp, 'phi'): dump_sig(lp.phi, "launching_position.phi")
            
            if hasattr(b, 'spot'):
                if hasattr(b.spot, 'size'): dump_sig(b.spot.size, "spot.size")
                if hasattr(b.spot, 'angle'): dump_sig(b.spot.angle, "spot.angle")
            
            if hasattr(b, 'phase'):
                if hasattr(b.phase, 'curvature'): dump_sig(b.phase.curvature, "phase.curvature")
                if hasattr(b.phase, 'angle'): dump_sig(b.phase.angle, "phase.angle")
            
            if hasattr(b, 'steering_angle_pol'):
                dump_sig(b.steering_angle_pol, "steering_angle_pol")
            if hasattr(b, 'steering_angle_tor'):
                dump_sig(b.steering_angle_tor, "steering_angle_tor")
    
    print(f"[Actor] Dumped ec_launchers to {filename}", file=sys.stdout)


def fix_ec_launchers_for_torbeam(ec_obj, target_time):
    """
    Prepare ec_launchers for Torbeam:
    1. Sync root time to match other IDSes
    2. Convert memoryview to numpy arrays
    3. Sync all signal times
    """
    if ec_obj is None:
        return ec_obj
    
    print(f"\n[Actor] Preparing ec_launchers for Torbeam...", file=sys.stdout)
    
    # Update root time
    original_time = ec_obj.time[0] if hasattr(ec_obj, 'time') and len(ec_obj.time) > 0 else None
    t_array = np.array([float(target_time)], dtype=np.float64)
    
    try:
        ec_obj.time = t_array
        print(f"[Actor] Updated ec_launchers.time: {original_time} -> {target_time}", file=sys.stdout)
    except Exception as e:
        print(f"[Actor] Warning: Could not update root time: {e}", file=sys.stderr)
    
    # Convert memoryview and sync times
    converted_count = 0
    
    def convert_node(node, name):
        nonlocal converted_count
        if node is None or not hasattr(node, 'data'):
            return
        
        val = node.data
        if isinstance(val, memoryview):
            arr = np.array(val)
            try:
                node.data = arr
                converted_count += 1
            except Exception:
                pass
        
        if hasattr(node, 'time'):
            try:
                node.time = t_array
            except Exception:
                pass
    
    if hasattr(ec_obj, 'beam'):
        n_beams = len(ec_obj.beam)
        print(f"[Actor] Processing {n_beams} beams...", file=sys.stdout)
        
        for i, beam in enumerate(ec_obj.beam):
            if hasattr(beam, 'frequency'):
                convert_node(beam.frequency, f"beam[{i}].frequency")
            if hasattr(beam, 'power_launched'):
                convert_node(beam.power_launched, f"beam[{i}].power_launched")
            
            if hasattr(beam, 'launching_position'):
                lp = beam.launching_position
                if hasattr(lp, 'r'): convert_node(lp.r, f"beam[{i}].pos.r")
                if hasattr(lp, 'z'): convert_node(lp.z, f"beam[{i}].pos.z")
                if hasattr(lp, 'phi'): convert_node(lp.phi, f"beam[{i}].pos.phi")
            
            if hasattr(beam, 'spot'):
                if hasattr(beam.spot, 'size'): convert_node(beam.spot.size, f"beam[{i}].spot.size")
                if hasattr(beam.spot, 'angle'): convert_node(beam.spot.angle, f"beam[{i}].spot.angle")
            
            if hasattr(beam, 'phase'):
                if hasattr(beam.phase, 'curvature'): convert_node(beam.phase.curvature, f"beam[{i}].phase.curvature")
                if hasattr(beam.phase, 'angle'): convert_node(beam.phase.angle, f"beam[{i}].phase.angle")
            
            if hasattr(beam, 'steering_angle_pol'):
                convert_node(beam.steering_angle_pol, f"beam[{i}].angle_pol")
            if hasattr(beam, 'steering_angle_tor'):
                convert_node(beam.steering_angle_tor, f"beam[{i}].angle_tor")
    
    print(f"[Actor] Preparation complete. Conversions: {converted_count}", file=sys.stdout)
    
    return ec_obj


class GenericM3Actor:
    """Generic MUSCLE3 Actor"""

    def __init__(self):
        print("[M3 Actor] Initializing...", file=sys.stdout)
        
        ports = {
            Operator.F_INIT: ["state_in"],
            Operator.S: ["ec_launchers"],
            Operator.O_F: ["ids_out"]
        }
        try:
            self.instance = Instance(ports)
            print("[M3 Actor] ✓ Instance created successfully", file=sys.stdout)
        except Exception as e:
            print(f"[M3 Actor] ✗ Failed to create Instance: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            self.actor_name = self.instance.get_setting("actor_name", "str")
        except KeyError:
            print("[M3 Actor] Error: 'actor_name' missing.", file=sys.stderr)
            sys.exit(1)
        
        try:
            self.config_folder_path = self.instance.get_setting("config_folder_path", "str")
        except KeyError:
            self.config_folder_path = "."
        
        try:
            self.xml_path = self.instance.get_setting("actor_xml_path", "str")
        except KeyError:
            self.xml_path = os.path.join(self.config_folder_path, f"input_{self.actor_name}.xml")
            if not os.path.exists(self.xml_path):
                self.xml_path = ""
        
        try:
            self.legacy_wrapper = WorkflowActor(self.actor_name, self.xml_path)
            self.actor_func = self.legacy_wrapper.getActor()
            self.input_keys = self.legacy_wrapper.getInputIDSList()
            self.output_keys = self.legacy_wrapper.getOutputIDSList()
        except Exception as e:
            print(f"[M3 Actor] Failed to load legacy actor: {e}", file=sys.stderr)
            sys.exit(1)
        
        print(f"[M3 Actor] Initialized: {self.actor_name}", file=sys.stdout)
        print(f"[M3 Actor] Inputs: {self.input_keys}", file=sys.stdout)

    def run(self):
        """Main loop"""
        print(f"[M3 Actor {self.actor_name}] Starting main loop...", file=sys.stdout)
        
        while self.instance.reuse_instance():
            input_data = {}
            timestamp = 0.0
            next_timestamp = 0.0

            try:
                msg_state = self.instance.receive("state_in")
                timestamp = msg_state.timestamp
                next_timestamp = msg_state.next_timestamp
                print(f"\n[M3 Actor {self.actor_name}] Received data at t={timestamp:.4f}", file=sys.stdout)
                
                state_data = deserialize_ids_dict(msg_state.data)
                input_data.update(state_data)
                
            except Exception as e:
                print(f"[M3 Actor] Error receiving state_in: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                break

            if "ec_launchers" in self.instance.list_ports():
                try:
                    msg_ec = self.instance.receive("ec_launchers")
                    ec_data = deserialize_ids_dict(msg_ec.data)
                    input_data.update(ec_data)
                except Exception:
                    pass

            # Prepare arguments
            call_args_list = []
            debug_info = []

            for base_key in self.input_keys:
                suffix_key = f"{base_key}_in"
                
                obj = None
                if base_key in input_data:
                    obj = input_data[base_key]
                elif suffix_key in input_data:
                    obj = input_data[suffix_key]
                
                if obj is not None:
                    call_args_list.append(obj)
                    content_info = inspect_ids_content(base_key, obj)
                    debug_info.append(f"{base_key}: OK ({content_info})")
                else:
                    print(f"[M3 Actor CRITICAL] Missing input: {base_key}", file=sys.stderr)
                    call_args_list.append(None)
                    debug_info.append(f"{base_key}: MISSING")

            print(f"[DEBUG] Data Content Inspection:", file=sys.stdout)
            for info in debug_info:
                print(f"  -> {info}", file=sys.stdout)

            # Fix ec_launchers
            for idx, key in enumerate(self.input_keys):
                if 'ec_launchers' in key and idx < len(call_args_list) and call_args_list[idx] is not None:
                    call_args_list[idx] = fix_ec_launchers_for_torbeam(call_args_list[idx], timestamp)

            # ============================================================
            # DIAGNOSTIC: Dump ec_launchers BEFORE calling Torbeam
            # Compare this file with the dump from original version!
            # ============================================================
            for idx, key in enumerate(self.input_keys):
                if 'ec_launchers' in key and idx < len(call_args_list) and call_args_list[idx] is not None:
                    dump_ec_launchers(call_args_list[idx], "/tmp/ec_m3_version.txt")
                    print("[Actor] === DUMPED to /tmp/ec_m3_version.txt ===", file=sys.stdout)

            sys.stdout.flush()
            sys.stderr.flush()

            # Execute physics code
            results = None
            try:
                print(f"[M3 Actor] About to call actor_func with {len(call_args_list)} arguments...", file=sys.stdout, flush=True)
                
                results = self.actor_func(*call_args_list)
                print(f"[M3 Actor {self.actor_name}] Solver finished successfully.", file=sys.stdout)
            except Exception as e:
                print(f"[M3 Actor {self.actor_name}] Python Exception: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                results = {}

            # Serialize & Send
            serialized_out = {}
            if results:
                if hasattr(results, 'serialize'):
                    key = self.output_keys[0] if self.output_keys else self.actor_name
                    serialized_out[key] = results.serialize()
                elif isinstance(results, (list, tuple)):
                    for i, val in enumerate(results):
                        if i < len(self.output_keys) and hasattr(val, 'serialize'):
                            serialized_out[self.output_keys[i]] = val.serialize()
                elif isinstance(results, dict):
                    for k, v in results.items():
                        if hasattr(v, 'serialize'):
                            serialized_out[k] = v.serialize()

            out_msg = Message(timestamp, next_timestamp, serialized_out)
            self.instance.send("ids_out", out_msg)
            print(f"[M3 Actor] Sent results.\n")
            sys.stdout.flush()


if __name__ == "__main__":
    actor = GenericM3Actor()
    actor.run()