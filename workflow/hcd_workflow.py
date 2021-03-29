import sys
import os
import copy
from utility_functions import gen_dict_extract
from lxml import etree
from multiprocessing import Pool
from time import time

from hcd_tools import (
    bundle_copy,
    create_workflow_param_from_file,
    is_nbi_on,
    is_ec_on,
    is_ic_on,
    import_actor,
    loadlist,
    is_compiled_for_mpi,
    read_actor_ids,
    create_workflow_param_from_file,
    create_maindict,
    clever_algo,
)
from stdout_redirector import redirect_stdout, stdout_back

# -------------------------------------------------------------------------------------------------

# CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
# (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
hcd_path = "/".join(os.path.realpath(__file__).split("/")[:-2])
workflow_xml = hcd_path + "/global_configuration/input_workflow_default.xml"
(
    maindict,
    compiled_actors,
    uncompiled_actors,
    code_selection,
    catdict,
) = create_maindict(workflow_xml, 2, 0)

# LIST OF EMPTY ACTORS, MERGERS AND OF EXTRA (NON-IDS) ARGUMENTS FOR EACH ACTOR
merge_actor_list = loadlist("merge_actor_list")
extra_argument_list = loadlist("extra_arguments")
list_of_actors = compiled_actors + merge_actor_list
for name in list_of_actors:
    err = import_actor(name, 0)


def run(cat, bundle, parameters):

    # For merge, bundle is a list of 2 bundles and the call is simpler
    if type(bundle) is list:
        ids_to_merge = cat.replace("merge_", "")
        return globals()[cat](bundle[0][ids_to_merge], bundle[1][ids_to_merge])

    # Get list of all codes in that category
    codeslist = catdict[cat]  # next(gen_dict_extract(cat,maindict))
    codeinfo = codeslist[parameters[cat]]
    code = codeinfo["name"]

    # Re-direct the logfile for this specific actor
    if code + "_log" in parameters.keys():
        stdout_redirect = parameters[code + "_log"]
        oldstrout, newstdout = redirect_stdout(stdout_redirect)

    inputargs = []
    extra_arg_nr = 0
    inputxml = []
    for i in codeinfo["input"]:
        if (
            i.find("extra_argument_list") is not -1
            and extra_argument_list.get(code) is not None
        ):
            inputargs.append(parameters[extra_argument_list[code][extra_arg_nr]])
            extra_arg_nr += 1
        elif i.find("codeparam") is not -1:
            inputxml.append(
                parameters["input_path"]
                + "/"
                + codeinfo["system"]
                + "/input_"
                + code
                + ".xml"
            )
        else:
            inputargs.append(bundle[i])

    inputmpi = []
    libmpi_path = eval(code + ".location") + "/native_wrapper/lib/lib" + code + ".so"
    args_np = {}
    if os.path.isfile(libmpi_path) is True and is_compiled_for_mpi(libmpi_path, "libmpi"):
        tree = etree.parse(inputxml[0])
        root = tree.getroot()
        for elem in root.iter():
            if elem.tag == "nproc_actor":
                nproc_actor = int(elem.text)
                print("MPI code --> nproc_actor = ", nproc_actor)
        args_np = {"mpi_processes": nproc_actor}
        exec_type = None
        if code in parameters.keys():
            exec_type = parameters[code]
        if exec_type == None:
            inputmpi.append("mpi_local")
        else:
            inputmpi.append(exec_type)

    inputs = inputargs + inputxml + inputmpi

    results = globals()[code](*inputs, **args_np)

    # Re-direct the logfile for this specific actor
    if code + "_log" in parameters.keys():
        stdout_back(oldstrout, newstdout)

    # Call of the chosen code
    return results


# -------------------------------------------------------------------------------------------------


