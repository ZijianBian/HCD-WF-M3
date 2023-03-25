import os, sys, copy, imas
import numpy as np

from lxml import etree
from workflow.hcd_workflow import hcd_workflow
from wftools.wf_tools import (
    add_ids_entry_to_dict,
    import_actor,
    read_actor_ids,
    bundle_copy,
    create_dict_from_idslist,
    check_if_code_fulfills_configuration,
    create_workflow_param_from_file,
    loadlist,
    create_maindict,
    find_nearest,
)
from waveform_cooker import add_dynamic
import logging
log = logging.getLogger()
log.setLevel(logging.ERROR)

def wf_wrapper(par_path):

    ##################################################################

    try:

        # ---------------------------------------------
        # READ WORKFLOW PARAMETERS FROM INPUT XML FILE
        # ---------------------------------------------
        workflow_xml = par_path + "/input_workflow.xml"
        wf_parameters = create_workflow_param_from_file(workflow_xml)['workflow_parameters'][0]

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
        ) = create_maindict(workflow_xml, 0)

        # LIST OF ACTIVATED PROCESSES AND SELECTED ACTORS
        list_of_processes = {}
        for process, code in code_selection.items():
            if code is not None:
                list_of_processes[process] = code

        if len(list_of_processes) == 0:
            print(
                "ERROR: no actor selected --> The H&CD workflow will not be executed",
                file=sys.stderr,
            )
            return

        # YAML FILE CONTAINING ALL USEFUL LISTS
        file = os.path.dirname(os.path.abspath(__file__))\
                    + "/../global_configuration/" + "global_lists.yaml"

        ids_scenario_list = loadlist(file,'ids_scenario_list')
        ids_md_list       = loadlist(file,'ids_md_list')
        ids_process_list  = loadlist(file,'ids_process_list')
        waveform_presets  = loadlist(file,'waveform_presets')

        # DEFINE THE TOTAL LIST OF INVOLVED INPUT AND OUTPUT IDSS ACCORDING TO THE ACTOR SELECTION
        process_bundle  = {}
        for process,actor in list_of_processes.items():
            [
                single_input_ids_list,
                single_output_ids_list,
                err,
            ] = read_actor_ids(actor, 0)

            process_bundle[process] = {}
            process_bundle[process]['input']  = {}
            process_bundle[process]['output'] = {}
            add_ids_entry_to_dict(process_bundle[process]['input'],single_input_ids_list)
            add_ids_entry_to_dict(process_bundle[process]['output'],single_output_ids_list)

        # TELL EACH ACTOR WHERE TO FIND ITS XML CODE PARAMETERS FILE AND INITIALIZE IT
        dictionary_of_actors = {}
        process_actor = {}
        for main_key in maindict:
            for category in maindict[main_key]:
                for process in maindict[main_key][category]:
                    for actor_name in maindict[main_key][category][process]:
                        if code_selection[process] is not None and actor_name == code_selection[process]:
                            process_actor[process] = actor_name
                            err = import_actor(actor_name,0)
                            actor = eval(actor_name)
                            runtime_settings = actor.get_runtime_settings()
                            runtime_settings.ids_storage.backend = imas.imasdef.MDSPLUS_BACKEND # IMAS-4055
                            code_parameters = actor.get_code_parameters()
                            code_parameters.parameters_path = par_path+"/"+category+"/"+process+"/input_"+actor_name+".xml"
                            if actor.is_mpi_code is True:
                                if actor.is_mpi_code is True:
                                    tree = etree.parse(par_path+"/"+category+"/"+process+"/input_"+actor_name+".xml")
                                    root = tree.getroot()
                                    for elem in root.iter():
                                        if elem.tag == "nproc_actor":
                                            nproc_actor = int(elem.text)
                                runtime_settings.mpi.mpi_processes = nproc_actor
                                code_parameters.__init__(default_parameters_path=par_path+"/"+category+"/"+process+"/input_"+actor_name+".xml",
                                                         schema_path=par_path+"/"+category+"/"+process+"/input_"+actor_name+".xsd")
                            actor.initialize(code_parameters=code_parameters,runtime_settings=runtime_settings)
                            dictionary_of_actors[actor_name] = actor
                            
        common_bundle = {}
        add_ids_entry_to_dict(common_bundle,ids_scenario_list)

        # Temporary version:
        # common_bundle contains all IDSs to be read via get_slice() from input scenario, defined by ids_scenario_list
        # process_bundle contains all other input and output IDSs (total list = ids_md_list + ids_process_list)
        #    - all its inputs from ids_md_list to be read via get() or get_slice()
        #    - all other inputs from ids_process_list are output of upstream actors 
        #      to be copied from the output bundle of upstream actors inside the time loop
        #      according to the parallel_dependency constraints

        # CHECK IF THE CODES ARE COMPATIBLE / PREREQUISITES ARE FULFILLED
        prerequisites = loadlist(file,"prerequisites")
        err = check_if_code_fulfills_configuration(prerequisites, code_selection)
        if err == 0:
            print("Selection fulfills all actor selection rules", file=sys.stdout)
        else:
            print("Please change the actor selection and try again.", file=sys.stderr)
            return

        ##################################################################

        # -------------------------------------
        # INPUT AND OUTPUT DATABASE MANAGEMENT
        # -------------------------------------

        # IMAS DB VERSION
        version = os.getenv("IMAS_VERSION")[0]

        # INPUT AND OUTPUT DB ENVIRONMENT
        input_user_or_path  = wf_parameters["input_user_or_path"][0]
        input_database      = wf_parameters["input_database"][0]
        output_user_or_path = wf_parameters["output_user_or_path"][0]
        output_database     = wf_parameters["output_database"][0]
        shot_nr             = wf_parameters["shot_nr"][0]
        run_in              = wf_parameters["run_in"][0]
        run_out             = wf_parameters["run_out"][0]
        dt_required         = wf_parameters["dt_required"][0]
        one_time_slice      = wf_parameters["one_time_slice"][0]
        tbegin              = wf_parameters["tbegin"][0]
        tend                = wf_parameters["tend"][0]

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
            shot_nr,
            run_in,
            input_user_or_path,
        )
        retstatus, idx_in = input.open()
        if retstatus != 0:
            print(
                "   ERROR while reading the input shot="
                + str(shot_nr)
                + " and run="
                + str(run_in)
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
            shot_nr,
            run_out,
            output_user_or_path,
        )
        retstatus, idx_out = output.create()
        if retstatus != 0:
            print(
                "   ERROR while creating the output shot="
                + str(shot_nr)
                + " and run="
                + str(run_out)
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
        md = imas.DBEntry(imas.imasdef.MEMORY_BACKEND,output_database,0,run_out,output_user_or_path)
        md.create()
        reduced_md_list = []
        flag_multiple_md = 0
        for process in process_bundle.keys():
            for ids in process_bundle[process]['input'].keys():
                if ids in ids_md_list:
                    process_bundle[process]['input'][ids] = input.get(ids)
                    # Overwrite with configured waveform if it exists
                    waveform_file = par_path\
                        +'/'+waveform_presets[process.split('_')[0]]['custom'][flag_multiple_md]
                    if os.path.exists(waveform_file):
                        process_bundle[process]['input'][ids] = add_dynamic(waveform_file)
                        flag_multiple_md+=1
                    md.put(process_bundle[process]['input'][ids])
                    if ids not in reduced_md_list:
                        reduced_md_list.append(ids)

        ##################################################################

        # WORKFLOW IDS CONFIGURATION ACCORDING TO THE TIME LOOP PARAMETERS
        workflow = imas.workflow()
        workflow.ids_properties.homogeneous_time = 1
        workflow.time.resize(1)
        workflow.time_loop.component.resize(1)
        workflow.time_loop.workflow_cycle.resize(1)
        workflow.time_loop.workflow_cycle[0].component.resize(1)
        workflow.time_loop.workflow_cycle[0].component[0].time_interval = dt_required

        for process in process_bundle.keys():
            if 'workflow' in process_bundle[process]['input'].keys():
                workflow.time_loop.component[0].name = process_actor[process].upper()
                process_bundle[process]['input']['workflow'] = copy.deepcopy(workflow)
        
        # -----------------------------------------
        # PREPARE THE TIME RANGE FOR THE TIME LOOP
        # -----------------------------------------

        if one_time_slice == 0:

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
            if tbegin < 0:
                tbegin = time_array[0]
                print(
                    "Initial time tbegin set to core_profiles first time slice. tbegin = ",
                    tbegin,
                    file=sys.stdout,
                )

            if tbegin > 0 and tbegin < time_array[0]:
                print(
                    "ERROR: tbegin out of range: "
                    + str(tbegin)
                    + " s is less than first time in core_profiles =",
                    "{:.2f}".format(time_array[0]),
                    "s",
                    file=sys.stderr,
                )
                return

            if tend < 0:
                tend = time_array[-1]
                print(
                    "Final time tend set to core_profiles final time slice, tend = ",
                    tend,
                    file=sys.stdout,
                )

            if tend > 0 and tend > time_array[-1]:
                print(
                    "ERROR: tend out of range: "
                    + str(tend)
                    + " s is greater than last time in core_profiles =",
                    "{:.2f}".format(time_array[-1]),
                    "s",
                    file=sys.stderr,
                )
                return
        else:
            tend = tbegin + dt_required

        ##################################################################

        # -----------------
        # BEGIN TIME LOOP
        # -----------------

        print("---------------------------------------------", file=sys.stdout)
        print("---- Enter time loop of the H&CD wrapper ----", file=sys.stdout)

        timenow = tbegin

        if one_time_slice == 0:
            nsteps = int((tend - tbegin) / dt_required)
        else:
            nsteps = 1
        if (
            dt_required * nsteps
            < int((tend - tbegin) * 10 ** 5) / 10 ** 5
        ):
            nsteps = nsteps + 1

        step = 0
        previous_time = {}

        while timenow < tend:

            step += 1

            print("---------------------------------------------", file=sys.stdout)
            print("Step = " + str(step) + "/" + str(nsteps), file=sys.stdout)
            print("Time = %5.2f" % timenow, "s", file=sys.stdout)
            print("dt   = %5.2f" % dt_required, "s", file=sys.stdout)

            # READ ALL INPUT IDSS FROM THE SCENARIO FOR THE CURRENT TIME SLICE
            for ids in ids_scenario_list:
                print("  Get", ids, file=sys.stdout)
                try:
                    common_bundle[ids] = input.get_slice(ids, timenow, 1)
                    #if common_bundle[ids] == 'equilibrium': # when equilibrium misses phi(r,z)
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
                
            # READ ALL MACHINE DESCRITPTION IDSS FOR THE CURRENT TIME SLICE
            for ids in reduced_md_list:
                print("  Get", ids, file=sys.stdout)
                try:
                    for process in process_bundle.keys():
                        if ids in process_bundle[process]['input'].keys():
                            process_bundle[process]['input'][ids] = md.get_slice(ids, timenow, 1)
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

            # ---------------------------------------------------------------------
            # FIND OUT WHETHER EACH PROCESS IS ACTIVATED OR NOT FOR THIS TIME SLICE
            # ---------------------------------------------------------------------
            try:
                time_base=create_workflow_param_from_file(workflow_xml)['time_base']
            except:
                time_base = None

            for process in process_bundle.keys():
                if time_base is not None:
                    if process in time_base[0]:
                        [tc,it]=find_nearest(np.array(time_base[0][process][0]\
                                                      ['wf_interval'][0]['time_array'][0]),timenow)
                        process_bundle[process]['status'] = time_base[0][process][0]\
                            ['wf_interval'][0]['status'][0][it]
                    else:
                        process_bundle[process]['status'] = 1
                else:
                    process_bundle[process]['status'] = 1

            process_bundle,err = hcd_workflow(process_bundle, workflow_xml, dictionary_of_actors)
            if err<0:
                print('  Error in H&CD workflow.',file=sys.stderr)
                return

            # ------------------------------
            # COMMON BUNDLE TO SAVE TO DISK
            # ------------------------------
            for ids in common_bundle.keys():
                if common_bundle[ids].ids_properties.homogeneous_time >= 0:
                    output.put_slice(common_bundle[ids])

            # ------------------------------
            # OUTPUT BUNDLE TO SAVE TO DISK
            # ------------------------------
            process_bundle_out = {}

            # TAKE THE MERGER OUTPUT IDS IF THERE IS ANY
            for process in process_bundle.keys():
                if 'merge_' in process:
                    key, value = list(process_bundle[process]['output'].items())[0]
                    process_bundle_out[key] = value

            # TAKE ALL OTHER OUTPUT IDS BUT ONLY IF IT WAS NOT A MERGER OUTPUT ALREADY
            for process in process_bundle.keys():
                for key, value in process_bundle[process]['output'].items():
                    if key not in process_bundle_out.keys():
                        process_bundle_out[key] = value

            # SAVE TO DISK
            for ids in process_bundle_out.keys():
                if len(process_bundle_out[ids].time) > 0: # Empty if process deactivated by an is_xx_on function
                    if process_bundle_out[ids].time[0] > 0 \
                       or 'merge' in process_bundle_out[ids].code.name:
                        output.put_slice(process_bundle_out[ids])
                        previous_time[ids] = process_bundle_out[ids].time[0]

            # ------------------------------------------------------------------------------------------
            # PREPARE FOR THE NEXT TIME STEP: COPY OUTPUT IDS IN INPUT OF ACTORS FOR THE NEXT TIME STEP
            # ------------------------------------------------------------------------------------------
            timenow = timenow*1.0 + dt_required*1.0
            for process in process_bundle.keys():
                if 'merge_' not in process:
                        for ids in process_bundle[process]['output'].keys():
                            if type(process_bundle[process]['input']) is dict \
                               and ids in process_bundle[process]['input'].keys():
                                  print('Copy '+ids+' from output to input for '\
                                        +process+' for next time slice')
                                  process_bundle[process]['input'][ids] = \
                                      process_bundle[process]['output'][ids]

        input.close()
        output.close()
        md.close()

        # FINALIZE ALL ACTORS
        for actor_name,actor in dictionary_of_actors.items():
            actor.finalize()

        print("---------------------------------------------", file=sys.stdout)
        print("End of H&CD workflow.", file=sys.stdout)
        print("---------------------", file=sys.stdout)

    except (KeyboardInterrupt, SystemExit):
        print(" wf_wrapper.py aborted by the user", file=sys.stderr)
        input.close()
        output.close()

    except:
        print("ERROR in wf_wrapper.py", file=sys.stderr)
        raise
