import copy
import os
import sys

import imas
from importlib_resources import files
from src.workflow_globals_reader import WorkflowGlobalsReader
from src.workflow_config_reader import WorkflowConfigReader


# TODO Separate static and runtime part of the data
class WorkflowData:
    def __init__(self, workflowConfig) -> None:
        workflowConfig = os.path.join(workflowConfig, "input_workflow.xml")
        self.globalList = str(files('src.global_configuration').joinpath('global_lists.yaml'))
    
        self.workflowConfig = WorkflowConfigReader(workflowConfig)
        self.globalListReader = WorkflowGlobalsReader(self.globalList)
        self.catdict = self.workflowConfig.getCategories()
        self.initializeData()

        self.validate()

        # self.createWorkflowIDS(self.dt_required)

    def validate(self):
        if self.workflowConfig.AreProcessesEmpty() is True:
            print(
                "ERROR: no actor selected --> The H&CD workflow will not be executed",
                file=sys.stderr,
            )
            return

        err = self.validatePrerquisitesOfCodes()
        if err == 0:
            print("Selection fulfills all actor selection rules", file=sys.stdout)
        else:
            print("Please change the actor selection and try again.", file=sys.stderr)
            return

    def getParamProcess(self):
        return self.workflowConfig.getParamProcess()

    # TODO make it object variable
    def getTimeBase(self):
        return self.workflowConfig.getTimeBase()

    def initializeData(self):
        self.dictionary_of_actors = self.workflowConfig.getAllActors()

        allProcesses = self.workflowConfig.getAllProcesses()
        self.code_selection = {k: v.name for (k, v) in allProcesses.items()}
        self.process_bundle = self.workflowConfig.getProcessBundle()
        self.workflowParameters = self.workflowConfig.getWorkflowParameters()
        self.dt_required = float(self.workflowParameters["dt_required"])
        self.one_time_slice = int(self.workflowParameters["one_time_slice"])
        self.tbegin = float(self.workflowParameters["tbegin"])
        self.tend = float(self.workflowParameters["tend"])

        self.prerequisites = self.globalListReader.getPrerequisites()
        self.waveform_presets = self.globalListReader.getWaveformPresetsList()
        self.parallel_dependency_list = self.globalListReader.getParallelDependency()
        self.merge_actor_list = self.globalListReader.getMergeActorList()
        self.parallel_dependency = self.globalListReader.getParallelDependency()
        self.algorithms = self.globalListReader.getAlgorithms()

        merge_actors = self.workflowConfig.getAllMergers(self.merge_actor_list)
        self.dictionary_of_actors.update(merge_actors)

    def createWorkflowIDS(self, dt_required):
        # WORKFLOW IDS CONFIGURATION ACCORDING TO THE TIME LOOP PARAMETERS
        workflow = imas.workflow()
        workflow.ids_properties.homogeneous_time = 1
        workflow.time.resize(1)
        workflow.time_loop.component.resize(1)
        workflow.time_loop.workflow_cycle.resize(1)
        workflow.time_loop.workflow_cycle[0].component.resize(1)
        workflow.time_loop.workflow_cycle[0].component[0].time_interval = dt_required

        for process in self.process_bundle.keys():
            if "workflow" in self.process_bundle[process]["input"].keys():
                workflow.time_loop.component[0].name = self.code_selection[
                    process
                ].upper()
                self.process_bundle[process]["input"]["workflow"] = copy.deepcopy(
                    workflow
                )

    # TODO Refactor this
    def validatePrerquisitesOfCodes(self):
        global_error = 0
        for entry, _ in self.code_selection.items():
            if self.code_selection != None:
                err = 0
                code = self.code_selection[entry]
                if self.prerequisites[entry] == "None":
                    self.prerequisites[entry] = None
                if (
                    self.prerequisites[entry] != None
                    and code in self.prerequisites[entry]
                ):
                    fulfills_all_prerequisites = [1] * (
                        len(self.prerequisites[entry][code])
                    )
                    for dep in [self.prerequisites[entry][code]]:
                        for i in dep.keys():
                            if "any" in str(dep[i]) and self.code_selection[i] != None:
                                pass
                            elif str(dep[i]).find(str(self.code_selection[i])) != -1:
                                pass
                            else:
                                if str(dep[i]) == "any":
                                    print(
                                        "ERROR: "
                                        + code.upper()
                                        + " needs any code as "
                                        + str(i),
                                        file=sys.stderr,
                                    )
                                else:
                                    if len(dep[i]) < 2:
                                        print(
                                            "ERROR: "
                                            + code.upper()
                                            + " needs the "
                                            + str(dep[i][0]).upper()
                                            + " code as "
                                            + str(i),
                                            file=sys.stderr,
                                        )
                                    else:
                                        print(
                                            "ERROR: "
                                            + code.upper()
                                            + " needs the "
                                            + " or ".join(dep[i])
                                            .upper()
                                            .replace("OR", "or")
                                            + " codes as "
                                            + str(i),
                                            file=sys.stderr,
                                        )
                                err = 1
                global_error = global_error + err
        return global_error
