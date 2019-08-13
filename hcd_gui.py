import os, sys
sys.path.append('interface')
sys.path.append('workflow')
sys.path.append(os.getcwd())

from tkinter import * 
from tkinter import filedialog, ttk
from lxml import etree
from datetime import datetime
from create_maindict import create_maindict
from create_workflow_param import create_workflow_param_from_file
from hover_class import *
from hcd_wrapper import hcd_wrapper
from shutil import copy2, copytree, rmtree
from simple_flowchart import make_flowchart

from developer_file import load_code_dependencies

#---------------------------------------------------------------------------------------------
##  create a python directory (maindict) that contains the name of all codes (nemo, bbnbi, ...) , their in & output IDSs, their category (ec_wavesolver, nbi_source, ..) the heating system they belong to (EC, IC, NBI, alpha)

print(os.getenv('KEPLER'))
actor_path = os.path.join(os.getenv('KEPLER'), 'imas/src/org/iter/imas/python')

ids_list = ['core_profiles','core_sources','equilibrium', 'pulse_schedule', 'nbi', 'ic_antennas', 'ec_antennas','wall', 'distribution_sources', 'distributions', 'waves']

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
                    (in_l, out_l) = read_inputoutput(icode)
                    dict1[icode] = [in_l, out_l]
                dict2[icat.tag] = [dict1, icat.text]
        dict3[isys.tag] = dict2
    maindict[step.tag] = dict3

# ---------------------------------------------------------------------------------------------
# set the path to the folders where the configuration and codeparameters are stored
    
run_config_folder_path = os.path.join(os.getcwd(), 'run_configurations/run_'+datetime.now().strftime('%m%d_%H%M%S'))
print(run_config_folder_path)
run_workflow_param_path = run_config_folder_path+ '/input_workflow.xml'

os.makedirs(run_config_folder_path)
for systemname in maindict['systems']:
    os.makedirs(run_config_folder_path+'/'+systemname)

copy2('input_workflow_default.xml', run_config_folder_path+'/input_workflow.xml', follow_symlinks=True)
        

## ------------------------------------------------------------------------------------------
## set a few standard colors to call later
c1 = 'white'
c2 = 'white smoke'
c3 = 'azure2'
c4 = 'ghost white'
c5 = 'azure4'
cb = 'LavenderBlush3'

default_workflow_param_path = 'input_workflow_default.xml'

## create mainwindow
window = Tk()
window.title('HCD WORKFLOW')
window.configure(bg = c1)
#window.geometry("1300x800")
#window.resizable(0,1)



