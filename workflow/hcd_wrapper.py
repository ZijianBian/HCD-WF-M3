def hcd_wrapper(par_path):
  import os,imas,sys, copy
  sys.path.append('interface')
  sys.path.append('workflow')
  sys.path.append(os.getcwd())
  from pyal import ALEnv
  from random import randint
  from hcd_workflow  import hcd_workflow
  from lxml import etree
  import xml.etree.ElementTree as ET
  from developer_file import load_code_dependencies
  from check_for_dependencies import check_for_dependencies
  import numpy as np 
  import pdb

  # IMPORT PARAMETERS FROM XML --------------------------------------
  
  tree = ET.parse(par_path+'/input_workflow.xml')
  root = tree.getroot()

  param = {}
  
  print('----- WORKFLOW PARAMETERS ----')

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
      print(elem.tag, ' = ', param[elem.tag])

  if param['run_simpletrans'] == 1:
      list_of_actors = ['simpletrans'] ## 
  else:
      list_of_actors = []

  for elem in root[2].iter():
      if elem.tag is not etree.Comment and len(elem)== 0:
          if int(elem.text) is not 0:
               list_of_actors.append(elem.attrib['list'].split()[int(elem.text)-1])
          
  if len(list_of_actors) == 0:
     print('ERROR: no actors selected - heating & current drive workflow will not be executed')
     return




  ##----------------------------------------------------------------------------------
  # make a list of input and output idss 

  actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')

  ids_list = ['core_profiles','core_sources','equilibrium', 'pulse_schedule', 'nbi', 'ic_antennas', 'ec_launchers','wall', 'distribution_sources', 'distributions', 'waves']


  in_l = []
  out_l = []

  

  for name in list_of_actors:
    try:
      sys.path[:0] = [os.path.join(actor_path,name)]
      globals()[name] = getattr(__import__(name), name)
  
      parstr = globals()[name].__doc__
        
      for iids in ids_list:
        # append to list only if the name of ids is in the paramters string AND if it's not already on the input (output) list - because we are looking to find the input and output ids of the whole workflow
        if parstr.find(':param '+iids) is not -1  and iids not in in_l:
                in_l.append(iids)
        if parstr.find(':param result: '+iids) is not -1 and iids not in out_l:
                out_l.append(iids)
    except:
        print(name, ' not found!')




  ## CHECK IF THE CODES ARE COMPATIBLE / DEPENDENCIES ARE FULFILLED
  dependencies = load_code_dependencies()
  check_for_dependencies(root, dependencies)


  # MAKE IDS BUNDLE --------------------------------------------------
  # bundling the idss makes it easier to pass them around between the actors
  # ids_bundle_initial:   idss of the input database file (all timeslices)
  # ids_bundle_work:      input idss of the current timestep, only one timeslice
  # ids_bundle_updated:   output idss of the curren timestep, only one timeslice

  # remote and local database environment
  user_in     = param['user']
  local_user  = os.getenv('USER')
  tokamakname = param['machine'] # assumed to be the same for remote/local DB
  version     = os.getenv('IMAS_VERSION')[0]

  # If the local database for the required tokamak does not exist yet: create it
  if not os.path.exists(os.getenv('HOME')+'/public/imasdb/'+tokamakname):
       print('--> Create local database '+os.getenv('HOME')+'/public/imasdb/'+tokamakname)
       os.popen("imasdb "+tokamakname).read()

  print('-- open input and output file --')
  input = imas.ids(param['shot_nr'], param['run_in'], 0,0)
  input.open_env(user_in,tokamakname,version)
  output = imas.ids(param["shot_nr"], param["run_out"], 0,0)
  output.create_env(local_user,tokamakname, version)
  idx_out = output.core_profiles.getPulseCtx()

  # DEFINE THE SHOT/RUN NUMBERS AND LOCATION OF THE TEMPORARY FILE
  exist = 'yes'
  shot_tmp = 9988
  while exist == 'yes':
    run_tmp  = randint(0,9999)
    tmp = imas.ids(shot_tmp,run_tmp,0,0)
    try:
      tmp.open_env(user,tokamakname,version)
    except Exception:
      exist = 'no'
  tmp_db = ALEnv(shot=shot_tmp, run_temp=run_tmp, machine_temp=tokamakname).ids_tmp

  ids_bundle_initial = {'core_profiles': input.core_profiles, 
                        'core_sources': input.core_sources,
                        'equilibrium': input.equilibrium, 
                        'pulse_schedule': input.pulse_schedule, 
                        'nbi': input.nbi, 
                        'ic_antennas': input.ic_antennas, 
                        'ec_launchers': input.ec_launchers, 
                        'wall': input.wall, 
                        'distribution_sources': input.distribution_sources, 
                        'distributions': input.distributions,
                        'waves': input.waves
                        }


  ids_bundle_work = copy.deepcopy(ids_bundle_initial)  

  for elem in ids_bundle_initial: 
      if  elem in in_l or elem in out_l:
           print('get ', elem)
           ids_bundle_initial[elem].get()

  ## ALWAYS GET CORE_PROFILES IDS, SINCE IT IS USED AS A REFERNCE, EVEN WHEN IT IS NOT USED 
  ## IN A SPECIFIC H&CD CODES (LIKE E.G. WITH ICCOUP)
  if len(ids_bundle_initial['core_profiles'].time)==0:
      print('get core_profiles')
      ids_bundle_initial['core_profiles'].get()

  ## CHECK & ADJUST TIME TO CORE_PROFILES IF NECESSARY
  if param['tbegin'] < 0:
      param['tbegin'] = ids_bundle_initial['core_profiles'].time[0]
      print('tbegin set to time of first core_profiles timeslice. tbegin = ', param['tbegin'])

  if param['tbegin'] > 0 and param['tbegin'] < ids_bundle_initial['core_profiles'].time[0]:
     print('ERROR: tbegin out of range ('+str(param['tbegin'])+'s is less than first time in core_profiles)')
     return

  if param['tend'] < 0:
      param['tend'] = ids_bundle_initial['core_profiles'].time[-1]
      print('tend set to time of last core_profiles timeslice, tend = ', param['tend'])

  if param['tend'] > 0 and param['tend'] > ids_bundle_initial['core_profiles'].time[-1]:
     print('ERROR: tend out of range  ('+str(param['tend'])+ 's is greater than last time in core_profiles)')
     return

  oldtime = {}

  for elem in ids_bundle_work: 

       ids_bundle_work[elem].getSlice(param['tbegin'],1)

       oldtime[elem] = [ids_bundle_work[elem].time, True]
         
  print('---- enter timeloop ----')
  
  #########################################################################
  #-----------------------------------------------------------------------
  #                  BEGIN TIME LOOP 
  #-----------------------------------------------------------------------
  ########################################################################


  timenow = param['tbegin']


  while timenow < param['tend']+param['dt_required']:
     
      print('Time =         ', timenow, 's')
      print('dt =           ', param['dt_required'], 's')

           
    
      print('entering heating & current drive workflow')
      ids_bundle_updated = hcd_workflow(ids_bundle_work, param)
    
      
      if param['run_simpletrans'] == 1:
        ## import simpletrans
        try:
             ids_bundle_updated['core_profiles'] = simpletrans(ids_bundle_updated['equilibirum'], ids_bundle_updated['core_profiles'], ids_bundle_updated['waves'], ids_bundle_updated['distributions'])
        except: 
             print('FAILED TO LOAD OR RUN SIMPLETRANS')
             print('WARNING - skipping simpletrans even though it has been choosen in the configuration!')
          

       
     

      for elem in ids_bundle_updated:   

           ids_bundle_updated[elem].setPulseCtx(idx_out)
           if timenow ==  (param['tbegin']):
               
               if ids_bundle_updated[elem].ids_properties.homogeneous_time == 1 or ids_bundle_updated[elem].ids_properties.homogeneous_time == 0:

                 ids_bundle_updated[elem].put()
               else:
             
                 pass
          ## if the ids has been modified - change the time to the workflow time - and definitely put to database
          #  elif the ids has not been modified AND the time has changed - put to database
          #  else (the ids has not been modified AND the time has not changed) - don't put

           if elem in out_l: 


                     
                 m = ids_bundle_updated['core_profiles'].time
                 m[0] = float(timenow)
                 ids_bundle_updated[elem].time = m


                 if not ids_bundle_updated[elem].ids_properties.homogeneous_time == 1 or not ids_bundle_updated[elem].ids_properties.homogeneous_time == 0: #if the ids didnot exist before (homogeneous time not filled) and it is an output set homogeneous time to 1
           
                     ids_bundle_updated[elem].ids_properties.homogeneous_time = 1
                 ids_bundle_work[elem].putSlice()


           elif oldtime[elem][1]:
                 if ids_bundle_updated[elem].ids_properties.homogeneous_time == 1 or ids_bundle_updated[elem].ids_properties.homogeneous_time == 0:
                     ids_bundle_updated[elem].putSlice()
                 else: 
                   pass
           else:
               pass
             


    #  print('prepare ids bundle for next timestep')
      timenow += param['dt_required']
      

      ids_bundle_work = copy.deepcopy(ids_bundle_initial)
      for elem in ids_bundle_work: 
          ids_bundle_work[elem].getSlice(timenow,1)
          
          ## does this new Slice have a different time than the old Slice? 
          if oldtime[elem][0] == ids_bundle_work[elem].time:
                oldtime[elem][1] = False
          else:
                oldtime[elem][1] = True
          oldtime[elem][0] =  ids_bundle_work[elem].time
      

          if elem in out_l: 
              ids_bundle_work[elem] =  copy.deepcopy(ids_bundle_updated[elem])
        #      print('using the '+ elem+ ' output as input for the next timeslice')


      
        
