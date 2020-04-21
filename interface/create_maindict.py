#---------------------------------------------------------------------------------
# CREATE A PYTHON DICTIONARY (MAINDICT) THAT CONTAINS THE NAME OF ALL H&CD CODES,
# THEIR INPUT & OUTPUT IDSS, THEIR CATEGORY (EC_WAVESOLVER, NBI_SOURCE, ..), 
# AND THE H&CD SYSTEM THEY BELONG TO (EC, IC, NBI, ALPHA)
#---------------------------------------------------------------------------------
import os, imas, sys
from lxml import etree
from hcd_tools import import_actor

def create_maindict(default_workflow_parameters):

    def read_inputoutput(name):
        from hcd_tools import loadlist
        ids_list = loadlist('ids_list')
        input_ids_list  = []
        output_ids_list = []
        err = import_actor(name)
        if err == 0:
            parstr = globals()[name].__doc__
            for iids in ids_list:
                if parstr.find(':param '+iids) is not -1:
                    input_ids_list.append(iids)
                if parstr.find(':param result: '+iids) is not -1:
                    output_ids_list.append(iids)
        return(input_ids_list,output_ids_list,err)

    # READ THE ACTOR_SELECTION STRUCTURE OF PARAMETERS FROM THE WORKFLOW INPUT XML FILE
    tree = etree.parse(default_workflow_parameters)
    root = tree.getroot()
    actor_selection = root[2]

    # -------------------------------
    # MAINDICT CONTAINS 2 MAIN KEYS:
    # - SYSTEMS      ---> 4 SYSTEMS: ECRH, ICRH, NBI, NUCLEAR              ---> CATEGORIES: EC_WAVE_SOLVER, ETC.
    # - POST_PROCESS ---> 2 SYSTEMS: FILL_CORE_SOURCES, FILL_CORE_PROFILES ---> CATEGORIES: SOURCE, PROFILES
    # -------------------------------
    # INSIDE EACH CATEGORY (EC_WAVE_SOLVER, IC_WAVE_SOLVER, IC_WAVE_FP, ...):
    # - KEYS ARE ACTOR NAMES
    # - VALUES ARE INPUT/OUTPUT IDSS
    # -------------------------------
    not_compiled_list = []
    maindict = {}
    for sub_structure in actor_selection:
        dict_system = {}
        for system in sub_structure:
            dict_category = {}
            for category in system:
                dict_actor = {}
                if category.tag is not etree.Comment:
                    for actor_name in category.attrib['list'].split():
                        (input_ids_list, output_ids_list, err) = read_inputoutput(actor_name)
                        if err != 0:
                            not_compiled_list.append(actor_name)
                        dict_actor[actor_name] = [input_ids_list, output_ids_list]
                    dict_category[category.tag] = dict_actor
            dict_system[system.tag] = dict_category
        maindict[sub_structure.tag] = dict_system

    return(maindict,not_compiled_list)
