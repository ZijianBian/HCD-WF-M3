import copy
import logging
import os
import sys
import numpy as np

from hcdworkflow.workflow_base import WorkflowBase
from hcdworkflow.workflow_data import WorkflowData
from hcdworkflow.workflow_executor import WorkflowExecutor

log = logging.getLogger()
log.setLevel(logging.ERROR)


def find_nearest(a, a0):
    "Element in nd array `a` closest to the scalar value `a0`"
    idx = np.abs(a - a0).argmin()
    return a.flat[idx], idx


class HCDWorkflow(WorkflowBase):
    def __init__(self):
        self.__initialized = False

    def initialize(self, workflowConfigPath: str):
        self.workflowData = WorkflowData(workflowConfigPath)
        self.__initialized = True

    def __call__(self, *args):
        return self.run(*args)

    def check_is_initialized(self):
        if not self.__initialized:
            message = "Workflow is not initialized. Initialize workflow by calling workflow.initialize() method"
            raise RuntimeError(message)

    def run(self, equilibrium, core_profiles, workflow,**kwargs):
        # self.check_is_initialized()
        inputIDSes = {
            "equilibrium": equilibrium,
            "core_profiles": core_profiles,
            "workflow": workflow,
        }
        for key, value in kwargs.items():
            inputIDSes[key] = value

        self._setIDSes(inputIDSes)
        param_process = self.workflowData.getParamProcess()
        hcd_wf = WorkflowExecutor(
            self.workflowData.process_bundle,
            self.workflowData.dictionary_of_actors,
            param_process,
            self.workflowData.catdict,
            self.workflowData.parallel_dependency,
            self.workflowData.algorithms,
            self.workflowData.parallel_dependency_list,
            self.workflowData.merge_actor_list,
        )
        err = hcd_wf.execute()
        if err < 0:
            print("  Error in H&CD workflow.", file=sys.stderr)
            return

        return self._getIDSes()

    def _setIDSes(self, idsSlices):
        for idsName, idsData in idsSlices.items():
            for process in self.workflowData.process_bundle.keys():
                if (
                    "merge_" not in process
                    and idsName
                    in self.workflowData.process_bundle[process]["input"].keys()
                ):
                    if idsName == "workflow":
                        # TODO Find way to set workflow IDS, passed from external world
                        workflow = idsData
                        workflow.ids_properties.homogeneous_time = 1
                        workflow.time.resize(1)
                        workflow.time_loop.component.resize(1)
                        workflow.time_loop.workflow_cycle.resize(1)
                        workflow.time_loop.workflow_cycle[0].component.resize(1)
                        try:
                            workflow.time_loop.workflow_cycle[0].component[0].time_interval_request = self.workflowData.dt_required
                        except:
                            workflow.time_loop.workflow_cycle[0].component[0].time_interval = self.workflowData.dt_required
                        workflow.time_loop.component[0].name = self.workflowData.code_selection[process].upper()
                        self.workflowData.process_bundle[process]["input"]["workflow"] = copy.deepcopy(workflow)
                        continue
                    self.workflowData.process_bundle[process]["input"][
                        idsName
                    ] = idsData
        

        for process in self.workflowData.process_bundle:
            if "workflow" in self.workflowData.process_bundle[process]["input"]:
                workflow.time_loop.component[0].name = self.workflowData.code_selection[
                    process
                ].upper()
                self.workflowData.process_bundle[process]["input"]["workflow"] = copy.deepcopy(
                    workflow
                )

    def setProcessStatus(self, timenow=None):
        if timenow is not None:
            time_base = self.workflowData.getTimeBase()

            for process in self.workflowData.process_bundle.keys():
                if time_base is not None:
                    if process in time_base:
                        [tc, it] = find_nearest(
                            np.array(
                                time_base[process][0]["wf_interval"][0]["time_array"][0]
                            ),
                            timenow,
                        )
                        self.workflowData.process_bundle[process]["status"] = time_base[
                            process
                        ][0]["wf_interval"][0]["status"][0][it]
                    else:
                        self.workflowData.process_bundle[process]["status"] = 1
                else:
                    self.workflowData.process_bundle[process]["status"] = 1
        else:
            for process in self.workflowData.process_bundle.keys():
                self.workflowData.process_bundle[process]["status"] = 1

    def _getIDSes(self):
        # ------------------------------
        # COMMON BUNDLE TO SAVE TO DISK
        # ------------------------------
        idsOut = {}

        # TAKE THE MERGER OUTPUT IDS IF THERE IS ANY
        for process in self.workflowData.process_bundle.keys():
            if "merge_" in process:
                key, value = list(
                    self.workflowData.process_bundle[process]["output"].items()
                )[0]
                idsOut[key] = value

        # TAKE ALL OTHER OUTPUT IDS BUT ONLY IF IT WAS NOT A MERGER OUTPUT ALREADY
        for process in self.workflowData.process_bundle.keys():
            for key, value in self.workflowData.process_bundle[process][
                "output"
            ].items():
                if key not in idsOut.keys():
                    idsOut[key] = value

        return idsOut

    def finalize(self):
        # FINALIZE ALL ACTORS
        pass
        # feature/repair_231017
        # for actor_name, actor in self.workflowData.dictionary_of_actors.items():
        #     actor.finalize()

    def get_state(self) -> str:
        pass

    def set_state(self, state: str) -> None:
        pass

    def get_timestamp(self) -> float:
        pass

        # Temporary version:
        # common_bundle contains all IDSs to be read via get_slice() from input scenario, defined by ids_scenario_list
        # process_bundle contains all other input and output IDSs (total list = ids_md_list + ids_process_list)
        #    - all its inputs from ids_md_list to be read via get() or get_slice()
        #    - all other inputs from ids_process_list are output of upstream actors
        #      to be copied from the output bundle of upstream actors inside the time loop
        #      according to the parallel_dependency constraints

        # READ ALL MACHINE DESCRITPTION IDSS FOR THE CURRENT TIME SLICE
        # for idsName, idsData in idsSlices.items():
        #     print("  Get", idsName, file=sys.stdout)
        #     for process in self.workflowData.process_bundle.keys():
        #         if idsName in self.workflowData.process_bundle[process]["input"].keys():
        #             self.workflowData.process_bundle[process]["input"][
        #                 idsName
        #             ] = idsData

        # ---------------------------------------------------------------------
        # FIND OUT WHETHER EACH PROCESS IS ACTIVATED OR NOT FOR THIS TIME SLICE
        # ---------------------------------------------------------------------
