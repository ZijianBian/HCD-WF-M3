import os, imas, sys
sys.path.append('interface')
sys.path.append('workflow')
sys.path.append(os.getcwd())
from lxml import etree

def create_maindict(default_workflow_parameters):
    #---------------------------------------------------------------------------------------------
    ##  create a python directory (maindict) that contains the name of all codes (nemo, bbnbi, ...) , their in & output IDSs, their category (ec_wavesolver, nbi_source, ..) the heating system they belong to (EC, IC, NBI, alpha)

    actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')

    ids_list = ['core_profiles','core_sourcres','equilibrium', 'pulse_schedule', 'nbi', 'ic_antennas', 'ec_antennas','wall', 'distribution_sources', 'distributions', 'waves']

    def read_inputoutput(name):

        in_l = []
        out_l = []
        try:
            sys.path[:0] = [os.path.join(actor_path,name)]
            globals()[name] = getattr(__import__(name), name)

            parstr = globals()[name].__doc__

            for iids in ids_list:
                if parstr.find(':param '+iids) is not -1:
                    in_l.append(iids)
                if parstr.find(':param result: '+iids) is not -1:
                    out_l.append(iids)
        except:
            print(name, 'not compiled')

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


    return(maindict, actor_path)
