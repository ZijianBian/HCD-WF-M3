import sys, os
from hcd_tools import import_actor, loadlist, is_compiled_for_mpi, read_actor_ids, create_workflow_param_from_file, create_maindict
from utility_functions import gen_dict_extract
from lxml import etree

# CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
# (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
hcd_path = '/'.join(os.path.realpath(__file__).split('/')[:-2])
workflow_xml = hcd_path+'/global_configuration/input_workflow_default.xml'
(maindict, compiled_actors, uncompiled_actors, code_selection) = \
    create_maindict(workflow_xml,2,0)

# LIST OF EMPTY ACTORS AND OF EXTRA (NON-IDS) ARGUMENTS FOR EACH ACTOR
empty_actor_list    = loadlist('empty_actor_list')
merge_actor_list    = loadlist('merge_actor_list')
extra_argument_list = loadlist('extra_arguments')

#print(maindict)
#print(compiled_actors)
#print(empty_actor_list)
#print(merge_actor_list)
#print(extra_argument_list)

list_of_actors = compiled_actors+empty_actor_list+merge_actor_list
for name in list_of_actors:
    err = import_actor(name,0)

#print(list_of_actors)

def run(cat, bundle, parameters):
    # Get list of all codes in that category
    catlist = next(gen_dict_extract(cat,maindict))
    #print(catlist)
    codeinfo = catlist[parameters[cat]]
    #print(codeinfo['name'])
    #print(codeinfo['input'])
    #print(codeinfo['output'])
    inputids = [bundle[ids] for ids in codeinfo['input']]
    # Call of the chosen code
    return globals()[codeinfo['name']](*inputids)

#parameters = create_workflow_param_from_file(workflow_xml,2)

#print(parameters)
#catlist = next(gen_dict_extract('ec_wave_solver',maindict))
#print(catlist)
#print(parameters['ec_wave_solver'])
#print(catlist[parameters['ec_wave_solver']])
#bundle = None
#run_actors('ec_wave_solver',None,parameters)
