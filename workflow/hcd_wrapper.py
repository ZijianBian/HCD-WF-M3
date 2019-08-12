
def hcd_wrapper(par_path):

  import os,imas,sys, copy
  sys.path.append('interface')
  sys.path.append('workflow')
  sys.path.append(os.getcwd())
  from hcd_workflow  import hcd_workflow
  import xml.etree.ElementTree as ET
  from developer_file import load_code_dependencies
  from check_for_dependencies import check_for_dependencies


  # IMPORT PARAMETERS FROM XML --------------------------------------
  
  tree = ET.parse(par_path+'/input_workflow.xml')
  print(par_path+'/input_workflow.xml')

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

  timearr = []
  if param['tbegin'] == 0:   
    timearr = core_profiles0.time

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

  print('open input and output file')
  input = imas.ids(param['shot_nr'], param['run_in'], 0,0)
  input.open_env(user_in,tokamakname,version)
  output = imas.ids(param["shot_nr"], param["run_out"], 0,0)
  output.create_env(local_user,tokamakname, version)
  idx_out = output.core_profiles.idx

  ids_bundle_initial = {'core_profiles': input.core_profiles, 
                        'core_sources': input.core_sources,
                        'equilibrium': input.equilibrium, 
                        'pulse_schedule': input.pulse_schedule, 
                        'nbi': input.nbi, 
                        'ic_antennas': input.ic_antennas, 
                        'ec_antennas': input.ec_antennas, 
                        'wall': input.wall, 
                        'distribution_sources': input.distribution_sources, 
                        'distributions': input.distributions,
                        'waves': input.waves
                        }

  ids_bundle_work = copy.deepcopy(ids_bundle_initial)  

  for elem in ids_bundle_initial: 
    ids_bundle_initial[elem].get()

  for elem in ids_bundle_work: 
    ids_bundle_work[elem].getSlice(param['tbegin'],1)

  
  #########################################################################
  #-----------------------------------------------------------------------
  #                  BEGIN TIME LOOP 
  #-----------------------------------------------------------------------
  ########################################################################


  timenow = param['tbegin']
  while timenow < param['tend']:
     
      print('Time =         ', timenow, 's')
      print('dt =           ', param['dt_required'], 's')

           
      
      print('entering heating & current drive workflow')
      ids_bundle_updated = hcd_workflow(ids_bundle_work, param)


      
      if param['run_simpletrans']:
           ids_bundle_updated['core_profiles'] = simpletrans(ids_bundle_updated['equilibirum'], ids_bundle_updated['core_profiles'], ids_bundle_updated['waves'], ids_bundle_updated['distributions'])
    


      print('prepare ids bundle for next timestep')
      timenow += param['dt_required']


      ids_bundle_work = copy.deepcopy(ids_bundle_initial)
      for elem in ids_bundle_work: 
          ids_bundle_work[elem].getSlice(timenow,1)
      
      ids_bundle_work['distribution_sources'] =  copy.deepcopy(ids_bundle_updated['distribution_sources'])
      ids_bundle_work['distributions']        =  copy.deepcopy(ids_bundle_updated['distributions'])
      ids_bundle_work['waves']                =  copy.deepcopy(ids_bundle_updated['waves'])
      ids_bundle_work['core_sources']         =  copy.deepcopy(ids_bundle_updated['core_sources'])
      ids_bundle_work['core_profiles']        =  copy.deepcopy(ids_bundle_updated['core_profiles'])


      

      print('set output')
      for elem in ids_bundle_work:    # not sure if this should be work or updated

        ids_bundle_work[elem].setExpIdx(idx_out)
        ids_bundle_work[elem].putNonTimed()
        ids_bundle_work[elem].putSlice()

      
        
