import copy
from multiprocessing import Pool
import os
import sys
from time import time

from lxml import etree

from tools.hcd_tools import (
    is_nbi_on,
    is_ec_on,
    is_ic_on,
)
from wf_tools import (
    bundle_copy,
    create_workflow_param_from_file,
    import_actor,
    loadlist,
    create_maindict,
    clever_algo,
)

from tools.stdout_redirector import redirect_stdout, stdout_back

# -------------------------------------------------------------------------------------------------

# CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
# (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
hcd_path = '/'.join(os.path.realpath(__file__).split('/')[:-2])
workflow_xml = hcd_path + '/global_configuration/input_workflow_default.xml'
(
    maindict,
    compiled_actors,
    uncompiled_actors,
    code_selection,
    catdict,
) = create_maindict(workflow_xml, 0)

def run(process, actor, bundle, parameters):

    # For merge, bundle is a list of 2 bundles and the call is simpler
    if type(bundle) is list:
        return globals()[process](bundle[0], bundle[1])

    # Get list of all codes in that category
    codeslist = catdict[process]  # next(gen_dict_extract(process,maindict))
    codeinfo = codeslist[parameters[process]]
    code = codeinfo['name']

    # Re-direct the logfile for this specific actor
    if code + '_log' in parameters.keys():
        stdout_redirect = parameters[code + '_log']
        oldstrout, newstdout = redirect_stdout(stdout_redirect)

    inputargs = []
    for i in codeinfo['input']:
        inputargs.append(bundle[i])

    results = actor(*inputargs)

    # Re-direct the logfile for this specific actor
    if code + '_log' in parameters.keys():
        stdout_back(oldstrout, newstdout)

    # Call of the chosen code
    return results


# -------------------------------------------------------------------------------------------------

