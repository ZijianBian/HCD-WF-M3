import sys
import os
import imas
from libmuscle import Instance, Message
from ymmsl import Operator

# 复用现有的 iwrap 封装
from hcdworkflow.workflow_actor import WorkflowActor
# 复用反序列化工具
from hcdworkflow.workflow_driver_m3 import deserialize_ids_dict

class GenericM3Actor:
    """
    [通用 Muscle3 Actor]
    支持两种模式：
    1. Standard Solver: NBI, ICRH, ECRH 等物理代码。
    2. Merger: 接收多个 IDS 并合并的工具 (例如 merge_core_sources)。
    """

    def __init__(self):
        # 1. 声明端口
        # state_in_1: 主输入 (Equilibrium / Core_Profiles / 待合并IDS_1)
        # state_in_2: 副输入 (待合并IDS_2, 仅 Merger 模式使用)
        # ids_out:  发送计算结果
        self.instance = Instance({
            "state_in_1": Operator.F_INIT, 
            "state_in_2": Operator.F_INIT, # 可选，用于 Merger
            "ids_out": Operator.O_F
        })

        # 2. 读取配置
        try:
            self.actor_name = self.instance.get_setting("actor_name", "str")
            self.config_folder_path = self.instance.get_setting("config_folder_path", "str")
            # 新增: 判断是否是 Merger 模式
            # 在 ymmsl 中设置 is_merger: true
            self.is_merger = self.instance.get_setting("is_merger", "bool") if self.instance.get_setting("is_merger", "bool") else False
        except KeyError:
            # 默认不是 Merger
            self.is_merger = False
            if not hasattr(self, 'actor_name'):
                print("[M3 Actor] Error: 'actor_name' missing.", file=sys.stderr)
                sys.exit(1)

        # 3. XML 路径构建
        # Merger 通常不需要 XML，或者是特殊的 XML
        try:
            self.xml_path = self.instance.get_setting("actor_xml_path", "str")
        except KeyError:
            self.xml_path = os.path.join(self.config_folder_path, f"input_{self.actor_name}.xml")
            if not os.path.exists(self.xml_path):
                self.xml_path = ""

        # 4. 初始化 Legacy Wrapper
        try:
            self.legacy_wrapper = WorkflowActor(self.actor_name, self.xml_path)
            # 预加载 Actor 函数
            self.actor_func = self.legacy_wrapper.getActor()
        except Exception as e:
            print(f"[M3 Actor] Failed to load legacy actor {self.actor_name}: {e}", file=sys.stderr)
            sys.exit(1)
        
        # 5. 获取输入输出键
        self.input_keys = self.legacy_wrapper.getInputIDSList()
        self.output_keys = self.legacy_wrapper.getOutputIDSList()
        
        mode_str = "MERGER" if self.is_merger else "SOLVER"
        print(f"[M3 Actor] Initialized as {mode_str}: {self.actor_name}", file=sys.stdout)

    def run(self):
        while self.instance.reuse_instance():
            # --- 1. 接收数据 ---
            # 总是接收主输入
            msg1 = self.instance.receive("state_in_1")
            timestamp = msg1.timestamp
            data1 = deserialize_ids_dict(msg1.data)
            
            # 如果是 Merger，还需要接收第二个输入
            data2 = None
            if self.is_merger and self.instance.is_connected("state_in_2"):
                msg2 = self.instance.receive("state_in_2")
                data2 = deserialize_ids_dict(msg2.data)
            
            # --- 2. 执行逻辑 ---
            print(f"[M3 Actor] Executing {self.actor_name} at t={timestamp}...", file=sys.stdout)
            results = None
            
            try:
                if self.is_merger:
                    # === Merger 模式 ===
                    # 根据 executor.py，Merger 接受两个参数 (IDS 对象)
                    # 我们需要从 data1 和 data2 中提取出待合并的 IDS 对象
                    # 假设 Merger 的 input_keys[0] 就是要合并的 IDS 类型名
                    target_key = self.input_keys[0]
                    
                    obj1 = data1.get(target_key)
                    obj2 = data2.get(target_key) if data2 else None
                    
                    if obj1 and obj2:
                        # 调用合并函数: actor(obj1, obj2)
                        results = self.actor_func(obj1, obj2)
                    else:
                        print(f"[M3 Merger] Error: Missing inputs for merge.", file=sys.stderr)
                
                else:
                    # === Solver 模式 (原逻辑) ===
                    call_args = {}
                    for key in self.input_keys:
                        if key in data1:
                            call_args[key] = data1[key]
                    
                    # 调用物理代码: actor(**kwargs)
                    results = self.actor_func(**call_args)
                    
            except Exception as e:
                print(f"[M3 Actor] Execution Error: {e}", file=sys.stderr)
                results = {}

            # --- 3. 序列化结果 ---
            serialized_out = {}
            
            # 通用序列化逻辑 (适配对象、字典、元组返回)
            if hasattr(results, 'serialize'):
                out_name = self.output_keys[0] if self.output_keys else self.actor_name
                serialized_out[out_name] = results.serialize()
            elif isinstance(results, dict):
                for k, v in results.items():
                    if hasattr(v, 'serialize'):
                        serialized_out[k] = v.serialize()
            elif isinstance(results, (list, tuple)):
                for i, val in enumerate(results):
                    if i < len(self.output_keys) and hasattr(val, 'serialize'):
                        serialized_out[self.output_keys[i]] = val.serialize()

            # --- 4. 发送 ---
            self.instance.send("ids_out", Message(timestamp, msg1.next_timestamp, serialized_out))
            print(f"[M3 Actor] Step finished.", file=sys.stdout)

if __name__ == "__main__":
    GenericM3Actor().run()