def open_gui(input_filepath):

    (maindict, actor_path) = create_maindict(input_filepath)
    workflow_param = create_workflow_param_from_file(input_filepath)

    ### setup 
    if not os.path.exists(run_config_folder_path):
        for systemname in maindict[list(maindict.keys())[0]]:
            os.makedirs(run_config_folder_path+'/'+systemname)
            copy2(input_filepath, run_workflow_param_path, follow_symlinks=True)
 
    fr_wfp = Frame(window, width = 300, height = 10000, background = c3)
    fr_wfp.grid(row = 0, column = 0, rowspan = 2,  sticky = 'nwes', padx = 3, pady = 3)

    fr_as = Frame(window, width = 10000, height = 10000, background = c1)
    fr_as.grid(row = 0, column = 1, rowspan = 2,  sticky = 'nwes', padx = 3, pady = 3)

    fr_fc = Frame(window, width = 100, height = 100, background = c1)
    fr_fc.grid(row = 0, column = 2, sticky = 'news', padx = 3, pady = 3)
    fr_fc.grid_remove()
    
    old_Fr = fr_fc

    ## abbreviations for the keys - makes it easier to change them in the xml file
    wfp_ref = list(workflow_param.keys())[0]
    fur_ref = list(workflow_param.keys())[1]
    cod_ref = list(workflow_param.keys())[2]

    actors_ref = list(maindict.keys())[0]
    make_core_ref = list(maindict.keys())[1]


    ## LEFT - CONFIGURING THE WORKFLOW PARAMETERS
    irow = 0
    for ref in [wfp_ref, fur_ref]:
        
        Label(fr_wfp, text = ref, bg = c3, font = '15').grid(row = irow, column = 0, columnspan = 3, pady = 10, padx = 5, sticky = 'we')
        irow += 1

        for elem in workflow_param[ref]:        
            
            Label(fr_wfp, text = elem, bg = c3).grid(row = irow,  column = 0, padx = 3, pady = 2, sticky = 'w')

            entrystring = StringVar()
            entrystring.set(workflow_param[ref][elem])
            entrystring.trace('w', lambda name, index, mode, elem = elem, entrystring = entrystring, ref = ref: update_workflow_param(ref, elem, entrystring.get()))                      # if an entry is changed, the new values should immediately be changed in the workflow_param dictionary
            Entry(fr_wfp, textvariable = entrystring, bg = c1).grid(row = irow, column = 1, padx = 3, pady = 2, sticky = 'e')
            irow += 1


    ## MIDDLE - SELECTING THE ACTORS
    rrow = 0

    for ref in [actors_ref, make_core_ref]:
        
        for hsys in maindict[ref]:
            Label(fr_as, text = hsys, bg = c1, font = '15').grid(row = rrow, column = 0, columnspan = 2, sticky = 'ew')
            rrow += 1

            for cat in maindict[ref][hsys]:
                Label(fr_as, text = cat, bg = c1,anchor=W, justify=LEFT).grid(row = rrow, column = 0, sticky = W)
                cb = ttk.Combobox(fr_as, value = ['']+list(maindict[ref][hsys][cat]))
                cb.grid(row = rrow, column = 1, padx = 20, pady = 5, sticky = 'ew')
                cb.current(workflow_param[cod_ref][cat])
                cb.bind('<<ComboboxSelected>>', lambda event, cat = cat, cb = cb: update_workflow_param(cod_ref, cat, str(cb.current())))
                rrow += 1


            


    ## RIGHT - FLOWCHART 
    


    ## BUTTONS 
    
    # left: 
    button_saveconfig = Button(fr_wfp, text = 'Save Configuration', bg = c2)
    button_saveconfig.grid(row = 52, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_saveconfig.configure(command = lambda: save_workflow_param_to_file(run_workflow_param_path))
    # save xml to the run folder
    button_loadconfig = Button(fr_wfp, text = 'Load Configuration', bg = c2)
    button_loadconfig.grid(row = 52, column = 1, padx = 5, pady = 5, sticky = 'ew')
    button_loadconfig.configure(command = lambda: load_configuration_from_file(filedialog.askopenfilename(initialdir =  os.path.join(os.getcwd(), 'run_configurations'))))

    button_saveandrun = Button(fr_wfp, text = 'Save and Run', bg = c2)
    button_saveandrun.grid(row = 51, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_saveandrun.configure(command = lambda: save_and_run(run_workflow_param_path, True))


    button_run_nosave = Button(fr_wfp, text = 'Run (without Saving)', bg = c2)
    button_run_nosave.grid(row = 51, column = 1, padx = 5, pady = 5, sticky = 'ew')
    button_run_nosave.configure(command = lambda: save_and_run(run_workflow_param_path, False))

    button_save_asdef = Button(fr_wfp, text = 'Save Configuration as Default', bg = c2)
    button_save_asdef.grid(row = 53, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_save_asdef.configure(command = lambda: save_workflow_param_to_file('input_workflow_default.xml'))

    # middle: 
    button_create_flowchart = Button(fr_as, text = 'Show Flowchart', bg = c2)
    button_create_flowchart.grid(row = 53, column = 1, padx = 5, pady = 5, sticky = 'ew')
    old_fr = fr_fc
    button_create_flowchart.configure(command = lambda: make_flowchart(old_fr, window, maindict, workflow_param, c1, c2, c3, c4,c5))

    button_edit_codeparameters = Button(fr_as, text = 'Edit Codeparameters', bg = c2)
    button_edit_codeparameters.grid(row = 53, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_edit_codeparameters.configure(command = lambda: edit_codeparam())




    ## MANAGE XML FILES
    def edit_codeparam():
        cp_top = Toplevel()
        cp_top.title('Edit Code Parameters')
        cp_top.geometry('500x700')

        fr_ab = Frame(cp_top, width = 200, height = 500, bg = c4)
        fr_ab.grid(row = 0, column = 0, rowspan = 2, sticky = 'ns')
        fr_main = Frame(cp_top, width = 500, height = 1500, bg = c1)
        fr_main.grid(row = 1, column = 1, sticky = 'nwes')
        prev_frame = fr_main
        fr_top = Frame(cp_top, width = 500, height = 50, bg = c2) 
        fr_top.grid(row = 0, column =1, sticky = 'ew')
        
        for hsys in maindict[actors_ref]:
            la_sys = Label(fr_ab, text = hsys, bg = c4)
            for cat in maindict[actors_ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    la_sys.grid(padx = 5, pady = 5, sticky = 'ew')

                    
                    curval = list(maindict[actors_ref][hsys][cat].keys())[int(workflow_param[cod_ref][cat])-1]
                    Button(fr_ab, text = curval, bg = c2, command = lambda actor_name = curval, hsys = hsys: make_frame(hsys, actor_name, prev_frame, False) ).grid(padx = 5, pady = 5, sticky = 'ew')                                                             
                                                                    
        def make_frame(hsys, actor_name,  prev_frame, is_load_default_from_kepler):
            prev_frame.grid_remove()
            prev_frame.grid_forget()

            fr = Frame(cp_top, width = 500, height = 1500, bg = c1)
            prev_frame = fr
            fr.grid(row = 1, column =1, sticky = 'nswe')
            fr.grid_propagate(0)

            codeparam_xml_path = StringVar()
            codeparam_xsd_path = StringVar()
        
            ## name of the codeparam file in the run_config_folder
            dest_file = os.path.join(run_config_folder_path+'/'+hsys+'/input_'+actor_name+'.xml')
            
            actor_python_script = actor_path+'/'+actor_name+'/'+actor_name+'.py'
            found_xml = False
            found_xsd = False



            with open(actor_python_script) as pfile:

                for iline in pfile:
                    if ('xml_location = ' in iline) and ('_default_xml_location' not in iline):
                        ## check if there already is a version of the xml file for this actor - this could be put outside of the loop for reading the file, but the code is shorter this way, it shouldnt be too confusing i hope 
                        if os.path.exists(dest_file) and is_load_default_from_kepler is False: 
                            ## if yes, use that one as xml 
                            codeparam_xml_path.set(dest_file)
                        else:
                            ## if not, OR it is supposed to load the default, use the one we just found 
                            codeparam_xml_path.set(iline[17:-2])
                            copy2(codeparam_xml_path.get(), dest_file, follow_symlinks=True) # copy the one stored in the kepler folder to the current runfolder necessary for saving the changes later
                        found_xml = True

                    if 'xsd_location = ' in iline:
                        codeparam_xsd_path.set(iline[17:-2])
                        found_xsd = True
                    if found_xml == True and found_xsd == True:
                        break

            


            #### read the additional information from the xsd file 
            try:
                xmlschema_doc = etree.parse(codeparam_xsd_path.get())
                root_xsd = xmlschema_doc.getroot()
                xmlschema = etree.XMLSchema(xmlschema_doc)
                docum_dict = {}
                for elem in root_xsd.iter():
                    if elem.tag ==  '{http://www.w3.org/2001/XMLSchema}element':
                        for i in elem.iter():
                            if i.tag ==  '{http://www.w3.org/2001/XMLSchema}documentation':
                                docum_dict[elem.attrib.values()[0]] = i.text
            except:
                docum_dict = {}

            ### load the list of code parameters, create the labels and entries
            tree = etree.parse(codeparam_xml_path.get())        
            root = tree.getroot()
       #     fr.grid_remove()
       #     fr.grid_forget()
       #     fr = Frame(cp_top, width = 500, height = 1500, bg = c1)
       #     fr.grid(row = 1, column = 1, sticky = 'nswe')
       #     fr.grid_propagate(0)

            rrow = 1
            ccolumn = 0
            codeparam_dict = {}

            for elem in root.iter():
                if ((elem.tag is not etree.Comment) and (len(elem) == 0)):
                    l = Label(fr, text = elem.tag.strip(), bg = c1)
                    l.grid(row = rrow, column = ccolumn)

                    entrystring = StringVar()
                    entrystring.set(elem.text.strip())
                    e = Entry(fr, textvar = entrystring, bg = c1)
                    e.grid(row = rrow, column = ccolumn+1, padx = 3, pady = 3)
                    codeparam_dict[elem.tag] = entrystring.get()
                    
                    entrystring.trace('w', lambda name, index, mode, elem = elem.tag, entrystring = entrystring: update_codeparam_dict(elem, entrystring.get()))
    
                   
                    try:
                         CreateToolTip(l, docum_dict[l.cget('text')])
                    except:
                        pass 

                    def update_codeparam_dict(elem, newvalue): 
                        codeparam_dict[elem] = newvalue
                       
                    
                    rrow +=1 
                    if rrow > 30:  ## if there are more than 30 entries start a new column
                        ccolumn += 2
                        rrow = 1
                        fr.grid_propagate(1)

            Button(fr_top, text = 'save', bg = c2,  command = lambda: save_codeparam_to_file(dest_file, codeparam_dict)).grid(row = 0 ,column = 1, padx = 5, pady = 5)
            Button(fr_top, text = 'load default', bg = c2, command = lambda: make_frame(hsys, actor_name,  prev_frame, True)).grid(row = 0, column =2, padx = 5, pady = 5)
                    


    ## FUNCTIONS - SAVING & UPDATING


    def update_workflow_param(ref, elem, newvalue):
        workflow_param[ref][elem] = newvalue
      
        
    def save_workflow_param_to_file(filepath):

       ## COPY 
        ## for all the active actors
        for hsys in maindict[actors_ref]:
            for cat in maindict[actors_ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    actor_name = list(maindict[actors_ref][hsys][cat].keys())[int(workflow_param[cod_ref][cat])-1]
                    # get xml path from actor.py 
                    
                    dest_file = os.path.join(run_config_folder_path+'/'+hsys+'/input_'+actor_name+'.xml')
                    if not os.path.exists(dest_file):
                        actor_python_script = actor_path+'/'+actor_name+'/'+actor_name+'.py'
                        found_xml = False
                        found_xsd = False

                        with open(actor_python_script) as pfile:

                            for iline in pfile:
                                if ('xml_location = ' in iline) and ('_default_xml_location' not in iline):
                                    path_to_kepler_xml_location = iline[17:-2]
                                    copy2(path_to_kepler_xml_location, dest_file, follow_symlinks=True)
              
                                    break


        tree = etree.parse(filepath)
        root = tree.getroot()
        
        rl = [wfp_ref, fur_ref, cod_ref]
        
        for iroot in range(3):
            for elem in root[iroot].iter():
                if((elem.tag is not etree.Comment) and (len(elem) == 0)):

                   elem.text = workflow_param[rl[iroot]][elem.tag]
                   
        tree.write(filepath)

    def save_and_run(filepath, save_yn):
        print(filepath)
        save_workflow_param_to_file(filepath)
        
        #window.destroy()
        hcd_wrapper(run_config_folder_path)

        if save_yn == 0:
            rmtree(run_config_folder_path)

    def load_configuration_from_file(filepath):
        print(filepath)
        if filepath is not (): 
            source_folder = filepath[:-19]

            #    rmtree(run_config_folder_path)
            if source_folder.find(run_config_folder_path) is -1:
                try:
                    copytree(source_folder, run_config_folder_path)
                except:
                    rmtree(run_config_folder_path)
                    copytree(source_folder, run_config_folder_path)

            
                open_gui(run_config_folder_path+ '/input_workflow.xml')
            
            else:
                print('this folder is the current folder. it is not possible to load the current configuration')
            

        else:
            print('no file selected')

        

    def save_codeparam_to_file(filepath, codeparam_dict):

        tree = etree.parse(filepath)
        root = tree.getroot()
        
        for elem in root.iter():
            if((elem.tag is not etree.Comment) and (len(elem) == 0)):
               elem.text = codeparam_dict[elem.tag]
        pass
        
        tree.write(filepath)

    window.mainloop()


open_gui(default_workflow_param_path)
