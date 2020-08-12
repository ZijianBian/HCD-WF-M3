# Load necessary modules
import os, sys, yaml, inspect, imas
from importlib import import_module
from inspect import getmodule,stack
from lxml import etree
from subprocess import Popen, PIPE

# Private function to inspect the full path of the function
def __foo():
  pass

#####################################################################################

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
    elif listname=='empty_actor_list':
        output_list = data['empty_actor_list'].split(' ')
    elif listname=='dependencies':
        output_list = data['dependencies']
    elif listname=='extra_arguments':
        output_list = data['extra_arguments']
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

def create_dict_from_idslist(idslist,imas_object):

    imas_dict = {}
    for ids in idslist:
        imas_dict[ids] = eval('imas_object.'+ids)

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
# ------------------------------------------------------------
# Output argument:
# - output_bundle: output copied bundle
# ------------------------------------------------------------

def bundle_copy(input_bundle,idslist=None):

    # OPTIONALLY RESTRICT THE LIST OF IDSS TO BE COPIED
    # IF NO LIST IS SPECIFIED: USE THE FULL LIST OF THE INITIAL BUNDLE
    if idslist == None:
        idslist = input_bundle.keys()

    # EMPTY IMAS STRUCTURE
    output_imas = imas.ids(0,0)
    
    # EMPTY OUTPUT BUNDLE (DICTIONARY)
    output_bundle = dict()

    # LOOP OVER IDSS OF THE BUNDLE TO COPY
    for key in input_bundle.keys():

        # ONLY COPY THE IDSS WE ARE INTERESTED IN
        if key in idslist:

            # IDS TO COPY
            ids = input_bundle[key]

            # COPY THE IDS INTO THE EMPTY IMAS STRUCTURE
            eval('output_imas.'+key+'.copyValues(ids)')

            # USE THIS STRUCTURE TO FILL THE DICTIONARY OF THE OUTPUT BUNDLE
            output_bundle[key] = eval('output_imas.'+key)

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
def create_maindict(workflow_parameters,input_option,verbose):

    # MEMO: STRUCTURE OF THE INPUT XML FILE
    # ROOT.ITER() = LOOP OVER ALL ELEMENTS OF THE INPUT XML FILE
    # ROOT[0] = workflow_parameters
    # ROOT[1] = further_settings
    # ROOT[2] = actor_selection

    # READ THE ACTOR_SELECTION STRUCTURE FROM THE WORKFLOW INPUT XML FILE
    tree = etree.parse(workflow_parameters)
    root = tree.getroot()
    actor_selection = root[2]

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
                            list_actor.append({'name':actor_name, 'input':input_ids_list, 'output':output_ids_list, 'system':system.tag})
                        else:
                            list_actor.append({'name':actor_name, 'input':input_arg_list, 'output':output_ids_list, 'system':system.tag})
                    # Prepend empty_* code
                    list_actor.insert(0,{'name':'empty_'+output_ids_list[0], 'input':['core_profiles'], 'output':[output_ids_list[0]], 'system':system.tag})
                    if category.text is not '0':
                      code_selection[category.tag] = category.attrib['list'].split(' ')\
                                                     [int(category.text)-1]
                    else:
                      code_selection[category.tag] = None
                    dict_category[category.tag] = list_actor
            dict_system[system.tag] = dict_category
        maindict[main_key.tag] = dict_system

    # Remove duplicates
    compiled_list     = list( dict.fromkeys(compiled_list) )
    not_compiled_list = list( dict.fromkeys(not_compiled_list) )

    return(maindict,compiled_list,not_compiled_list,code_selection)

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
# Check whether the dependencies are fulfilled in the actual actor section
# -------------------------------------------------------------------------

def check_for_dependencies(workflow_xml):

    def check_if_code_fulfills_configuration(dependencies, entry, code_selection):
        err = 0
        code = code_selection[entry]
        if dependencies[entry] == 'None':
          dependencies[entry] = None
        if dependencies[entry] is not None and code in dependencies[entry]:                 
          fulfills_all_dependencies = [1] * (len(dependencies[entry][code]))
          for dep in [dependencies[entry][code]]:
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
    (maindict, compiled_actors, uncompiled_actors, code_selection) = create_maindict(workflow_xml,1,0)

    # LOAD THE LIST OF DEPENDENCIES BETWEEN THE CODES
    dependencies = loadlist('dependencies')

    # FOR EACH OF THE SELECTED ACTORS, CHECK THAT DEPENDENCY RULES ARE FULFILLED
    global_error = 0
    for entry in code_selection:
        if code_selection is not None:
            err = check_if_code_fulfills_configuration(dependencies, entry, code_selection)
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

def create_workflow_param_from_file(filepath,option):
    tree = etree.parse(filepath)
    root = tree.getroot()

    name0 = root[0].attrib['display']
    name1 = root[1].attrib['display']
    name2 = root[2].attrib['display']

    # With the 3-tree structure of the input xml file
    if option == 1:
        workflow_param = {name0: {}, name1: {}, name2: {}}
        for elem in root[0].iter():
            if len(elem) == 0 and elem.tag is not etree.Comment:
                workflow_param[name0][elem.tag] = elem.text
        for elem in root[1].iter():
            if len(elem) == 0 and elem.tag is not etree.Comment:
                workflow_param[name1][elem.tag] = elem.text     
        for elem in root[2].iter():
            if len(elem) == 0 and elem.tag is not etree.Comment:
                workflow_param[name2][elem.tag] = elem.text

    # Without the 3-tree structure of the input xml file
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
    workflow_param['ic_wave_nr_toroidal_modes'] = 1
    workflow_param['fokker_flag'] = 0

    # FOLDER WHERE THE INPUT XML FILE IS LOCATED
    workflow_param['input_path'] = '/'.join(filepath.split('/')[:-1])

    return(workflow_param)

#####################################################################################

# -------------------
# Merge dictionaries
# -------------------
def dict_merge(dict1, dict2): 
  res = {**dict1, **dict2} 
  return res 

