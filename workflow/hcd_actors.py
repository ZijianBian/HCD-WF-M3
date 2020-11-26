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
    inputargs = []
    extra_arg_nr = 0
    inputxml = []
    for i in codeinfo['input']:
        if i.find('extra_argument_list') is not -1 \
           and extra_argument_list.get(code) is not None:
            inputargs.append(parameters[extra_argument_list[code][extra_arg_nr]])
            extra_arg_nr += 1
        elif i.find('codeparam') is not -1:
            inputxml.append(parameters['input_path']+'/'+ \
                              codeinfo['system']+'/input_'+code+'.xml')
        else:
            inputargs.append(bundle[i])


    inputmpi = []
    libmpi_path = eval(code+'.location')+'/native_wrapper/lib/lib'\
                  +code+'.so'
    args_np = {}
    if is_compiled_for_mpi(libmpi_path, 'libmpi'):
        if cat == 'nbi_fp':
            args_np = {'mpi_processes':parameters["nproc_ion_fp"]}
        inputmpi.append('mpi_local') # FOR NON-FP CODES, DEFAULT IS NPROC=4

    inputs = inputargs + inputxml + inputmpi
    # Call of the chosen code
    return globals()[code](*inputs, **args_np)

def run_step(name,bundle_in,parameters):

    from hcd_tools import bundle_copy

    bundle_out = bundle_copy(bundle_in)

    if name == 'nbi_source':
        bundle_out['distribution_sources'] = actors.run(name,bundle_in,parameters)

    if name == 'ic_coup':
        bundle_out['waves'] = actors.run('ic_coup',bundle_in,parameters)

    if name == 'ic_wave_solver':
        bundle_out['waves'] = actors.run('ic_wave_solver',bundle_in,parameters)

    if name == 'ec_wave_solver':
        bundle_out['waves'] = actors.run('ec_wave_solver',bundle_in,parameters)

    if name == 'nuclear_source':
        bundle_out['distribution_sources'] = actors.run('nuclear_source',bundle_in,parameters)

    if name == 'ic_wave_fp':
        bundle_out['distributions'] = actors.run('ic_wave_fp',bundle_in,parameters)

    if name == 'nbi_fp':
        bundle_out['distributions'] = actors.run('nbi_fp',bundle_in,parameters)

    if name == 'nuclear_fp':
        bundle_out['distributions'] = actors.run('nuclear_fp',bundle_in,parameters)

    if name == 'merge_distributions':
        bundle_out['distributions'] = actors.merge_distributions(bundle_in['distributions'],bundle_in['distributions'])
        bundle_out['distributions'] = actors.merge_distributions(bundle_in['distributions'],distrib_nbi_ic)

    if name == 'merge_waves':
        bundle_out['waves'] = actors.merge_waves(bundle_in['waves'],bundle_in['waves'])

    if name == 'merge_distribution_sources':
        bundle_out['distribution_sources'] = actors.merge_distribution_sources(bundle_in['distribution_sources'],bundle_in['distribution_sources'])

    if name == 'fill_core_sources':
        bundle_out['core_sources']  = actors.run('fill_core_sources',bundle_in,parameters)

    if name == 'fill_core_profiles':
        bundle_out['core_profiles'] = actors.run('fill_core_profiles',bundle_in,parameters)


