def hcd_wrapper(par_path):
  import os,imas,sys
  from lxml import etree
  import xml.etree.ElementTree as ET
  from hcd_tools import read_actor_ids, \
    bundle_copy, create_dict_from_idslist, create_maindict, \
    check_for_dependencies, create_workflow_param_from_file
  from hcd_workflow import hcd_workflow
  import numpy as np

  ##################################################################

  try:

    # --------------------------------------------------------------
    # READ PARAMETERS FROM INPUT PARAMETER XML FILE OF THE WORKFLOW
    # --------------------------------------------------------------
    workflow_xml = par_path+'/input_workflow.xml'
    param = create_workflow_param_from_file(workflow_xml,2)

    ##################################################################

    # -------------------------------------------------
    # DEFINE LIST OF SELECTED ACTORS AND INVOLVED IDSS
    # -------------------------------------------------

    # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
    # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
    (maindict, compiled_actors, uncompiled_actors, code_selection, catlist) = \
            create_maindict(workflow_xml,1,0)

    # LIST OF SELECTED ACTORS
    list_of_actors = []
    for process,code in code_selection.items():
      if code is not None:
        list_of_actors.append(code)
    if len(list_of_actors) == 0:
       print('ERROR: no actor selected --> The H&CD workflow will not be executed', file=sys.stderr)
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
    ids_list        = list(set(input_ids_list+output_ids_list))

    # ALWAYS INCLUDE CORE_PROFILES IDS SINCE IT IS USED AS A REFERENCE
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
      print('-- Create local database for output file '+output_folder, file=sys.stdout)
      os.makedirs(output_folder)

    # OPEN INPUT DATAFILE
    print('-- Open input and output file --', file=sys.stdout)
    input = imas.DBEntry(imas.imasdef.MDSPLUS_BACKEND,input_database,\
                         param['shot_nr'],param['run_in'],input_user_or_path)
    retstatus,idx_in = input.open()
    if retstatus != 0:
      print('   ERROR while reading the input shot='+str(param['shot_nr'])\
            +' and run='+str(param['run_in'])+'\n   for user_or_path = '+input_user_or_path\
            +' and database = '+input_database, file=sys.stderr)
      print('   Please check that the file exists.', file=sys.stderr)
      return

    # CREATE OUTPUT DATAFILE
    output = imas.DBEntry(imas.imasdef.MDSPLUS_BACKEND,output_database,\
                          param["shot_nr"],param["run_out"],output_user_or_path)
    retstatus,idx_out = output.create()
    if retstatus < 0:
      print('   ERROR while creating the output shot='+str(param['shot_nr'])\
            +' and run='+str(param['run_out'])+'\n   for user_or_path = '+output_user_or_path\
            +' and database = '+output_database, file=sys.stderr)
      print('   --> Aborted.', file=sys.stderr)
      return

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
    ids_bundle_input  = create_dict_from_idslist(ids_list)
    ids_bundle_output = create_dict_from_idslist(ids_list)

    ##################################################################

    # -----------------------------------------
    # PREPARE THE TIME RANGE FOR THE TIME LOOP
    # -----------------------------------------

    # INPUT TIME ARRAY
    try:
      time_array = input.partial_get(ids_name='equilibrium',data_path='time')
    except:
      print('  ERROR while reading the core_profiles IDS: is it really present in the input file?'\
            ,file=sys.stderr)
      print('  ----> Aborted.', file=sys.stderr)
      return

    # CHECK & ADJUST CHOSEN TIME TO CORE_PROFILES IF NECESSARY
    if param['tbegin'] < 0:
        param['tbegin'] = time_array[0]
        print('Initial time tbegin set to core_profiles first time slice. tbegin = ',\
              param['tbegin'], file=sys.stdout)

    if param['tbegin'] > 0 and param['tbegin'] < time_array[0]:
       print('ERROR: tbegin out of range: '+str(param['tbegin'])\
             +' s is less than first time in core_profiles =', '{:.2f}'.format(time_array[0]),'s',\
             file=sys.stderr)
       return

    if param['tend'] < 0:
        param['tend'] = time_array[-1]
        print('Final time tend set to core_profiles final time slice, tend = ', param['tend'], file=sys.stdout)

    if param['tend'] > 0 and param['tend'] > time_array[-1]:
       print('ERROR: tend out of range: '+str(param['tend'])\
             + ' s is greater than last time in core_profiles =', '{:.2f}'.format(time_array[-1]),'s',\
             file=sys.stderr)
       return

    ##################################################################

    #-----------------
    # BEGIN TIME LOOP 
    #-----------------

    print('---------------------------------------------', file=sys.stdout)
    print('---- Enter time loop of the H&CD wrapper ----', file=sys.stdout)

    timenow = param['tbegin']
    nsteps  = int((param['tend']-param['tbegin'])/param['dt_required'])+1
    step = 0

    while timenow < param['tend']:

        step+=1

        print('---------------------------------------------', file=sys.stdout)
        print('Step = '+str(step)+'/'+str(nsteps), file=sys.stdout)
        print('Time = %5.2f' % timenow, 's', file=sys.stdout)
        print('dt   = %5.2f' % param['dt_required'], 's', file=sys.stdout)

        # READ ALL INPUT IDSS FOR THE CURRENT TIME SLICE
        for elem in input_ids_list:
          print('  Get', elem, file=sys.stdout)
          try:
            ids_bundle_input[elem] = input.get_slice(elem,timenow,1)
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
          list_to_get = [value for value in input_ids_list if (value not in output_ids_list \
                         or value =='core_profiles')] 
          ids_bundle_work.update(bundle_copy(ids_bundle_input,list_to_get))

        ids_bundle_work = hcd_workflow(ids_bundle_work,workflow_xml)

        # OPTIONALLY CALL THE SIMPLE TRANSPORT SOLVER
        if param['run_simpletrans'] == 1:
          try:
               ids_bundle_work['core_profiles'] = simpletrans(ids_bundle_work['equilibirum'], \
                                                              ids_bundle_work['core_profiles'], \
                                                              ids_bundle_work['waves'], \
                                                              ids_bundle_work['distributions'])
          except: 
               print('Failed to load or run SimpleTrans', file=sys.stderr)
               print('WARNING - Skipping SimpleTrans even though it has been'+\
                     ' choosen in the configuration!', file=sys.stdout)

        # COPY WORK BUNDLE TO OUTPUT BUNDLE TO SAVE THE RESULTS TO DISK
        ids_bundle_output = bundle_copy(ids_bundle_work)

        for elem in ids_bundle_output:

          # IF THE IDS IS NOT EMPTY (INPUT OR OUTPUT) IT IS GOING TO BE SAVED USING THE TIME OF 
          # THE WORKFLOW (TO AVOID SAVING IDENTICAL TIME VALUES IN CASE THE WORKFLOW TIME 
          # RESOLUTION IS SCARCER THAN THE INPUT ONE)
          if ids_bundle_output[elem].ids_properties.homogeneous_time>=0:
            ids_bundle_output[elem].time = np.array([timenow])

            # FIRST TIME SLICE: PUT() INSTEAD OF PUT_SLICE() TO SAVE ALSO STATIC DATA
            if timenow == param['tbegin']:
              output.put(ids_bundle_output[elem])

            # OTHER TIME SLICES: SAVE ONLY THE TIME SLICE
            else:
              output.put_slice(ids_bundle_output[elem])

        # PREPARE FOR THE NEXT TIME STEP
        timenow += param['dt_required']
        for elem in ids_bundle_work:
          ids_bundle_work[elem].time = np.array([timenow])

        # CLEAN TO SAVE A BIT OF MEMORY
        del ids_bundle_output

    input.close()
    output.close()

    print('---------------------------------------------', file=sys.stdout)
    print('End of H&CD workflow.', file=sys.stdout)      
    print('---------------------', file=sys.stdout)

  except (KeyboardInterrupt, SystemExit):
    print(' hcd_wrapper.py aborted by the user', file=sys.stderr)
    input.close()
    output.close()

  except:
    print('ERROR in hcd_wrapper.py', file=sys.stderr)
    raise

