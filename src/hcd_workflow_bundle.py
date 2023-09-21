import copy
import logging
import os
import sys

from multiprocessing import Pool
from time import time


import imas
import numpy as np
from lxml import etree
from src.global_list_reader import GlobalListReader
from src.workflow_base import WorkflowBase
from src.workflow_config_reader import WorkflowConfigReader
from waveform_cooker import add_dynamic
from wftools.wf_tools import (
    add_ids_entry_to_dict,
    bundle_copy,
    check_if_code_fulfills_configuration,
    clever_algo,
    create_dict_from_idslist,
    create_maindict,
    create_workflow_param_from_file,
    find_nearest,
    import_actor,
    loadlist,
    read_actor_ids,
)

from tools.hcd_tools import is_ec_on, is_ic_on, is_lh_on, is_nbi_on

log = logging.getLogger()
log.setLevel(logging.ERROR)

from tools.stdout_redirector import redirect_stdout, stdout_back

root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class HCDWorkflow(WorkflowBase):
    def __init__(self, workflowConfigPath: str):
        # READ WORKFLOW PARAMETERS FROM INPUT XML FILE
        # YAML FILE CONTAINING ALL USEFUL LISTS
        self.global_lists = (
            os.path.dirname(os.path.abspath(__file__))
            + "/../global_configuration/"
            + "global_lists.yaml"
        )
        self.globalListReader = GlobalListReader(self.global_lists)

    def readWorkflowConfig(self, workflowConfig: str):
        _, _, _, _, self.catdict = create_maindict(workflowConfig, 0)

        self.workflowConfig = WorkflowConfigReader(workflowConfig)
        if self.workflowConfig.AreProcessesEmpty() is True:
            print(
                "ERROR: no actor selected --> The H&CD workflow will not be executed",
                file=sys.stderr,
            )
            return
        self.dictionary_of_actors = self.workflowConfig.getAllActors()
        self.code_selection = self.workflowConfig.getAllProcesses()
        self.workflowParameters = self.workflowConfig.getWorkflowParameters()
        self.process_bundle = self.workflowConfig.getProcessBundle()

        self.dt_required = self.workflowParameters["dt_required"]
        self.one_time_slice = self.workflowParameters["one_time_slice"]
        self.tbegin = self.workflowParameters["tbegin"]
        self.tend = self.workflowParameters["tend"]

    def createMachineDescriptionIDSes(self, inputMdsDict):
        mdCounter = 0
        waveform_presets = self.globalListReader.getWaveformPresetsList()
        allMachineDescriptionIDSes = []
        for process in self.process_bundle.keys():
            if "nuclear" not in process:  # No waveform for nuclear reactions
                for ids in self.process_bundle[process]["input"].keys():
                    if ids in inputMdsDict.keys():
                        self.process_bundle[process]["input"][ids] = inputMdsDict[ids]
                        # Overwrite with configured waveform if it exists
                        waveform_file = (
                            f"{self.workflowConfig.workflowDirectory}/"
                            + waveform_presets[process.split("_")[0]]["custom"][
                                mdCounter
                            ]
                        )
                        if os.path.exists(waveform_file):
                            self.process_bundle[process]["input"][ids] = add_dynamic(
                                waveform_file
                            )
                            mdCounter += 1
                        self.md.put(self.process_bundle[process]["input"][ids])
                        if ids not in allMachineDescriptionIDSes:
                            allMachineDescriptionIDSes.append(ids)
        return allMachineDescriptionIDSes

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
                workflow.time_loop.component[0].name = self.dictionary_of_actors[
                    process
                ].upper()
                self.process_bundle[process]["input"]["workflow"] = copy.deepcopy(
                    workflow
                )

    # TODO Refactor this
    def validatePrerquisitesOfCodes(self, prerequisites, code_selection):
        global_error = 0
        for entry, _ in code_selection.items():
            if code_selection != None:
                err = 0
                code = code_selection[entry]
                if prerequisites[entry] == "None":
                    prerequisites[entry] = None
                if prerequisites[entry] != None and code in prerequisites[entry]:
                    fulfills_all_prerequisites = [1] * (len(prerequisites[entry][code]))
                    for dep in [prerequisites[entry][code]]:
                        for i in dep.keys():
                            if "any" in str(dep[i]) and code_selection[i] != None:
                                pass
                            elif str(dep[i]).find(str(code_selection[i])) != -1:
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

    def initialize(self, inputdb, outputdb, machineDb, inputIds, inputMdsDict):
        prerequisites = self.globalListReader.getPrerequisites()
        err = self.validatePrerquisitesOfCodes(prerequisites, self.code_selection)
        if err == 0:
            print("Selection fulfills all actor selection rules", file=sys.stdout)
        else:
            print("Please change the actor selection and try again.", file=sys.stderr)
            return
        self.md = machineDb
        self.machineDescriptionIDSes = self.createMachineDescriptionIDSes(inputMdsDict)
        self.createWorkflowIDS(self.dt_required)

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
        mytime_array = args[0]
        idsslices = args[1]
        mdidsslices = args[2]
        if self.one_time_slice == 0:
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
            if self.tbegin < 0:
                self.tbegin = time_array[0]
                print(
                    "Initial time tbegin set to core_profiles first time slice. tbegin = ",
                    self.tbegin,
                    file=sys.stdout,
                )

            if self.tbegin > 0 and self.tbegin < time_array[0]:
                print(
                    "ERROR: tbegin out of range: "
                    + str(self.tbegin)
                    + " s is less than first time in core_profiles =",
                    "{:.2f}".format(time_array[0]),
                    "s",
                    file=sys.stderr,
                )
                return

            if self.tend < 0:
                self.tend = time_array[-1]
                print(
                    "Final time tend set to core_profiles final time slice, tend = ",
                    self.tend,
                    file=sys.stdout,
                )

            if self.tend > 0 and self.tend > time_array[-1]:
                print(
                    "ERROR: tend out of range: "
                    + str(self.tend)
                    + " s is greater than last time in core_profiles =",
                    "{:.2f}".format(time_array[-1]),
                    "s",
                    file=sys.stderr,
                )
                return
        else:
            self.tend = self.tbegin + self.dt_required

        ##################################################################

        # -----------------
        # BEGIN TIME LOOP
        # -----------------

        print("---------------------------------------------", file=sys.stdout)
        print("---- Enter time loop of the H&CD wrapper ----", file=sys.stdout)

        timenow = self.tbegin

        if self.one_time_slice == 0:
            nsteps = int((self.tend - self.tbegin) / self.dt_required)
        else:
            nsteps = 1
        if (
            self.dt_required * nsteps
            < int((self.tend - self.tbegin) * 10**5) / 10**5
        ):
            nsteps = nsteps + 1

        step = 0
        previous_time = {}

        while timenow < self.tend:
            step += 1

            print("---------------------------------------------", file=sys.stdout)
            print("Step = " + str(step) + "/" + str(nsteps), file=sys.stdout)
            print("Time = %5.2f" % timenow, "s", file=sys.stdout)
            print("dt   = %5.2f" % self.dt_required, "s", file=sys.stdout)

            # READ ALL INPUT IDSS FROM THE SCENARIO FOR THE CURRENT TIME SLICE
            self.initializeIDSSlices(
                timenow,
                self.ids_scenario_list,
                self.inputDb,
                self.common_bundle,
                self.process_bundle,
            )

            self.process_bundle, err = self.hcd_workflow(
                self.process_bundle, self.dictionary_of_actors
            )
            if err < 0:
                print("  Error in H&CD workflow.", file=sys.stderr)
                return

            process_bundle_out = self.storeIDSOutput(
                self.common_bundle, self.process_bundle, self.outputDb
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
            timenow = timenow * 1.0 + self.dt_required * 1.0
            for process in self.process_bundle.keys():
                if "merge_" not in process:
                    for ids in self.process_bundle[process]["output"].keys():
                        if (
                            type(self.process_bundle[process]["input"]) is dict
                            and ids in self.process_bundle[process]["input"].keys()
                        ):
                            print(
                                "Copy "
                                + ids
                                + " from output to input for "
                                + process
                                + " for next time slice"
                            )
                            self.process_bundle[process]["input"][
                                ids
                            ] = self.process_bundle[process]["output"][ids]

    def initializeIDSSlices(
        self,
        timenow,
        ids_scenario_list,
        inputDb,
        common_bundle,
        process_bundle,
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
                for process in process_bundle.keys():
                    if (
                        "merge_" not in process
                        and ids in process_bundle[process]["input"].keys()
                    ):
                        process_bundle[process]["input"][ids] = common_bundle[ids]
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
                for process in self.process_bundle.keys():
                    if ids in self.process_bundle[process]["input"].keys():
                        self.process_bundle[process]["input"][ids] = self.md.get_slice(
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
        time_base = self.workflowConfig.getTimeBase()

        for process in process_bundle.keys():
            if time_base is not None:
                if process in time_base:
                    [tc, it] = find_nearest(
                        np.array(
                            time_base[process][0]["wf_interval"][0]["time_array"][0]
                        ),
                        timenow,
                    )
                    process_bundle[process]["status"] = time_base[process][0][
                        "wf_interval"
                    ][0]["status"][0][it]
                else:
                    process_bundle[process]["status"] = 1
            else:
                process_bundle[process]["status"] = 1

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

    def run_internal(self, process, actor, bundle, parameters):
        # print("--------------------run_internal-----------------------")
        # print("--------------------process-----------------------")
        # print(process)
        # print("--------------------actor-----------------------")
        # print(actor)
        # print("--------------------bundle-----------------------")
        # print(bundle)
        # print("--------------------parameters-----------------------")
        # print(parameters)
        # For merge, bundle is a list of 2 bundles and the call is simpler
        if type(bundle) is list:
            return globals()[process](bundle[0], bundle[1])

        # Get list of all codes in that category
        codeslist = self.catdict[process]  # next(gen_dict_extract(process,maindict))
        codeinfo = codeslist[parameters[process]]
        code = codeinfo["name"]

        # Re-direct the logfile for this specific actor

        if code + "_log" in parameters.keys():
            stdout_redirect = parameters[code + "_log"]
            oldstrout, newstdout = redirect_stdout(stdout_redirect)

        inputargs = []
        for i in codeinfo["input"]:
            inputargs.append(bundle[i])

        results = actor(*inputargs)

        # Re-direct the logfile for this specific actor
        if code + "_log" in parameters.keys():
            stdout_back(oldstrout, newstdout)

        # Call of the chosen code
        return results

    def hcd_workflow(self, process_bundle, dictionary_of_actors):
        # # READ ALL INPUT IDSS FROM THE SCENARIO FOR THE CURRENT TIME SLICE
        # for ids in idsslices:
        #     for process in self.process_bundle.keys():
        #         if (
        #             "merge_" not in process
        #             and ids in self.process_bundle[process]["input"].keys()
        #         ):
        #             self.process_bundle[process]["input"][ids] = idsslices[ids]

        # for ids in mdidsslices:
        #     for process in self.process_bundle.keys():
        #         if ids in self.process_bundle[process]["input"].keys():
        #             self.process_bundle[process]["input"][ids] = mdidsslices[ids]

        # time_base = self.workflowConfig.getTimeBase()
        # for process in self.process_bundle.keys():
        #     if time_base is not None:
        #         if process in time_base:
        #             [tc, it] = find_nearest(
        #                 np.array(
        #                     time_base[process][0]["wf_interval"][0]["time_array"][0]
        #                 ),
        #                 timenow,
        #             )
        #             self.process_bundle[process]["status"] = time_base[process][0][
        #                 "wf_interval"
        #             ][0]["status"][0][it]
        #         else:
        #             self.process_bundle[process]["status"] = 1
        #     else:
        #         self.process_bundle[process]["status"] = 1

        # print("process_bundle-------------------------")
        # print(process_bundle)
        # print("workflow_xml-----------------------")
        # print(workflow_xml)
        # print("dictionary_of_actors---------------------")
        # print(dictionary_of_actors)
        # YAML FILE CONTAINING ALL USEFUL LISTS
        print("Execute H&CD workflow for current time slice", file=sys.stdout)

        file = (
            os.path.dirname(os.path.abspath(__file__))
            + "/../global_configuration/"
            + "global_lists.yaml"
        )

        # EXTRACT ACTOR SELECTION PARAMETERS FROM INPUT XML FILE
        # actor_parameters = create_workflow_param_from_file(workflow_xml)[
        #     "actor_selection"
        # ][0]

        # CREATE PARAMETERS DICTIONARY WITH DIRECTLY EACH PROCESS AS KEY
        param_process = self.workflowConfig.getParamProcess()
        # for main_key in actor_parameters:
        #     for category in actor_parameters[main_key][0]:
        #         for process in actor_parameters[main_key][0][category][0]:
        #             param_process[process] = actor_parameters[main_key][0][category][0][
        #                 process
        #             ][0]
        # print(param_process)
        # exit(0)
        # print("##########################self.catdict##########################")
        # # process and actor is extracted
        # print(self.catdict)
        # print("##########################actor_parameters##########################")
        # # process and actor is extracted
        # print(actor_parameters)
        # print("#############################param_process#######################")
        # print(param_process)
        # print("####################################################")
        # IF AN H&CD SOURCE IS CONFIGURED BUT IT HAS NO POWER FOR THIS TIME SLICE,
        # DO NOT RUN THE CODE(S) FOR THIS SOURCE
        for process in process_bundle.keys():
            if (
                "nbi" in process_bundle[process]["input"]
                and process_bundle[process]["input"][
                    "nbi"
                ].ids_properties.homogeneous_time
                < 0
            ):
                print("  NBI required but no waveform!!!", file=sys.stderr)
                print(
                    "  --> Edit H&CD waveforms before executing the workflow.",
                    file=sys.stderr,
                )
                print("  --> Abort.", file=sys.stderr)
                return process_bundle, -1

            if "nbi" in process_bundle[process]["input"] and not is_nbi_on(
                process_bundle[process]["input"]["nbi"],
                process_bundle[process]["input"]["core_profiles"].time,
            ):
                print("  No NBI power for this time slice", file=sys.stdout)
                param_process["nbi_source"] = 0
                param_process["nbi_fp"] = 0

            if (
                "ic_antennas" in process_bundle[process]["input"]
                and process_bundle[process]["input"][
                    "ic_antennas"
                ].ids_properties.homogeneous_time
                < 0
            ):
                print("  ICRH required but no waveform!!!", file=sys.stderr)
                print(
                    "  --> Edit H&CD waveforms before executing the workflow.",
                    file=sys.stderr,
                )
                print("  --> Abort.", file=sys.stderr)
                return process_bundle, -1

            if "ic_antennas" in process_bundle[process]["input"] and not is_ic_on(
                process_bundle[process]["input"]["ic_antennas"],
                process_bundle[process]["input"]["core_profiles"].time,
            ):
                print("  No IC power for this time slice", file=sys.stdout)
                param_process["ic_coup"] = 0
                param_process["ic_wave_solver"] = 0
                param_process["ic_wave_fp"] = 0

            if (
                "ec_launchers" in process_bundle[process]["input"]
                and process_bundle[process]["input"][
                    "ec_launchers"
                ].ids_properties.homogeneous_time
                < 0
            ):
                print("  ECRH required but no waveform!!!", file=sys.stderr)
                print(
                    "  --> Edit H&CD waveforms before executing the workflow.",
                    file=sys.stderr,
                )
                print("  --> Abort.", file=sys.stderr)
                return process_bundle, -1

            if "ec_launchers" in process_bundle[process]["input"] and not is_ec_on(
                process_bundle[process]["input"]["ec_launchers"],
                process_bundle[process]["input"]["core_profiles"].time,
            ):
                print("  No EC power for this time slice", file=sys.stdout)
                param_process["ec_wave_solver"] = 0
                param_process["ec_wave_fp"] = 0

            if "lh_antennas" in process_bundle[process]["input"] and not is_lh_on(
                process_bundle[process]["input"]["lh_antennas"],
                process_bundle[process]["input"]["core_profiles"].time,
            ):
                print("  No LH power for this time slice", file=sys.stdout)
                param_process["lh_wave_solver"] = 0

        # DEFINE THE SEQUENCE OF CODES TO BE EXECUTED
        if (
            "ic_wave_fp" in self.catdict.keys()
            and self.catdict["ic_wave_fp"][param_process["ic_wave_fp"]]["name"]
            != "fopla"
        ):
            print("--- Default algorithm ---", file=sys.stdout)
            input_algorithm = loadlist(file, "algorithm")["default"]
        else:
            print("--- NBI+IC synergy algorithm ---", file=sys.stdout)
            input_algorithm = loadlist(file, "algorithm")["nbi_ic_synergy"]

        final_algorithm, waiting_for, parallel_runs = clever_algo(
            input_algorithm, param_process, self.catdict, file
        )

        # print("final_algo", final_algorithm)
        # print(" ")
        # print("waiting_for", waiting_for)
        # print(" ")
        # print("parallel_runs", parallel_runs)

        # EXECUTE THE CODES ACCORDING TO THE REQUESTED SEQUENCE
        bundle_out = {}

        # EXECUTION OF THE WORKFLOW
        for process in final_algorithm:
            actor = dictionary_of_actors[
                self.catdict[process][param_process[process]]["name"]
            ]
            if not "merge_" in process:
                if process_bundle[process]["status"] == 1:
                    print(
                        " PROCESS --> ",
                        process,
                        "=",
                        self.catdict[process][param_process[process]]["name"].upper(),
                        file=sys.stdout,
                    )
                else:
                    print(
                        " PROCESS",
                        process,
                        "=",
                        self.catdict[process][param_process[process]]["name"].upper(),
                        " not called for this time slice",
                        file=sys.stdout,
                    )
                output_ids_list = self.catdict[process][param_process[process]][
                    "output"
                ]
                # REMOVE WARNINGS AND HCD2CORE_SOURCES CRASHS (DOES NOT LIKE RECEIVING EMPTY IDSS)
                for ids in process_bundle[process]["input"].keys():
                    if (
                        process_bundle[process]["input"][
                            ids
                        ].ids_properties.homogeneous_time
                        < 1
                    ):
                        process_bundle[process]["input"][
                            ids
                        ].ids_properties.homogeneous_time = 1
                        process_bundle[process]["input"][ids].time = process_bundle[
                            process
                        ]["input"]["core_profiles"].time
                if process_bundle[process]["status"] == 1:
                    output_ids_data = self.run_internal(
                        process, actor, process_bundle[process]["input"], param_process
                    )
                else:
                    output_ids_data = []
                    for ids in process_bundle[process]["output"]:
                        if len(process_bundle[process]["output"]) == 1:
                            if ids in process_bundle[process]["input"]:
                                output_ids_data = process_bundle[process]["input"][ids]
                            else:
                                output_ids_data = eval("imas." + ids + "()")
                        else:
                            if ids in process_bundle[process]["input"]:
                                output_ids_data.append(
                                    process_bundle[process]["input"][ids]
                                )
                            else:
                                import imas

                                output_ids_data.append(eval("imas." + ids + "()"))
            else:
                kmerge = 0
                ids_to_be_merged = process_bundle[process]["input"][0].__name__
                for (
                    each_proc
                ) in (
                    process_bundle.keys()
                ):  # merge only if at least one of involved codes is called
                    if (
                        ids_to_be_merged in process_bundle[each_proc]["input"]
                        and process_bundle[each_proc]["status"] == 1
                    ):
                        kmerge = 1
                if kmerge == 1:
                    print(" PROCESS -->", process, file=sys.stdout)
                    output_ids_data = self.run_internal(
                        process, actor, process_bundle[process]["input"], param_process
                    )
                    del bundle_out[output_ids_list[0]]

            for iids in range(len(output_ids_list)):
                if not hasattr(output_ids_data, "__len__"):
                    # if hasattr(output_ids_data,'__len__'):
                    #    for iids in range(len(output_ids_data)):
                    process_bundle[process]["output"][
                        output_ids_data.__name__
                    ] = output_ids_data
                else:
                    process_bundle[process]["output"][
                        output_ids_data[iids].__name__
                    ] = output_ids_data[iids]

                if (
                    output_ids_list[iids] not in bundle_out.keys()
                    or "merge_" in process
                ):
                    if not hasattr(output_ids_data, "__len__"):
                        bundle_out[output_ids_list[iids]] = process_bundle[process][
                            "output"
                        ][output_ids_data.__name__]
                    else:
                        bundle_out[output_ids_list[iids]] = process_bundle[process][
                            "output"
                        ][output_ids_data[iids].__name__]
                else:
                    process_bundle["merge_" + output_ids_list[iids]] = {}
                    process_bundle["merge_" + output_ids_list[iids]]["input"] = [
                        bundle_out[output_ids_list[iids]],
                        output_ids_data,
                    ]
                    process_bundle["merge_" + output_ids_list[iids]]["output"] = {}
                    process_bundle["merge_" + output_ids_list[iids]]["output"][
                        output_ids_list[iids]
                    ] = {}

            # COPY THE OUTPUT IDS OF THE CURRENT PROCESS TO THE INPUT ONES
            # OF THE DOWNSTREAM DEPENDENT PROCESSES
            parallel_dependency = loadlist(file, "parallel_dependency")
            for stepc in final_algorithm[final_algorithm.index(process) + 1 :]:
                if process in parallel_dependency[stepc]:
                    if stepc in process_bundle:  # (merger keys may not exist yet)
                        for idskey, idsvalue in process_bundle[process][
                            "output"
                        ].items():
                            if type(process_bundle[stepc]["input"]) is not list:
                                process_bundle[stepc]["input"][idskey] = copy.deepcopy(
                                    idsvalue
                                )

        print("End of time slice", file=sys.stdout)

        return process_bundle, 0

    def finalize(self):
        # FINALIZE ALL ACTORS
        for actor_name, actor in self.dictionary_of_actors.items():
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
