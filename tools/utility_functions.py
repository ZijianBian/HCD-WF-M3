import os, sys
from lxml import etree
from shutil import copy2

############################################################################################
def save_workflow_param_to_file(default_wf_param_file,current_wf_param_file,\
    workflow_param,wfp_ref,fur_ref,cod_ref):

    # Copy the default workflow parameter file into the current one
    copy2(default_wf_param_file,current_wf_param_file,follow_symlinks=True)

    # Update workflow parameter file if changed from the interface
    tree = etree.parse(current_wf_param_file)
    root = tree.getroot()
    rl = [wfp_ref, fur_ref, cod_ref]
    for iroot in range(3):
        for elem in root[iroot].iter():
            if elem.tag is not etree.Comment and len(elem) == 0:
                elem.text = workflow_param[rl[iroot]][elem.tag]
    tree.write(current_wf_param_file)
    return 0

############################################################################################
def read_and_save_codeparam(current_config_folder,previous_folder,hsys,actor_name,default):

    from hcd_tools import import_actor

    # NAME OF THE CODEPARAM FILE FOR THIS ACTOR IN THE CURRENT CONFIGURATION FOLDER
    destination_file = current_config_folder+'/'+hsys+'/input_'+actor_name+'.xml'

    # INITIALISE INTERFACE STRINGS FOR CODEPARAM XML AND XSD FILES
    codeparam_xml_path = ''
    codeparam_xsd_path = ''

    # IMPORT THE ACTOR TO KNOW WHERE IT IS LOCATED
    import_actor(actor_name,0)
    actor_python_folder = eval(actor_name+'.location')

    # LOOK FOR ITS XML AND XSD FILES FOR USER-DEFINED PARAMETERS
    found_xml = False
    found_xsd = False
    with open(actor_python_folder+'/wrapper.py') as pfile:
        for iline in pfile:
            if 'xml_location = ' in iline and '_default_xml_location' not in iline:
                # CHECK IF THE XML FILE EXISTS IN THE DESTINATION FOLDER ALREADY
                if os.path.exists(destination_file) and default is False:
                    codeparam_xml_path = destination_file
                # IF NOT, COPY IT FROM THE ACTOR LOCATION
                else:
                    xml_name = iline.split('+')[-1].replace("'","").replace(" ","")\
                               .replace("\n","")
                    if not 'None' in xml_name:
                        codeparam_xml_path = actor_python_folder+xml_name
                        copy2(codeparam_xml_path, destination_file, follow_symlinks=True)
                        # IF DEFAULT IS NOT REQUIRED AND IF CONFIG LOADED FROM A PREVIOUS RUN,
                        # REPLACE THE XML FILE BY THE ONE OF THE PREVIOUS CONFIGURATION
                        if previous_folder is not None and default is False:
                            xml_name = hsys+'/input_'+actor_name+'.xml'
                            codeparam_xml_path = previous_folder+'/'+xml_name
                            if codeparam_xml_path != destination_file:
                                copy2(codeparam_xml_path, destination_file, follow_symlinks=True)
                        found_xml = True

            if 'xsd_location = ' in iline:
                xsd_name = iline.split('+')[-1].replace("'","").replace(" ","").replace("\n","")
                if not 'None' in xsd_name:
                    codeparam_xsd_path = actor_python_folder+xsd_name
                    found_xsd = True

            if found_xml is True and found_xsd is True:
                break

    # READ THE ADDITIONAL INFORMATION FROM THE XSD FILE
    if found_xsd:
        xmlschema_doc = etree.parse(codeparam_xsd_path)
        root_xsd      = xmlschema_doc.getroot()
        xmlschema     = etree.XMLSchema(xmlschema_doc)
        docum_dict = {}
        for elem in root_xsd.iter():
            if elem.tag == '{http://www.w3.org/2001/XMLSchema}element':
                for i in elem.iter():
                    if i.tag == '{http://www.w3.org/2001/XMLSchema}documentation':
                        docum_dict[elem.attrib.values()[0]] = i.text
    else:
        xmlschema  = {}
        docum_dict = {}

    # LOAD THE LIST OF CODE PARAMETERS, CREATE THE LABELS AND ENTRIES
    if found_xml:
        tree = etree.parse(codeparam_xml_path)
        root = tree.getroot()
        codeparam_dict = {}
        for elem in root.iter():
            if elem.tag is not etree.Comment and len(elem) == 0:
                codeparam_dict[elem.tag] = elem.text
    else:
        codeparam_dict = {}

    return destination_file,codeparam_dict,docum_dict,codeparam_xml_path, \
        xmlschema

############################################################################################
def update_codeparam_file(destination_file,codeparam_dict,verbose):

    tree = etree.parse(destination_file)
    root = tree.getroot()
    for elem in root.iter():
        if elem.tag is not etree.Comment and len(elem) == 0:
            elem.text = codeparam_dict[elem.tag]
    tree.write(destination_file)

    if verbose == 1:
        print('---> Configuration saved in '+destination_file, file=sys.stdout)

    return 0

