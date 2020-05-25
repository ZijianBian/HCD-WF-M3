import os, sys

try:
    import tkinter
    import tkinter.ttk
    import tkinter.filedialog
except:
    print('ERROR: tkinter not found')
    print('---> TIP: source the HCD configuration file')
    sys.exit()

try:
    from lxml import etree
except:
    print('ERROR: lxml module not found')
    print('---> TIP: source the HCD configuration file')
    sys.exit()

try:
    import colour_definitions as col
    from hcd_tools import import_actor, create_maindict, loadlist, \
        create_workflow_param_from_file
    from codeparam_edit import edit_codeparam
    from utility_functions import save_workflow_param_to_file, \
        save, run, save_codeparam_to_file, destr_and_make, \
        update_workflow_param,load
except:
    raise
    print('ERROR while loading internal HCD modules')
    print('---> TIP: source the HCD configuration file')
    sys.exit()

#---------------------------------------------------------------------------------------------
# Folder from which to find the compiled HCD actors

if os.getenv('ACTOR_FOLDER') is None:
    print('ERROR: the environment variable ACTOR_FOLDER has not been set up')
    sys.exit()
else:
    ACTOR_FOLDER = os.getenv('ACTOR_FOLDER')

# --------------------------------------------------------------------------------------------
# Path to the default parameter file

default_wf_param_file = os.getenv('HCD_FOLDER')+'/input_workflow_default.xml'

# --------------------------------------------------------------------------------------------
# Create the main window (define font, title and background colour)
window = tkinter.Tk()
fontsize = int(window.winfo_screenheight()/100)+3 # Adjusted with screen size
if fontsize > 14:
    fontsize = 14
if fontsize < 5:
    fontsize = 5
window.option_add('*font','courier '+str(fontsize))
window.title('HCD WORKFLOW')
window.configure(bg=col.c1)

