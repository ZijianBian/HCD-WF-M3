# Load necessary modules
import os, sys, yaml, inspect, imas, copy
import numpy as np
from importlib import import_module
from inspect import getmodule,stack
from lxml import etree
from subprocess import Popen, PIPE

# Private function to inspect the full path of the function
def __foo():
  pass

#####################################################################################

# Function to find the index of a value in a time array, and the closest array value
def find_nearest(a, a0):
    "Element in nd array `a` closest to the scalar value `a0`"
    idx = np.abs(a - a0).argmin()
    return a.flat[idx],idx

# -----------------------------------------------------
# Function to read the yaml file containing the global
# lists used in many places of the H&CD workflow
# -----------------------------------------------------

# Create lists from the global configuration yaml file
def loadlist(listname):

    path_file = os.path.abspath(inspect.getfile(__foo))
    path = '/'.join(path_file.split('/')[:-1])

    file = open(path+'/../global_configuration/'+'global_lists.yaml', 'r')
    data = yaml.load(file, Loader=yaml.CLoader)

    if listname=='ids_list':
        output_list = data['ids_list'].split(' ')
    elif listname=='actor_list':
        output_list = data['actor_list'].split(' ')
    elif listname=='merge_actor_list':
        output_list = data['merge_actor_list'].split(' ')
    elif listname=='algorithm':
        output_list = data['algorithm']
    elif listname=='prerequisites':
        output_list = data['prerequisites']
    elif listname=='extra_arguments':
        output_list = data['extra_arguments']
    elif listname=='parallel_dependency':
        output_list = data['parallel_dependency']
    elif listname=='exec_types':
        output_list = data['exec_types'].split(' ')
    else:
        print('Error: bad listname in loadlist()', file=sys.stderr)
        output_list=[]

    return output_list

# ---------------------------------------------------------------------------------
# Function used in import_actor, to add the actor folder to the path and import it
# ---------------------------------------------------------------------------------
def __syspath_import_actor(actor_name,verbose):

    from importlib import import_module

    # Import the module of the actor
    try:
      actor_module = import_module(actor_name)
    except:
      if verbose == 1:
        print('Actor '+actor_name.upper()+' not found.', file=sys.stderr)
      return [],1

    # Import the actor function
    actor_function = getattr(import_module(actor_name+'.wrapper'), actor_name+'_actor')

    # Folder where the actor is located
    actor_function.location = '/'.join(getattr(actor_module,'__file__').split('/')[:-1])

    return actor_function,0

#####################################################################################

# -----------------------------
# Function to import an actor
# -----------------------------
def import_actor(actor_input,verbose):

    error=0

    # Import the actor(s) and put into a dictionary
    dictactor = {}
    if type(actor_input) is str:
        dictactor[actor_input],error = __syspath_import_actor(actor_input,verbose)
    else:
        for actor_name in actor_input:
            dictactor[actor_name],err = __syspath_import_actor(actor_name,verbose)
            if err==1:
                error=1

    # Add this dictionary into the local variables of the calling routine:
    # 1) from interactive sessions, f_locals from current frame is modified
    # 2) when called from a script, the dictionary of the calling module is modified

    # For interactive sessions
    if getmodule(stack()[1].frame) is None:
        stack()[1].frame.f_locals.update(dictactor)
    # When called from a module
    else:
        getmodule(stack()[1].frame).__dict__.update(dictactor)

    return error

#####################################################################################

# ------------------------------------------------
# Create dictionary from IDS list and IMAS object
# ------------------------------------------------

def create_dict_from_idslist(idslist):

    imas_dict = {}
    for ids in idslist:
        imas_dict[ids] = eval('imas.'+ids+'()')

    return imas_dict

#####################################################################################

# ------------------------------------------------------------
# Function to copy a bundle of idss
# Note: a bundle is here defined as a set of IDSs assembled 
#       into a dictionary
# ------------------------------------------------------------
# Input arguments:
# - input_bundle: initial bundle to copy
# - idslist (optional): restricted list of idss to copy from
#   the initial bundle
# - origin_bundle (optional): existing bundle to which we 
#   want to copy the initial bundle
# ------------------------------------------------------------
# Output argument:
# - output_bundle: output copied bundle
# ------------------------------------------------------------

