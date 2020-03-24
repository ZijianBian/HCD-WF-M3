def hcd_wrapper(par_path):
  import os,imas,sys
  sys.path.append('interface')
  sys.path.append('workflow')
  sys.path.append(os.getcwd())
  from hcd_workflow  import hcd_workflow
  from lxml import etree
  import xml.etree.ElementTree as ET
  from developer_file import load_code_dependencies
  from check_for_dependencies import check_for_dependencies
  from bundle_copy import bundle_copy
  from import_actor import import_actor
  from tmp_ids_storage import tmp_ids_storage
  import numpy as np

  # IMPORT PARAMETERS FROM THE XML PARAMETER FILE OF THE WORKFLOW  
  tree = ET.parse(par_path+'/input_workflow.xml')
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

  if param['run_simpletrans'] == 1:
      list_of_actors = ['simpletrans']
  else:
      list_of_actors = []

  for elem in root[2].iter():
      if elem.tag is not etree.Comment and len(elem)== 0:
          if int(elem.text) is not 0:
               list_of_actors.append(elem.attrib['list'].split()[int(elem.text)-1])
          
  if len(list_of_actors) == 0:
     print('ERROR: no actors selected --> Heating & Current Drive workflow will not be executed')
     return

  # MAKE A LIST OF INPUT AND OUTPUT IDSS OF THE WHOLE WORKFLOW FROM THE LIST OF SELECTED ACTORS
  ids_list = ['core_profiles',\
              'core_sources',\
              'equilibrium',\
              'nbi',\
              'ic_antennas',\
              'ec_launchers',\
              'wall',\
              'distribution_sources',\
              'distributions',\
              'waves']
  in_l  = []
  out_l = []

  # LOOP OVER ALL SELECTED ACTORS
  for name in list_of_actors:

    import_actor(name)
    parstr = globals()[name].__doc__
    for iids in ids_list:
      # APPEND ONLY IF THE IDS IS IN THE PARAMETERS STRING AND NOT ALREADY IN THE INPUT (OUTPUT) LIST
      if parstr.find(':param '+iids) is not -1  and iids not in in_l:
        in_l.append(iids)
      if parstr.find(':param result: '+iids) is not -1 and iids not in out_l:
        out_l.append(iids)

  # ALWAYS INCLUDE CORE_PROFILES IDS, SINCE IT IS USED AS A REFERENCE, EVEN WHEN IT IS NOT USED
  # IN A SPECIFIC H&CD CODES (LIKE E.G. WITH ICCOUP)
  if not 'core_profiles' in in_l:
      in_l.append('core_profiles')

  # CHECK IF THE CODES ARE COMPATIBLE / DEPENDENCIES ARE FULFILLED
  dependencies = load_code_dependencies()
  check_for_dependencies(root, dependencies)

  # ------------------------------------------------------------------------
  # IDS BUNDLES
  # BUNDLING THE IDSS MAKES IT EASIER TO PASS THEM AROUND BETWEEN THE ACTORS
  # IDS_BUNDLE_INPUT:  IDSS FROM THE INPUT DATABASE
  # IDS_BUNDLE_WORK:   IDSS OF THE CURRENT TIMESTEP IN THE WORKFLOW
  # IDS_BUNDLE_OUTPUT: IDSS FOR THE OUTPUT DATABASE
  # ------------------------------------------------------------------------

  # IMAS DB VERSION
  version = os.getenv('IMAS_VERSION')[0]

  # INPUT DB ENVIRONMENT
  input_user_or_path = param['input_user_or_path']
  input_database     = param['input_database']

  # OUTPUT DB ENVIRONMENT
  output_user_or_path = param['output_user_or_path']
  output_database     = param['output_database']

  # DEFAULT OUTPUT USER_OR_PATH NAME IS ENVIRONMENT VARIABLE $USER
  if output_user_or_path=='default':
    output_user_or_path = os.getenv('USER')

  # DEFAULT LOCAL DATABASE NAME IS THE SAME AS THE INPUT ONE
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

  # FOR THE TEMPORARY FILE, ONLY THE DEFAULT USER_OR_PATH BASED ON USERNAME IS USED
  # CLEVERLY CHOOSE 'TMP' FOR DATABASE NAME TO NEVER MIX TEMPORARY FILES WITH OTHERS
  tmp_user_or_path = os.getenv('USER') # (PUTTING IT TO SOMETHING ELSE DOES NOT MAKE A DIFFERENCE)
  tmp_database = 'tmp'
  tmp_folder = os.getenv('HOME')+'/public/imasdb/'+tmp_database+'/3/0'
  if os.path.isdir(tmp_folder) == False:
    print('-- Create local database for tmp file '+tmp_folder)
    os.makedirs(tmp_folder)

  # OPEN INPUT DATAFILE
  print('-- Open input and output file --')
  input = imas.ids(param['shot_nr'], param['run_in'])
  input.open_env(input_user_or_path,input_database,version)
  idx_in = input.core_profiles.getPulseCtx()

  # CREATE OUTPUT DATAFILE
  output = imas.ids(param["shot_nr"], param["run_out"])
  output.create_env(output_user_or_path,output_database,version)
  idx_out = output.core_profiles.getPulseCtx()

  # SETUP ENVIRONMENT FOR TEMPORARY FILE
  tmp_ids_storage()

  # TOTAL LIST OF IDSS TO BE READ FROM THE INPUT SCENARIO FOR H&CD CALCULATIONS
  ids_bundle_input = {'core_profiles':        input.core_profiles, 
                      'core_sources':         input.core_sources,
                      'equilibrium':          input.equilibrium, 
                      'nbi':                  input.nbi, 
                      'ic_antennas':          input.ic_antennas, 
                      'ec_launchers':         input.ec_launchers, 
                      'wall':                 input.wall, 
                      'distribution_sources': input.distribution_sources, 
                      'distributions':        input.distributions,
                      'waves':                input.waves}

  # TOTAL LIST OF IDSS TO BE WRITTEN AS AN OUTPUT
  ids_bundle_output = {'core_profiles':       output.core_profiles, 
                      'core_sources':         output.core_sources,
                      'equilibrium':          output.equilibrium, 
                      'nbi':                  output.nbi, 
                      'ic_antennas':          output.ic_antennas, 
                      'ec_launchers':         output.ec_launchers, 
                      'wall':                 output.wall, 
                      'distribution_sources': output.distribution_sources, 
                      'distributions':        output.distributions,
                      'waves':                output.waves}

  # FOR TIME REFERENCE
  time_array = ids_bundle_input['core_profiles'].partialGet('time')

  # CHECK & ADJUST TIME TO CORE_PROFILES IF NECESSARY
  if param['tbegin'] < 0:
      param['tbegin'] = time_array[0]
      print('Initial time tbegin set to core_profiles first time slice. tbegin = ', param['tbegin'])

  if param['tbegin'] > 0 and param['tbegin'] < time_array[0]:
     print('ERROR: tbegin out of range ('+str(param['tbegin'])+'s is less than first time in core_profiles)')
     return

  if param['tend'] < 0:
      param['tend'] = time_array[-1]
      print('Final time tend set to core_profiles final time slice, tend = ', param['tend'])

  if param['tend'] > 0 and param['tend'] > time_array[-1]:
     print('ERROR: tend out of range  ('+str(param['tend'])+ 's is greater than last time in core_profiles)')
     return

  print('---------------------------------------------')
  print('---- Enter time loop of the H&CD wrapper ----')
  
  ########################################################################
  #-----------------------------------------------------------------------
  #                  BEGIN TIME LOOP 
  #-----------------------------------------------------------------------
  ########################################################################

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
      for elem in in_l:
        print('  Get', elem)
        ids_bundle_input[elem].getSlice(timenow,1)

      # COPY THE INITIAL BUNDLE TO THE WORK BUNDLE
      # WHEN IT IS NOT THE FIRST TIME SLICE: COPY ONLY IDSS WHICH ARE NO OUTPUT OF H&CD ACTORS
      # EXCEPTION: CORE_PROFILES TO ALWAYS BE READ EVEN IF IT IS AN OUTPUT OF HCD2CORE_PROFILES
      if timenow == param['tbegin']:
        ids_bundle_work = bundle_copy(ids_bundle_input,in_l)
      else:
        list_to_get = [value for value in in_l if (value not in out_l or value =='core_profiles')] 
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

  print('---------------------------------------------')
  print('End of H&CD workflow.')      
  print('---------------------')

