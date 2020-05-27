import os
import colour_definitions as col
from lxml import etree

############################################################################################
def save_workflow_param_to_file(current_config_folder,maindict,uncompiled_actors, \
    workflow_param,wfp_ref,fur_ref,cod_ref,cat):

    from hcd_tools import import_actor
    from shutil import copy2

    for hsys in maindict:
        for cat in maindict[hsys]:
            if int(workflow_param[cod_ref][cat]) is not 0:
                actor_name = list(maindict[hsys][cat].keys())[
                    int(workflow_param[cod_ref][cat])-1]
                # get xml path from actor.py
                if actor_name in uncompiled_actors:
                    print('ERROR:', actor_name, 'is selected as an active actor, '
                          'but it has not been found. \n'
                          'Please change your actor selection or load',
                          actor_name, 'and try again')
                    return False
                dest_file = os.path.join(current_config_folder+'/'+hsys+'/input_'
                                         +actor_name+'.xml')
                if not os.path.exists(dest_file):
                    import_actor(actor_name,0)
                    actor_python_folder = eval(actor_name+'.location')
                    found_xml = False
                    found_xsd = False
                    with open(actor_python_folder+'/wrapper.py') as pfile:
                        for iline in pfile:
                            if 'xml_location = ' in iline and \
                               '_default_xml_location' not in iline:
                                xml_name = iline.split('+')[-1].replace("'","")\
                                           .replace(" ","").replace("\n","")
                                # IF XML_NAME TOO SMALL: MEANS NO INPUT XML (NOTHING TO COPY)
                                if len(xml_name) > 5:
                                    copy2(actor_python_folder+xml_name,dest_file,\
                                          follow_symlinks=True)
                                break
    tree = etree.parse(current_config_folder+'/input_workflow.xml')
    root = tree.getroot()
    rl = [wfp_ref, fur_ref, cod_ref]
    for iroot in range(3):
        for elem in root[iroot].iter():
            if elem.tag is not etree.Comment and len(elem) == 0:
                elem.text = workflow_param[rl[iroot]][elem.tag]
    tree.write(current_config_folder+'/input_workflow.xml')
    return True

############################################################################################
def save(current_config_folder,default_wf_param_file,maindict,uncompiled_actors,workflow_param,\
         wfp_ref,fur_ref,cod_ref,cat):

    from datetime import datetime
    from shutil import copy2

    # Define the current folder (either chosen by the system with 'save' 
    # or by the user with 'save as')
    if current_config_folder is None:
        current_config_folder = os.path.join(os.getenv('HCD_FOLDER'),'data/run_'\
                                +datetime.now().strftime('%y%m%d_%H:%M:%S'))

    # When operation is cancelled from the interface
    if current_config_folder is () or current_config_folder == '':
        print('Save_as cancelled.')
        return None

    # Define the workflow parameter file within the current folder
    current_wf_param_file = current_config_folder+ '/input_workflow.xml'

    # Read the default workflow parameters
    root = etree.parse(default_wf_param_file).getroot()

    # Dont want to write configuration directly in $HCD_FOLDER or $HCD_FOLDER/data
    if current_config_folder == os.getenv('HCD_FOLDER')+'/data' or \
       current_config_folder == os.getenv('HCD_FOLDER'):
         print('Refuse to write directly in folder '+current_config_folder)
         return None

    # Dont want to write configuration in folders called ECRH, ICRH, NBI, NUCLEAR 
    # because it would be too confusing
    folder_name = current_config_folder.split('/')[-1]
    if folder_name in ['ECRH','ICRH','NBI','NUCLEAR']:
        print('Refuse to write directly in a folder named '+folder_name+ \
              ' because it could be mixed with process sub-folders')
        return None

    # Create the current configuration folder and its sub-folders for each HCD process
    if not os.path.exists(current_config_folder):
        os.makedirs(current_config_folder)
    for systemname in root[2][0]:
        if not os.path.exists(current_config_folder+'/'+systemname.tag):
            os.makedirs(current_config_folder+'/'+systemname.tag)

    # Copy the default workflow parameter file into the current one
    copy2(default_wf_param_file,current_wf_param_file,follow_symlinks=True)

    # Copy the code parameter files for the actors of the chosen configuration into their 
    # respective sub-folders
    save_workflow_param_to_file(current_config_folder,maindict,uncompiled_actors, \
                                workflow_param,wfp_ref,fur_ref,cod_ref,cat)

    print('---> Configuration saved in '+current_config_folder)

    return current_config_folder
    
############################################################################################
def run(current_config_folder):

    from hcd_wrapper import hcd_wrapper

    hcd_wrapper(current_config_folder)

############################################################################################
def save_codeparam_to_file(filepath, codeparam_dict):
    tree = etree.parse(filepath)
    root = tree.getroot()
    for elem in root.iter():
        if elem.tag is not etree.Comment and len(elem) == 0:
            elem.text = codeparam_dict[elem.tag]
    tree.write(filepath)
    print('---> Configuration saved in '+filepath)

############################################################################################
def destr_and_make(removed_by_close_button, window, maindict,workflow_param):

    from flowchart_display import make_flowchart

    base = make_flowchart(removed_by_close_button, window, maindict,
                          workflow_param)
    removed_by_close_button.append(base)

############################################################################################
def load(chosen_folder,open_gui):

    if chosen_folder is () or chosen_folder == '':
        print('Load cancelled')
        return

    # Check if the chosen folder is a valid configuration folder
    if not os.path.exists(chosen_folder+'/input_workflow.xml'):
        print('The selected folder '+chosen_folder+' does not appear to be a proper')
        print('configuration folder since it contains no input_workflow.xml file '\
              +'--> Nothing loaded.')
        return
    for hcd_process in ['ECRH','ICRH','NBI','NUCLEAR']:
        if not os.path.exists(chosen_folder+'/'+hcd_process):
            print('The selected folder '+chosen_folder+' does not appear to be a proper')
            print('configuration folder since it contains no '+hcd_process+' folder '\
                  +'--> Nothing loaded.')
            return

    print('---> Configuration loaded from '+chosen_folder)
    open_gui(chosen_folder+'/input_workflow.xml')

############################################################################################
def update_workflow_param(workflow_param,ref,elem,newvalue):
    workflow_param[ref][elem] = newvalue
    return workflow_param

############################################################################################

def update_codeparam_dict(codeparam_dict,elem,root,newvalue,xmlschema,entry1):
    codeparam_dict[elem] = newvalue
    for i in root.iter():
        if elem in [str(i.tag)] and i.tag is not etree.Comment:
            i.text = newvalue
        if xmlschema.validate(root):
            entry1.config(bg=col.c1)
        else:
            entry1.config(bg='salmon1')

