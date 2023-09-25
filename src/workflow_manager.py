import copy
import logging
import os
import sys
from multiprocessing import Pool
from time import time

import imas
import numpy as np
from lxml import etree
from waveform_cooker import add_dynamic
from wftools.wf_tools import (add_ids_entry_to_dict, bundle_copy,
                              check_if_code_fulfills_configuration,
                              clever_algo, create_dict_from_idslist,
                              create_maindict, create_workflow_param_from_file,
                              find_nearest, import_actor, read_actor_ids)

from src.workflow_base import WorkflowBase
from src.workflow_config_reader import WorkflowConfigReader
from src.workflow_data import WorkflowData
from src.workflow_executor import WorkflowExecutor
from src.workflow_globals_reader import WorkflowGlobalsReader

log = logging.getLogger()
log.setLevel(logging.ERROR)

from tools.stdout_redirector import redirect_stdout, stdout_back

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class WorkflowManager():
    def __init__(self, workflowConfigPath: str):
        # READ WORKFLOW PARAMETERS FROM INPUT XML FILE
        # YAML FILE CONTAINING ALL USEFUL LISTS
        self.workflowConfigPath = workflowConfigPath

    def createMachineDescriptionIDSes(self, inputMdsDict):
        mdCounter = 0

        allMachineDescriptionIDSes = []
        for process in self.workflowData.process_bundle.keys():
            if "nuclear" not in process:  # No waveform for nuclear reactions
                for ids in self.workflowData.process_bundle[process]["input"].keys():
                    if ids in inputMdsDict.keys():
                        self.workflowData.process_bundle[process]["input"][ids] = inputMdsDict[ids]
                        # Overwrite with configured waveform if it exists
                        waveform_file = (
                            f"{self.workflowConfigPath}/"
                            + self.workflowData.waveform_presets[process.split("_")[0]]["custom"][
                                mdCounter
                            ]
                        )
                        if os.path.exists(waveform_file):
                            self.workflowData.process_bundle[process]["input"][ids] = add_dynamic(
                                waveform_file
                            )
                            mdCounter += 1
                        self.md.put(self.workflowData.process_bundle[process]["input"][ids])
                        if ids not in allMachineDescriptionIDSes:
                            allMachineDescriptionIDSes.append(ids)
        return allMachineDescriptionIDSes

    def initializeSlice(self):
        self.workflowData = WorkflowData(self.workflowConfigPath)

        # self.md = machineDb
        # self.machineDescriptionIDSes = self.createMachineDescriptionIDSes(inputMdsDict)

        # # DEFINE LIST OF SELECTED ACTORS AND INVOLVED IDSS
        # # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
        # # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
        # self.inputDb = inputdb
        # self.outputDb = outputdb
        # self.ids_scenario_list = inputIds

        # self.common_bundle = {}
        # add_ids_entry_to_dict(self.common_bundle, self.ids_scenario_list)

        # # IMAS DB VERSION
        # version = os.getenv("IMAS_VERSION")[0]

    def initialize(self, inputdb, outputdb, machineDb, inputIds, inputMdsDict):
        self.workflowData = WorkflowData(self.workflowConfigPath)

        self.md = machineDb
        self.machineDescriptionIDSes = self.createMachineDescriptionIDSes(inputMdsDict)

        # DEFINE LIST OF SELECTED ACTORS AND INVOLVED IDSS
        # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
        # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
        self.inputDb = inputdb
        self.outputDb = outputdb
        self.ids_scenario_list = inputIds

        self.common_bundle = {}
        add_ids_entry_to_dict(self.common_bundle, self.ids_scenario_list)

        # IMAS DB VERSION
        version = os.getenv("IMAS_VERSION")[0]

    def __call__(self, *args):
        return self.run(*args)

    def check_is_initialized(self):
        if not self.__initialized:
            message = "Workflow is not initialized. Initialize workflow by calling workflow.initialize() method"
            raise RuntimeError(message)

    def run(self, *args):
        # -----------------------------------------
        # PREPARE THE TIME RANGE FOR THE TIME LOOP
        # -----------------------------------------       
        if self.workflowData.one_time_slice == 0:
            # INPUT TIME ARRAY
            try:
                time_array = self.inputDb.partial_get(
                    ids_name="equilibrium", data_path="time"
                )
            except:
                print(
                    "  ERROR while reading the core_profiles IDS: is it really present in the input file?",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return

            # CHECK & ADJUST CHOSEN TIME TO CORE_PROFILES IF NECESSARY
            if self.workflowData.tbegin < 0:
                self.workflowData.tbegin = time_array[0]
                print(
                    "Initial time tbegin set to core_profiles first time slice. tbegin = ",
                    self.workflowData.tbegin,
                    file=sys.stdout,
                )

            if self.workflowData.tbegin > 0 and self.workflowData.tbegin < time_array[0]:
                print(
                    "ERROR: tbegin out of range: "
                    + str(self.workflowData.tbegin)
                    + " s is less than first time in core_profiles =",
                    "{:.2f}".format(time_array[0]),
                    "s",
                    file=sys.stderr,
                )
                return

            if self.workflowData.tend < 0:
                self.tend = time_array[-1]
                print(
                    "Final time tend set to core_profiles final time slice, tend = ",
                    self.tend,
                    file=sys.stdout,
                )

            if self.workflowData.tend > 0 and self.workflowData.tend > time_array[-1]:
                print(
                    "ERROR: tend out of range: "
                    + str(self.workflowData.tend)
                    + " s is greater than last time in core_profiles =",
                    "{:.2f}".format(time_array[-1]),
                    "s",
                    file=sys.stderr,
                )
                return
        else:
            self.workflowData.tend = self.workflowData.tbegin + self.workflowData.dt_required

        ##################################################################

        # -----------------
        # BEGIN TIME LOOP
        # -----------------

        print("---------------------------------------------", file=sys.stdout)
        print("---- Enter time loop of the H&CD wrapper ----", file=sys.stdout)

        timenow = self.workflowData.tbegin

        if self.workflowData.one_time_slice == 0:
            nsteps = int((self.workflowData.tend - self.workflowData.tbegin) / self.workflowData.dt_required)
        else:
            nsteps = 1
        if (
            self.workflowData.dt_required * nsteps
            < int((self.workflowData.tend - self.workflowData.tbegin) * 10**5) / 10**5
        ):
            nsteps = nsteps + 1

        step = 0
        previous_time = {}

        while timenow < self.workflowData.tend:
            step += 1

            print("---------------------------------------------", file=sys.stdout)
            print("Step = " + str(step) + "/" + str(nsteps), file=sys.stdout)
            print("Time = %5.2f" % timenow, "s", file=sys.stdout)
            print("dt   = %5.2f" % self.workflowData.dt_required, "s", file=sys.stdout)

            # READ ALL INPUT IDSS FROM THE SCENARIO FOR THE CURRENT TIME SLICE
            self.initializeIDSSlices(
                timenow,
                self.ids_scenario_list,
                self.inputDb,
                self.common_bundle,
            )
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

            process_bundle_out = self.storeIDSOutput(
                self.common_bundle, self.workflowData.process_bundle, self.outputDb
            )

            for ids in process_bundle_out.keys():
                if (
                    len(process_bundle_out[ids].time) > 0
                ):  # Empty if process deactivated by an is_xx_on function
                    if (
                        process_bundle_out[ids].time[0] > 0
                        or "merge" in process_bundle_out[ids].code.name
                    ):
                        previous_time[ids] = process_bundle_out[ids].time[0]
            # ------------------------------------------------------------------------------------------
            # PREPARE FOR THE NEXT TIME STEP: COPY OUTPUT IDS IN INPUT OF ACTORS FOR THE NEXT TIME STEP
            # ------------------------------------------------------------------------------------------
            timenow = timenow * 1.0 + self.workflowData.dt_required * 1.0
            for process in self.workflowData.process_bundle.keys():
                if "merge_" not in process:
                    for ids in self.workflowData.process_bundle[process]["output"].keys():
                        if (
                            type(self.workflowData.process_bundle[process]["input"]) is dict
                            and ids in self.workflowData.process_bundle[process]["input"].keys()
                        ):
                            print(
                                "Copy "
                                + ids
                                + " from output to input for "
                                + process
                                + " for next time slice"
                            )
                            self.workflowData.process_bundle[process]["input"][
                                ids
                            ] = self.workflowData.process_bundle[process]["output"][ids]

    def runSlice(self, idsslices, mdidsslices, timenow):
        # READ ALL INPUT IDSS FROM THE SCENARIO FOR THE CURRENT TIME SLICE
        self.initializeExtermalIDSSlices(idsslices, mdidsslices, timenow)
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

            # process_bundle_out = self.storeIDSOutput(
            #     self.common_bundle, self.process_bundle, self.outputDb
            # )

            # for ids in process_bundle_out.keys():
            #     if (
            #         len(process_bundle_out[ids].time) > 0
            #     ):  # Empty if process deactivated by an is_xx_on function
            #         if (
            #             process_bundle_out[ids].time[0] > 0
            #             or "merge" in process_bundle_out[ids].code.name
            #         ):
            #             previous_time[ids] = process_bundle_out[ids].time[0]
            # # ------------------------------------------------------------------------------------------
            # # PREPARE FOR THE NEXT TIME STEP: COPY OUTPUT IDS IN INPUT OF ACTORS FOR THE NEXT TIME STEP
            # # ------------------------------------------------------------------------------------------
            # timenow = timenow * 1.0 + self.dt_required * 1.0
            # for process in self.process_bundle.keys():
            #     if "merge_" not in process:
            #         for ids in self.process_bundle[process]["output"].keys():
            #             if (
            #                 type(self.process_bundle[process]["input"]) is dict
            #                 and ids in self.process_bundle[process]["input"].keys()
            #             ):
            #                 print(
            #                     "Copy "
            #                     + ids
            #                     + " from output to input for "
            #                     + process
            #                     + " for next time slice"
            #                 )
            #                 self.process_bundle[process]["input"][
            #                     ids
            #                 ] = self.process_bundle[process]["output"][ids]

    def initializeIDSSlices(
        self,
        timenow,
        ids_scenario_list,
        inputDb,
        common_bundle,
    ):
        for ids in ids_scenario_list:
            print("  Get", ids, file=sys.stdout)
            try:
                common_bundle[ids] = inputDb.get_slice(ids, timenow, 1)
                # if common_bundle[ids] == 'equilibrium': # when equilibrium misses phi(r,z)
                #  if len(common_bundle[ids].time_slice[0].profiles_2d[0].phi)==0:
                #    print('   --- Interpolate missing phi(R,Z) ---')
                #    r1d_eq   = common_bundle[ids].time_slice[0].profiles_2d[0].grid.dim1
                #    z1d_eq   = common_bundle[ids].time_slice[0].profiles_2d[0].grid.dim2
                #    rho1d_eq = common_bundle[ids].time_slice[0].profiles_1d.rho_tor_norm
                #    psi1d_eq = common_bundle[ids].time_slice[0].profiles_1d.psi
                #    psi2d_eq = common_bundle[ids].time_slice[0].profiles_2d[0].psi
                #    rho_from_psi = interpolate.interp1d(psi1d_eq,rho1d_eq,kind='linear')
                #    phi2d_eq = np.zeros(np.shape(psi2d_eq))
                #    for ir in range(len(r1d_eq)):
                #      for iz in range(len(z1d_eq)):
                #        try: # Inside LCFS
                #          phi2d_eq[ir,iz] = rho_from_psi(psi2d_eq[ir,iz])
                #        except: # Outside LCFS
                #          phi2d_eq[ir,iz] = 1.
                #    common_bundle[ids].time_slice[0].profiles_2d[0].phi = phi2d_eq
                for process in self.workflowData.process_bundle.keys():
                    if (
                        "merge_" not in process
                        and ids in self.workflowData.process_bundle[process]["input"].keys()
                    ):
                        self.workflowData.process_bundle[process]["input"][ids] = common_bundle[ids]
            except:
                print("  ERROR while reading the " + ids + " IDS:", file=sys.stderr)
                print(
                    "  ----> Check the version of the Data Dictionary between the"
                    + " input and the loaded IMAS version.",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return

        # READ ALL MACHINE DESCRITPTION IDSS FOR THE CURRENT TIME SLICE
        for ids in self.machineDescriptionIDSes:
            print("  Get", ids, file=sys.stdout)
            try:
                for process in self.workflowData.process_bundle.keys():
                    if ids in self.workflowData.process_bundle[process]["input"].keys():
                        self.workflowData.process_bundle[process]["input"][ids] = self.md.get_slice(
                            ids, timenow, 1
                        )
            except:
                print("  ERROR while reading the " + ids + " IDS:", file=sys.stderr)
                print(
                    "  ----> Check the version of the Data Dictionary between the"
                    + " input and the loaded IMAS version.",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return

        # ---------------------------------------------------------------------
        # FIND OUT WHETHER EACH PROCESS IS ACTIVATED OR NOT FOR THIS TIME SLICE
        # ---------------------------------------------------------------------
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
                    self.workflowData.process_bundle[process]["status"] = time_base[process][0][
                        "wf_interval"
                    ][0]["status"][0][it]
                else:
                    self.workflowData.process_bundle[process]["status"] = 1
            else:
                self.workflowData.process_bundle[process]["status"] = 1

    def initializeExtermalIDSSlices(self, idsSlices, mdIdsSlices, timenow):
        for idsName, idsData in idsSlices.items():
            print("  Loading slice", idsName, file=sys.stdout)
            for process in self.workflowData.process_bundle.keys():
                if (
                    "merge_" not in process
                    and idsName in self.workflowData.process_bundle[process]["input"].keys()
                ):
                    self.workflowData.process_bundle[process]["input"][idsName] = idsData

        # READ ALL MACHINE DESCRITPTION IDSS FOR THE CURRENT TIME SLICE
        for idsName, idsData in mdIdsSlices.items():
            print("  Get", idsName, file=sys.stdout)
            for process in self.workflowData.process_bundle.keys():
                if idsName in self.workflowData.process_bundle[process]["input"].keys():
                    self.workflowData.process_bundle[process]["input"][idsName] = idsData

        # ---------------------------------------------------------------------
        # FIND OUT WHETHER EACH PROCESS IS ACTIVATED OR NOT FOR THIS TIME SLICE
        # ---------------------------------------------------------------------
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
                    self.workflowData.process_bundle[process]["status"] = time_base[process][0][
                        "wf_interval"
                    ][0]["status"][0][it]
                else:
                    self.workflowData.process_bundle[process]["status"] = 1
            else:
                self.workflowData.process_bundle[process]["status"] = 1

    def storeIDSOutput(self, common_bundle, process_bundle, outputDb):
        # ------------------------------
        # COMMON BUNDLE TO SAVE TO DISK
        # ------------------------------
        for ids in common_bundle.keys():
            if common_bundle[ids].ids_properties.homogeneous_time >= 0:
                outputDb.put_slice(common_bundle[ids])

        # ------------------------------
        # OUTPUT BUNDLE TO SAVE TO DISK
        # ------------------------------
        process_bundle_out = {}

        # TAKE THE MERGER OUTPUT IDS IF THERE IS ANY
        for process in process_bundle.keys():
            if "merge_" in process:
                key, value = list(process_bundle[process]["output"].items())[0]
                process_bundle_out[key] = value

        # TAKE ALL OTHER OUTPUT IDS BUT ONLY IF IT WAS NOT A MERGER OUTPUT ALREADY
        for process in process_bundle.keys():
            for key, value in process_bundle[process]["output"].items():
                if key not in process_bundle_out.keys():
                    process_bundle_out[key] = value

        # SAVE TO DISK
        for ids in process_bundle_out.keys():
            if (
                len(process_bundle_out[ids].time) > 0
            ):  # Empty if process deactivated by an is_xx_on function
                if (
                    process_bundle_out[ids].time[0] > 0
                    or "merge" in process_bundle_out[ids].code.name
                ):
                    outputDb.put_slice(process_bundle_out[ids])

        return process_bundle_out

    def finalize(self):
        # FINALIZE ALL ACTORS
        for actor_name, actor in self.workflowData.dictionary_of_actors.items():
            actor.finalize()

        print("---------------------------------------------", file=sys.stdout)
        print("End of H&CD workflow.", file=sys.stdout)
        print("---------------------", file=sys.stdout)

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
