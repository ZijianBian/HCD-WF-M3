# Load necessary modules
import imas, os, sys, yaml, inspect
from importlib import import_module
from inspect import getmodule,stack

#####################################################################################

# -----------------------------------------------------------------------------------------
# Private function used in import_actor, to add the actor folder to the path and import it
# -----------------------------------------------------------------------------------------
def __syspath_import_actor(actor_folder,actor_name):

    actor_function=[]
    error = 0

    # Folder where the actor is located
    actor_folder_name = actor_folder+"/"+actor_name
    if not os.path.isdir(actor_folder_name):
        print('Actor '+actor_name+' not found.')
        error = 1
        return actor_function,error
    version = [f for f in os.listdir(actor_folder_name) \
        if os.path.isdir(os.path.join(actor_folder_name,f))][0]

    # Determine the actor location
    if os.path.isfile(actor_folder_name+'/'+version+'/'+actor_name+'/'+'wrapper.py'): # Actors with version number
        actor_location = actor_folder_name+'/'+version+'/'+actor_name
        sys.path.insert(0,actor_folder_name+'/'+version)
    else: # Actors without version number
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
def import_actor(actor_input):

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
        dictactor[actor_input],error = __syspath_import_actor(ACTOR_FOLDER,actor_input)
    else:
        for actor_name in actor_input:
            dictactor[actor_name],err = __syspath_import_actor(ACTOR_FOLDER,actor_name)
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

# Load necessary modules
import yaml, inspect, os

# Private function to inspect the full path of the function
def __foo():
  pass

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
    else:
        print('Error: bad listname in loadlist()')
        output_list=[]

    return output_list