def bundle_copy(input_bundle,idslist=None,origin_bundle=None):

    # OPTIONALLY RESTRICT THE LIST OF IDSS TO BE COPIED
    # IF NO LIST IS SPECIFIED: USE THE FULL LIST OF THE INITIAL BUNDLE
    if idslist == None:
        idslist = input_bundle.keys()

    # COPY THE BUNDLE, IDS PER IDS
    if origin_bundle == None:
      output_bundle = dict()
    else:
      output_bundle = origin_bundle

    for key in input_bundle.keys():
        if key in idslist:
            output_bundle[key] = copy.deepcopy(input_bundle[key])

    return output_bundle

#####################################################################################

# ---------------------------------------------------------------------
# Returns the input IDSs, input arguments, and output IDSs of an actor
# ---------------------------------------------------------------------

def read_actor_ids(name,verbose):
    ids_list = loadlist('ids_list')
    input_ids_list  = []
    input_arg_list  = []
    output_ids_list = []
    err = import_actor(name,verbose)
    if err == 0:
        parstr = eval(name+'.__doc__')

        for elem in parstr.split('\n'):

            for iids in ids_list:
                if elem.find(':param '+iids) is not -1:
                    input_ids_list.append(iids)
                    input_arg_list.append(iids)
                    break
                elif elem.find('integ') is not -1:
                    input_arg_list.append('extra_argument_list')
                    break
                elif elem.find('doub') is not -1:
                    input_arg_list.append('extra_argument_list')
                    break
                elif elem.find('codeparam') is not -1:
                    input_arg_list.append('codeparam')
                    break
                elif elem.find(':param result: ') is not -1 \
                     and elem.find(iids) is not -1:
                    output_ids_list.append(iids)

    return(input_ids_list,input_arg_list,output_ids_list,err)

#####################################################################################

#---------------------------------------------------------------------------------
# Create a python dictionary (maindict) that contains the name of all H&CD codes,
# their input & output IDSs, their category (ec_wavesolver, nbi_source, ..), 
# and the H&CD system they belong to (EC, IC, NBI, nuclear)
#---------------------------------------------------------------------------------
def create_maindict(workflow_parameters_path,input_option,verbose):

    # MEMO: STRUCTURE OF THE INPUT XML FILE
    # ROOT.ITER() = LOOP OVER ALL ELEMENTS OF THE INPUT XML FILE
    # ROOT[0] = workflow_parameters_path
    # ROOT[1] = actor_selection

    # READ THE ACTOR_SELECTION STRUCTURE FROM THE WORKFLOW INPUT XML FILE
    tree = etree.parse(workflow_parameters_path)
    root = tree.getroot()
    actor_selection = root[1]

    # --------------------------------------------------------------------------------------------
    # MAINDICT CONTAINS 2 MAIN KEYS:
    # - SYSTEMS      --> 4 SYSTEMS: ECRH, ICRH, NBI, NUCLEAR              --> CATEGORIES: 
    #                                                                         EC_WAVE_SOLVER, ETC.
    # - POST_PROCESS --> 2 SYSTEMS: FILL_CORE_SOURCES, FILL_CORE_PROFILES --> CATEGORIES: 
    #                                                                         SOURCE, PROFILES
    # --------------------------------------------------------------------------------------------
    # INSIDE EACH CATEGORY (EC_WAVE_SOLVER, IC_WAVE_SOLVER, IC_WAVE_FP, ...):
    # - LIST OF CODES, EACH BEING DESCRIBED BY A DICTIONARY CONTAINING NAME, INPUT and OUTPUT, 
    #   INCLUDING THE EMPTY GENERATOR (ORDER IN THE LIST CORRESPONDS TO XML ORDER)
    # --------------------------------------------------------------------------------------------
    code_selection = {}
    compiled_list = []
    not_compiled_list = []
    maindict = {}
    catdict = {}

    # DISPLAY FOR TEST PURPOSES
    #for main_key in actor_selection:
    #    print('main_key',main_key)
    #    for system in main_key:
    #        print('  system',system)
    #        for category in system:
    #            print('    category',category)
    #            if category.tag is not etree.Comment:
    #                for actor_name in category.attrib['list'].split():
    #                    print('     actor_name',actor_name)

    for main_key in actor_selection:
        dict_system = {}
        for system in main_key:
            dict_category = {}
            for category in system:
                list_actor = []
                dict_actor = {}
                if category.tag is not etree.Comment:
                    for actor_name in category.attrib['list'].split():
                        if actor_name in not_compiled_list:
                          verbose_eff = 0
                        else:
                          verbose_eff = verbose
                          (input_ids_list, input_arg_list, output_ids_list, err) = \
                            read_actor_ids(actor_name,verbose_eff)
                        if err == 0:
                            compiled_list.append(actor_name)
                        else:
                            not_compiled_list.append(actor_name)
                        if input_option==1:
                            dict_actor[actor_name] = [input_ids_list, output_ids_list]                           
                            list_actor.append({'name':actor_name, 'input':input_ids_list, 'output':output_ids_list, 'system':system.tag})
                        else:
                            dict_actor[actor_name] = [input_arg_list, output_ids_list]
                            list_actor.append({'name':actor_name, 'input':input_arg_list, 'output':output_ids_list, 'system':system.tag})
                    # Prepend empty_* code
                    list_actor.insert(0,{'name':'empty_'+output_ids_list[0], 'input':['core_profiles'], 'output':[output_ids_list[0]], 'system':system.tag})
                    if category.text is not '0':
                      code_selection[category.tag] = category.attrib['list'].split(' ')\
                                                     [int(category.text)-1]
                    else:
                      code_selection[category.tag] = None
                    dict_category[category.tag] = dict_actor
                    catdict[category.tag] = list_actor
            dict_system[system.tag] = dict_category
        maindict[main_key.tag] = dict_system

    # Remove duplicates
    compiled_list     = list( dict.fromkeys(compiled_list) )
    not_compiled_list = list( dict.fromkeys(not_compiled_list) )

    return(maindict,compiled_list,not_compiled_list,code_selection,catdict)

