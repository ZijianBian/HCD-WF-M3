def hcd_jintrac_interface(ids_bundle_input,hcd_path,hcd_xml_path):
  import os,imas,sys
  sys.path.append(hcd_path+'/interface')
  sys.path.append(hcd_path+'/workflow')
  sys.path.append(hcd_path)
  print('Plugin routine hcd_jintrac_interface called, HCD path set as:',hcd_path)

  # SET HCD DIRECTORY AS WORKING DIRECTORY
  jintrac_path = os.path.abspath(os.getcwd())
  os.chdir(hcd_path)
  
  from pyal import ALEnv
  from hcd_workflow  import hcd_workflow
  from lxml import etree
  import xml.etree.ElementTree as ET
  from developer_file import load_code_dependencies
  from check_for_dependencies import check_for_dependencies
  from bundle_copy import bundle_copy
  import numpy as np

  # IMPORT PARAMETERS FROM THE XML PARAMETER FILE OF THE WORKFLOW  
  par_path = hcd_xml_path
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

  list_of_actors = []

  for elem in root[2].iter():
      if elem.tag is not etree.Comment and len(elem)== 0:
          if int(elem.text) is not 0:
               list_of_actors.append(elem.attrib['list'].split()[int(elem.text)-1])
          
  if len(list_of_actors) == 0:
     print('ERROR: no actors selected --> Heating & Current Drive workflow will not be executed')
     return

  # CHECK IF THE CODES ARE COMPATIBLE / DEPENDENCIES ARE FULFILLED
  dependencies = load_code_dependencies()
  check_for_dependencies(root, dependencies)

  print('---- Call H&C workflow ----')
  
  ########################################################################
  #-----------------------------------------------------------------------
  #                  CALL HCD WORKFLOW
  #-----------------------------------------------------------------------
  ########################################################################

  timenow = ids_bundle_input['core_profiles'].time

  print('---------------------------------------------')
  print('Time =', timenow, 's')
#  print('dt   =', param['dt_required'], 's') #not used for now

  # COPY INPUT BUNDLE TO OUTPUT BUNDLE
  ids_bundle_output = bundle_copy(ids_bundle_input)

  # ARTIFICIALLY REMOVE WARNINGS
  warning_list = ['distribution_sources','distributions','ec_launchers','ic_antennas','nbi','wall']
  for ids in warning_list:
      if ids in ids_bundle_output:
          ids_bundle_output[ids].ids_properties.homogeneous_time = 1
          ids_bundle_output[ids].time = ids_bundle_output['core_profiles'].time

  print('Execute H&CD workflow for current time slice')
  ids_bundle_output = hcd_workflow(ids_bundle_output, param)

  # SWITCH BACK TO JINTRAC WORKING DIRECTORY
  os.chdir(jintrac_path)


  print('---------------------------------------------')
  print('End of H&CD workflow.')      
  print('---------------------')

  return ids_bundle_output

