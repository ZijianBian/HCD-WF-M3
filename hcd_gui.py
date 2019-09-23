import os, sys, copy
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


#---------------------------------------------------------------------------------------------


if (os.getenv('KEPLER') is None)  or ('/work/imas/extra' in os.getenv('KEPLER')):
    print('ERROR: the local version of Kepler is not loaded')
    sys.exit()

# ---------------------------------------------------------------------------------------------
# set the path to the folders where the configuration and codeparameters are stored
    
global run_config_folder_path 
run_config_folder_path  = os.path.join(os.getcwd(), 'run_configurations/run_'+datetime.now().strftime('%m%d_%H%M%S'))

run_workflow_param_path = run_config_folder_path+ '/input_workflow.xml'

root1 = etree.parse('input_workflow_default.xml').getroot()

os.makedirs(run_config_folder_path)
for systemname in root1[2][0]:
    os.makedirs(run_config_folder_path+'/'+systemname.tag)

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
window = Tk()
## create mainwindow

fontsize = int(window.winfo_screenheight()/100)-2

if fontsize > 14:
    fontsize = 14
if fontsize < 5:
    fontsize = 5

print(fontsize)

window.option_add('*font', 'courier '+str(fontsize))
#window.option_add('*font', 'courier 50')
      

window.title('HCD WORKFLOW')
window.configure(bg = c1)


print(window.winfo_screenheight())

