import logging
import os
import sys
import inspect
from pathlib import Path

from libmuscle import Instance, Message
from ymmsl import Operator

import imas
import hcdworkflow
from gui.gui_methods import create_workflow_param_from_file
from hcdworkflow.hcd_workflow import HCDWorkflow
from hcdworkflow.workflow_dbhelper import WorkflowDbHelper
from hcdworkflow.workflow_globals_reader import WorkflowGlobalsReader

log = logging.getLogger()
log.setLevel(logging.ERROR)

# Check for waveform_cooker
isWaveformCookerPresent = True
try:
    from waveform_cooker import add_dynamic
except Exception as _:
    isWaveformCookerPresent = False


def deserialize_ids_dict(serialized_dict):
    """反序列化 IDS 字典"""
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
                    print(f"[Driver Warning] Could not deserialize {key}", file=sys.stderr)
        else:
            restored_objects[key] = data_bytes
    return restored_objects

class WorkflowDriverM3:
    """
    replace wf_wrapper.py + workflow_driver.py
    MUSCLE3 分布式 Driver
    职责：调度、数据分发、结果收集
    不包含：计算逻辑（在 Actor 中）
    """
    
    def __init__(self, config_folder_path=None):
        # ==========================================
        # 步骤 1: 读取 Actor 列表（Instance 创建前）
        # ==========================================
        actors_env = os.environ.get("HCD_ACTORS", "")
        self.actor_list = [a.strip() for a in actors_env.split(",") if a.strip()]
        
        if not self.actor_list:
            print("[M3 Driver] Warning: No actors in HCD_ACTORS", file=sys.stderr)
            self.actor_list = []
        
        print(f"[M3 Driver] Actors: {self.actor_list}", file=sys.stdout)
        
        # ==========================================
        # 步骤 2: 动态生成端口字典
        # ✅ 修复核心错误：格式必须是 {"name": Operator}
        # ==========================================
        ports = {}
        
        # 1. 定义输出端口 (O_I)
        ports["state_out"] = Operator.O_I
        
        # ==========================================
        # 步骤 2: 动态生成端口字典 (强制 Legacy 格式)
        # ==========================================
        
        # 准备端口名称列表
        out_port_names = ["state_out"]
        in_port_names = [f"result_from_{actor}" for actor in self.actor_list]
        
        print(f"[M3 Driver] Out ports: {out_port_names}", file=sys.stdout)
        print(f"[M3 Driver] In ports: {in_port_names}", file=sys.stdout)

        # 强制使用旧版格式：{ Operator: [List of Strings] }
        # 你的报错证明系统正在尝试遍历 Value，所以 Value 必须是列表
        ports = {
            Operator.O_I: out_port_names,
            Operator.S:   in_port_names
        }
        
        print(f"[M3 Driver] Ports dictionary constructed with keys: {list(ports.keys())}", file=sys.stdout)
        
        # ==========================================
        # 步骤 3: 创建 MUSCLE3 Instance
        # ==========================================
        try:
            self.instance = Instance(ports)
            print("[M3 Driver] ✓ Instance created successfully", file=sys.stdout)
        except Exception as e:
            print(f"[M3 Driver] ✗ Failed to create Instance: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # ==========================================
        # 步骤 4: 读取配置路径
        # ==========================================
        try:
            self.config_path = self.instance.get_setting("config_folder_path", "str")
        except KeyError:
            if config_folder_path:
                self.config_path = os.path.abspath(config_folder_path)
            else:
                print("[M3 Driver] Error: config_folder_path missing.", file=sys.stderr)
                sys.exit(1)
        
        print(f"[M3 Driver] Config path: {self.config_path}", file=sys.stdout)
        
        # ==========================================
        # 步骤 5: 读取收敛参数
        # ==========================================
        try:
            self.max_iterations = self.instance.get_setting("max_iterations", "int")
        except:
            self.max_iterations = 1  # 默认不迭代
        
        try:
            self.convergence_tol = self.instance.get_setting("convergence_tolerance", "float")
        except:
            self.convergence_tol = 1e-3
        
        print(f"[M3 Driver] Convergence: max_iter={self.max_iterations}, tol={self.convergence_tol}")
        
        # ==========================================
        # 步骤 6: 初始化数据库环境
        self._initialize_full_environment()

    def _initialize_full_environment(self):
        """
        Initialize databases and configuration (from original wrapper).
        This replaces the wf_wrapper function's setup logic.
        """
        print("[M3 Driver] Setting up environment...", file=sys.stdout)
        
        # Load global configuration
        pathGlobalConfiguration = Path(inspect.getfile(hcdworkflow)).parent / "global_configuration"
        globalListPath = str(pathGlobalConfiguration / "global_lists.yaml")
        
        # Load workflow parameters
        inputworkflow_xml = os.path.join(self.config_path, "input_workflow.xml")
        print("path of the input workflow", inputworkflow_xml)
        try:
            wf_parameters = create_workflow_param_from_file(inputworkflow_xml)["workflow_parameters"][0]
        except Exception as e:
            print(f"[M3 Driver] Error loading workflow XML: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Extract database parameters
        input_user_or_path = wf_parameters["input_user_or_path"][0]
        input_database = wf_parameters["input_database"][0]
        input_backend = wf_parameters.get("input_backend", ["MDSPLUS"])[0]
        output_user_or_path = wf_parameters["output_user_or_path"][0]
        output_database = wf_parameters["output_database"][0]
        output_backend = wf_parameters.get("output_backend", ["MDSPLUS"])[0]
        shot_nr = wf_parameters["shot_nr"][0]
        run_in = wf_parameters["run_in"][0]
        run_out = wf_parameters["run_out"][0]
        
        # Extract time parameters (replace workflowObject.workflowData)
        self.tbegin = wf_parameters.get("tbegin", [-1.0])[0]
        self.tend = wf_parameters.get("tend", [-1.0])[0]
        self.dt_required = wf_parameters.get("dt_required", [0.1])[0]
        self.one_time_slice = wf_parameters.get("one_time_slice", [0])[0]
        # Initialize database helper
        dbhelper = WorkflowDbHelper(
            input_user_or_path, input_database, input_backend,
            output_user_or_path, output_database, output_backend,
            shot_nr, run_in, run_out
        )
        self.inputDb = dbhelper.getInputDatabase()
        self.outputDb = dbhelper.getOutputDatabase()
        self.md = dbhelper.getMachineDatabase()
        
        # Read global lists
        globallistReader = WorkflowGlobalsReader(globalListPath)
        self.inputIds = globallistReader.getIdsScenarioList()
        self.inputIds.append("workflow")
        self.inputMds = globallistReader.getIdsMdList()
        wall_md = globallistReader.getWallMD()
        
        # Prepare machine descriptions
        self._prepare_machine_descriptions(wall_md)
        
        # Load waveforms if present
        self._load_waveforms()
        
        print("[M3 Driver] Environment setup complete.", file=sys.stdout)

    def _prepare_machine_descriptions(self, wall_md):
        """Prepare machine description database"""
        for idsName in self.inputMds:
            try:
                idsObject = self.inputDb.get(idsName)
                # TODO: Verify compatibility with IMAS DD 4.0.0
                if idsObject.ids_properties.homogeneous_time != imas.imasdef.EMPTY_INT:
                    self.md.put(idsObject)
                else:
                    if idsName == "wall":
                        try:
                            _backend = getattr(imas.imasdef, wall_md["backend"] + "_BACKEND")
                            wall = imas.DBEntry(
                                _backend, wall_md["database"], wall_md["shot"],
                                wall_md["run"], wall_md["user_or_path"]
                            )
                            wall.open()
                            self.md.put(wall.get("wall"))
                        except Exception:
                            print(f"[M3 Driver] Wall IDS not found in MD database")
                    else:
                        print(f"[M3 Driver] {idsName} not in scenario data")
            except Exception as e:
                print(f"[M3 Driver] Error loading {idsName}: {e}", file=sys.stderr)

    def _load_waveforms(self):
        """Load waveform configurations if present (from original wrapper)."""
        for filename in os.listdir(self.config_path):
            filePath = os.path.join(self.config_path, filename)
            if filePath.endswith("waveforms.yaml") and os.path.exists(filePath):
                if isWaveformCookerPresent:
                    idsObject = add_dynamic(filePath)
                    if idsObject is not None:
                        self.md.put(idsObject)
                        print(f"[M3 Driver] Loaded waveform: {filename}")

# ---------------------------------------------------------
    # copy from the original WorkflowDriver
    # ---------------------------------------------------------
    def getIDSSlices(self, timenow):
        """从数据库读取切片 (Copy from legacy driver)"""
        idsSlices = {}

        # Read scenario IDSes
        for ids in self.inputIds:
            try:
                idsSlices[ids] = self.inputDb.get_slice(ids, timenow, 1)
            except Exception as e:
                print(f"[M3 Driver] Error reading {ids}: {e}", file=sys.stderr)
                return None
        
        # Read machine description IDSes
        for ids in self.inputMds:
            try:
                idsSlices[ids] = self.md.get_slice(ids, timenow, 1)
            except Exception:
                pass  # MD 可能不存在某些切片
        return idsSlices

    def storeIDSSlices(self, ids_dict):
        """保存 IDS 切片到输出数据库"""
        for idsName, idsData in ids_dict.items():
            if not hasattr(idsData, 'ids_properties'):
                continue
            
            # 跳过输入 IDS（避免重复保存）
            if idsName in self.inputIds or idsName in self.inputMds:
                continue
            
            # 保存有时间数据的输出 IDS
            if hasattr(idsData, 'time') and len(idsData.time) > 0:
                try:
                    self.outputDb.put_slice(idsData)
                    print(f"[M3 Driver] Saved {idsName}")
                except Exception as e:
                    print(f"[M3 Driver] Error saving {idsName}: {e}", file=sys.stderr)

    def run(self):
        """主循环：时间步 + 耦合迭代"""
        print("[M3 Driver] Starting Main Loop...", file=sys.stdout)
        
        # 1. 确定时间范围
        try:
            time_array = self.inputDb.partial_get(ids_name="equilibrium", data_path="time")
            if self.tbegin < 0:
                self.tbegin = time_array[0]
            if self.tend < 0:
                self.tend = time_array[-1]
        except Exception as e:
            print(f"[M3 Driver] Warning: Could not read time array: {e}", file=sys.stderr)
            if self.tbegin < 0:
                self.tbegin = 0.0
            if self.tend < 0:
                self.tend = 1.0
        
        # 处理单时间切片模式
        if self.one_time_slice != 0:
            self.tend = self.tbegin + self.dt_required
        
        print(f"[M3 Driver] Time range: {self.tbegin:.3f} -> {self.tend:.3f} s, dt={self.dt_required:.3f}")
        
        # 2. MUSCLE3 主循环
        while self.instance.reuse_instance():
            timenow = self.tbegin
            step = 0
            
            # 3. 时间步循环
            while timenow < self.tend:
                step += 1
                t_next = timenow + self.dt_required
                
                print(f"\n{'='*60}")
                print(f"Step {step}: t={timenow:.4f} s")
                print(f"{'='*60}")
                
                # A. 读取输入数据
                ids_slices = self.getIDSSlices(timenow)
                if ids_slices is None:
                    print("[M3 Driver] Failed to read IDS slices, aborting")
                    break
                
                # B. 耦合迭代循环
                converged = False
                iteration = 0
                prev_results = None
                
                while not converged and iteration < self.max_iterations:
                    iteration += 1
                    print(f"\n--- Iteration {iteration} ---")
                    
                    # B1. 序列化并广播
                    payload = {}
                    for key, obj in ids_slices.items():
                        # 跳过 workflow IDS，因为它经常是空的且会导致 crash
                        if key == "workflow": 
                            continue

                        if hasattr(obj, 'serialize'):
                            try:
                                payload[key] = obj.serialize()
                            except Exception as e:
                                print(f"[M3 Driver] Warning: Skipping serialization of '{key}': {e}", file=sys.stdout)
                        else:
                            payload[key] = obj
                    
                    # B2. 发送给所有 Actor（使用动态端口）
                    msg = Message(timenow, t_next, payload)
                    try:
                        self.instance.send("state_out", msg)
                        print(f"  → Broadcast to all actors via state_out")
                    except Exception as e:
                        print(f"[M3 Driver] Error sending: {e}", file=sys.stderr)
                        break
                    
                    # B3. 收集所有 Actor 结果
                    merged_results = {}
                    for actor in self.actor_list:
                        port_name = f"result_from_{actor}"
                        print(f"  ← Waiting for {actor}...")
                        
                        try:
                            msg_in = self.instance.receive(port_name)
                            actor_result = deserialize_ids_dict(msg_in.data)
                            merged_results.update(actor_result)
                            print(f"  ✓ Received from {actor}")
                        except Exception as e:
                            print(f"  ✗ Error receiving from {actor}: {e}", file=sys.stderr)
                    
                    # B4. 检查收敛（简化版）
                    if prev_results is not None and iteration > 1:
                        # TODO: 实现真正的物理量收敛判据
                        converged = True  # 暂时假设收敛
                        print("  ✓ Converged (placeholder logic)")
                    
                    prev_results = merged_results
                    
                    # B5. 如果未收敛，更新 ids_slices 用于下次迭代
                    if not converged and iteration < self.max_iterations:
                        # TODO: 根据 merged_results 更新等离子体状态
                        pass
                
                # C. 保存最终结果
                self.storeIDSSlices(merged_results)
                
                # D. 推进时间
                timenow = t_next
                print(f"[M3 Driver] Step {step} complete.\n")
        
        # 4. 清理
        self.inputDb.close()
        self.outputDb.close()
        self.md.close()
        print("[M3 Driver] Workflow finished.", file=sys.stdout)


if __name__ == "__main__":
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else None
    driver = WorkflowDriverM3(cfg_path)
    driver.run()