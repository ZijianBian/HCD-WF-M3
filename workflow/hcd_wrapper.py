def hcd_wrapper(par_path):
  import os,imas,sys
  from lxml import etree
  import xml.etree.ElementTree as ET
  from hcd_tools import import_actor, read_actor_ids, \
    bundle_copy, create_dict_from_idslist, create_maindict, \
    check_for_dependencies
  from hcd_workflow import hcd_workflow
  import numpy as np

  ##################################################################

  try:

    # --------------------------------------------------------------
    # READ PARAMETERS FROM INPUT PARAMETER XML FILE OF THE WORKFLOW
    # --------------------------------------------------------------
    workflow_xml = par_path+'/input_workflow.xml'
    tree = ET.parse(workflow_xml)
    root = tree.getroot()

    param = {}  
    for elem in root.iter():
      if len(elem) == 0:
        try:
          param[elem.tag] = int(elem.text)
        except:
          try:
            param[elem.tag] = float(elem.text)
          except:
            param[elem.tag] = elem.text

        param['input_path'] = par_path

    # HARDCODED UNTIL THESE VARIABLES DISAPPEAR (TO REMOVE THEM FROM THE INTERFACE)
    param['run_simpletrans'] = 0

    ##################################################################

    # -------------------------------------------------
    # DEFINE LIST OF SELECTED ACTORS AND INVOLVED IDSS
    # -------------------------------------------------

    # LIST OF SELECTED ACTORS
    if param['run_simpletrans'] == 1:
        list_of_actors = ['simpletrans']
    else:
        list_of_actors = []

    for elem in root[2].iter():
        if elem.tag is not etree.Comment and len(elem)== 0:
            if int(elem.text) is not 0:
                 list_of_actors.append(elem.attrib['list'].split()[int(elem.text)-1])

    # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
    # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
    (maindict, compiled_actors, uncompiled_actors, code_selection) = \
            create_maindict(workflow_xml,1,0)

    if len(list_of_actors) == 0:
       print('ERROR: no actor selected --> The H&CD workflow will not be executed')
       return

    # DEFINE THE TOTAL LIST OF INVOLVED INPUT AND OUTPUT IDSS ACCORDING TO THE ACTOR SELECTION
    input_ids_list  = []
    output_ids_list = []
    for name in list_of_actors:
       [single_input_ids_list,single_input_arg_list,single_output_ids_list,err] = \
           read_actor_ids(name,0)
       input_ids_list  = input_ids_list  + single_input_ids_list
       output_ids_list = output_ids_list + single_output_ids_list
    input_ids_list  = list(set(input_ids_list))
    output_ids_list = list(set(output_ids_list))

    # TOTAL LIST OF INVOLVED IDSS ACCORDING TO THE ACTOR SELECTION
    ids_list = list(set(input_ids_list+output_ids_list))

    # ALWAYS INCLUDE CORE_PROFILES IDS, SINCE IT IS USED AS A REFERENCE
    if not 'core_profiles' in input_ids_list:
        input_ids_list.append('core_profiles')

    # CHECK IF THE CODES ARE COMPATIBLE / DEPENDENCIES ARE FULFILLED
    err = check_for_dependencies(workflow_xml)
    if err != 0:
      return

    ##################################################################

    # -------------------------------------
    # INPUT AND OUTPUT DATABASE MANAGEMENT
    # -------------------------------------

     # IMAS DB VERSION
    version = os.getenv('IMAS_VERSION')[0]

    # INPUT AND OUTPUT DB ENVIRONMENT
    input_user_or_path  = param['input_user_or_path']
    input_database      = param['input_database']
    output_user_or_path = param['output_user_or_path']
    output_database     = param['output_database']

    # DEFAULT OUTPUT USER_OR_PATH IS $USER
    if output_user_or_path=='default':
      output_user_or_path = os.getenv('USER')

    # DEFAULT OUTPUT LOCAL DB NAME IS EQUAL TO THE INPUT ONE
    if output_database=='default':
      output_database = input_database

    # IF THE OUTPUT DATABASE DOES NOT EXIST: CREATE IT
    if output_user_or_path== os.getenv('USER'):
      output_folder = os.getenv('HOME')+'/public/imasdb/'+output_database+'/3/0'
    else:
      output_folder = output_user_or_path+'/'+output_database+'/3/0'
    if os.path.isdir(output_folder) == False:
      print('-- Create local database for output file '+output_folder)
      os.makedirs(output_folder)

    # OPEN INPUT DATAFILE
    print('-- Open input and output file --')
    input = imas.ids(param['shot_nr'], param['run_in'])
    input.open_env(input_user_or_path,input_database,version)
    idx_in = input.core_profiles.getPulseCtx()

    # CREATE OUTPUT DATAFILE
    output = imas.ids(param["shot_nr"], param["run_out"])
    output.create_env(output_user_or_path,output_database,version)
    idx_out = output.core_profiles.getPulseCtx()

    ##################################################################

    # ------------------
    # BUNDLE MANAGEMENT
    # ------------------
    # BUNDLING THE IDSS MAKES IT EASIER TO PASS THEM BETWEEN ACTORS
    # IDS_BUNDLE_INPUT:  IDSS FROM THE INPUT DATABASE
    # IDS_BUNDLE_WORK:   IDSS OF THE CURRENT TIMESTEP IN THE WORKFLOW
    # IDS_BUNDLE_OUTPUT: IDSS FOR THE OUTPUT DATABASE
    # ----------------------------------------------------------------

    # TOTAL LIST OF INPUT AND OUTPUT IDSS FOR H&CD CALCULATIONS
    ids_bundle_input  = create_dict_from_idslist(ids_list,input)
    ids_bundle_output = create_dict_from_idslist(ids_list,output)

    ##################################################################

    # -----------------------------------------
    # PREPARE THE TIME RANGE FOR THE TIME LOOP
    # -----------------------------------------

    # INPUT TIME ARRAY
    try:
      time_array = ids_bundle_input['core_profiles'].partialGet('time')
    except:
      print('  ERROR while reading the core_profiles IDS: is it really present in the input file?',\
            file=sys.stderr)
      print('  ----> Aborted.', file=sys.stderr)
      return

    # CHECK & ADJUST CHOSEN TIME TO CORE_PROFILES IF NECESSARY
    if param['tbegin'] < 0:
        param['tbegin'] = time_array[0]
        print('Initial time tbegin set to core_profiles first time slice. tbegin = ', param['tbegin'])

    if param['tbegin'] > 0 and param['tbegin'] < time_array[0]:
       print('ERROR: tbegin out of range ('+str(param['tbegin'])\
             +'s is less than first time in core_profiles)')
       return

    if param['tend'] < 0:
        param['tend'] = time_array[-1]
        print('Final time tend set to core_profiles final time slice, tend = ', param['tend'])

    if param['tend'] > 0 and param['tend'] > time_array[-1]:
       print('ERROR: tend out of range  ('+str(param['tend'])\
             + 's is greater than last time in core_profiles)')
       return

    ##################################################################

    #-----------------
    # BEGIN TIME LOOP 
    #-----------------

    print('---------------------------------------------')
    print('---- Enter time loop of the H&CD wrapper ----')

    timenow = param['tbegin']
    nsteps  = int((param['tend']-param['tbegin'])/param['dt_required'])+1
    step = 0

    while timenow < param['tend']:

        step+=1

        print('---------------------------------------------')
        print('Step = '+str(step)+'/'+str(nsteps))
        print('Time = %5.2f' % timenow, 's')
        print('dt   = %5.2f' % param['dt_required'], 's')

        # READ ALL INPUT IDSS FOR THE CURRENT TIME SLICE
        for elem in input_ids_list:
          print('  Get', elem)
          try:
            ids_bundle_input[elem].getSlice(timenow,1)
          except:
            print('  ERROR while reading the '+elem+' IDS:', file=sys.stderr)
            print('  ----> Check the version of the Data Dictionary between the'+ \
                  ' input and the loaded IMAS version.',file=sys.stderr)
            print('  ----> Aborted.', file=sys.stderr)
            return

        # COPY THE INITIAL BUNDLE TO THE WORK BUNDLE
        # WHEN IT IS NOT THE FIRST TIME SLICE: COPY ONLY IDSS WHICH ARE NO OUTPUT OF H&CD ACTORS
        # EXCEPTION: CORE_PROFILES TO ALWAYS BE READ EVEN IF IT IS AN OUTPUT OF HCD2CORE_PROFILES
        if timenow == param['tbegin']:
          ids_bundle_work = bundle_copy(ids_bundle_input,input_ids_list)
        else:
          list_to_get = [value for value in input_ids_list if (value not in output_ids_list or value =='core_profiles')] 
          ids_bundle_work.update(bundle_copy(ids_bundle_input,list_to_get))

        # ARTIFICIALLY REMOVE WARNINGS
        warning_list = ['distribution_sources','distributions','ec_launchers','ic_antennas','nbi','wall']
        for ids in warning_list:
          if ids in ids_bundle_work:
            ids_bundle_work[ids].ids_properties.homogeneous_time = 1
            ids_bundle_work[ids].time = ids_bundle_input['core_profiles'].time

        print('Execute H&CD workflow for current time slice')
        ids_bundle_work = hcd_workflow(ids_bundle_work, param)

        # OPTIONALLY CALL THE SIMPLE TRANSPORT SOLVER
        if param['run_simpletrans'] == 1:
          try:
               ids_bundle_work['core_profiles'] = simpletrans(ids_bundle_work['equilibirum'], \
                                                              ids_bundle_work['core_profiles'], \
                                                              ids_bundle_work['waves'], \
                                                              ids_bundle_work['distributions'])
          except: 
               print('Failed to load or run SimpleTrans')
               print('WARNING - Skipping SimpleTrans even though it has been choosen in the configuration!')

        # COPY WORK BUNDLE TO OUTPUT BUNDLE TO SAVE THE RESULTS TO DISK
        ids_bundle_output = bundle_copy(ids_bundle_work)

        for elem in ids_bundle_output:

          # THE OUTPUT PULSECTX IS NOT PRESERVED IN THE WORKFLOW ITSELF
          ids_bundle_output[elem].setPulseCtx(idx_out)

          # IF THE IDS IS NOT EMPTY (INPUT OR OUTPUT) IT IS GOING TO BE SAVED USING THE TIME OF THE WORKFLOW
          # (TO AVOID SAVING IDENTICAL TIME VALUES IN CASE THE WORKFLOW TIME RESOLUTION IS SCARCER THAN THE INPUT ONE)
          if ids_bundle_output[elem].ids_properties.homogeneous_time>=0:
            ids_bundle_output[elem].time = np.array([timenow])

            # FIRST TIME SLICE: PUT() INSTEAD OF PUTSLICE() TO SAVE ALSO STATIC DATA
            if timenow == param['tbegin']:
              ids_bundle_output[elem].put()

            # OTHER TIME SLICES: SAVE ONLY THE TIME SLICE
            else:
              ids_bundle_output[elem].putSlice()

        # PREPARE FOR THE NEXT TIME STEP
        timenow += param['dt_required']
        for elem in ids_bundle_work:
          ids_bundle_work[elem].time = np.array([timenow])

        # CLEAN TO SAVE A BIT OF MEMORY
        del ids_bundle_output

    input.close()
    output.close()

    print('---------------------------------------------')
    print('End of H&CD workflow.')      
    print('---------------------')

  except (KeyboardInterrupt, SystemExit):
    print('  hcd_wrapper.py aborted via Ctrl-C')

  except:
    print('ERROR in hcd_wrapper.py')
    raise