def hcd_workflow(BNDL_in, workflow_xml):

    print("Execute H&CD workflow for current time slice", file=sys.stdout)

    # EXTRACT PARAMETERS FROM INPUT XML FILE
    parameters = create_workflow_param_from_file(workflow_xml, 2)

    # IF AN H&CD SOURCE IS CONFIGURED BUT IT HAS NO POWER FOR THIS TIME SLICE,
    # DO NOT RUN THE CODE(S) FOR THIS SOURCE
    if "nbi" in BNDL_in.keys() and not is_nbi_on(BNDL_in["nbi"], BNDL_in["nbi"].time):
        print("  No NBI power for this time slice")
        parameters["nbi_source"] = 0
        parameters["nbi_fp"] = 0
    if "ic_antennas" in BNDL_in.keys() and not is_ic_on(
        BNDL_in["ic_antennas"], BNDL_in["ic_antennas"].time
    ):
        print("  No IC power for this time slice")
        parameters["iccoup"] = 0
        parameters["ic_wave_solver"] = 0
        parameters["ic_wave_fp"] = 0
    if "ec_launchers" in BNDL_in.keys() and not is_ec_on(
        BNDL_in["ec_launchers"], BNDL_in["ec_launchers"].time
    ):
        print("  No EC power for this time slice")
        parameters["ec_wave_solver"] = 0

    # ARTIFICIALLY REMOVE WARNINGS
    warning_list = [
        "distribution_sources",
        "distributions",
        "ec_launchers",
        "ic_antennas",
        "nbi",
        "wall",
    ]
    for ids in warning_list:
        if ids in BNDL_in:
            BNDL_in[ids].ids_properties.homogeneous_time = 1
            BNDL_in[ids].time = BNDL_in["core_profiles"].time

    # DEFINE THE SEQUENCE OF CODES TO BE EXECUTED
    if catdict["ic_wave_fp"][parameters["ic_wave_fp"]]["name"] != "fopla":
        print("--- Default algorithm ---")
        input_algorithm = loadlist("algorithm")["default"]
    else:
        print("--- NBI+IC synergy algorithm ---")
        input_algorithm = loadlist("algorithm")["nbi_ic_synergy"]
    final_algorithm, waiting_for, parallel_runs = clever_algo(
        input_algorithm, parameters, catdict
    )

    # print('final_algo',final_algorithm)
    # print(' ')
    # print('waiting_for',waiting_for)
    # print(' ')
    # print('parallel_runs',parallel_runs)

    # EXECUTE THE CODES ACCORDING TO THE REQUESTED SEQUENCE
    BNDL_work = bundle_copy(BNDL_in)
    BNDL_out = {}
    BNDL_to_merge = {}

    parallel_f = parameters["parallel_workflow"]

    # SERIAL EXECUTION OF THE WORKFLOW
    if parallel_f == 0:
        for steprun in final_algorithm:
            if not "merge_" in steprun:
                print(
                    " STEPRUN --> ",
                    steprun,
                    "=",
                    catdict[steprun][parameters[steprun]]["name"].upper(),
                )
                output_ids_list = catdict[steprun][parameters[steprun]]["output"]
                output_ids_data = run(steprun, BNDL_work, parameters)
            else:
                print(" STEPRUN --> ", steprun)
                output_ids_list = [steprun.replace("merge_", "")]
                output_ids_data = run(steprun, [BNDL_work, BNDL_to_merge], parameters)
                del BNDL_to_merge[output_ids_list[0]]
            for iids in range(len(output_ids_list)):
                if len(output_ids_list) == 1:
                    output_ids = output_ids_data
                else:
                    output_ids = output_ids_data[iids]
                if output_ids_list[iids] not in BNDL_out.keys() or "merge_" in steprun:
                    BNDL_out[output_ids_list[iids]] = output_ids
                    BNDL_work[output_ids_list[iids]] = copy.deepcopy(
                        BNDL_out[output_ids_list[iids]]
                    )
                else:
                    BNDL_to_merge[output_ids_list[iids]] = output_ids

    # PARALLEL EXECUTION OF THE WORKFLOW
    else:
        t0 = time()
        for i in range(len(parallel_runs)):
            print("Section", i, parallel_runs[i])
        for isection in range(len(parallel_runs)):
            t1 = time()
            N_actor = len(parallel_runs[isection])
            P = Pool(N_actor)
            print("Section =", isection, ", No. of actors = ", N_actor)
            output_ids_lists = []
            output_ids_data_rs = []
            output_ids_datas = []
            for i_actor in range(N_actor):
                steprun = parallel_runs[isection][i_actor]
                if not "merge_" in steprun:
                    actor_name = catdict[steprun][parameters[steprun]]["name"]
                    print("cat = ", steprun, ", actor = ", actor_name)
                    logfile = (
                        "log/Section_"
                        + str(isection)
                        + "_"
                        + str(i_actor)
                        + "_"
                        + actor_name
                        + ".log"
                    )
                    parameters[actor_name + "_log"] = logfile
                    output_ids_list = catdict[steprun][parameters[steprun]]["output"]
                    output_ids_lists.append(output_ids_list)
                    inputs = (steprun, BNDL_work, parameters)
                    output_ids_data = P.apply_async(run, inputs)
                    output_ids_data_rs.append(output_ids_data)
                else:
                    output_ids_list = [steprun.replace("merge_", "")]
                    output_ids_lists.append(output_ids_list)
                    inputs = (steprun, [BNDL_work, BNDL_to_merge], parameters)
                    output_ids_data = P.apply_async(run, inputs)
                    output_ids_data_rs.append(output_ids_data)
            P.close()
            P.join()
            for i_actor in range(N_actor):
                steprun = parallel_runs[isection][i_actor]
                output_ids_data = output_ids_data_rs[i_actor].get()
                output_ids_datas.append(output_ids_data)
                for iids in range(len(output_ids_lists[i_actor])):
                    if len(output_ids_lists[i_actor]) == 1:
                        output_ids = output_ids_datas[i_actor]
                    else:
                        output_ids = output_ids_datas[i_actor][iids]
                    if (
                        output_ids_lists[i_actor][iids] not in BNDL_out.keys()
                        or "merge_" in steprun
                    ):
                        BNDL_out[output_ids_lists[i_actor][iids]] = output_ids
                        BNDL_work[output_ids_lists[i_actor][iids]] = copy.deepcopy(
                            BNDL_out[output_ids_lists[i_actor][iids]]
                        )
                    else:
                        BNDL_to_merge[output_ids_lists[i_actor][iids]] = output_ids
            del output_ids_data_rs[:]
            t2 = time()
            print("Section:", i, " time:", round(t2 - t1, 4), "sec")
        tend = time()
        print("CPU time for the workflow time step:", round(tend - t0, 4), "sec")

    # COPY ALL OTHER IDSS FROM INPUT TO OUTPUT BUNDLE
    for iids in BNDL_in.keys():
        if iids not in BNDL_out.keys():
            BNDL_out[iids] = copy.deepcopy(BNDL_in[iids])

    print("End of time slice", file=sys.stdout)

    return BNDL_out
