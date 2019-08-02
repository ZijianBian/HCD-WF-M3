
def hcd_wrapper(par_path):

  import os,imas,sys, copy
  from hcd_workflow  import hcd_workflow
  import xml.etree.ElementTree as ET

  # IMPORT PARAMETERS FROM XML --------------------------------------
  
  tree = ET.parse(par_path+'/input_workflow.xml')
  print(par_path+'/input_workflow.xml')

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
      print(elem.tag, ' = ', param[elem.tag])

  timearr = []
  if param['tbegin'] == 0:   
    timearr = core_profiles0.time


  # MAKE IDS BUNDLE --------------------------------------------------
  # bundling the idss makes it easier to pass them around between the actors
  # ids_bundle_initial:   idss of the input database file (all timeslices)
  # ids_bundle_work:      input idss of the current timestep, only one timeslice
  # ids_bundle_updated:   output idss of the curren timestep, only one timeslice

  # local database environment

  user = os.getenv('USER')
  tokamakname = 'iter'
  version = os.getenv('IMAS_VERSION')[0]

  print('open input and output file')
  input = imas.ids(param['shot_nr'], param['run_in'], 0,0)
  input.open_env(user,tokamakname,'3')
  output = imas.ids(param["shot_nr"], param["run_out"], 0,0)
  output.create_env(user,tokamakname, version)
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
      
#      if param['run_simpletrans']:
#           ids_bundle_updated['core_profiles'] = simpletrans(ids_bundle_updated['equilibirum'], ids_bundle_updated['core_profiles'], ids_bundle_updated['waves'], ids_bundle_updated['distributions'])


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

      
        