# --------------------------------------------------------------------------------------------
def open_gui(wf_param_file):

    # CHECK THAT MANDATORY ACTORS ARE THERE
    merge_actor_list = loadlist('merge_actor_list')
    empty_actor_list = loadlist('empty_actor_list')
    err_global = 0
    for actor in merge_actor_list:
        err = import_actor(actor,1)
        err_global = err_global + err
    for actor in empty_actor_list:
        err = import_actor(actor,1)
        err_global = err_global + err
    if err_global!=0:
        print('---------------------------------------------')
        print('One or more mandatory actor(s) not accessible')
        print('--> Program stopped.')
        print('---------------------------------------------')
        return

    try:
        wh = window.winfo_reqheight()
        ww = window.winfo_reqwidth()
        wx = window.winfo_x()
        wy = window.winfo_y()
        window.geometry("+%d+%d" %(wx, wy))
    except:
        pass

    # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
    # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
    (maindict, compiled_actors, uncompiled_actors, code_selection) = \
        create_maindict(wf_param_file,1,1)
    workflow_param = create_workflow_param_from_file(wf_param_file,1)

    ### setup

    fr_wfp = tkinter.Frame(window, width=300, height=500, background=col.c3)
    fr_wfp.grid(row=0, column=0, rowspan=2, sticky='nwes', padx=3, pady=3)

    fr_as = tkinter.Frame(window, width=500, height=500, background=col.c1)
    fr_as.grid(row=0, column=1, rowspan=2, sticky='nwes', padx=3, pady=3)

    fr_fc = tkinter.Frame(window, width=500, height=500, background=col.c1)
    fr_fc.grid(row=0, column=2, rowspan=2, sticky='nwes', padx=3, pady=3)

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

        tkinter.Label(fr_wfp, text=ref, bg=col.c3, font='15').grid(row=irow,
                                                       column=0,
                                                       columnspan=3,
                                                       pady=10,
                                                       padx=5,
                                                       sticky='we')
        irow += 1

        for elem in workflow_param[ref]:

            tkinter.Label(fr_wfp, text=elem, bg=col.c3).grid(row=irow,
                                                 column=0,
                                                 padx=1,
                                                 pady=2,
                                                 sticky='w')

            entrystring = tkinter.StringVar()
            entrystring.set(workflow_param[ref][elem])
            entrystring.trace('w', lambda name, index, mode,
                                          elem=elem, entrystring=entrystring,
                                          ref=ref: update_workflow_param(workflow_param,ref,
                                                                         elem,
                                                                         entrystring.get()))
            # if an entry is changed, the new values should immediately be changed
            # in the workflow_param dictionary
            tkinter.Entry(fr_wfp, textvariable=entrystring, bg=col.c1).grid(row=irow,
                                                                column=1,
                                                                padx=1,
                                                                pady=2,
                                                                sticky='e')
            irow += 1


    ## MIDDLE - SELECTING THE ACTORS
    rrow = 0
    for ref in [actors_ref, make_core_ref]:
        for hsys in maindict[ref]:
            tkinter.Label(fr_as, text=hsys, bg=col.c1, font='15').grid(row=rrow,
                                                           column=0,
                                                           columnspan=2,
                                                           sticky='ew')
            rrow += 1
            for cat in maindict[ref][hsys]:
                tkinter.Label(fr_as,text=cat,bg=col.c1,anchor=tkinter.W,\
                              justify=tkinter.LEFT).grid(row=rrow,column=0,sticky=tkinter.W)
                cb = tkinter.ttk.Combobox(fr_as, value=['']+list(maindict[ref][hsys][cat]))
                cb.grid(row=rrow, column=1, padx=20, pady=5, sticky='ew')
                cb.current(workflow_param[cod_ref][cat])
                cb.bind('<<ComboboxSelected>>',lambda event, cat=cat, cb=cb: \
                        update_workflow_param(workflow_param,cod_ref,cat,str(cb.current())))
                rrow += 1

    # -------------------------------------------------------------------------------------

    # Class to not re-generate a new folder name between two 'save' statements
    class saved_folder_name(object):
        def __init__(self):
            self.value = None
        def NoAction(self):
            self.value = self.value
        def Save(self,chosen_folder,init_folder):
            if chosen_folder == init_folder: # 1st SAVE, or SAVE after a LOAD (but before a SAVE AS)
                self.value=save(self.value,default_wf_param_file,maindict[actors_ref],\
                        uncompiled_actors,workflow_param,wfp_ref,fur_ref,cod_ref,cat)
            else:
                if chosen_folder is None:
                    if self.value is None: # 1st SAVE after a LOAD
                        self.value=save(init_folder,default_wf_param_file,\
                            maindict[actors_ref],uncompiled_actors,workflow_param, \
                            wfp_ref,fur_ref,cod_ref,cat)
                    else: # SAVE after a SAVE AS which is after a LOAD
                        self.value=save(self.value,default_wf_param_file, \
                            maindict[actors_ref],uncompiled_actors,workflow_param, \
                            wfp_ref,fur_ref,cod_ref,cat)
                else: # SAVE AS
                    if_cancelled = self.value
                    self.value=save(chosen_folder,default_wf_param_file,maindict[actors_ref], \
                            uncompiled_actors,workflow_param,wfp_ref,fur_ref,cod_ref,cat)
                    if self.value is None:
                        self.value = if_cancelled
            return self.value

    saved_folder = saved_folder_name()

    # -------------------------------------------------------------------------------------

    # To use the folder loaded through the 'load' function for the next 'save' statements
    if wf_param_file == default_wf_param_file:
        init_folder = None
    else:
        init_folder = ('/').join(wf_param_file.split('/')[:-1])

    # -------------------------------------------------------------------------------------

    ## RIGHT - FLOWCHART

    # Left panel
    button_loadconfig = tkinter.Button(fr_wfp, text='Load', bg=col.c2)
    button_loadconfig.grid(row=51, column=0, padx=5, pady=5, sticky='ew')
    button_loadconfig.configure(command=lambda: load(tkinter.filedialog.\
                                askdirectory(initialdir=os.path.join(os.getcwd(),'data')),open_gui))

    button_saveconfig = tkinter.Button(fr_wfp, text='Save', bg=col.c2)
    button_saveconfig.grid(row=52, column=0, padx=5, pady=5, sticky='ew')
    button_saveconfig.configure(command=lambda: saved_folder.Save(None,init_folder))

    button_saveas = tkinter.Button(fr_wfp, text='Save as', bg=col.c2)
    button_saveas.grid(row=53, column=0, padx=5, pady=5, sticky='ew')
    button_saveas.configure(command=lambda: saved_folder.Save(tkinter.filedialog.\
                            askdirectory(initialdir=os.path.join(os.getcwd(),'data')),init_folder))

    button_saveandrun = tkinter.Button(fr_wfp, text='Run', bg=col.c2, state='normal')
    button_saveandrun.grid(row=51, column=1, padx=5, pady=5, sticky='ew')
    button_saveandrun.configure(command=lambda: run(saved_folder.Save(None,init_folder)))

    button_restore_def = tkinter.Button(fr_wfp, text='Restore Default', bg=col.c2)
    button_restore_def.grid(row=52, column=1, padx=5, pady=5, sticky='ew')
    button_restore_def.configure(command=lambda: open_gui(default_wf_param_file))

    button_exit = tkinter.Button(fr_wfp, text='Exit', bg='light grey')
    button_exit.grid(row=55, column=0, padx=5, pady=5, sticky='w')
    button_exit.configure(command=lambda: sys.exit())

    # Middle panel
    button_edit_codeparameters = tkinter.Button(fr_as, text='Edit Code Parameters', bg=col.c2)
    button_edit_codeparameters.grid(row=53, column=0, padx=5, pady=5, sticky='ew')
    button_edit_codeparameters.configure(command=lambda: edit_codeparam\
    (maindict,actors_ref,workflow_param,cod_ref,saved_folder.Save(None,init_folder)))

    button_create_flowchart = tkinter.Button(fr_as, text='Show Flowchart', bg=col.c2)
    button_create_flowchart.grid(row=53, column=1, padx=5, pady=5, sticky='ew')
    button_create_flowchart.configure(command=lambda: destr_and_make\
                (removed_by_close_button, window, maindict,workflow_param))

    window.mainloop()

#---------------------------------------------------------------------------------------------
if __name__ == "__main__":

    open_gui(default_wf_param_file)

