import os
import sys

import imas
import numpy as np

from workflow.hcd_workflow import hcd_workflow
from tools.hcd_tools import (
    read_actor_ids,
    bundle_copy,
    create_dict_from_idslist,
    create_maindict,
    check_for_prerequisites,
    create_workflow_param_from_file,
    loadlist
)
from tools.utility_functions import add_ids_entry_to_dict


def hcd_wrapper(par_path):

    ##################################################################

    try:

        # --------------------------------------------------------------
        # READ PARAMETERS FROM INPUT PARAMETER XML FILE OF THE WORKFLOW
        # --------------------------------------------------------------
        workflow_xml = par_path + "/input_workflow.xml"
        param = create_workflow_param_from_file(workflow_xml, 2)

        ##################################################################

        # -------------------------------------------------
        # DEFINE LIST OF SELECTED ACTORS AND INVOLVED IDSS
        # -------------------------------------------------

        # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
        # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
        (
            maindict,
            compiled_actors,
            uncompiled_actors,
            code_selection,
            catlist,
        ) = create_maindict(workflow_xml, 1, 0)

        # LIST OF ACTIVATED PROCESSES AND SELECTED ACTORS
        list_of_processes = {}
        for process, code in code_selection.items():
            if code is not None:
                list_of_processes[process] = code

        if len(list_of_processes) == 0:
            print(
                "ERROR: no actor selected --> The Diagnostic workflow will not be executed",
                file=sys.stderr,
            )
            return

        ids_scenario_list = loadlist('ids_scenario_list')
        ids_md_list       = loadlist('ids_md_list')
        ids_process_list  = loadlist('ids_process_list')

        # DEFINE THE TOTAL LIST OF INVOLVED INPUT AND OUTPUT IDSS ACCORDING TO THE ACTOR SELECTION
        process_bundle  = {}
        for process,actor in list_of_processes.items():
            [
                single_input_ids_list,
                single_input_arg_list,
                single_output_ids_list,
                err,
            ] = read_actor_ids(actor, 0)

            process_bundle[process] = {}
            process_bundle[process]['input']  = {}
            process_bundle[process]['output'] = {}
            add_ids_entry_to_dict(process_bundle[process]['input'],single_input_ids_list)
            add_ids_entry_to_dict(process_bundle[process]['output'],single_output_ids_list)

        common_bundle = {}
        add_ids_entry_to_dict(common_bundle,ids_scenario_list)

        # Temporary version:
        # common_bundle contains all IDSs to be read via get_slice() from input scenario, defined by ids_scenario_list
        # process_bundle contains all other input and output IDSs (total list = ids_md_list + ids_process_list)
        #    - all its inputs from ids_md_list to be read via get()
        #    - all other inputs from ids_process_list are output of upstream actors 
        #      to be copied from the output bundle of upstream actors inside the time loop
        #      according to the parallel_dependency constraints

        # CHECK IF THE CODES ARE COMPATIBLE / PREREQUISITES ARE FULFILLED
        err = check_for_prerequisites(workflow_xml)
        if err != 0:
            return

        ##################################################################

        # -------------------------------------
        # INPUT AND OUTPUT DATABASE MANAGEMENT
        # -------------------------------------

        # IMAS DB VERSION
        version = os.getenv("IMAS_VERSION")[0]

        # INPUT AND OUTPUT DB ENVIRONMENT
        input_user_or_path = param["input_user_or_path"]
        input_database = param["input_database"]
        output_user_or_path = param["output_user_or_path"]
        output_database = param["output_database"]

        # DEFAULT OUTPUT USER_OR_PATH IS $USER
        if output_user_or_path == "default":
            output_user_or_path = os.getenv("USER")

        # DEFAULT OUTPUT LOCAL DB NAME IS EQUAL TO THE INPUT ONE
        if output_database == "default":
            output_database = input_database

        # IF THE OUTPUT DATABASE DOES NOT EXIST: CREATE IT
        if output_user_or_path == os.getenv("USER"):
            output_folder = (
                os.getenv("HOME") + "/public/imasdb/" + output_database + "/3/0"
            )
        else:
            output_folder = output_user_or_path + "/" + output_database + "/3/0"
        if os.path.isdir(output_folder) == False:
            print(
                "-- Create local database for output file " + output_folder,
                file=sys.stdout,
            )
            os.makedirs(output_folder)

        # OPEN INPUT DATAFILE
        print("-- Open input and output file --", file=sys.stdout)
        input = imas.DBEntry(
            imas.imasdef.MDSPLUS_BACKEND,
            input_database,
            param["shot_nr"],
            param["run_in"],
            input_user_or_path,
        )
        retstatus, idx_in = input.open()
        if retstatus != 0:
            print(
                "   ERROR while reading the input shot="
                + str(param["shot_nr"])
                + " and run="
                + str(param["run_in"])
                + "\n   for user_or_path = "
                + input_user_or_path
                + " and database = "
                + input_database,
                file=sys.stderr,
            )
            print("   Please check that the file exists.", file=sys.stderr)
            return

        # CREATE OUTPUT DATAFILE
        output = imas.DBEntry(
            imas.imasdef.MDSPLUS_BACKEND,
            output_database,
            param["shot_nr"],
            param["run_out"],
            output_user_or_path,
        )
        retstatus, idx_out = output.create()
        if retstatus != 0:
            print(
                "   ERROR while creating the output shot="
                + str(param["shot_nr"])
                + " and run="
                + str(param["run_out"])
                + "\n   for user_or_path = "
                + output_user_or_path
                + " and database = "
                + output_database,
                file=sys.stderr,
            )
            print("   --> Aborted.", file=sys.stderr)
            return

        ##################################################################

        # READ INPUT MACHINE DESCRIPTION DATA
        for process in process_bundle.keys():
            for ids in process_bundle[process]['input'].keys():
                if ids in ids_md_list:
                    process_bundle[process]['input'][ids] = input.get(ids)

        ##################################################################

        # -----------------------------------------
        # PREPARE THE TIME RANGE FOR THE TIME LOOP
        # -----------------------------------------

        if param["one_time_slice"] == 0:

            # INPUT TIME ARRAY
            try:
                time_array = input.partial_get(ids_name="equilibrium", data_path="time")
            except:
                print(
                    "  ERROR while reading the core_profiles IDS: is it really present in the input file?",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return

            # CHECK & ADJUST CHOSEN TIME TO CORE_PROFILES IF NECESSARY
            if param["tbegin"] < 0:
                param["tbegin"] = time_array[0]
                print(
                    "Initial time tbegin set to core_profiles first time slice. tbegin = ",
                    param["tbegin"],
                    file=sys.stdout,
                )

            if param["tbegin"] > 0 and param["tbegin"] < time_array[0]:
                print(
                    "ERROR: tbegin out of range: "
                    + str(param["tbegin"])
                    + " s is less than first time in core_profiles =",
                    "{:.2f}".format(time_array[0]),
                    "s",
                    file=sys.stderr,
                )
                return

            if param["tend"] < 0:
                param["tend"] = time_array[-1]
                print(
                    "Final time tend set to core_profiles final time slice, tend = ",
                    param["tend"],
                    file=sys.stdout,
                )

            if param["tend"] > 0 and param["tend"] > time_array[-1]:
                print(
                    "ERROR: tend out of range: "
                    + str(param["tend"])
                    + " s is greater than last time in core_profiles =",
                    "{:.2f}".format(time_array[-1]),
                    "s",
                    file=sys.stderr,
                )
                return
        else:
            param["tend"] = param["tbegin"] + param["dt_required"]

        ##################################################################

        # -----------------
        # BEGIN TIME LOOP
        # -----------------

        print("---------------------------------------------", file=sys.stdout)
        print("---- Enter time loop of the H&CD wrapper ----", file=sys.stdout)

        timenow = param["tbegin"]

        nsteps = int((param["tend"] - param["tbegin"]) / param["dt_required"])
        if (
            param["dt_required"] * nsteps
            < int((param["tend"] - param["tbegin"]) * 10 ** 5) / 10 ** 5
        ):
            nsteps = nsteps + 1

        step = 0
        previous_time = {}

        while timenow < param["tend"]:

            step += 1

            print("---------------------------------------------", file=sys.stdout)
            print("Step = " + str(step) + "/" + str(nsteps), file=sys.stdout)
            print("Time = %5.2f" % timenow, "s", file=sys.stdout)
            print("dt   = %5.2f" % param["dt_required"], "s", file=sys.stdout)

            # READ ALL INPUT IDSS FROM THE SCENARIO FOR THE CURRENT TIME SLICE
            for ids in ids_scenario_list:
                print("  Get", ids, file=sys.stdout)
                try:
                    common_bundle[ids] = input.get_slice(ids, timenow, 1)
                    for process in process_bundle.keys():
                        if 'merge_' not in process and ids in process_bundle[process]['input'].keys():
                            process_bundle[process]['input'][ids] = common_bundle[ids]
                except:
                    print(
                        "  ERROR while reading the " + ids + " IDS:", file=sys.stderr
                    )
                    print(
                        "  ----> Check the version of the Data Dictionary between the"
                        + " input and the loaded IMAS version.",
                        file=sys.stderr,
                    )
                    print("  ----> Aborted.", file=sys.stderr)
                    return

            process_bundle = hcd_workflow(process_bundle, workflow_xml)

            for ids in common_bundle.keys():

                # IF THE IDS IS NOT EMPTY (INPUT OR OUTPUT) IT IS GOING TO BE SAVED USING THE TIME OF
                # THE WORKFLOW (TO AVOID SAVING IDENTICAL TIME VALUES IN CASE THE WORKFLOW TIME
                # RESOLUTION IS SCARCER THAN THE INPUT ONE)
                if common_bundle[ids].ids_properties.homogeneous_time >= 0:
                    common_bundle[ids].time = np.array([timenow])

                    # FIRST TIME SLICE: PUT() INSTEAD OF PUT_SLICE() TO SAVE ALSO STATIC DATA
                    if timenow == param["tbegin"]:
                        output.put(common_bundle[ids])

                    # OTHER TIME SLICES: SAVE ONLY THE TIME SLICE
                    else:
                        output.put_slice(common_bundle[ids])

            # OUTPUT BUNDLE TO SAVE TO DISK
            process_bundle_out = {}
            # SAVE THE MERGER OUTPUT IDS IF THERE IS ANY
            for process in process_bundle.keys():
                if 'merge_' in process:
                    key, value = list(process_bundle[process]['output'].items())[0]
                    process_bundle_out[key] = value
            # SAVE ALL OTHER OUTPUT IDS BUT ONLY IF IT WAS NOT A MERGER OUTPUT ALREADY
            for process in process_bundle.keys():
                    for key, value in process_bundle[process]['output'].items():
                        if key not in process_bundle_out.keys():
                            process_bundle_out[key] = value
            # SAVE TO DISK
            for ids in process_bundle_out.keys():

                # FIRST TIME SLICE: PUT() INSTEAD OF PUT_SLICE() TO SAVE ALSO STATIC DATA
                if ids not in previous_time:
                    if process_bundle_out[ids].time[0] > 0 or 'merge' in process_bundle_out[ids].code.name:
                        output.put(process_bundle_out[ids])
                        previous_time[ids] = process_bundle_out[ids].time[0]
                # OTHER TIME SLICES: SAVE ONLY THE TIME SLICE
                else:
                    if process_bundle_out[ids] != {}:
                        if process_bundle_out[ids].time[0] > previous_time[ids] \
                           or 'merge' in process_bundle_out[ids].code.name:
                              output.put_slice(process_bundle_out[ids])
                              previous_time[ids] = process_bundle_out[ids].time[0]

            # PREPARE FOR THE NEXT TIME STEP: COPY OUTPUT IDS IN INPUT OF ACTORS FOR THE NEXT TIME STEP
            timenow = timenow*1.0 + param["dt_required"]*1.0
            for process in process_bundle.keys():
                if 'merge_' not in process:
                        for ids in process_bundle[process]['output'].keys():
                            if type(process_bundle[process]['input']) is dict \
                               and ids in process_bundle[process]['input'].keys():
                                  print('Copy '+ids+' from output to input for '+process+' for next time slice')
                                  process_bundle[process]['input'][ids] = process_bundle[process]['output'][ids]

        input.close()
        output.close()

        print("---------------------------------------------", file=sys.stdout)
        print("End of H&CD workflow.", file=sys.stdout)
        print("---------------------", file=sys.stdout)

    except (KeyboardInterrupt, SystemExit):
        print(" hcd_wrapper.py aborted by the user", file=sys.stderr)
        input.close()
        output.close()

    except:
        print("ERROR in hcd_wrapper.py", file=sys.stderr)
        raise