def open_gui(input_filepath):

    try:
        wh = window.winfo_reqheight()
        ww = window.winfo_reqwidth()
        wx = window.winfo_x()
        wy = window.winfo_y()
        window.geometry("+%d+%d" %(wx, wy))
        
    except: 

        pass

    ##  create a python directory (maindict) that contains the name of all codes (nemo, bbnbi, ...) , their in & output IDSs, their category (ec_wavesolver, nbi_source, ..) the heating system they belong to (EC, IC, NBI, alpha)
    (maindict, actor_path, list_of_uncompiled_actors) = create_maindict(input_filepath)
    workflow_param = create_workflow_param_from_file(input_filepath)

    ### setup 
    if not os.path.exists(run_config_folder_path):
        for systemname in maindict[list(maindict.keys())[0]]:
            os.makedirs(run_config_folder_path+'/'+systemname)
            copy2(input_filepath, run_workflow_param_path, follow_symlinks=True)
 
    fr_wfp = Frame(window, width = 300, height = 500, background = c3)
    fr_wfp.grid(row = 0, column = 0, rowspan = 2,  sticky = 'nwes', padx = 3, pady = 3)

    fr_as = Frame(window, width = 500, height = 500, background = c1)
    fr_as.grid(row = 0, column = 1, rowspan = 2,  sticky = 'nwes', padx = 3, pady = 3)

    fr_fc = Frame(window, width = 500, height = 500, background = c1)
    fr_fc.grid(row = 0, column = 2, rowspan = 2,  sticky = 'nwes', padx = 3, pady = 3)

    removed_by_close_button = [fr_fc]
    fr_fc.grid_remove()

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
            
            Label(fr_wfp, text = elem, bg = c3).grid(row = irow,  column = 0, padx = 1, pady = 2, sticky = 'w')

            entrystring = StringVar()
            entrystring.set(workflow_param[ref][elem])
            entrystring.trace('w', lambda name, index, mode, elem = elem, entrystring = entrystring, ref = ref: update_workflow_param(ref, elem, entrystring.get()))                      # if an entry is changed, the new values should immediately be changed in the workflow_param dictionary
            Entry(fr_wfp, textvariable = entrystring, bg = c1).grid(row = irow, column = 1, padx = 1, pady = 2, sticky = 'e')
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
    button_saveconfig.configure(command = lambda: save_workflow_param_to_file(run_config_folder_path))
    # save xml to the run folder
    button_loadconfig = Button(fr_wfp, text = 'Load Configuration', bg = c2)
    button_loadconfig.grid(row = 52, column = 1, padx = 5, pady = 5, sticky = 'ew')
    button_loadconfig.configure(command = lambda: load_configuration_from_file(filedialog.askopenfilename(initialdir =  os.path.join(os.getcwd(), 'run_configurations'))))

    button_saveandrun = Button(fr_wfp, text = 'Save and Run', bg = c2)
    button_saveandrun.grid(row = 51, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_saveandrun.configure(command = lambda: save_and_run(run_config_folder_path, True))


    button_run_nosave = Button(fr_wfp, text = 'Run (without Saving)', bg = c2)
    button_run_nosave.grid(row = 51, column = 1, padx = 5, pady = 5, sticky = 'ew')
    button_run_nosave.configure(command = lambda: save_and_run(run_config_folder_path, False))

    button_save_asdef = Button(fr_wfp, text = 'Save Configuration as Default', bg = c2)
    button_save_asdef.grid(row = 53, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_save_asdef.configure(command = lambda: save_workflow_param_to_file('input_workflow_default.xml'))

    button_restore_def = Button(fr_wfp, text = 'Restore Default', bg =c2)
    button_restore_def.grid(row = 53, column = 1, padx = 5, pady = 5, sticky = 'ew')
    button_restore_def.configure(command = lambda: open_gui('input_workflow_default.xml'))

    button_saveas      = Button(fr_wfp, text = 'Save as', bg = c2)
    button_saveas.grid(row = 54, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_saveas.configure(command = lambda: save_as())

    button_exit = Button(fr_wfp, text = 'Exit', bg = 'light grey')
    button_exit.grid(row = 55, column = 0, padx = 5, pady = 5, sticky = 'w')
    button_exit.configure(command = lambda: sys.exit())

   
    # middle: 
    button_create_flowchart = Button(fr_as, text = 'Show Flowchart', bg = c2)
    button_create_flowchart.grid(row = 53, column = 1, padx = 5, pady = 5, sticky = 'ew')
    button_create_flowchart.configure(command = lambda: destr_and_make(removed_by_close_button, window, maindict, workflow_param, c1, c2, c3, c4,c5))
   

    def destr_and_make(removed_by_close_button,  window, maindict, workflow_param, c1, c2, c3, c4,c5):
        
        base = make_flowchart(removed_by_close_button, window, maindict, workflow_param, c1, c2, c3, c4,c5)
        removed_by_close_button.append(base)

      

    button_edit_codeparameters = Button(fr_as, text = 'Edit Codeparameters', bg = c2)
    button_edit_codeparameters.grid(row = 53, column = 0, padx = 5, pady = 5, sticky = 'ew')
    button_edit_codeparameters.configure(command = lambda: edit_codeparam())

    

    ## MANAGE XML FILES
    def edit_codeparam():
        cp_top = Toplevel()
        cp_top.title('Edit Code Parameters')
        cp_top.geometry('500x700')


        fr_ab = Frame(cp_top, width = 200, height = 650, bg = c4)
        fr_ab.grid(row = 0, column = 0, rowspan = 2, sticky = 'ns')
        
        fr_main = Frame(cp_top, width = 500, height = 650, bg = c1)
        fr_main.grid(row = 1, column = 2, sticky = 'nwes')
        fr_main.grid_propagate(0)
        prev_frame = Canvas(fr_main, width = 500, height = 1500)
        
        fr_top = Frame(cp_top, width = 500, height = 50, bg = c2) 
        fr_top.grid(row = 0, column =1, sticky = 'ew', columnspan = 2)
        
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

 

          def populate(frame):
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

            rrow = 1
            ccolumn = 0
            codeparam_dict = {}
            


            for elem in root.iter():
                if ((elem.tag is not etree.Comment) and (len(elem) == 0)):
                    l = Label(fr, text = elem.tag.strip(), bg = c1, wraplength = '200', anchor = 'w', justify = LEFT )
                    l.grid(row = rrow, column = ccolumn, sticky = 'w')

                    entrystring = StringVar()
                    entrystring.set(elem.text.strip())
                    e = Entry(fr, textvar = entrystring, bg = c1)
                    e.grid(row = rrow, column = ccolumn+1, padx = 3, pady = 3)
                    codeparam_dict[elem.tag] = entrystring.get()
                    
                    entrystring.trace('w', lambda name, index, mode, elem = elem.tag, entrystring = entrystring, e = e: update_codeparam_dict(elem, entrystring.get(), e))
              
                   
                    try:
                         CreateToolTip(l, docum_dict[l.cget('text')])
                    except:
                        pass 

                    def update_codeparam_dict(elem, newvalue, entry1): 
                        codeparam_dict[elem] = newvalue
                        for i in root.iter():
                            if (elem in [str(i.tag)]) and (i.tag is not etree.Comment): 
                                i.text = newvalue


                        if xmlschema.validate(root): 
                            entry1.config(bg = c1)
                        else:
                            entry1.config(bg = 'salmon1')


                    
                    rrow +=1 

                    

                    if rrow > 20:
                        v_scroll.grid(row = 1, column = 1, sticky = 'ns')
                    else:
                        v_scroll.grid_remove()

          # end of populate frame       
          
          def onFrameConfigure(canvas):
              canvas.configure(scrollregion = canvas.bbox('all'))

          canvas = Canvas(cp_top, borderwidth = 0, highlightthickness = 0, background = c1)
          fr = Frame(canvas, width = 500, height = 1500, bg = c1)
          prev_frame = fr
          v_scroll = Scrollbar(cp_top, orient = 'vertical', command = canvas.yview)
          canvas.configure(yscrollcommand = v_scroll.set)
        #  v_scroll.grid()

         
          canvas.grid(row = 1, column = 2, sticky = ' news')
          canvas.create_window((4,4), window = fr, anchor = 'nw')

          #    fr.grid_propagate(0)
          fr.bind('<Configure>', lambda event, canvas = canvas: onFrameConfigure(canvas))
          
          populate(fr)
          
        


          Button(fr_top, text = 'save', bg = c2,  command = lambda: save_codeparam_to_file(dest_file, codeparam_dict)).grid(row = 0 ,column = 1, padx = 5, pady = 5)
          Button(fr_top, text = 'load default', bg = c2, command = lambda: make_frame(hsys, actor_name,  prev_frame, True)).grid(row = 0, column =2, padx = 5, pady = 5)
          Button(fr_top, text = 'exit', bg = c2, command = lambda: cp_top.destroy()).grid(row = 0, column = 4, padx = (20, 5), pady = 5)        



          populate(fr)    
                    


    ## FUNCTIONS - SAVING & UPDATING


    def update_workflow_param(ref, elem, newvalue):
        workflow_param[ref][elem] = newvalue
      
        
    def save_workflow_param_to_file(filepath):
        global run_config_folder_path
        if filepath == '':
            filepath = run_config_folder_path
         
       ## COPY 
        ## for all the active actors
        for hsys in maindict[actors_ref]:
            for cat in maindict[actors_ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    actor_name = list(maindict[actors_ref][hsys][cat].keys())[int(workflow_param[cod_ref][cat])-1]
                    # get xml path from actor.py 
                    if actor_name in list_of_uncompiled_actors:
                         print('ERROR: ', actor_name, ' is selected as an active actor, but it has not been found. \n Please change your selection of actors or load', actor_name, 'and try again')
                         return False

                    
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

        if  'xml'  not in filepath[-4:]:
             filepath = filepath+'/input_workflow.xml'

      
        tree = etree.parse(filepath)
        root = tree.getroot()
        
        rl = [wfp_ref, fur_ref, cod_ref]
        
        for iroot in range(3):
            for elem in root[iroot].iter():
                if((elem.tag is not etree.Comment) and (len(elem) == 0)):

                   elem.text = workflow_param[rl[iroot]][elem.tag]
                   
        tree.write(filepath)
        return True

    def save_as():
        
        filepath = filedialog.askdirectory()
       
        global run_config_folder_path
        old_run_config_folder_path = copy.copy(run_config_folder_path)
      

        if os.path.exists(filepath):
            
            run_config_folder_path = copy.copy(filepath)
            save_workflow_param_to_file(run_config_folder_path)
            if old_run_config_folder_path is not run_config_folder_path:
                rmtree(old_run_config_folder_path) 

        else:
            copytree(run_config_folder_path, filepath)
            run_config_folder_path = copy.copy(filepath)
            save_workflow_param_to_file(run_config_folder_path)

            if old_run_config_folder_path is not run_config_folder_path:
                rmtree(old_run_config_folder_path) 
       
   
     

    def save_and_run(filepath, save_yn):
        noerror = save_workflow_param_to_file(filepath)
        if noerror:
        #window.destroy()
            hcd_wrapper(run_config_folder_path)

            if save_yn == 0:
                rmtree(run_config_folder_path)        
   

    def load_configuration_from_file(filepath):
        if 'input_workflow_default.xml' in filepath:
            print('if you want to load the default configuration please choose load default')
            filepath = ()
        elif 'input_workflow.xml' not in filepath: 
            print('please choose an input_workflow.xml file')
            filepath = ()
       

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