#####################################################################################

# ------------------------------------------------------------------------
# Set of functions to check if an actor has been compiled with MPI or not
# ------------------------------------------------------------------------
def __get_result(p):
    stdout = p.communicate()
    for s in stdout:
        if len(s) is not 0:
            res = True
        elif len(s) is 0:
            res = False
        break
    return(res)
        
def __run_cmd(cmd):
    p = Popen(cmd, shell = True, stdout = PIPE)
    p.wait()
    return __get_result(p)

def is_compiled_for_mpi(file_path, grep_str):
    cmd = 'ldd '+file_path + '| grep '+grep_str
    return(__run_cmd(cmd))

#####################################################################################

# -------------------------------------------------------------------------
# Check whether the prerequisites are fulfilled in the actual actor section
# -------------------------------------------------------------------------

def check_for_prerequisites(workflow_xml):

    def check_if_code_fulfills_configuration(prerequisites, entry, code_selection):
        err = 0
        code = code_selection[entry]
        if prerequisites[entry] == 'None':
          prerequisites[entry] = None
        if prerequisites[entry] is not None and code in prerequisites[entry]:                 
          fulfills_all_prerequisites = [1] * (len(prerequisites[entry][code]))
          for dep in [prerequisites[entry][code]]:
            for i in dep.keys():
              if 'any'in str(dep[i]) and code_selection[i] is not None:
                pass
              elif str(dep[i]).find(str(code_selection[i]))is not -1:
                pass
              else:
                if str(dep[i]) == 'any':
                  print('ERROR: '+code.upper()+' needs any code as '+str(i), file=sys.stderr)
                else:
                  if len(dep[i]) < 2:
                    print('ERROR: '+code.upper()+' needs the '+str(dep[i][0]).upper()\
                          +' code as '+str(i),file=sys.stderr)
                  else:
                    print('ERROR: '+code.upper()+' needs the '+ \
                          ' or '.join(dep[i]).upper().replace('OR','or') \
                          +' codes as '+str(i),file=sys.stderr)
                err = 1
        return err

    # FIND THE ACTUAL ACTOR SELECTION
    (maindict, compiled_actors, uncompiled_actors, code_selection, catdict) = create_maindict(workflow_xml,1,0)

    # LOAD THE LIST OF PREREQUISITES BETWEEN THE CODES
    prerequisites = loadlist('prerequisites')

    # FOR EACH OF THE SELECTED ACTORS, CHECK THAT DEPENDENCY RULES ARE FULFILLED
    global_error = 0
    for entry in code_selection:
        if code_selection is not None:
            err = check_if_code_fulfills_configuration(prerequisites, entry, code_selection)
            global_error = global_error + err

    if global_error == 0:
        print('Selection fulfills all actor selection rules', file=sys.stdout)
    else:
        print('Please change the actor selection and try again.', file=sys.stderr)

    return global_error

