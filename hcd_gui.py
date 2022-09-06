import os,sys,copy

try:
    import tkinter
    import tkinter.ttk
    import tkinter.filedialog
    import tkinter.font as font
except:
    print("ERROR: tkinter not found", file=sys.stderr)
    print(
        "---> TIP: load the HCD module or source the configuration file",
        file=sys.stderr,
    )
    sys.exit()

try:
    from lxml import etree
except:
    print("ERROR: lxml module not found", file=sys.stderr)
    print(
        "---> TIP: load the HCD module or source the configuration file",
        file=sys.stderr,
    )
    sys.exit()

try:
    import colour_definitions.bluish as col
    from wf_tools import (
        import_actor,
        create_workflow_param_from_file,
        dict_merge,
        save,
        run,
        destr_and_make,
        update_workflow_param,
        loadlist,
        load,
        create_maindict,
        saved_folder_name,
)
    from gui_tools import edit_codeparam, edit_waveforms
except:
    raise
    print("ERROR while loading internal HCD modules", file=sys.stderr)
    print(
        "---> TIP: load the HCD module or source the configuration file",
        file=sys.stderr,
    )
    sys.exit()

# --------------------------------------------------------------------------------------------
# Path to the default parameter file

hcd_path = "/".join(os.path.realpath(__file__).split("/")[:-1])
default_wf_param_file = hcd_path + "/global_configuration/input_workflow_default.xml"

# --------------------------------------------------------------------------------------------
# Create the main window (define font, title and background colour)
window = tkinter.Tk()
fontsize = int(window.winfo_screenheight() / 100) + 3  # Adjusted with screen size
if fontsize > 10:
    fontsize = 10
if fontsize < 5:
    fontsize = 5
window.option_add("*font", "courier " + str(fontsize))
window.title("HCD WORKFLOW")
window.configure(bg=col.c1)

