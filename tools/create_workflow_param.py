from lxml import etree

def create_workflow_param_from_file(filepath,option):
    tree = etree.parse(filepath)
    root = tree.getroot()

    name0 = root[0].attrib['display']
    name1 = root[1].attrib['display']
    name2 = root[2].attrib['display']

    # With the 3-tree structure of the input xml file
    if option == 1:
        workflow_param = {name0: {}, name1: {}, name2: {}}
        for elem in root[0].iter():
            if len(elem) == 0 and elem.tag is not etree.Comment:
                workflow_param[name0][elem.tag] = elem.text
        for elem in root[1].iter():
            if len(elem) == 0 and elem.tag is not etree.Comment:
                workflow_param[name1][elem.tag] = elem.text     
        for elem in root[2].iter():
            if len(elem) == 0 and elem.tag is not etree.Comment:
                workflow_param[name2][elem.tag] = elem.text

    # Without the 3-tree structure of the input xml file
    else:
        workflow_param = {}
        for elem in root.iter():
          if len(elem) == 0:
            try:
              workflow_param[elem.tag] = int(elem.text)
            except:
              try:
                workflow_param[elem.tag] = float(elem.text)
              except:
                workflow_param[elem.tag] = elem.text

    # HARDCODED UNTIL THESE VARIABLES DISAPPEAR (TO REMOVE THEM FROM THE INTERFACE)
    workflow_param['run_simpletrans'] = 0
    workflow_param['ic_wave_nr_toroidal_modes'] = 1
    workflow_param['fokker_flag'] = 0

    # FOLDER WHERE THE INPUT XML FILE IS LOCATED
    workflow_param['input_path'] = '/'.join(filepath.split('/')[:-1])

    return(workflow_param)