#####################################################################################

# ------------------------------------------------------------------------
# Create the workflow parameter structure from the workflow input xml file
# ------------------------------------------------------------------------

def create_workflow_param_from_file(workflow_parameters_path,option):
    tree = etree.parse(workflow_parameters_path)
    root = tree.getroot()

    # With the 2-tree structure of the input xml file
    if option == 1:
        workflow_param = {}
        for iroot in range(2):
          workflow_param[root[iroot].attrib['display']] = {}
          for elem in root[iroot].iter():
            if len(elem) == 0 and elem.tag is not etree.Comment:
              workflow_param[root[iroot].attrib['display']][elem.tag] = elem.text

    # Without the 2-tree structure of the input xml file
    else:
        workflow_param = {}
        for elem in root.iter():
          if len(elem) == 0 and elem.tag is not etree.Comment:
            try:
              workflow_param[elem.tag] = int(elem.text)
            except:
              try:
                workflow_param[elem.tag] = float(elem.text)
              except:
                workflow_param[elem.tag] = elem.text

    # HARDCODED UNTIL THESE VARIABLES DISAPPEAR (TO REMOVE THEM FROM THE INTERFACE)
    workflow_param['run_simpletrans'] = 0
    workflow_param['fokker_flag'] = 0

    # FOLDER WHERE THE INPUT XML FILE IS LOCATED
    workflow_param['input_path'] = '/'.join(workflow_parameters_path.split('/')[:-1])

    return(workflow_param)

#####################################################################################

# -------------------
# Merge dictionaries
# -------------------
def dict_merge(dict1, dict2): 
  res = {**dict1, **dict2} 
  return res 

#####################################################################################

# ------------------------------------------------------
# IS THE NBI SYSTEM ON? 
# --> CHECK THE POWER ON ALL UNITS FOR THIS TIME SLICE
# ------------------------------------------------------

def is_nbi_on(nbi,time_slice):
  if len(nbi.time)>0:
      time_array = nbi.time
  else:
      return False
  [tc,it] = find_nearest(time_array,time_slice)
  nunit = len(nbi.unit)
  power = 0.
  if nunit > 0:
      for iunit in range(nunit):
          if nbi.unit[iunit].power_launched.data[it]>0:
              power = power + nbi.unit[iunit].power_launched.data[it]
      if power == 0:
          return False
      else:
          return True
  else:
      return False

#####################################################################################

# ------------------------------------------------------
# IS THE EC SYSTEM ON? 
# --> CHECK THE POWER ON ALL LAUNCHERS FOR THIS TIME SLICE
# ------------------------------------------------------

def is_ec_on(ec_launchers,time_slice):
    if len(ec_launchers.time)>0:
        time_array = ec_launchers.time
    else:
        return False
    [tc,it] = find_nearest(time_array,time_slice)
    nlauncher = len(ec_launchers.launcher)
    power = 0.
    if nlauncher > 0:
        for ilauncher in range(nlauncher):
            if ec_launchers.launcher[ilauncher].power_launched.data[it]>0:
                power = power + ec_launchers.launcher[ilauncher].power_launched.data[it]
        if power == 0:
            return False
        else:
            return True
    else:
        return False

#####################################################################################

# ------------------------------------------------------
# IS THE IC SYSTEM ON? 
# --> CHECK THE POWER ON ALL ANTENNAS FOR THIS TIME SLICE
# ------------------------------------------------------

def is_ic_on(ic_antennas,time_slice):
    if len(ic_antennas.time)>0:
        time_array = ic_antennas.time
    else:
        return False
    [tc,it] = find_nearest(time_array,time_slice)
    nantenna = len(ic_antennas.antenna)
    power = 0.
    if nantenna > 0:
        for iantenna in range(nantenna):
            if ic_antennas.antenna[iantenna].power_launched.data[it]>0:
                power = power + ic_antennas.antenna[iantenna].power_launched.data[it]
        if power == 0:
            return False
        else:
            return True
    else:
        return False