def hcd_workflow(process_bundle, workflow_xml, dictionary_of_actors):

    print('Execute H&CD workflow for current time slice', file=sys.stdout)

    # YAML FILE CONTAINING ALL USEFUL LISTS
    file = os.path.dirname(os.path.abspath(__file__))\
        + '/../global_configuration/' + 'global_lists.yaml'
    
    # EXTRACT ACTOR SELECTION PARAMETERS FROM INPUT XML FILE
    parameters = create_workflow_param_from_file(workflow_xml)['actor_selection'][0]

    # CREATE PARAMETERS DICTIONARY WITH DIRECTLY EACH PROCESS AS KEY
    param_process = {}
    for main_key in parameters:
        for category in parameters[main_key][0]:
            for process in parameters[main_key][0][category][0]:
                param_process[process] = parameters[main_key][0][category][0][process][0]

    # IF AN H&CD SOURCE IS CONFIGURED BUT IT HAS NO POWER FOR THIS TIME SLICE,
    # DO NOT RUN THE CODE(S) FOR THIS SOURCE
    for process in  process_bundle.keys():

        if 'nbi' in process_bundle[process]['input'] \
           and not is_nbi_on(process_bundle[process]['input']['nbi'], \
                             process_bundle[process]['input']['core_profiles'].time):
            print('  No NBI power for this time slice')
            param_process['nbi_source'] = 0
            param_process['nbi_fp'] = 0

        if 'ic_antennas' in process_bundle[process]['input'] \
           and not is_ic_on(process_bundle[process]['input']['ic_antennas'], \
                            process_bundle[process]['input']['core_profiles'].time):
            print('  No IC power for this time slice')
            param_process['ic_coup'] = 0
            param_process['ic_wave_solver'] = 0
            param_process['ic_wave_fp'] = 0

        if 'ec_launchers' in process_bundle[process]['input'] \
          and not is_ec_on(process_bundle[process]['input']['ec_launchers'], \
                           process_bundle[process]['input']['core_profiles'].time):
           print('  No EC power for this time slice')
           param_process['ec_wave_solver'] = 0

    # DEFINE THE SEQUENCE OF CODES TO BE EXECUTED
    if catdict['ic_wave_fp'][param_process['ic_wave_solver']]['name'] != 'fopla':
        print('--- Default algorithm ---')
        input_algorithm = loadlist(file,'algorithm')['default']
    else:
        print('--- NBI+IC synergy algorithm ---')
        input_algorithm = loadlist(file,'algorithm')['nbi_ic_synergy']

    final_algorithm, waiting_for, parallel_runs = clever_algo(
        input_algorithm, param_process, catdict, file
    )

    # print('final_algo',final_algorithm)
    # print(' ')
    # print('waiting_for',waiting_for)
    # print(' ')
    # print('parallel_runs',parallel_runs)

    # EXECUTE THE CODES ACCORDING TO THE REQUESTED SEQUENCE
    bundle_out = {}

    # EXECUTION OF THE WORKFLOW
    for process in final_algorithm:
        actor = dictionary_of_actors[catdict[process][param_process[process]]['name']]
        if not 'merge_' in process:
            print(
                ' PROCESS --> ',
                process,
                '=',
                catdict[process][param_process[process]]['name'].upper(),
            )
            output_ids_list = catdict[process][param_process[process]]['output']
            # REMOVE WARNINGS AND HCD2CORE_SOURCE CRASHS (DOES NOT LIKE RECEIVING EMPTY IDSS)
            for ids in process_bundle[process]['input'].keys(): 
                if process_bundle[process]['input'][ids].ids_properties.homogeneous_time < 1:
                    process_bundle[process]['input'][ids].ids_properties.homogeneous_time = 1
                    process_bundle[process]['input'][ids].time = process_bundle[process]['input']['core_profiles'].time
            output_ids_data = run(process, actor, process_bundle[process]['input'], param_process)
        else:
            kmerge = 0
            ids_to_be_merged = process_bundle[process]['input'][0].__name__
            for each_proc in process_bundle.keys(): # merge only if at least one of involved codes is called
                if ids_to_be_merged in process_bundle[each_proc]['input']:
                    kmerge = 1                
            if kmerge == 1:
                print(' PROCESS -->', process)
                output_ids_data = run(process, actor, process_bundle[process]['input'], param_process)
                del bundle_out[output_ids_list[0]]

        for iids in range(len(output_ids_list)):
            if type(output_ids_data) is not list:
                process_bundle[process]['output'][output_ids_data.__name__] = output_ids_data
            else:
                process_bundle[process]['output'][output_ids_data[iids].__name__] = output_ids_data[iids]

            if output_ids_list[iids] not in bundle_out.keys() or 'merge_' in process:
                if type(output_ids_data) is not list:
                    bundle_out[output_ids_list[iids]] = process_bundle[process]['output'][output_ids_data.__name__]
                else:
                    bundle_out[output_ids_list[iids]] = process_bundle[process]['output'][output_ids_data[iids].__name__]
            else:
                process_bundle['merge_'+output_ids_list[iids]]={}
                process_bundle['merge_'+output_ids_list[iids]]['input']= \
                              [bundle_out[output_ids_list[iids]],output_ids_data]
                process_bundle['merge_'+output_ids_list[iids]]['output']={}
                process_bundle['merge_'+output_ids_list[iids]]['output'][output_ids_list[iids]]={}

        # COPY THE OUTPUT IDS OF THE CURRENT PROCESS TO THE INPUT ONES
        # OF THE DOWNSTREAM DEPENDENT PROCESSES
        parallel_dependency = loadlist(file,'parallel_dependency')
        for stepc in final_algorithm[final_algorithm.index(process)+1:]:
            if process in parallel_dependency[stepc]:
                if stepc in process_bundle: # (merger keys may not exist yet)
                    for idskey,idsvalue in process_bundle[process]['output'].items():
                        if type(process_bundle[stepc]['input']) is not list:
                            process_bundle[stepc]['input'][idskey] = copy.deepcopy(idsvalue)

    print('End of time slice', file=sys.stdout)

    return process_bundle
