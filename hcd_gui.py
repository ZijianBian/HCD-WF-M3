import os, sys, copy
from shutil import copy2, copytree, rmtree
from inspect import getfile
from interface_functions import save_workflow_param_to_file, \
    save, run, save_codeparam_to_file, destr_and_make, \
    load_configuration, update_workflow_param
    #update_workflow_param
from edit_code_parameters import edit_codeparam

try:
    from tkinter import *
    from tkinter import filedialog, ttk
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
    from create_workflow_param import create_workflow_param_from_file
    from hover_class import *
    from hcd_wrapper import hcd_wrapper
    from simple_flowchart import make_flowchart
    from hcd_tools import import_actor, create_maindict, loadlist
except:
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
# Colors to be used later

c1 = 'white'
c2 = 'white smoke'
c3 = 'azure2'
c4 = 'ghost white'
c5 = 'azure4'
cb = 'LavenderBlush3'

# --------------------------------------------------------------------------------------------
# Create the main window (define font, title and background colour)
window = Tk()
fontsize = int(window.winfo_screenheight()/100)+3 # Adjusted with screen size
if fontsize > 14:
    fontsize = 14
if fontsize < 5:
    fontsize = 5
window.option_add('*font','courier '+str(fontsize))
window.title('HCD WORKFLOW')
window.configure(bg=c1)

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
    workflow_param = create_workflow_param_from_file(wf_param_file)

    ### setup

    fr_wfp = Frame(window, width=300, height=500, background=c3)
    fr_wfp.grid(row=0, column=0, rowspan=2, sticky='nwes', padx=3, pady=3)

    fr_as = Frame(window, width=500, height=500, background=c1)
    fr_as.grid(row=0, column=1, rowspan=2, sticky='nwes', padx=3, pady=3)

    fr_fc = Frame(window, width=500, height=500, background=c1)
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

        Label(fr_wfp, text=ref, bg=c3, font='15').grid(row=irow,
                                                       column=0,
                                                       columnspan=3,
                                                       pady=10,
                                                       padx=5,
                                                       sticky='we')
        irow += 1

        for elem in workflow_param[ref]:

            Label(fr_wfp, text=elem, bg=c3).grid(row=irow,
                                                 column=0,
                                                 padx=1,
                                                 pady=2,
                                                 sticky='w')

            entrystring = StringVar()
            entrystring.set(workflow_param[ref][elem])
            entrystring.trace('w', lambda name, index, mode,
                                          elem=elem, entrystring=entrystring,
                                          ref=ref: update_workflow_param(workflow_param,ref,
                                                                         elem,
                                                                         entrystring.get()))
            # if an entry is changed, the new values should immediately be changed
            # in the workflow_param dictionary
            Entry(fr_wfp, textvariable=entrystring, bg=c1).grid(row=irow,
                                                                column=1,
                                                                padx=1,
                                                                pady=2,
                                                                sticky='e')
            irow += 1


    ## MIDDLE - SELECTING THE ACTORS
    rrow = 0
    for ref in [actors_ref, make_core_ref]:
        for hsys in maindict[ref]:
            Label(fr_as, text=hsys, bg=c1, font='15').grid(row=rrow,
                                                           column=0,
                                                           columnspan=2,
                                                           sticky='ew')
            rrow += 1
            for cat in maindict[ref][hsys]:
                Label(fr_as, text=cat, bg=c1, anchor=W, justify=LEFT).grid(row=rrow,
                                                                           column=0,
                                                                           sticky=W)
                cb = ttk.Combobox(fr_as, value=['']+list(maindict[ref][hsys][cat]))
                cb.grid(row=rrow, column=1, padx=20, pady=5, sticky='ew')
                cb.current(workflow_param[cod_ref][cat])
                cb.bind('<<ComboboxSelected>>',
                        lambda event, cat=cat, cb=cb: update_workflow_param(workflow_param,cod_ref,
                                                                            cat,
                                                                            str(cb.current())))
                rrow += 1


    ## RIGHT - FLOWCHART

    # Left panel
    button_loadconfig = Button(fr_wfp, text='Load', bg=c2)
    button_loadconfig.grid(row=51, column=0, padx=5, pady=5, sticky='ew')
    button_loadconfig.configure(command=lambda: load_configuration(filedialog.askdirectory(initialdir=os.path.join(os.getcwd(),'data'))))
    class save_only_once(object):
        def __init__(self):
            self.value = None
        def Return(self,chosen_folder):
            if chosen_folder is None:
                self.value=save(self.value,default_wf_param_file,maindict[actors_ref],uncompiled_actors,workflow_param,wfp_ref,fur_ref,cod_ref,cat)
            else:
                self.value=save(chosen_folder,default_wf_param_file,maindict[actors_ref],uncompiled_actors,workflow_param,wfp_ref,fur_ref,cod_ref,cat)
            return self.value

    saving_state = save_only_once()

    button_saveconfig = Button(fr_wfp, text='Save', bg=c2)
    button_saveconfig.grid(row=52, column=0, padx=5, pady=5, sticky='ew')
    button_saveconfig.configure(command=lambda: saving_state.Return(None))

    button_saveas = Button(fr_wfp, text='Save as', bg=c2)
    button_saveas.grid(row=53, column=0, padx=5, pady=5, sticky='ew')
    button_saveas.configure(command=lambda: saving_state.Return(filedialog.askdirectory(initialdir=os.path.join(os.getcwd(),'data'))))

    button_saveandrun = Button(fr_wfp, text='Run', bg=c2, state='normal')
    button_saveandrun.grid(row=51, column=1, padx=5, pady=5, sticky='ew')
    button_saveandrun.configure(command=lambda: run(saving_state.Return(None)))

    button_restore_def = Button(fr_wfp, text='Restore Default', bg=c2)
    button_restore_def.grid(row=52, column=1, padx=5, pady=5, sticky='ew')
    button_restore_def.configure(command=lambda: open_gui(default_wf_param_file))

    button_exit = Button(fr_wfp, text='Exit', bg='light grey')
    button_exit.grid(row=55, column=0, padx=5, pady=5, sticky='w')
    button_exit.configure(command=lambda: sys.exit())

    # Middle panel
    button_edit_codeparameters = Button(fr_as, text='Edit Code Parameters', bg=c2)
    button_edit_codeparameters.grid(row=53, column=0, padx=5, pady=5, sticky='ew')
    button_edit_codeparameters.configure(command=lambda: edit_codeparam())

    button_create_flowchart = Button(fr_as, text='Show Flowchart', bg=c2)
    button_create_flowchart.grid(row=53, column=1, padx=5, pady=5, sticky='ew')
    button_create_flowchart.configure(command=lambda: destr_and_make(removed_by_close_button, window, maindict,workflow_param,c1,c2,c3,c4,c5))

    window.mainloop()

#---------------------------------------------------------------------------------------------
if __name__ == "__main__":

    open_gui(default_wf_param_file)

