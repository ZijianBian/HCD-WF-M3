# Load necessary modules
import os, sys
from importlib import import_module
from inspect import getmodule,stack

# Sub-function to add the actor folder to the path and to import it
def syspath_import_actor(actor_folder,actor_name):

    # Folder where the actor is located
    actor_folder_name = actor_folder+"/"+actor_name
    version = [f for f in os.listdir(actor_folder_name) if os.path.isdir(os.path.join(actor_folder_name,f))][0]

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

    return actor_function

# Function to import an actor
def import_actor(actor_input):

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
        dictactor[actor_input] = syspath_import_actor(ACTOR_FOLDER,actor_input)
    else:
        for actor_name in actor_input:
            dictactor[actor_name] = syspath_import_actor(ACTOR_FOLDER,actor_name)

    # Add this dictionary into the local variables of the calling routine:
    # 1) from interactive sessions, f_locals from current frame is modified
    # 2) when called from a script, the dictionary of the calling module is modified

    # For interactive sessions
    if getmodule(stack()[1].frame) is None:
        stack()[1].frame.f_locals.update(dictactor)
    # When called from a module
    else:
        getmodule(stack()[1].frame).__dict__.update(dictactor)




