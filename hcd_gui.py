import os, sys, copy
from datetime import datetime
from shutil import copy2, copytree, rmtree
from inspect import getfile
import argparse

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
root1 = etree.parse(default_wf_param_file).getroot()

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

def open_gui(wf_param_file, norun, input_dir, output_dir):

    # ----------------------

    # Define the current folder and current workflow parameter file
    current_config_folder = os.path.join(os.getenv('HCD_FOLDER'),'data/run_'+datetime.now().strftime('D%d_M%m_Y%y_H%H%M%S'))
    current_wf_param_file = current_config_folder+ '/input_workflow.xml'

    # Create the current configuration folder and its sub-folders for each HCD process
    os.makedirs(current_config_folder)
    for systemname in root1[2][0]:
        os.makedirs(current_config_folder+'/'+systemname.tag)

    # Copy the default workflow parameter file into the current one
    copy2(default_wf_param_file, current_wf_param_file,follow_symlinks=True)

    # ----------------------

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

    def load_configuration_from_file(filepath):
        if 'input_workflow_default.xml' in filepath:
            print('if you want to load the default configuration '
                  'please choose load default')
            filepath = ()
        elif 'input_workflow.xml' not in filepath:
            print('please choose an input_workflow.xml file')
            filepath = ()
        print(filepath)
        if filepath is not ():
            source_folder = "/".join(filepath.split('/')[0:-1])
            if source_folder.find(current_config_folder) is -1:
                try:
                    copytree(source_folder, current_config_folder)
                except:
                    rmtree(current_config_folder)
                    copytree(source_folder, current_config_folder)
                open_gui(current_config_folder+ '/input_workflow.xml', norun, None, None)
            else:
                print('this folder is the current folder. '
                      'it is not possible to load the current configuration')
        else:
            print('no file selected')

    if output_dir is not None:
        current_config_folder = output_dir
        run_config_param_path = current_config_folder+ '/input_workflow.xml'

    if input_dir is not None:
        load_configuration_from_file(input_dir+ '/input_workflow.xml')

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
    if not os.path.exists(current_config_folder):
        for systemname in maindict[list(maindict.keys())[0]]:
            os.makedirs(current_config_folder+'/'+systemname)
            copy2(wf_param_file, current_wf_param_file, follow_symlinks=True)

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
                                          ref=ref: update_workflow_param(ref,
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
                        lambda event, cat=cat, cb=cb: update_workflow_param(cod_ref,
                                                                            cat,
                                                                            str(cb.current())))
                rrow += 1


    ## RIGHT - FLOWCHART



    ## BUTTONS

    run_state = 'normal'
    if norun:
        run_state = 'disabled'

    # left:
    button_saveconfig = Button(fr_wfp, text='Save Configuration', bg=c2)
    button_saveconfig.grid(row=52, column=0, padx=5, pady=5, sticky='ew')
    button_saveconfig.configure(command=lambda:
                                save_workflow_param_to_file(current_config_folder))
    # save xml to the run folder
    button_loadconfig = Button(fr_wfp, text='Load Configuration', bg=c2)
    button_loadconfig.grid(row=52, column=1, padx=5, pady=5, sticky='ew')
    button_loadconfig.configure(command=lambda:
                                load_configuration_from_file(filedialog.askopenfilename(
                                    initialdir=os.path.join(os.getcwd(), 'run_configurations'))))

    button_saveandrun = Button(fr_wfp, text='Save and Run', bg=c2, state=run_state)
    button_saveandrun.grid(row=51, column=0, padx=5, pady=5, sticky='ew')
    button_saveandrun.configure(command=lambda: save_and_run(current_config_folder, True))

    button_run_nosave = Button(fr_wfp, text='Run (without Saving)', bg=c2, state=run_state)
    button_run_nosave.grid(row=51, column=1, padx=5, pady=5, sticky='ew')
    button_run_nosave.configure(command=lambda: save_and_run(current_config_folder, False))

    button_save_asdef = Button(fr_wfp, text='Save Configuration as Default', bg=c2)
    button_save_asdef.grid(row=53, column=0, padx=5, pady=5, sticky='ew')
    button_save_asdef.configure(command=lambda:
                                save_workflow_param_to_file('input_workflow_default.xml'))

    button_restore_def = Button(fr_wfp, text='Restore Default', bg=c2)
    button_restore_def.grid(row=53, column=1, padx=5, pady=5, sticky='ew')
    button_restore_def.configure(command=lambda:
                                 open_gui('input_workflow_default.xml', norun, None, None))

    button_saveas = Button(fr_wfp, text='Save as', bg=c2)
    button_saveas.grid(row=54, column=0, padx=5, pady=5, sticky='ew')
    button_saveas.configure(command=lambda: save_as())

    button_exit = Button(fr_wfp, text='Exit', bg='light grey')
    button_exit.grid(row=55, column=0, padx=5, pady=5, sticky='w')
    button_exit.configure(command=lambda: sys.exit())


    # middle:
    button_create_flowchart = Button(fr_as, text='Show Flowchart', bg=c2)
    button_create_flowchart.grid(row=53, column=1, padx=5, pady=5, sticky='ew')
    button_create_flowchart.configure(command=lambda:
                                      destr_and_make(
                                          removed_by_close_button, window, maindict,
                                          workflow_param, c1, c2, c3, c4, c5))

    def destr_and_make(removed_by_close_button, window, maindict,
                       workflow_param, c1, c2, c3, c4, c5):

        base = make_flowchart(removed_by_close_button, window, maindict,
                              workflow_param, c1, c2, c3, c4, c5)
        removed_by_close_button.append(base)

    button_edit_codeparameters = Button(fr_as, text='Edit Codeparameters', bg=c2)
    button_edit_codeparameters.grid(row=53, column=0, padx=5, pady=5, sticky='ew')
    button_edit_codeparameters.configure(command=lambda: edit_codeparam())


    ## MANAGE XML FILES
    def edit_codeparam():
        cp_top = Toplevel()
        cp_top.title('Edit Code Parameters')
        cp_top.geometry('500x700')

        fr_ab = Frame(cp_top, width=200, height=650, bg=c4)
        fr_ab.grid(row=0, column=0, rowspan=2, sticky='ns')

        fr_main = Frame(cp_top, width=500, height=650, bg=c1)
        fr_main.grid(row=1, column=2, sticky='nwes')
        fr_main.grid_propagate(0)
        prev_frame = Canvas(fr_main, width=500, height=1500)

        fr_top = Frame(cp_top, width=500, height=50, bg=c2)
        fr_top.grid(row=0, column=1, sticky='ew', columnspan=2)

        for hsys in maindict[actors_ref]:
            la_sys = Label(fr_ab, text=hsys, bg=c4)
            for cat in maindict[actors_ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    la_sys.grid(padx=5, pady=5, sticky='ew')

                    curval = list(maindict[actors_ref][hsys][cat].keys())[int(
                        workflow_param[cod_ref][cat])-1]
                    Button(fr_ab, text=curval, bg=c2,
                           command=lambda actor_name=curval,
                                          hsys=hsys: make_frame(hsys,
                                                                actor_name,
                                                                prev_frame,
                                                                False)).grid(padx=5,
                                                                             pady=5,
                                                                             sticky='ew')

        def make_frame(hsys, actor_name, prev_frame, is_load_default_from_kepler):
            prev_frame.grid_remove()
            prev_frame.grid_forget()

            def populate(frame):
                codeparam_xml_path = StringVar()
                codeparam_xsd_path = StringVar()

                ## name of the codeparam file in the run_config_folder
                dest_file = os.path.join(current_config_folder+'/'+hsys
                                         +'/input_'+actor_name+'.xml')

                import_actor(actor_name,0)
                actor_python_folder = eval(actor_name+'.location')
                found_xml = False
                found_xsd = False

                with open(actor_python_folder+'/wrapper.py') as pfile:

                    for iline in pfile:
                        if 'xml_location = ' in iline and '_default_xml_location' not in iline:
                            ## check if there is already is a version of the xml file for this actor
                            ## - this could be put outside of the loop for reading the file,
                            ## but the code is shorter this way, it shouldnt be too confusing i hope
                            if os.path.exists(dest_file) and is_load_default_from_kepler is False:
                                ## if yes, use that one as xml
                                codeparam_xml_path.set(dest_file)
                            else:
                                ## if not, OR it is supposed to load the default, use the one we just found
                                xml_name = iline.split('+')[-1].replace("'","").replace(" ","").replace("\n","")
                                codeparam_xml_path.set(actor_python_folder+xml_name)
                                copy2(codeparam_xml_path.get(), dest_file, follow_symlinks=True)
                            found_xml = True

                        if 'xsd_location = ' in iline:
                            xsd_name = iline.split('+')[-1].replace("'","").replace(" ","").replace("\n","")
                            codeparam_xsd_path.set(actor_python_folder+xsd_name)
                            found_xsd = True

                        if found_xml is True and found_xsd is True:
                            break

                #### read the additional information from the xsd file
                try:
                    xmlschema_doc = etree.parse(codeparam_xsd_path.get())
                    root_xsd = xmlschema_doc.getroot()
                    xmlschema = etree.XMLSchema(xmlschema_doc)
                    docum_dict = {}
                    for elem in root_xsd.iter():
                        if elem.tag == '{http://www.w3.org/2001/XMLSchema}element':
                            for i in elem.iter():
                                if i.tag == '{http://www.w3.org/2001/XMLSchema}documentation':
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
                    if elem.tag is not etree.Comment and len(elem) == 0:
                        l = Label(fr, text=elem.tag.strip(), bg=c1,
                                  wraplength='200', anchor='w', justify=LEFT)
                        l.grid(row=rrow, column=ccolumn, sticky='w')

                        entrystring = StringVar()
                        entrystring.set(elem.text.strip())
                        e = Entry(fr, textvar=entrystring, bg=c1)
                        e.grid(row=rrow, column=ccolumn+1, padx=3, pady=3)
                        codeparam_dict[elem.tag] = entrystring.get()

                        entrystring.trace('w', lambda name, index, mode,
                                                      elem=elem.tag, entrystring=entrystring,
                                                      e=e: update_codeparam_dict(elem,
                                                                                 entrystring.get(),
                                                                                 e))

                        try:
                            CreateToolTip(l, docum_dict[l.cget('text')])
                        except:
                            pass

                        def update_codeparam_dict(elem, newvalue, entry1):
                            codeparam_dict[elem] = newvalue
                            for i in root.iter():
                                if elem in [str(i.tag)] and i.tag is not etree.Comment:
                                    i.text = newvalue
                            if xmlschema.validate(root):
                                entry1.config(bg=c1)
                            else:
                                entry1.config(bg='salmon1')

                        rrow += 1

                        if rrow > 20:
                            v_scroll.grid(row=1, column=1, sticky='ns')
                        else:
                            v_scroll.grid_remove()

                return dest_file, codeparam_dict

            # end of populate frame

            def onFrameConfigure(canvas):
                canvas.configure(scrollregion=canvas.bbox('all'))

            canvas = Canvas(cp_top, borderwidth=0, highlightthickness=0, background=c1)
            fr = Frame(canvas, width=500, height=1500, bg=c1)
            prev_frame = fr
            v_scroll = Scrollbar(cp_top, orient='vertical', command=canvas.yview)
            canvas.configure(yscrollcommand=v_scroll.set)
            #  v_scroll.grid()


            canvas.grid(row=1, column=2, sticky=' news')
            canvas.create_window((4, 4), window=fr, anchor='nw')

            #  fr.grid_propagate(0)
            fr.bind('<Configure>', lambda event, canvas=canvas: onFrameConfigure(canvas))

            dest_file, codeparam_dict = populate(fr)

            Button(fr_top, text='save', bg=c2, command=lambda:
                   save_codeparam_to_file(dest_file, codeparam_dict)).grid(
                       row=0, column=1, padx=5, pady=5)
            Button(fr_top, text='load default', bg=c2, command=lambda:
                   make_frame(hsys, actor_name, prev_frame, True)).grid(
                       row=0, column=2, padx=5, pady=5)
            Button(fr_top, text='exit', bg=c2, command=lambda:
                   cp_top.destroy()).grid(row=0, column=4, padx=(20, 5), pady=5)

            dest_file, codeparam_dict = populate(fr)

    ## FUNCTIONS - SAVING & UPDATING

    def update_workflow_param(ref, elem, newvalue):
        workflow_param[ref][elem] = newvalue

    def save_workflow_param_to_file(filepath):
        if filepath == '':
            filepath = current_config_folder

        ## COPY
        ## for all the active actors
        for hsys in maindict[actors_ref]:
            for cat in maindict[actors_ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    actor_name = list(maindict[actors_ref][hsys][cat].keys())[
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
                        #actor_python_folder = ACTOR_FOLDER+'/'+actor_name+'/'+actor_name
                        found_xml = False
                        found_xsd = False

                        with open(actor_python_folder+'/wrapper.py') as pfile:
                            for iline in pfile:
                                if 'xml_location = ' in iline and \
                                   '_default_xml_location' not in iline:
                                    xml_name = iline.split('+')[-1].replace("'","").replace(" ","").replace("\n","")
                                    # IF XML_NAME IS TOO SMALL: IT MEANS THERE IS NO INPUT XML FILE (NOTHING TO COPY)
                                    if len(xml_name) > 5:
                                        copy2(actor_python_folder+xml_name, dest_file,
                                              follow_symlinks=True)
                                    break

        if 'xml' not in filepath[-4:]:
            filepath = filepath+'/input_workflow.xml'

        tree = etree.parse(filepath)
        root = tree.getroot()

        rl = [wfp_ref, fur_ref, cod_ref]

        for iroot in range(3):
            for elem in root[iroot].iter():
                if elem.tag is not etree.Comment and len(elem) == 0:
                    elem.text = workflow_param[rl[iroot]][elem.tag]

        tree.write(filepath)
        return True

    def save_as():
        filepath = filedialog.askdirectory()

        old_current_config_folder = copy.copy(current_config_folder)

        if os.path.exists(filepath):

            current_config_folder = copy.copy(filepath)
            save_workflow_param_to_file(current_config_folder)
            if old_current_config_folder is not current_config_folder:
                rmtree(old_current_config_folder)

        else:
            copytree(current_config_folder, filepath)
            current_config_folder = copy.copy(filepath)
            save_workflow_param_to_file(current_config_folder)

            if old_current_config_folder is not current_config_folder:
                rmtree(old_current_config_folder)

    def save_and_run(filepath, save_yn):
        noerror = save_workflow_param_to_file(filepath)
        if noerror:
        #window.destroy()
            hcd_wrapper(current_config_folder)

            if save_yn == 0:
                rmtree(current_config_folder)

    def save_codeparam_to_file(filepath, codeparam_dict):

        tree = etree.parse(filepath)
        root = tree.getroot()

        for elem in root.iter():
            if elem.tag is not etree.Comment and len(elem) == 0:
                elem.text = codeparam_dict[elem.tag]
        pass

        tree.write(filepath)

    window.mainloop()

#---------------------------------------------------------------------------------------------
if __name__ == "__main__":

    # Parse optional arguments
    # Invoke script with -h to list arguments

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="GUI for Heating and Current Drive actor")

    parser.add_argument("-s", "--norun", action="store_true",
                        help="Disable all run options (i.e. allow setup only)")

    parser.add_argument("-i", "--input_dir", default=None,
                        help="Directory containing primary XML file")

    parser.add_argument("-o", "--output_dir", default=None,
                        help="Directory in which to save copies of the XML files "
                        "(overriding the default time-stamped directory)")

    args = parser.parse_args()

    open_gui(default_wf_param_file, args.norun, args.input_dir, args.output_dir)

