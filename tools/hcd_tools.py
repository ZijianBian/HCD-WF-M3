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

# ---------------------------------------------------------------------------------
# Function used in import_actor, to add the actor folder to the path and import it
# ---------------------------------------------------------------------------------
def __syspath_import_actor(actor_folder,actor_name,verbose):

    actor_function=[]
    error = 0

    # Folder where the actor is located
    actor_folder_name = actor_folder+"/"+actor_name
    if not os.path.isdir(actor_folder_name):
        if verbose == 1:
            print('Actor '+actor_name+' not found.')
        error = 1
        return actor_function,error
    version = [f for f in os.listdir(actor_folder_name) \
        if os.path.isdir(os.path.join(actor_folder_name,f))][0]

    # Determine the actor location
    # 1) Actors with version number
    if os.path.isfile(actor_folder_name+'/'+version+'/'+actor_name+'/'+'wrapper.py'): 
        actor_location = actor_folder_name+'/'+version+'/'+actor_name
        sys.path.insert(0,actor_folder_name+'/'+version)
    # 2) Actors without version number
    else:
        actor_location = actor_folder_name+'/'+actor_name
        sys.path.insert(0,actor_folder_name)

    # Import the actor and save its location
    actor_function = getattr(import_module(actor_name+'.wrapper'),actor_name+'_actor')
    actor_function.location = actor_location

    return actor_function,error

#####################################################################################

# -----------------------------
# Function to import an actor
# -----------------------------
def import_actor(actor_input,verbose):

    error=0

    # Check if ACTOR_FOLDER is defined
    ACTOR_FOLDER = os.environ.get('ACTOR_FOLDER')
    if ACTOR_FOLDER is None:
        if type(actor_input) is str:
            print('$ACTOR_FOLDER not defined --> '+actor_input+' not loaded.')
        else:
            print('$ACTOR_FOLDER not defined --> '+', '.join(actor_input)+' not loaded.')
        return

    # Import the actor(s) and put into a dictionary
    dictactor = {}
    if type(actor_input) is str:
        dictactor[actor_input],error = __syspath_import_actor(ACTOR_FOLDER,actor_input,verbose)
    else:
        for actor_name in actor_input:
            dictactor[actor_name],err = __syspath_import_actor(ACTOR_FOLDER,actor_name,verbose)
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
    else:
        print('Error: bad listname in loadlist()')
        output_list=[]

    return output_list

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
        parstr = globals()[name].__doc__

        for elem in parstr.split('\n'):

            for iids in ids_list:
                if elem.find(':param '+iids) is not -1:
                    input_ids_list.append(iids)
                    input_arg_list.append(iids)
                    break
                elif elem.find('integ') is not -1:
                    input_arg_list.append('add_arg')
                    break
                elif elem.find('doub') is not -1:
                    input_arg_list.append('add_arg')
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
    # - KEYS ARE ACTOR NAMES
    # - VALUES ARE INPUT/OUTPUT IDSS
    # --------------------------------------------------------------------------------------------
    code_selection = {}
    compiled_list = []
    not_compiled_list = []
    maindict = {}
    for main_key in actor_selection:
        dict_system = {}
        for system in main_key:
            dict_category = {}
            for category in system:
                dict_actor = {}
                if category.tag is not etree.Comment:
                    for actor_name in category.attrib['list'].split():
                        (input_ids_list, input_arg_list, output_ids_list, err) = \
                            read_actor_ids(actor_name,verbose)
                        if err == 0:
                            compiled_list.append(actor_name)
                        else:
                            not_compiled_list.append(actor_name)
                        if input_option==1:
                            dict_actor[actor_name] = [input_ids_list, output_ids_list]
                        else:
                            dict_actor[actor_name] = [input_arg_list, output_ids_list]
                    if category.text is not '0':
                      code_selection[category.tag] = category.attrib['list'].split(' ')[int(category.text)-1]
                    else:
                      code_selection[category.tag] = None
                    dict_category[category.tag] = dict_actor
            dict_system[system.tag] = dict_category
        maindict[main_key.tag] = dict_system

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
                    print('ERROR: '+code.upper()+' needs the '+str(dep[i][0]).upper()+' code as '+str(i), \
                          file=sys.stderr)
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
        print('Selection fulfills all actor selection rules', file=sys.stderr)
    else:
        print('Please change the actor selection and try again.', file=sys.stderr)

    return global_error
