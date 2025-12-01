import sys
import os
import imas
from libmuscle import Instance, Message
from ymmsl import Operator

# Reuse existing iwrap wrapper
from hcdworkflow.workflow_actor import WorkflowActor


def deserialize_ids_dict(serialized_dict):
    """Deserialize IDS dictionary"""
    restored_objects = {}
    for key, data_bytes in serialized_dict.items():
        if hasattr(imas, key):
            cls = getattr(imas, key)
            obj = cls()
            if hasattr(obj, 'deserialize'):
                obj.deserialize(data_bytes)
                restored_objects[key] = obj
            else:
                try:
                    obj.put_transfer(data_bytes)
                    restored_objects[key] = obj
                except:
                    print(f"[Actor Warning] Could not deserialize {key}", file=sys.stderr)
        else:
            restored_objects[key] = data_bytes
    return restored_objects


class GenericM3Actor:
    """
    Generic MUSCLE3 Actor
    """

    def __init__(self):
        print("[M3 Actor] Initializing...", file=sys.stdout)
        
        # ==========================================
        # Step 1: Define ports (match yMMSL configuration)
        # ==========================================
        ports = {
            Operator.F_INIT: ["state_in"],
            Operator.O_F: ["ids_out"]
        }
        try:
            self.instance = Instance(ports)
            print("[M3 Actor] ✓ Instance created successfully", file=sys.stdout)
        except Exception as e:
            print(f"[M3 Actor] ✗ Failed to create Instance: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # ==========================================
        # Step 2: Read configuration
        # ==========================================
        try:
            self.actor_name = self.instance.get_setting("actor_name", "str")
        except KeyError:
            print("[M3 Actor] Error: 'actor_name' missing in yMMSL settings.", file=sys.stderr)
            sys.exit(1)
        
        try:
            self.config_folder_path = self.instance.get_setting("config_folder_path", "str")
        except KeyError:
            self.config_folder_path = "."
            print("[M3 Actor] Warning: using default config path '.'")
        
        print(f"[M3 Actor] Actor name: {self.actor_name}", file=sys.stdout)
        print(f"[M3 Actor] Config path: {self.config_folder_path}", file=sys.stdout)
        
        # ==========================================
        # Step 3: Construct XML path
        # ==========================================
        try:
            self.xml_path = self.instance.get_setting("actor_xml_path", "str")
        except KeyError:
            # Default naming rule: input_{actor_name}.xml
            self.xml_path = os.path.join(
                self.config_folder_path, 
                f"input_{self.actor_name}.xml"
            )
            if not os.path.exists(self.xml_path):
                print(f"[M3 Actor] Warning: XML not found: {self.xml_path}", file=sys.stderr)
                self.xml_path = ""
        
        # ==========================================
        # Step 4: Initialize Legacy Wrapper
        # ==========================================
        try:
            self.legacy_wrapper = WorkflowActor(self.actor_name, self.xml_path)
            self.actor_func = self.legacy_wrapper.getActor()
            self.input_keys = self.legacy_wrapper.getInputIDSList()
            self.output_keys = self.legacy_wrapper.getOutputIDSList()
        except Exception as e:
            print(f"[M3 Actor] Failed to load legacy actor '{self.actor_name}': {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        print(f"[M3 Actor] Initialized: {self.actor_name}", file=sys.stdout)
        print(f"[M3 Actor] Inputs: {self.input_keys}", file=sys.stdout)
        print(f"[M3 Actor] Outputs: {self.output_keys}", file=sys.stdout)

    def run(self):
        """Main loop：receive → calculate → send"""
        print(f"[M3 Actor {self.actor_name}] Starting main loop...", file=sys.stdout)
        
        while self.instance.reuse_instance():
            # ==========================================
            # step 1: receive data
            # ==========================================
            try:
                msg = self.instance.receive("state_in")
                timestamp = msg.timestamp
                next_timestamp = msg.next_timestamp
                
                print(f"\n[M3 Actor {self.actor_name}] Received data at t={timestamp:.4f}", file=sys.stdout)
            except Exception as e:
                print(f"[M3 Actor {self.actor_name}] Error receiving: {e}", file=sys.stderr)
                break
            
            # deserialization
            try:
                input_data = deserialize_ids_dict(msg.data)
                print(f"[M3 Actor {self.actor_name}] Deserialized {len(input_data)} IDS objects")
            except Exception as e:
                print(f"[M3 Actor {self.actor_name}] Deserialization error: {e}", file=sys.stderr)
                input_data = {}
            
            # ==========================================
            # step 2: execute calculation
            # ==========================================
            results = None
            
            try:
                # 准备调用参数 (改为有序列表)
                call_args_list = []
                # 仅用于打印日志
                loaded_keys = [] 
                
                for key in self.input_keys:
                    if key in input_data:
                        call_args_list.append(input_data[key])
                        loaded_keys.append(key)
                    else:
                        print(f"[M3 Actor {self.actor_name}] Warning: missing input '{key}'", file=sys.stderr)
                        # 如果缺失，可能需要填 None，或者让物理代码自己报错
                        # 这里我们暂时不 append，或者视 wrapper 具体要求而定
                        # 通常遗留 wrapper 期望参数个数必须对齐
                        pass 
                
                # 检查是否有足够的输入
                if not call_args_list:
                    print(f"[M3 Actor {self.actor_name}] Error: No valid inputs found", file=sys.stderr)
                    results = {}
                else:
                    # 调用物理代码
                    print(f"[M3 Actor {self.actor_name}] Running solver with inputs: {loaded_keys}", file=sys.stdout)
                    # ✅ 修复：使用 *argsList (位置参数)
                    results = self.actor_func(*call_args_list)
                    print(f"[M3 Actor {self.actor_name}] Solver finished.", file=sys.stdout)
                    
            except Exception as e:
                print(f"[M3 Actor {self.actor_name}] Execution Error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                results = {}

            # ==========================================
            # step 3: serialize the result
            # ==========================================
            serialized_out = {}
            
            if results is None:
                print(f"[M3 Actor {self.actor_name}] Warning: actor returned None", file=sys.stderr)
            
            elif hasattr(results, 'serialize'):
                # 单个 IDS 对象
                out_name = self.output_keys[0] if self.output_keys else self.actor_name
                try:
                    serialized_out[out_name] = results.serialize()
                    print(f"[M3 Actor {self.actor_name}] Serialized result as '{out_name}'")
                except Exception as e:
                    print(f"[M3 Actor {self.actor_name}] Serialization error: {e}", file=sys.stderr)
            
            elif isinstance(results, dict):
                # 字典（多个 IDS）
                for k, v in results.items():
                    if hasattr(v, 'serialize'):
                        try:
                            serialized_out[k] = v.serialize()
                            print(f"[M3 Actor {self.actor_name}] Serialized '{k}'")
                        except Exception as e:
                            print(f"[M3 Actor {self.actor_name}] Error serializing '{k}': {e}", file=sys.stderr)
                    else:
                        print(f"[M3 Actor {self.actor_name}] Warning: '{k}' cannot be serialized", file=sys.stderr)
            
            elif isinstance(results, (list, tuple)):
                # 列表/元组（多个 IDS）
                for i, val in enumerate(results):
                    if i < len(self.output_keys) and hasattr(val, 'serialize'):
                        key = self.output_keys[i]
                        try:
                            serialized_out[key] = val.serialize()
                            print(f"[M3 Actor {self.actor_name}] Serialized '{key}'")
                        except Exception as e:
                            print(f"[M3 Actor {self.actor_name}] Error serializing '{key}': {e}", file=sys.stderr)
            
            else:
                print(f"[M3 Actor {self.actor_name}] Warning: unexpected result type {type(results)}", file=sys.stderr)

            # ==========================================
            # 步骤 4: 发送结果
            # ==========================================
            out_msg = Message(timestamp, next_timestamp, serialized_out)
            try:
                self.instance.send("ids_out", out_msg)
                print(f"[M3 Actor {self.actor_name}] Sent {len(serialized_out)} results.\n")
            except Exception as e:
                print(f"[M3 Actor {self.actor_name}] Error sending: {e}", file=sys.stderr)


if __name__ == "__main__":
    actor = GenericM3Actor()
    actor.run()