#####################################################################################

# ----------------------------------------------------------
# AUTOMATICALLY ADD THE MERGERS TO THE CHRONOLOGY OF
# CODES TO BE EXECUTED, WHEN THERE ARE TWO SAME OUTPUT IDSS
# ----------------------------------------------------------
def clever_algo(algo_input,parameters,catdict):

  import collections
  from utility_functions import common_elements

  ## ADD MERGERS TO THE FLOW
  output_list = []
  algo_final  = []
  code_list   = []
  for istep in range(len(algo_input)):
      stepmodel = algo_input[istep]
      choice    = parameters[stepmodel]
      for ikey,ivalue in catdict.items():
          if stepmodel == ikey and choice !=0:
              algo_final   = algo_final + [stepmodel]
              output_list  = output_list + ivalue[choice]['output']
              code_list    = code_list   + [ivalue[choice]['name']]
              ids_to_merge = [item for item, count \
                              in collections.Counter(output_list).items() if count > 1]
              if 'waves' in ids_to_merge:
                  algo_final = algo_final + ['merge_waves']
                  code_list  = code_list  + ['merge_waves']
              if 'distributions' in ids_to_merge:
                  algo_final = algo_final + ['merge_distributions']
                  code_list  = code_list  + ['merge_distributions']
              if 'distribution_sources' in ids_to_merge:
                  algo_final = algo_final + ['merge_distribution_sources']
                  code_list  = code_list  + ['merge_distribution_sources']
              seen = set();
              output_list = [x for x in output_list if x not in seen and not seen.add(x)]


  # DEFINE WHEN TO PUT WAITING POINTS WHEN WORKFLOW ACTORS RUN IN PARALLEL
  parallel_dependency_list = loadlist('parallel_dependency')
  previous_occ = dict.fromkeys(algo_final,0)
  waiting_for  = {}
  for istep in range(len(algo_final)):
    steprun = algo_final[istep]
    index = [i for i, x in enumerate(algo_final) if x == steprun][previous_occ[steprun]]
    previous_occ[steprun] = previous_occ[steprun] + 1
    waiting_for[str(istep)] = {}
    waiting_for[str(istep)]['steprun'] = steprun
    if index>0:
        all_possible_dependencies = list(set(common_elements(algo_final[0:index],\
                                  parallel_dependency_list[steprun])))
        reduced_dependencies = copy.deepcopy(all_possible_dependencies)
        for dep in all_possible_dependencies:
          for keystep in waiting_for.keys():
            if 'dependencies' in waiting_for[keystep] and waiting_for[keystep]['dependencies'] is not None:
              # Remove indirect dependencies
              if dep in waiting_for[keystep]['dependencies'] \
                 and not 'merge_' in dep \
                 and waiting_for[keystep]['steprun'] in all_possible_dependencies \
                 and dep in reduced_dependencies:
                reduced_dependencies.remove(dep)
        if len(reduced_dependencies)>0:
          waiting_for[str(istep)]['dependencies'] = reduced_dependencies
        else:
          waiting_for[str(istep)]['dependencies'] = None
    else:
        waiting_for[str(istep)]['dependencies'] = None

  # COMPUTE THE LIST OF STEPS OF CODES THAT CAN RUN IN PARALLEL
  parallel_runs = {}
  parallel_step = 0
  for key in waiting_for.keys():
      if parallel_step not in parallel_runs.keys():
          parallel_runs[parallel_step] = [waiting_for[key]['steprun']]
      else:
          there_is_a_dependency = False
          if waiting_for[key]['dependencies'] is not None:
              for dep in waiting_for[key]['dependencies']:
                  if dep in parallel_runs[parallel_step]:
                      there_is_a_dependency = True
              if there_is_a_dependency:
                  parallel_step = parallel_step + 1
                  parallel_runs[parallel_step] = [waiting_for[key]['steprun']]
              else:
                  parallel_runs[parallel_step] = parallel_runs[parallel_step]+[waiting_for[key]['steprun']]
          else:
              parallel_runs[0] = parallel_runs[0]+[waiting_for[key]['steprun']]

  return algo_final,waiting_for,parallel_runs