# --------------------------------------------------------------------------------------------
def open_gui(wf_param_file):

    # CHECK THAT MANDATORY ACTORS ARE THERE
    file = os.path.dirname(os.path.abspath(__file__))\
                + "/global_configuration/" + "global_lists.yaml"
    merge_actor_list = loadlist(file,"merge_actor_list")
    process_list = loadlist(file,"process_list")
    err_global = 0
    for actor in merge_actor_list:
        err = import_actor(actor, 1)
        err_global = err_global + err
    if err_global != 0:
        print("---------------------------------------------", file=sys.stderr)
        print("One or more mandatory actor(s) not accessible", file=sys.stderr)
        print("--> Program stopped.", file=sys.stderr)
        print("---------------------------------------------", file=sys.stderr)
        return

    try:
        wh = window.winfo_reqheight()
        ww = window.winfo_reqwidth()
        wx = window.winfo_x()
        wy = window.winfo_y()
        window.geometry("+%d+%d" % (wx, wy))
    except:
        pass

    # LIST OF PRE-CONFIGURED WAVEFORMS
    waveform_folder = os.getenv('EBROOTWAVEFORMMINCOOKER')+'/ITER_PRESETS/'
    #waveform_folder = '/home/ITER/schneim/public/git/waveform-cooker/ITER_PRESETS/'
    waveform_presets = loadlist(file,'waveform_presets')

    # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
    # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)
    (
        maindict,
        compiled_actors,
        uncompiled_actors,
        code_selection,
        catlist,
    ) = create_maindict(wf_param_file, 1)

    workflow_param = create_workflow_param_from_file(wf_param_file)

    # Setup

    fr_wfp = tkinter.Frame(window, width=300, height=500, background=col.c3)
    fr_wfp.grid(row=0, column=0, rowspan=2, sticky="nwes", padx=3, pady=3)

    fr_as = tkinter.Frame(window, width=500, height=500, background=col.c1)
    fr_as.grid(row=0, column=1, rowspan=2, sticky="nwes", padx=3, pady=3)

    fr_fc = tkinter.Frame(window, width=500, height=500, background=col.c1)
    fr_fc.grid(row=0, column=2, rowspan=2, sticky="nwes", padx=3, pady=3)

    removed_by_close_button = [fr_fc]
    fr_fc.grid_remove()

    ## LEFT - CONFIGURING THE WORKFLOW PARAMETERS
    tkinter.Label(fr_wfp, text=workflow_param['workflow_parameters'][1], bg=col.c3, font=('Courier',fontsize,'bold')).grid(
        row=0, column=0, columnspan=3, pady=10, padx=5, sticky="we"
    )
    irow = 1
    for elem in workflow_param['workflow_parameters'][0]:

        elem_name = workflow_param['workflow_parameters'][0][elem][1]

        label = tkinter.Label(fr_wfp, text=elem_name, bg=col.c3).grid(
            row=irow, column=0, padx=1, pady=2, sticky="w"
        )

        # Catch any update of the variable from the interface
        entrystring = tkinter.StringVar()
        entrystring.set(workflow_param['workflow_parameters'][0][elem][0])
        entrystring.trace(
            "w",
            lambda name, index, mode, elem=elem, entrystring=entrystring,
            ref='workflow_parameters': update_workflow_param(
                workflow_param, 'workflow_parameters', '', '', elem, entrystring.get()
            ),
        )
        # if an entry is changed, the new values should immediately be changed
        # in the workflow_param dictionary
        tkinter.Entry(fr_wfp, textvariable=entrystring, bg=col.c1).grid(
            row=irow, column=1, padx=1, pady=2, sticky="e"
        )
        irow += 1

    ## MIDDLE - SELECTING THE ACTORS
    rrow = 0
    complex_button = {}
    for main_key in maindict.keys():
        for category in maindict[main_key]:
            tkinter.Label(fr_as, text=workflow_param['actor_selection'][0][main_key][0][category][1], \
                          bg=col.c1, font=('Courier',fontsize,'bold'),fg='darkcyan').grid(
                row=rrow, column=0, columnspan=2, sticky="w"
            )
            rrow += 1

            for process in maindict[main_key][category]:
                process_name = workflow_param['actor_selection'][0][main_key][0][category][0][process][1]
                proc_dict = copy.deepcopy(maindict[main_key][category][process])
                tkinter.Label(
                    fr_as, text=' - '+process_name, bg=col.c1, anchor=tkinter.W, justify=tkinter.LEFT
                ).grid(row=rrow, column=0, sticky=tkinter.W)
                cb = tkinter.ttk.Combobox(
                    fr_as, value=[""] + list(proc_dict)
                )
                cb.grid(row=rrow, column=1, padx=20, pady=5, sticky="ew")
                cb.current(workflow_param['actor_selection'][0][main_key][0][category][0][process][0])
                cb.bind(
                    "<<ComboboxSelected>>",
                    lambda event, main_key=main_key, process=process, cb=cb, category=category: update_workflow_param(
                        workflow_param, 'actor_selection', main_key, category, process, str(cb.current())
                    ),
                )
                complex_button[process] = tkinter.Button(master=fr_as,text="Time Base",bg=col.c2)
                complex_button[process]['font'] = font.Font(size=8)
                complex_button[process].config(activebackground=col.c4)
                complex_button[process].grid(row=rrow, column=2, padx=0, pady=0, sticky="w")
                complex_button[process].configure(command=lambda process=process: cm.complex_mode(fr_as,process,workflow_param))
                font.Font(size=fontsize)
                rrow += 1

    # -------------------------------------------------------------------------------------

    saved_folder = saved_folder_name(default_wf_param_file,maindict,
                 uncompiled_actors,workflow_param,'workflow_parameters','actor_selection',process_list)

    # -------------------------------------------------------------------------------------

    # To use the folder loaded through the 'load' function for the next 'save' statements
    if wf_param_file == default_wf_param_file:
        init_folder = None
    else:
        init_folder = ("/").join(wf_param_file.split("/")[:-1])

    # -------------------------------------------------------------------------------------

    ## RIGHT - FLOWCHART

    # Left panel
    button_loadconfig = tkinter.Button(fr_wfp, text="Load", bg=col.c2)
    button_loadconfig.grid(row=52, column=0, padx=5, pady=5, sticky="ew")
    button_loadconfig.configure(
        command=lambda: load(
            tkinter.filedialog.askdirectory(
                initialdir=os.path.join(os.getcwd(), "data")
            ),
            open_gui,
            process_list,
        )
    )

    button_saveconfig = tkinter.Button(fr_wfp, text="Save", bg=col.c2)
    button_saveconfig.grid(row=53, column=0, padx=5, pady=5, sticky="ew")
    button_saveconfig.configure(command=lambda: saved_folder.Save(None, init_folder))

    button_saveas = tkinter.Button(fr_wfp, text="Save as", bg=col.c2)
    button_saveas.grid(row=54, column=0, padx=5, pady=5, sticky="ew")
    button_saveas.configure(
        command=lambda: saved_folder.Save(
            tkinter.filedialog.askdirectory(
                initialdir=os.path.join(os.getcwd(), "data")
            ),
            init_folder,
        )
    )

    button_loadlconfig = tkinter.Button(fr_wfp, text="Load latest", bg=col.c2)
    button_loadlconfig.grid(row=52, column=1, padx=5, pady=5, sticky="ew")
    button_loadlconfig.configure(command=lambda: load("latest", open_gui, process_list))

    button_saveandrun = tkinter.Button(fr_wfp, text="Run", bg=col.c2, state="normal")
    button_saveandrun.grid(row=53, column=1, padx=5, pady=5, sticky="ew")
    button_saveandrun.configure(
        command=lambda: run(saved_folder.Save(None, init_folder))
    )

    button_restore_def = tkinter.Button(fr_wfp, text="Restore Default", bg=col.c2)
    button_restore_def.grid(row=54, column=1, padx=5, pady=5, sticky="ew")
    button_restore_def.configure(command=lambda: open_gui(default_wf_param_file))

    button_exit = tkinter.Button(fr_wfp, text="Exit", bg="light grey")
    button_exit.grid(row=56, column=0, padx=5, pady=5, sticky="w")
    button_exit.configure(command=lambda: sys.exit())

    # Middle panel
    button_edit_codeparameters = tkinter.Button(
        fr_as, text="Edit Code Parameters", bg=col.c2
    )
    button_edit_codeparameters.grid(row=53, column=0, padx=5, pady=5, sticky="ew")
    button_edit_codeparameters.configure(
        command=lambda: edit_codeparam(
            maindict,
            workflow_param,
            saved_folder.Save(None, init_folder),
        )
    )

    button_edit_waveforms = tkinter.Button(fr_as, text="Edit H&CD waveforms", bg=col.c2)
    button_edit_waveforms.grid(row=53, column=1, padx=5, pady=5, sticky="ew")
    button_edit_waveforms.configure(
        command=lambda: edit_waveforms(\
            waveform_presets,waveform_folder,saved_folder.Save(None, init_folder)))

    window.mainloop()


# ---------------------------------------------------------------------------------------------
if __name__ == "__main__":

    open_gui(default_wf_param_file)
