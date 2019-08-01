def code_information(list_of_actors):


    actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')


    inoutdict = {}
    ids_list = ['core_profiles','core_sourcres','equilibrium', 'pulse_schedule', 'nbi', 'ic_antennas', 'ec_antennas','wall', 'distribution_sources', 'distributions', 'waves']

    for name in list_of_actors:

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

        inoutdict[name] = [in_l, out_l]

    tree = etree.parse('input_workflow_default.xml')
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
                            dict1[icode] = inoutdict[icode]
                    dict2[icat.tag] = [dict1, icat.text]
            dict3[isys.tag] = dict2
        maindict[step.tag] = dict3

    return maindict
