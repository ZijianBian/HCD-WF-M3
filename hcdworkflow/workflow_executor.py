import collections
import copy
import sys

from tools.hcd_tools import is_ec_on, is_ic_on, is_lh_on, is_nbi_on
from tools.stdout_redirector import redirect_stdout, stdout_back


def _ensure_ids_name(ids_obj, name):
    """Ensure an IDS object has __name__ attribute (IMAS-Python 2.0 compatibility).

    IMAS-Python 2.0 / DD 4.0 no longer provides __name__ on IDS objects.
    The workflow executor relies on __name__ to identify IDS types.
    This helper safely sets it using object.__setattr__ to bypass
    IMAS's custom __setattr__ which rejects unknown attributes.
    """
    if not hasattr(ids_obj, '__name__'):
        object.__setattr__(ids_obj, '__name__', name)


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
        self.validateAndUpdateProcessBundle()
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

                # =============================================================
                # DEBUG: Exhaustive inspection of stix_redist inputs
                # Compare pre- vs post-reserialize to find data loss.
                #
                # Standalone stix_redist prints "Reading RF power profiles..."
                # after elongation line, but MUSCLE3 integrated run does NOT.
                # => stix_redist silently fails reading power profiles from waves.
                # => Re-serialize may be losing profiles_1d array data.
                #
                # Remove this entire block once the issue is resolved.
                # =============================================================
                if self.catdict[process][self.param_process[process]]["name"] == "stix_redist":
                    import imas as _dbg_imas
                    import numpy as np

                    def _dbg_inspect_waves(label, waves_ids):
                        """Exhaustive dump of waves IDS structure and data sizes."""
                        print(f"\n{'=' * 70}", flush=True)
                        print(f"DEBUG [stix_redist] [{label}]: WAVES IDS INSPECTION", flush=True)
                        print(f"{'=' * 70}", flush=True)

                        # Top-level attributes
                        print(f"  type(waves) = {type(waves_ids)}", flush=True)
                        print(f"  ids_properties.homogeneous_time = {waves_ids.ids_properties.homogeneous_time}", flush=True)
                        try:
                            _t = waves_ids.time
                            print(f"  time = {_t} (len={len(_t)})", flush=True)
                        except Exception as e:
                            print(f"  time: ERROR {e}", flush=True)

                        # vacuum_toroidal_field
                        try:
                            vtf = waves_ids.vacuum_toroidal_field
                            print(f"  vacuum_toroidal_field.r0 = {vtf.r0}", flush=True)
                            print(f"  vacuum_toroidal_field.b0 = {vtf.b0} (len={len(vtf.b0) if hasattr(vtf.b0, '__len__') else 'scalar'})", flush=True)
                        except Exception as e:
                            print(f"  vacuum_toroidal_field: ERROR {e}", flush=True)

                        ncw = len(waves_ids.coherent_wave)
                        print(f"  coherent_wave count = {ncw}", flush=True)

                        for i, cw in enumerate(waves_ids.coherent_wave):
                            print(f"\n  --- coherent_wave[{i}] ---", flush=True)

                            # identifier
                            try:
                                print(f"    identifier.type.index = {cw.identifier.type.index}", flush=True)
                                print(f"    identifier.type.name = '{cw.identifier.type.name}'", flush=True)
                                print(f"    identifier.type.description = '{cw.identifier.type.description}'", flush=True)
                            except Exception as e:
                                print(f"    identifier: ERROR {e}", flush=True)

                            # global_quantities
                            try:
                                ngq = len(cw.global_quantities)
                                print(f"    global_quantities count = {ngq}", flush=True)
                                for gi, gq in enumerate(cw.global_quantities):
                                    print(f"      [{gi}] frequency = {gq.frequency}", flush=True)
                                    print(f"      [{gi}] power = {gq.power}", flush=True)
                                    try:
                                        print(f"      [{gi}] power_launched.time = {gq.power_launched.time} (len={len(gq.power_launched.time) if hasattr(gq.power_launched.time, '__len__') else 'N/A'})", flush=True)
                                    except:
                                        pass
                            except Exception as e:
                                print(f"    global_quantities: ERROR {e}", flush=True)

                            # profiles_1d - THIS IS THE CRITICAL SECTION
                            try:
                                np1d = len(cw.profiles_1d)
                                print(f"    profiles_1d count = {np1d}", flush=True)
                                for pi, p1d in enumerate(cw.profiles_1d):
                                    print(f"      --- profiles_1d[{pi}] ---", flush=True)

                                    # grid
                                    try:
                                        rho = p1d.grid.rho_tor_norm
                                        print(f"        grid.rho_tor_norm: len={len(rho)}, min={np.min(rho):.6f}, max={np.max(rho):.6f}" if len(rho) > 0 else "        grid.rho_tor_norm: EMPTY", flush=True)
                                    except Exception as e:
                                        print(f"        grid.rho_tor_norm: ERROR {e}", flush=True)
                                    try:
                                        rho = p1d.grid.rho_tor
                                        print(f"        grid.rho_tor: len={len(rho)}, min={np.min(rho):.6f}, max={np.max(rho):.6f}" if len(rho) > 0 else "        grid.rho_tor: EMPTY", flush=True)
                                    except Exception as e:
                                        print(f"        grid.rho_tor: ERROR {e}", flush=True)

                                    # electrons
                                    try:
                                        e = p1d.electrons
                                        for attr in ['power_density', 'power_density_thermal', 'power_density_n_tor',
                                                      'power_inside', 'power_inside_thermal']:
                                            try:
                                                val = getattr(e, attr)
                                                if hasattr(val, '__len__'):
                                                    if len(val) > 0:
                                                        print(f"        electrons.{attr}: len={len(val)}, [0]={val[0]:.6e}, [-1]={val[-1]:.6e}", flush=True)
                                                    else:
                                                        print(f"        electrons.{attr}: EMPTY array", flush=True)
                                                elif hasattr(val, 'has_value'):
                                                    print(f"        electrons.{attr}: has_value={val.has_value}", flush=True)
                                                else:
                                                    print(f"        electrons.{attr}: {val}", flush=True)
                                            except Exception as e2:
                                                print(f"        electrons.{attr}: ERROR {e2}", flush=True)
                                    except Exception as e:
                                        print(f"        electrons: ERROR {e}", flush=True)

                                    # ions
                                    try:
                                        nion = len(p1d.ion)
                                        print(f"        ion count = {nion}", flush=True)
                                        for ji, ion in enumerate(p1d.ion):
                                            for attr in ['power_density_thermal', 'power_inside_thermal']:
                                                try:
                                                    val = getattr(ion, attr)
                                                    if hasattr(val, '__len__') and len(val) > 0:
                                                        print(f"          ion[{ji}].{attr}: len={len(val)}, [0]={val[0]:.6e}", flush=True)
                                                    elif hasattr(val, '__len__'):
                                                        print(f"          ion[{ji}].{attr}: EMPTY", flush=True)
                                                    else:
                                                        print(f"          ion[{ji}].{attr}: has_value={getattr(val, 'has_value', 'N/A')}", flush=True)
                                                except Exception as e2:
                                                    print(f"          ion[{ji}].{attr}: ERROR {e2}", flush=True)
                                            # ion element info
                                            try:
                                                for ei, elem in enumerate(ion.element):
                                                    print(f"          ion[{ji}].element[{ei}]: a={elem.a}, z_n={elem.z_n}", flush=True)
                                            except:
                                                pass
                                    except Exception as e:
                                        print(f"        ions: ERROR {e}", flush=True)

                                    # e_field_n_phi (IC-specific, critical for stix_redist)
                                    try:
                                        nef = len(p1d.e_field_n_phi)
                                        print(f"        e_field_n_phi count = {nef}", flush=True)
                                        for ei, ef in enumerate(p1d.e_field_n_phi):
                                            print(f"          [{ei}] n_tor = {ef.n_tor}", flush=True)
                                            for comp_name in ['plus', 'minus', 'parallel']:
                                                try:
                                                    comp = getattr(ef, comp_name)
                                                    amp = comp.amplitude
                                                    if hasattr(amp, '__len__') and len(amp) > 0:
                                                        print(f"          [{ei}].{comp_name}.amplitude: len={len(amp)}, max={np.max(np.abs(amp)):.6e}", flush=True)
                                                    elif hasattr(amp, '__len__'):
                                                        print(f"          [{ei}].{comp_name}.amplitude: EMPTY", flush=True)
                                                    else:
                                                        print(f"          [{ei}].{comp_name}.amplitude: has_value={getattr(amp, 'has_value', 'N/A')}", flush=True)
                                                except Exception as e2:
                                                    print(f"          [{ei}].{comp_name}: ERROR {e2}", flush=True)
                                    except Exception as e:
                                        print(f"        e_field_n_phi: ERROR {e}", flush=True)

                            except Exception as e:
                                print(f"    profiles_1d: ERROR {e}", flush=True)

                            # profiles_2d
                            try:
                                np2d = len(cw.profiles_2d)
                                print(f"    profiles_2d count = {np2d}", flush=True)
                            except Exception as e:
                                print(f"    profiles_2d: ERROR {e}", flush=True)

                        # Serialize size check
                        try:
                            _ser = waves_ids.serialize()
                            print(f"\n  serialize() bytes = {len(_ser)}", flush=True)
                        except Exception as e:
                            print(f"\n  serialize(): ERROR {e}", flush=True)

                        print(f"{'=' * 70}\n", flush=True)

                    # ---- INSPECT ALL INPUTS PRE-RESERIALIZE ----
                    print("\n" + "=" * 70, flush=True)
                    print("DEBUG [stix_redist]: ALL INPUT IDS KEYS:", flush=True)
                    for _k, _v in self.process_bundle[process]["input"].items():
                        print(f"  '{_k}': type={type(_v).__name__}", flush=True)
                    print("=" * 70, flush=True)

                    # Inspect waves BEFORE reserialize
                    if "waves" in self.process_bundle[process]["input"]:
                        _dbg_inspect_waves("PRE-RESERIALIZE", self.process_bundle[process]["input"]["waves"])

                        # Dump PRE-reserialize waves to run 998
                        try:
                            _dbg_db = _dbg_imas.DBEntry(_dbg_imas.ids_defs.HDF5_BACKEND, 'ITER', 134173, 998, 'bianz')
                            _dbg_db.create()
                            _dbg_db.put(self.process_bundle[process]["input"]["waves"])
                            _dbg_db.close()
                            print("DEBUG [stix_redist]: PRE-reserialize waves dumped to run 998", flush=True)
                        except Exception as e:
                            print(f"DEBUG [stix_redist]: Could not dump PRE waves to 998: {e}", flush=True)

                    # ---- RE-SERIALIZE ALL INPUT IDS ----
                    for _fix_key in list(self.process_bundle[process]["input"].keys()):
                        _fix_ids = self.process_bundle[process]["input"][_fix_key]
                        if hasattr(_fix_ids, 'serialize'):
                            try:
                                _pre_ser = _fix_ids.serialize()
                                _pre_len = len(_pre_ser)

                                _fix_name = _fix_key
                                _clean = getattr(_dbg_imas.IDSFactory(), _fix_name)()
                                _clean.deserialize(_pre_ser)

                                _post_ser = _clean.serialize()
                                _post_len = len(_post_ser)

                                _match = "MATCH" if _pre_len == _post_len else f"MISMATCH (delta={_post_len - _pre_len})"
                                print(f"DEBUG [stix_redist]: Re-serialized {_fix_key}: {_pre_len} -> {_post_len} bytes [{_match}]", flush=True)

                                # Check if round-trip changes the bytes
                                if _pre_ser != _post_ser:
                                    print(f"  WARNING: {_fix_key} serialize bytes differ after round-trip!", flush=True)

                                self.process_bundle[process]["input"][_fix_key] = _clean
                            except Exception as _fix_e:
                                import traceback
                                print(f"DEBUG [stix_redist]: FAILED to re-serialize {_fix_key}: {_fix_e}", flush=True)
                                traceback.print_exc()

                    # Inspect waves AFTER reserialize
                    if "waves" in self.process_bundle[process]["input"]:
                        _dbg_inspect_waves("POST-RESERIALIZE", self.process_bundle[process]["input"]["waves"])

                        # Dump POST-reserialize waves to run 999
                        try:
                            _dbg_db = _dbg_imas.DBEntry(_dbg_imas.ids_defs.HDF5_BACKEND, 'ITER', 134173, 999, 'bianz')
                            _dbg_db.create()
                            _dbg_db.put(self.process_bundle[process]["input"]["waves"])
                            _dbg_db.close()
                            print("DEBUG [stix_redist]: POST-reserialize waves dumped to run 999", flush=True)
                        except Exception as e:
                            print(f"DEBUG [stix_redist]: Could not dump POST waves to 999: {e}", flush=True)

                    # ---- ALSO INSPECT equilibrium and core_profiles sizes ----
                    for _chk_name in ["equilibrium", "core_profiles", "ic_antennas"]:
                        if _chk_name in self.process_bundle[process]["input"]:
                            _chk_ids = self.process_bundle[process]["input"][_chk_name]
                            try:
                                _chk_ser = _chk_ids.serialize()
                                print(f"DEBUG [stix_redist]: {_chk_name} post-reserialize size = {len(_chk_ser)} bytes", flush=True)
                                # Quick sanity: time arrays
                                if hasattr(_chk_ids, 'time'):
                                    print(f"  {_chk_name}.time = {_chk_ids.time}", flush=True)
                            except Exception as e:
                                print(f"DEBUG [stix_redist]: {_chk_name} serialize check ERROR: {e}", flush=True)

                    
                    # ---- CLEAN WORKING DIRECTORY STATE ----
                    import os, glob, shutil
                    print(f"DEBUG [stix_redist]: cwd = {os.getcwd()}", flush=True)
                    if os.path.isdir('Plot_data_stix'):
                        _old_files = os.listdir('Plot_data_stix')
                        print(f"DEBUG [stix_redist]: Cleaning Plot_data_stix/ ({_old_files})", flush=True)
                        shutil.rmtree('Plot_data_stix')
                    for _stale in glob.glob('fort.*'):
                        print(f"DEBUG [stix_redist]: Removing stale {_stale}", flush=True)
                        os.remove(_stale)

                # =============================================================
                # END DEBUG BLOCK
                # =============================================================

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
                                _tmp_ids = self.process_bundle[process]["input"][ids]
                            else:
                                _tmp_ids = eval("imas." + ids + "()")
                            _ensure_ids_name(_tmp_ids, ids)
                            output_ids_data.append(_tmp_ids)
            else:
                # feature/repair_231017
                actor = self.dictionary_of_actors[process]
                kmerge = 0
                _ensure_ids_name(self.process_bundle[process]["input"][0],
                                 "unknown")
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

        # Ensure __name__ on returned IDS (IMAS-Python 2.0 compatibility)
        output_ids_list = codeinfo["output"]
        if not hasattr(results, "__len__"):
            _ensure_ids_name(results, output_ids_list[0] if output_ids_list else "unknown")
        else:
            for i, ids_name in enumerate(output_ids_list):
                if i < len(results):
                    _ensure_ids_name(results[i], ids_name)

        # Call of the chosen code
        return results