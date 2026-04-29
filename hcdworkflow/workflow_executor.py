import collections
import copy
import sys

from tools.hcd_tools import is_ec_on, is_ic_on, is_lh_on, is_nbi_on
from tools.stdout_redirector import redirect_stdout, stdout_back


def _ensure_ids_name(ids_obj, name):
    if not hasattr(ids_obj, "__name__"):
        object.__setattr__(ids_obj, "__name__", name)


class WorkflowExecutor:
    def __init__(
        self,
        process_bundle,
        dictionary_of_actors,
        param_process,
        catdict,
        parallel_dependency,
        algorithm,
        parallel_dependency_list,
        merge_actor_list,
    ) -> None:
        self.process_bundle = process_bundle
        self.dictionary_of_actors = dictionary_of_actors
        self.param_process = param_process
        self.catdict = catdict
        self.parallel_dependency = parallel_dependency
        self.algorithm = algorithm
        self.parallel_dependency_list = parallel_dependency_list
        self.merge_actor_list = merge_actor_list

    def execute(self):
        print("Execute H&CD workflow for current time slice", file=sys.stdout)
        err = self.validateAndUpdateProcessBundle()
        if err is not None and err < 0:
            print("  Skipping time slice due to validation error", file=sys.stderr)
            return err
        final_algorithm, waiting_for, parallel_runs = self.decideAlgorithm()
        # print("final_algo", final_algorithm)
        # print(" ")
        # print("waiting_for", waiting_for)
        # print(" ")
        # print("parallel_runs", parallel_runs)

        # EXECUTE THE CODES ACCORDING TO THE REQUESTED SEQUENCE
        self.executeAlgorithm(final_algorithm)
        print("End of time slice", file=sys.stdout)

        return 0

    def decideAlgorithm(self):
        # DEFINE THE SEQUENCE OF CODES TO BE EXECUTED
        if (
            "ic_wave_fp" in self.catdict.keys()
            and self.catdict["ic_wave_fp"][self.param_process["ic_wave_fp"]]["name"] != "fopla"
        ):
            print("--- Default algorithm ---", file=sys.stdout)
            input_algorithm = self.algorithm["default"]
        else:
            print("--- NBI+IC synergy algorithm ---", file=sys.stdout)
            input_algorithm = self.algorithm["nbi_ic_synergy"]

        final_algorithm, waiting_for, parallel_runs = self.adjustAlgorithm(input_algorithm)
        return final_algorithm, waiting_for, parallel_runs

    def validateAndUpdateProcessBundle(self):
        # IF AN H&CD SOURCE IS CONFIGURED BUT IT HAS NO POWER FOR THIS TIME SLICE,
        # DO NOT RUN THE CODE(S) FOR THIS SOURCE
        for process in self.process_bundle.keys():
            time_array = None
            if (
                isinstance(self.process_bundle[process]["input"], dict)
                and "core_profiles" in self.process_bundle[process]["input"].keys()
            ):
                time_array = self.process_bundle[process]["input"]["core_profiles"].time
            elif (
                isinstance(self.process_bundle[process]["input"], dict)
                and "equilibrium" in self.process_bundle[process]["input"].keys()
            ):
                time_array = self.process_bundle[process]["input"]["equilibrium"].time
            if (
                "nbi" in self.process_bundle[process]["input"]
                and "nuclear" not in process
                and self.process_bundle[process]["input"]["nbi"].ids_properties.homogeneous_time < 0
            ):
                print("  NBI required but no waveform!!!", file=sys.stderr)
                print(
                    "  --> Edit H&CD waveforms before executing the workflow.",
                    file=sys.stderr,
                )
                print("  --> Abort.", file=sys.stderr)
                return -1

            if "nbi" in self.process_bundle[process]["input"] and not is_nbi_on(
                self.process_bundle[process]["input"]["nbi"],
                time_array,
            ):
                print("  No NBI power for this time slice", file=sys.stdout)
                self.param_process["nbi_source"] = 0
                self.param_process["nbi_fp"] = 0

            if (
                "ic_antennas" in self.process_bundle[process]["input"]
                and self.process_bundle[process]["input"]["ic_antennas"].ids_properties.homogeneous_time < 0
            ):
                print("  ICRH required but no waveform!!!", file=sys.stderr)
                print(
                    "  --> Edit H&CD waveforms before executing the workflow.",
                    file=sys.stderr,
                )
                print("  --> Abort.", file=sys.stderr)
                return -1

            if "ic_antennas" in self.process_bundle[process]["input"] and not is_ic_on(
                self.process_bundle[process]["input"]["ic_antennas"],
                time_array,
            ):
                print("  No IC power for this time slice", file=sys.stdout)
                self.param_process["ic_coup"] = 0
                self.param_process["ic_wave_solver"] = 0
                self.param_process["ic_wave_fp"] = 0

            if (
                "ec_launchers" in self.process_bundle[process]["input"]
                and self.process_bundle[process]["input"]["ec_launchers"].ids_properties.homogeneous_time < 0
            ):
                print("  ECRH required but no waveform!!!", file=sys.stderr)
                print(
                    "  --> Edit H&CD waveforms before executing the workflow.",
                    file=sys.stderr,
                )
                print("  --> Abort.", file=sys.stderr)
                return -1

            if "ec_launchers" in self.process_bundle[process]["input"] and not is_ec_on(
                self.process_bundle[process]["input"]["ec_launchers"],
                time_array,
            ):
                print("  No EC power for this time slice", file=sys.stdout)
                self.param_process["ec_wave_solver"] = 0
                self.param_process["ec_wave_fp"] = 0

            if "lh_antennas" in self.process_bundle[process]["input"] and not is_lh_on(
                self.process_bundle[process]["input"]["lh_antennas"],
                time_array,
            ):
                print("  No LH power for this time slice", file=sys.stdout)
                self.param_process["lh_wave_solver"] = 0

    # TODO Just use set
    def common_elements(self, list1, list2):
        result = []
        for element in list1:
            if element in list2:
                result.append(element)
        return result

    def adjustAlgorithm(self, algo_input):
        # -----------------------------------------------------------------
        # Automatically adjust the algorithm according to the dependencies
        # between actors and IDSs to be merged
        # -----------------------------------------------------------------

        # ADD MERGERS TO THE FLOW
        output_list = []
        algo_final = []
        code_list = []
        for istep in range(len(algo_input)):
            stepmodel = algo_input[istep]
            choice = self.param_process[stepmodel]
            for ikey, ivalue in self.catdict.items():
                if stepmodel == ikey and choice != 0:
                    algo_final = algo_final + [stepmodel]
                    output_list = output_list + ivalue[choice]["output"]
                    code_list = code_list + [ivalue[choice]["name"]]
                    ids_to_merge = [item for item, count in collections.Counter(output_list).items() if count > 1]
                    for merge in self.merge_actor_list:
                        if merge.split("_")[1] in ids_to_merge:
                            algo_final = algo_final + [merge]
                            code_list = code_list + [merge]
                    seen = set()
                    output_list = [x for x in output_list if x not in seen and not seen.add(x)]

        print("Algorithm =", algo_final)

        # DEFINE WHEN TO PUT WAITING POINTS WHEN WORKFLOW ACTORS RUN IN PARALLEL
        previous_occ = dict.fromkeys(algo_final, 0)
        waiting_for = {}
        for istep in range(len(algo_final)):
            steprun = algo_final[istep]
            index = [i for i, x in enumerate(algo_final) if x == steprun][previous_occ[steprun]]
            previous_occ[steprun] = previous_occ[steprun] + 1
            waiting_for[str(istep)] = {}
            waiting_for[str(istep)]["steprun"] = steprun
            if index > 0:
                all_possible_dependencies = list(
                    set(self.common_elements(algo_final[0:index], self.parallel_dependency_list[steprun]))
                )
                reduced_dependencies = copy.deepcopy(all_possible_dependencies)
                for dep in all_possible_dependencies:
                    for keystep in waiting_for.keys():
                        if "dependencies" in waiting_for[keystep] and waiting_for[keystep]["dependencies"] is not None:
                            # Remove indirect dependencies
                            if (
                                dep in waiting_for[keystep]["dependencies"]
                                and "merge_" not in dep
                                and waiting_for[keystep]["steprun"] in all_possible_dependencies
                                and dep in reduced_dependencies
                            ):
                                reduced_dependencies.remove(dep)
                if len(reduced_dependencies) > 0:
                    waiting_for[str(istep)]["dependencies"] = reduced_dependencies
                else:
                    waiting_for[str(istep)]["dependencies"] = None
            else:
                waiting_for[str(istep)]["dependencies"] = None

        # COMPUTE THE LIST OF STEPS OF CODES THAT CAN RUN IN PARALLEL
        parallel_runs = {}
        parallel_step = 0
        for key in waiting_for.keys():
            if parallel_step not in parallel_runs.keys():
                parallel_runs[parallel_step] = [waiting_for[key]["steprun"]]
            else:
                there_is_a_dependency = False
                if waiting_for[key]["dependencies"] is not None:
                    for dep in waiting_for[key]["dependencies"]:
                        if dep in parallel_runs[parallel_step]:
                            there_is_a_dependency = True
                    if there_is_a_dependency:
                        parallel_step = parallel_step + 1
                        parallel_runs[parallel_step] = [waiting_for[key]["steprun"]]
                    else:
                        parallel_runs[parallel_step] = parallel_runs[parallel_step] + [waiting_for[key]["steprun"]]
                else:
                    parallel_runs[0] = parallel_runs[0] + [waiting_for[key]["steprun"]]

        return algo_final, waiting_for, parallel_runs

    def executeAlgorithm(self, final_algorithm):
        bundle_out = {}

        # EXECUTION OF THE WORKFLOW
        for process in final_algorithm:
            # feature/repair_231017
            if "merge_" not in process:
                actor = self.dictionary_of_actors[self.catdict[process][self.param_process[process]]["name"]]
                if self.process_bundle[process]["status"] == 1:
                    print(
                        " PROCESS --> ",
                        process,
                        "=",
                        self.catdict[process][self.param_process[process]]["name"].upper(),
                        file=sys.stdout,
                    )
                else:
                    print(
                        " PROCESS",
                        process,
                        "=",
                        self.catdict[process][self.param_process[process]]["name"].upper(),
                        " not called for this time slice",
                        file=sys.stdout,
                    )
                output_ids_list = self.catdict[process][self.param_process[process]]["output"]
                # REMOVE WARNINGS AND HCD2CORE_SOURCES CRASHS (DOES NOT LIKE RECEIVING EMPTY IDSS)
                for ids in self.process_bundle[process]["input"].keys():
                    if self.process_bundle[process]["input"][ids].ids_properties.homogeneous_time < 1:
                        self.process_bundle[process]["input"][ids].ids_properties.homogeneous_time = 1
                        self.process_bundle[process]["input"][ids].time = self.process_bundle[process]["input"][
                            "core_profiles"
                        ].time
                if self.process_bundle[process]["status"] == 1:
                    output_ids_data = self.executeProcess(
                        process,
                        actor,
                        self.process_bundle[process]["input"],
                        self.param_process,
                    )
                    if process == "equilibrium_solver":
                        for proc in self.process_bundle:
                            self.process_bundle[proc]["input"]["equilibrium"] = output_ids_data
                else:
                    output_ids_data = []
                    for ids in self.process_bundle[process]["output"]:
                        if len(self.process_bundle[process]["output"]) == 1:
                            if ids in self.process_bundle[process]["input"]:
                                output_ids_data = self.process_bundle[process]["input"][ids]
                            else:
                                output_ids_data = eval("imas." + ids + "()")
                            _ensure_ids_name(output_ids_data, ids)
                        else:
                            if ids in self.process_bundle[process]["input"]:
                                tmp_ids = self.process_bundle[process]["input"][ids]
                            else:
                                tmp_ids = eval("imas." + ids + "()")
                            _ensure_ids_name(tmp_ids, ids)
                            output_ids_data.append(tmp_ids)
            else:
                # feature/repair_231017
                actor = self.dictionary_of_actors[process]
                kmerge = 0
                _ensure_ids_name(self.process_bundle[process]["input"][0], process.replace("merge_", "", 1))
                ids_to_be_merged = self.process_bundle[process]["input"][0].__name__
                for each_proc in self.process_bundle.keys():  # merge only if at least one of involved codes is called
                    if (
                        ids_to_be_merged in self.process_bundle[each_proc]["input"]
                        and self.process_bundle[each_proc]["status"] == 1
                    ):
                        kmerge = 1
                if kmerge == 1:
                    print(" PROCESS -->", process, file=sys.stdout)
                    output_ids_data = self.executeProcess(
                        process,
                        actor,
                        self.process_bundle[process]["input"],
                        self.param_process,
                    )
                    del bundle_out[output_ids_list[0]]

            for iids in range(len(output_ids_list)):
                if not hasattr(output_ids_data, "__len__"):
                    # if hasattr(output_ids_data,'__len__'):
                    #    for iids in range(len(output_ids_data)):
                    _ensure_ids_name(output_ids_data, output_ids_list[iids])
                    self.process_bundle[process]["output"][output_ids_data.__name__] = output_ids_data
                else:
                    _ensure_ids_name(output_ids_data[iids], output_ids_list[iids])
                    self.process_bundle[process]["output"][output_ids_data[iids].__name__] = output_ids_data[iids]

                if output_ids_list[iids] not in bundle_out.keys() or "merge_" in process:
                    if not hasattr(output_ids_data, "__len__"):
                        bundle_out[output_ids_list[iids]] = self.process_bundle[process]["output"][
                            output_ids_data.__name__
                        ]
                    else:
                        bundle_out[output_ids_list[iids]] = self.process_bundle[process]["output"][
                            output_ids_data[iids].__name__
                        ]
                else:
                    # feature/repair_231017
                    if hasattr(output_ids_data, "__len__"):
                        tmp_output_ids_data = output_ids_data[iids]
                    else:
                        tmp_output_ids_data = output_ids_data
                    _ensure_ids_name(bundle_out[output_ids_list[iids]], output_ids_list[iids])
                    _ensure_ids_name(tmp_output_ids_data, output_ids_list[iids])
                    if bundle_out[output_ids_list[iids]].__name__ == tmp_output_ids_data.__name__:
                        self.process_bundle["merge_" + output_ids_list[iids]] = {}
                        self.process_bundle["merge_" + output_ids_list[iids]]["input"] = [
                            bundle_out[output_ids_list[iids]],
                            tmp_output_ids_data,
                        ]
                        self.process_bundle["merge_" + output_ids_list[iids]]["output"] = {}
                        self.process_bundle["merge_" + output_ids_list[iids]]["output"][output_ids_list[iids]] = {}

            # COPY THE OUTPUT IDS OF THE CURRENT PROCESS TO THE INPUT ONES
            # OF THE DOWNSTREAM DEPENDENT PROCESSES

            for stepc in final_algorithm[final_algorithm.index(process) + 1 :]:
                if process in self.parallel_dependency[stepc]:
                    if stepc in self.process_bundle:  # (merger keys may not exist yet)
                        for idskey, idsvalue in self.process_bundle[process]["output"].items():
                            if type(self.process_bundle[stepc]["input"]) is not list:
                                self.process_bundle[stepc]["input"][idskey] = copy.deepcopy(idsvalue)

    def executeProcess(self, process, actor, bundle, parameters):
        # For merge, bundle is a list of 2 bundles and the call is simpler
        if type(bundle) is list:
            # feature/repair_231017
            return actor(bundle[0], bundle[1])

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

        # TODO assign callbacks for status
        # TODO initialize finalize methods
        results = actor(*inputargs)

        # Re-direct the logfile for this specific actor
        if code + "_log" in parameters.keys():
            stdout_back(oldstrout, newstdout)

        # Call of the chosen code
        output_ids_list = codeinfo["output"]
        if not hasattr(results, "__len__"):
            _ensure_ids_name(results, output_ids_list[0] if output_ids_list else "unknown")
        else:
            for i, ids_name in enumerate(output_ids_list):
                if i < len(results):
                    _ensure_ids_name(results[i], ids_name)

        return results
