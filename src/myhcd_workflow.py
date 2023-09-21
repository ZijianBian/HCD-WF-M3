import os
import sys
import copy
from tools.stdout_redirector import redirect_stdout, stdout_back
from wftools.wf_tools import clever_algo, loadlist
from tools.hcd_tools import is_ec_on, is_ic_on, is_lh_on, is_nbi_on
import imas


class MyHcdWorkflow:
    def __init__(
        self,
        process_bundle,
        dictionary_of_actors,
        param_process,
        catdict,
        parallel_dependency,
    ) -> None:
        self.process_bundle = process_bundle
        self.dictionary_of_actors = dictionary_of_actors
        self.param_process = param_process
        self.catdict = catdict
        self.parallel_dependency = parallel_dependency

    def hcd_workflow(self):
        param_process = self.param_process
        process_bundle = self.process_bundle
        dictionary_of_actors = self.dictionary_of_actors
        parallel_dependency = self.parallel_dependency
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
