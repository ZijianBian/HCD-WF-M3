import logging
import os
import sys
import inspect
from pathlib import Path


from libmuscle import Instance, Message, USES_CHECKPOINT_API
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

class WorkflowDriverM3(WorkflowDriver):
    """
    replace wf_wrapper.py + workflow_driver.py
    """
    
    def __init__(self, config_folder_path=None):

        self.instance = Instance({
            "state_out": Operator.O_I,
            "state_in": Operator.S
        })

        try:
            self.config_path = self.instance.get_setting("config_folder_path", "str")
        except KeyError:
            if config_folder_path:
                self.config_path = os.path.abspath(config_folder_path)
            else:
                print("[M3 Driver] Error: 'config_folder_path' not set.", file=sys.stderr)
                sys.exit(1)

        print(f"[M3 Driver] Init with config: {self.config_path}", file=sys.stdout)

        super().__init__(self.config_path)

        self._initialize_full_environment()
        
    def _initialize_full_environment(self):
        """
        Initialize databases and configuration (from original wrapper).
        This replaces the wf_wrapper function's setup logic.
        """
        #config_folder_path = self.workflowConfigPath
        
        # Load global configuration
        pathGlobalConfiguration = Path(inspect.getfile(hcdworkflow)).parent / "global_configuration"
        globalListPath = str(pathGlobalConfiguration / "global_lists.yaml")
        
        # Load workflow parameters
        inputworkflow_xml = os.path.join(config_folder_path, "input_workflow.xml")
        print("path of the input workflow", inputworkflow_xml)
        wf_parameters = create_workflow_param_from_file(inputworkflow_xml)["workflow_parameters"][0]
        
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
        
    def _prepare_machine_descriptions(self, wall_md):
        """Prepare machine description database (from original wrapper)."""
        for idsName in self.inputMds:
            idsObject = self.inputDb.get(idsName)
            if idsObject.ids_properties.homogeneous_time != imas.imasdef.EMPTY_INT:
                self.md.put(idsObject)
            else:
                if idsName == "wall":
                    try:
                        _backend = getattr(imas.imasdef, wall_md["backend"] + "_BACKEND")
                        wall = imas.DBEntry(
                            _backend,
                            wall_md["database"],
                            wall_md["shot"],
                            wall_md["run"],
                            wall_md["user_or_path"],
                        )
                        wall.open()
                        self.md.put(wall.get("wall"))
                    except Exception:
                        print("The wall IDS is neither in scenario data nor found in MD database --> try to run without.")
                else:
                    print(f"{idsName} is not present in the scenario data, "
                          "you can provide it with waveform cooker if required.")
    
    def _load_waveforms(self):
        """Load waveform configurations if present (from original wrapper)."""
        for filename in os.listdir(self.config_path):
            filePath = os.path.join(self.config_path, filename)
            if filePath.endswith("waveforms.yaml"):
                if os.path.exists(filePath):
                    idsObject = add_dynamic(filePath) if isWaveformCookerPresent else None
                    if idsObject is not None:
                        self.md.put(idsObject)
    


    
    def executeTimeloop(self, one_time_slice=None, tbegin=None, tend=None, dt_required=None):
        """
        Execute the main time loop (from original driver).
        Enhanced with MUSCLE3 communication capabilities.
        """
        # Set time parameters
        if one_time_slice is not None:
            self.workflowObject.workflowData.one_time_slice = one_time_slice
        if tbegin is not None:
            self.workflowObject.workflowData.tbegin = tbegin
        if tend is not None:
            self.workflowObject.workflowData.tend = tend
        if dt_required is not None:
            self.workflowObject.workflowData.dt_required = dt_required
        
        # Prepare time range
        self._prepare_time_range()
        
        # MUSCLE3: Check if we should reuse this instance
        while self.instance.reuse_instance():
            self._run_time_loop()
            
        # Cleanup
        self._cleanup()
    
    def _prepare_time_range(self):
        """Prepare and validate time range for the time loop."""
        if self.workflowObject.workflowData.one_time_slice == 0:
            # Get time array from equilibrium
            time_array = self.inputDb.partial_get(ids_name="equilibrium", data_path="time")
            
            # Adjust tbegin if needed
            if self.workflowObject.workflowData.tbegin < 0:
                self.workflowObject.workflowData.tbegin = time_array[0]
                print(f"Initial time tbegin set to equilibrium first time slice. tbegin = "
                      f"{self.workflowObject.workflowData.tbegin}", file=sys.stdout)
            
            if (self.workflowObject.workflowData.tbegin > 0 and 
                self.workflowObject.workflowData.tbegin < time_array[0]):
                print(f"ERROR: tbegin out of range: {self.workflowObject.workflowData.tbegin} s "
                      f"is less than first time in equilibrium = {time_array[0]:.2f} s",
                      file=sys.stderr)
                return
            
            # Adjust tend if needed
            if self.workflowObject.workflowData.tend < 0:
                self.workflowObject.workflowData.tend = time_array[-1]
                print(f"Final time tend set to equilibrium final time slice, tend = "
                      f"{self.workflowObject.workflowData.tend}", file=sys.stdout)
            
            if (self.workflowObject.workflowData.tend > 0 and 
                self.workflowObject.workflowData.tend > time_array[-1]):
                print(f"ERROR: tend out of range: {self.workflowObject.workflowData.tend} s "
                      f"is greater than last time in equilibrium = {time_array[-1]:.2f} s",
                      file=sys.stderr)
                return
        else:
            self.workflowObject.workflowData.tend = (
                self.workflowObject.workflowData.tbegin + 
                self.workflowObject.workflowData.dt_required
            )
    
    def _run_time_loop(self):
        """Execute the main time loop."""
        print("---------------------------------------------", file=sys.stdout)
        print("---- Enter time loop of the H&CD wrapper ----", file=sys.stdout)
        
        timenow = self.workflowObject.workflowData.tbegin
        
        # Calculate number of steps
        if self.workflowObject.workflowData.one_time_slice == 0:
            nsteps = int(
                (self.workflowObject.workflowData.tend - self.workflowObject.workflowData.tbegin)
                / self.workflowObject.workflowData.dt_required
            )
        else:
            nsteps = 1
        
        if (self.workflowObject.workflowData.dt_required * nsteps <
            int((self.workflowObject.workflowData.tend - self.workflowObject.workflowData.tbegin) * 10**5) / 10**5):
            nsteps = nsteps + 1
        
        step = 0
        previous_time = {}
        
        # Main time loop
        while timenow < self.workflowObject.workflowData.tend:
            step += 1
            
            print("---------------------------------------------", file=sys.stdout)
            print(f"Step = {step}/{nsteps}", file=sys.stdout)
            print(f"Time = {timenow:5.2f} s", file=sys.stdout)
            print(f"dt   = {self.workflowObject.workflowData.dt_required:5.2f} s", file=sys.stdout)
            
            # Get IDS slices for current time
            idsSlices = self.getIDSSlices(timenow)
            if idsSlices is None:
                return
            
            # Separate mandatory and non-mandatory IDSes
            nonmandatoryIDSes = {
                k: v for k, v in idsSlices.items() 
                if k not in ["equilibrium", "core_profiles", "workflow"]
            }
            
            # Set process status
            self.workflowObject.setProcessStatus(timenow)
            
            # Run workflow
            idsData = self.workflowObject.run(
                equilibrium=idsSlices["equilibrium"],
                core_profiles=idsSlices["core_profiles"],
                workflow=idsSlices["workflow"],
                **nonmandatoryIDSes,
            )
            
            # Prepare output IDSes
            idsOut = {
                idsName: idsData 
                for idsName, idsData in idsSlices.items() 
                if idsName not in self.inputMds
            }
            
            # Store IDS slices
            process_bundle_out = self.storeIDSSlices(idsOut)
            
            # Update previous_time tracking
            for ids in process_bundle_out.keys():
                if len(process_bundle_out[ids].time) > 0:
                    if (process_bundle_out[ids].time[0] > 0 or 
                        "merge" in process_bundle_out[ids].code.name):
                        previous_time[ids] = process_bundle_out[ids].time[0]
            
            # MUSCLE3: Send results at each time step
            self._send_muscle3_outputs(timenow, process_bundle_out)
            
            # Prepare for next time step
            timenow = timenow + self.workflowObject.workflowData.dt_required
            self._copy_output_to_input()
    
    def getIDSSlices(self, timenow):
        """
        Get IDS slices for the current time (from original driver).
        Could be enhanced to receive data via MUSCLE3 ports.
        """
        idsSlices = {}
        
        # Read scenario IDSes
        for ids in self.inputIds:
            print(f"  Get {ids}", file=sys.stdout)
            try:
                idsSlices[ids] = self.inputDb.get_slice(ids, timenow, 1)
            except Exception:
                print(f"  ERROR while reading the {ids} IDS:", file=sys.stderr)
                print("  ----> Check the version of the Data Dictionary between the "
                      "input and the loaded IMAS version.", file=sys.stderr)
                print("  ----> Aborted.", file=sys.stderr)
                return None
        
        # Read machine description IDSes
        for ids in self.inputMds:
            try:
                idsSlices[ids] = self.md.get_slice(ids, timenow, 1)
            except Exception:
                print(f"  ERROR while reading the {ids} IDS:", file=sys.stderr)
                print("  ----> Check the version of the Data Dictionary between the "
                      "input and the loaded IMAS version.", file=sys.stderr)
                print("  ----> Aborted.", file=sys.stderr)
                return None
        
        return idsSlices
    
    def storeIDSSlices(self, inputSlices):
        """Store IDS slices to output database (from original driver)."""
        # Store input IDSes to disk
        for idsName, idsData in inputSlices.items():
            if idsData.ids_properties.homogeneous_time >= 0:
                self.outputDb.put_slice(idsData)
        
        # Prepare output bundle
        process_bundle_out = {}
        
        # Take merger output IDS if there is any
        for process in self.workflowObject.workflowData.process_bundle.keys():
            if "merge_" in process:
                key, value = list(
                    self.workflowObject.workflowData.process_bundle[process]["output"].items()
                )[0]
                process_bundle_out[key] = value
        
        # Take all other output IDS but only if not already a merger output
        for process in self.workflowObject.workflowData.process_bundle.keys():
            for key, value in self.workflowObject.workflowData.process_bundle[process]["output"].items():
                if key not in process_bundle_out.keys():
                    process_bundle_out[key] = value
        
        # Save to disk
        for ids in process_bundle_out:
            if len(process_bundle_out[ids].time) > 0:
                if (process_bundle_out[ids].time[0] > 0 or 
                    "merge" in process_bundle_out[ids].code.name):
                    if ids != "equilibrium":
                        self.outputDb.put_slice(process_bundle_out[ids])
        
        return process_bundle_out
    
    def _copy_output_to_input(self):
        """Copy output IDS to input for next time step."""
        for process in self.workflowObject.workflowData.process_bundle.keys():
            if "merge_" not in process:
                for ids in self.workflowObject.workflowData.process_bundle[process]["output"].keys():
                    if (type(self.workflowObject.workflowData.process_bundle[process]["input"]) is dict and
                        ids in self.workflowObject.workflowData.process_bundle[process]["input"].keys()):
                        print(f"Copy {ids} from output to input for {process} for next time slice")
                        self.workflowObject.workflowData.process_bundle[process]["input"][ids] = \
                            self.workflowObject.workflowData.process_bundle[process]["output"][ids]
    
    def _send_muscle3_outputs(self, timenow, process_bundle_out):
        """
        Send outputs via MUSCLE3 ports.
        This is the key MUSCLE3 integration point.
        """
        # Package results for MUSCLE3 transmission
        results = {
            'time': timenow,
            'process_outputs': {}
        }
        
        for ids_name, ids_data in process_bundle_out.items():
            if len(ids_data.time) > 0:
                # Convert IDS data to serializable format
                # This might need custom serialization depending on your data structure
                results['process_outputs'][ids_name] = {
                    'time': ids_data.time.tolist() if hasattr(ids_data.time, 'tolist') else ids_data.time,
                    # Add other relevant fields as needed
                }
        
        # Send via MUSCLE3
        self.instance.send('results_out', Message(timenow, data=results))
    
    def _cleanup(self):
        """Cleanup databases and resources."""
        if self.inputDb:
            self.inputDb.close()
        if self.outputDb:
            self.outputDb.close()
        if self.md:
            self.md.close()
        print("End of workflow execution")


def main():
    """
    Main entry point for MUSCLE3-enabled workflow.
    Replaces the original wf_wrapper function call.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python driver_m3.py <config_folder_path>")
        sys.exit(1)
    
    config_folder_path = sys.argv[1]
    
    # Initialize driver
    driver = WorkflowDriverMUSCLE3(config_folder_path)
    
    # Initialize from configuration
    driver.initialize_from_config()
    
    # Execute time loop with MUSCLE3 integration
    driver.executeTimeloop()


if __name__ == "__main__":
    main()