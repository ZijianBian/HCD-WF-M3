import sys, os
from hcd_tools import import_actor, loadlist, is_compiled_for_mpi, read_actor_ids, create_workflow_param_from_file, create_maindict
from utility_functions import gen_dict_extract
from lxml import etree

# CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
# (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
hcd_path = '/'.join(os.path.realpath(__file__).split('/')[:-2])
workflow_xml = hcd_path+'/global_configuration/input_workflow_default.xml'
(maindict, compiled_actors, uncompiled_actors, code_selection, catdict) = \
    create_maindict(workflow_xml,2,0)

# LIST OF EMPTY ACTORS AND OF EXTRA (NON-IDS) ARGUMENTS FOR EACH ACTOR
empty_actor_list    = loadlist('empty_actor_list')
merge_actor_list    = loadlist('merge_actor_list')
extra_argument_list = loadlist('extra_arguments')

list_of_actors = compiled_actors+empty_actor_list+merge_actor_list
for name in list_of_actors:
    err = import_actor(name,0)

def run(cat, bundle, parameters):
    # Get list of all codes in that category
    codeslist = catdict[cat] #next(gen_dict_extract(cat,maindict))
    codeinfo = codeslist[parameters[cat]]
    code = codeinfo['name']
    inputids = []
    inputextra = []
    extra_arg_nr = 0
    inputxml = []
    for i in codeinfo['input']:
        if i.find('extra_argument_list') is not -1 \
           and extra_argument_list.get(code) is not None:
            inputextra.append(parameters[extra_argument_list[code][extra_arg_nr]])
            extra_arg_nr += 1
        elif i.find('codeparam') is not -1:
            inputxml.append(parameters['input_path']+'/'+ \
                              codeinfo['system']+'/input_'+code+'.xml')
        else:
            inputids.append(bundle[i])


    inputmpi = []
    libmpi_path = eval(code+'.location')+'/native_wrapper/lib/lib'\
                  +code+'.so'
    if is_compiled_for_mpi(libmpi_path, 'libmpi'):
        if cat == 'nbi_fp':
            inputmpi.append(['mpi_local','mpi_processes='+parameters["nproc_ion_fp"]])
        else:
            inputmpi.append(['mpi_local']) # FOR NON-FP CODES, DEFAULT IS NPROC=4

    inputs = inputids + inputextra + inputxml + inputmpi
    # Call of the chosen code
    return globals()[code](*inputs)