############################################################################################
def save_codeparam_to_file(current_config_folder,previous_folder,maindict,uncompiled_actors, \
                           workflow_param,verbose):

    from hcd_tools import import_actor

    cod_ref = list(workflow_param.keys())[2]

    for hsys in maindict:
        for cat in maindict[hsys]:
            if int(workflow_param[cod_ref][cat]) is not 0:
                actor_name = list(maindict[hsys][cat].keys())[
                    int(workflow_param[cod_ref][cat])-1]
                if actor_name in uncompiled_actors:
                    print('ERROR:', actor_name.upper(), 'is selected as an active actor, '
                          'but it has not been found. \n'
                          'Please change your actor selection or load',
                          actor_name.upper(), 'and try again', file=sys.stderr)
                    return -1

                destination_file,codeparam_dict,docum_dict,codeparam_xml_path,xmlschema = \
                    read_and_save_codeparam(current_config_folder,previous_folder,\
                                            hsys,actor_name,False)

                # Update code parameter files if changed from interface (and if exists)
                if codeparam_dict != {}:
                    update_codeparam_file(destination_file,codeparam_dict,verbose)

    return 0

############################################################################################
def save(current_config_folder,default_wf_param_file,previous_folder,maindict,uncompiled_actors,\
         workflow_param,wfp_ref,fur_ref,cod_ref,hcd_path):

    from datetime import datetime

    # Define the current folder (either chosen by the system with 'save' 
    # or by the user with 'save as')
    if current_config_folder is None:
        first_save = 1
        current_config_folder = os.path.join(hcd_path,'data/run_'\
                                +datetime.now().strftime('%y%m%d_%H:%M:%S'))
    else:
        first_save = 0

    # When operation is cancelled from the interface
    if current_config_folder is () or current_config_folder == '':
        print('Save_as cancelled.', file=sys.stderr)
        return None

    # Define the workflow parameter file within the current folder
    current_wf_param_file = current_config_folder+ '/input_workflow.xml'

    # Dont want to write configuration directly in hcd_path or hcd_path/data
    if current_config_folder == hcd_path+'/data' or current_config_folder == hcd_path:
         print('Refuse to write directly in folder '+current_config_folder, file=sys.stderr)
         return None

    # Dont want to write configuration in folders called ECRH, ICRH, NBI, NUCLEAR 
    # because it would be too confusing
    folder_name = current_config_folder.split('/')[-1]
    if folder_name in ['ECRH','ICRH','NBI','NUCLEAR','source','profiles']:
        print('Refuse to write directly in a folder named '+folder_name+ \
              ' because it could be mixed with process sub-folders', file=sys.stderr)
        return None

    # Read the default workflow parameters file
    root = etree.parse(default_wf_param_file).getroot()

    # Create the current configuration folder and its sub-folders for each process
    if not os.path.exists(current_config_folder):
        os.makedirs(current_config_folder)
    for systemname in root[2][0]: # HCD process
        if not os.path.exists(current_config_folder+'/'+systemname.tag):
            os.makedirs(current_config_folder+'/'+systemname.tag)
    for postproc in root[2][1]: # Post-processins
        if not os.path.exists(current_config_folder+'/'+postproc.tag):
            os.makedirs(current_config_folder+'/'+postproc.tag)

    # Copy/update the workflow parameter file if changed from the interface
    err = save_workflow_param_to_file(default_wf_param_file,current_wf_param_file,\
        workflow_param,wfp_ref,fur_ref,cod_ref)

    # Copy/update code parameter files for chosen actors in their respective sub-folders
    err = save_codeparam_to_file(current_config_folder,previous_folder,maindict,\
        uncompiled_actors,workflow_param,0)

    if err == 0:
        print('---> Configuration saved in '+current_config_folder, file=sys.stdout)
    else:
        current_config_folder = None

    return current_config_folder
    
############################################################################################
def run(current_config_folder):

    if current_config_folder is not None:
        from hcd_wrapper import hcd_wrapper
        hcd_wrapper(current_config_folder)
    else:
        print('Aborted.')

############################################################################################
def destr_and_make(removed_by_close_button, window, maindict,workflow_param):

    from flowchart_display import make_flowchart

    base = make_flowchart(removed_by_close_button, window, maindict,
                          workflow_param)
    removed_by_close_button.append(base)

############################################################################################
def load(chosen_folder,open_gui):

    if chosen_folder is () or chosen_folder == '':
        print('Load cancelled', file=sys.stderr)
        return

    # Check if the chosen folder is a valid configuration folder
    if not os.path.exists(chosen_folder+'/input_workflow.xml'):
        print('The selected folder '+chosen_folder+' does not appear to be a proper', \
              file=sys.stderr)
        print('configuration folder since it contains no input_workflow.xml file '\
              +'--> Nothing loaded.', file=sys.stderr)
        return
    for hcd_process in ['ECRH','ICRH','NBI','NUCLEAR','source','profiles']:
        if not os.path.exists(chosen_folder+'/'+hcd_process):
            print('The selected folder '+chosen_folder+' does not appear to be a proper', \
                  file=sys.stderr)
            print('configuration folder since it contains no '+hcd_process+' folder '\
                  +'--> Nothing loaded.', file=sys.stderr)
            return

    print('---> Configuration loaded from '+chosen_folder, file=sys.stdout)
    open_gui(chosen_folder+'/input_workflow.xml')

############################################################################################
def update_workflow_param(workflow_param,ref,elem,newvalue):
    workflow_param[ref][elem] = newvalue
    return workflow_param

############################################################################################
def update_codeparam_dict(codeparam_dict,elem,newvalue):
    codeparam_dict[elem] = newvalue
    return codeparam_dict

