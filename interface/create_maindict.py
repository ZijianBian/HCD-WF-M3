import os, imas, sys
sys.path.append('interface')
sys.path.append('workflow')
sys.path.append(os.getcwd())
from lxml import etree
from import_actor import import_actor
from loadlist import loadlist

def create_maindict(default_workflow_parameters):
    #---------------------------------------------------------------------------------------------
    # CREATE A PYTHON DIRECTORY (MAINDICT) THAT CONTAINS THE NAME OF ALL CODES (NEMO, BBNBI, ...) , 
    # THEIR INPUT & OUTPUT IDSS, THEIR CATEGORY (EC_WAVESOLVER, NBI_SOURCE, ..), 
    # THE HEATING SYSTEM THEY BELONG TO (EC, IC, NBI, ALPHA)
    #---------------------------------------------------------------------------------------------

    ids_list = loadlist('ids_list')

    not_compiled_list = []

    def read_inputoutput(name):
        in_l  = []
        out_l = []
        err = import_actor(name)
        if err == 0:
            parstr = globals()[name].__doc__
            for iids in ids_list:
                if parstr.find(':param '+iids) is not -1:
                    in_l.append(iids)
                if parstr.find(':param result: '+iids) is not -1:
                    out_l.append(iids)
        else:
            not_compiled_list.append(name)
        return(in_l, out_l)

    tree = etree.parse(default_workflow_parameters)
    root = tree.getroot()

    maindict = {}
    for step in root[2]:
        dict3 = {}
        for isys in step:
            dict2 = {}
            for icat in isys:
                dict1 = {}
                if icat.tag is not etree.Comment:
                    for icode in icat.attrib['list'].split():
                        (in_l, out_l) = read_inputoutput(icode)
                        dict1[icode] = [in_l, out_l]
                    dict2[icat.tag] = dict1
            dict3[isys.tag] = dict2
        maindict[step.tag] = dict3

    return(maindict,not_compiled_list)
