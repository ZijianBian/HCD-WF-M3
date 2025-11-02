import glob
import os
import sys
try:
    import tkinter as tk
except:
    pass
from inspect import getmodule, stack
from shutil import copy2

import numpy as np
from lxml import etree

from gui.tooltip import CreateToolTip

from .colour_definitions import bluish as col


def string2num(string):

    newstring = string.replace(" ", "").replace("[", "").replace("]", "").split(",")

    if len(newstring) == 1:  # Scalars

        try:
            return int(string)  # Integer scalar
        except Exception as _:  # noqa F841
            None
        try:
            return float(string)  # Float scalar
        except Exception as _:  # noqa F841
            None
        return string  # String scalar

    else:  # Arrays

        try:
            return np.array([int(i) for i in newstring])  # Integer array
        except Exception as _:  # noqa F841
            None
        try:
            return np.array([float(i) for i in newstring])  # Float array
        except Exception as _:  # noqa F841
            None
        return string  # string array


def xml2dict(root):
    children = {}
    for child in root:
        if child.tag != etree.Comment:
            key = child.tag
            if "display" in child.attrib:
                display = child.attrib["display"]
            else:
                display = key
            if len(child) > 0:
                children[key] = [xml2dict(child), display]
            else:
                children[key] = [string2num(child.text), display]

    return children


def create_workflow_param_from_file(workflow_parameters_path):

    # CREATE THE TREE ROOT FROM THE INPUT XML FILE
    tree = etree.parse(workflow_parameters_path)
    root = tree.getroot()

    # CONVERT XML INFORMATION INTO DICTONARY
    workflow_param = xml2dict(root)

    return workflow_param


def load(chosen_folder, open_gui, process_list):

    if chosen_folder == () or chosen_folder == "":
        print("Load cancelled", file=sys.stderr)
        return

    # Optionally load the most recent folder configuration
    if chosen_folder == "latest":
        list_of_folders = glob.glob(os.path.join(os.getcwd(), "data/*"))
        if len(list_of_folders) > 0:
            chosen_folder = max(list_of_folders, key=os.path.getctime)
        else:
            print("No folder found --> Nothing loaded.")
            return

    # Check if the chosen folder is a valid configuration folder
    if not os.path.exists(chosen_folder + "/input_workflow.xml"):
        print(
            "The selected folder " + chosen_folder + " does not appear to be a proper",
            file=sys.stderr,
        )
        print(
            "configuration folder since it contains no input_workflow.xml file " + "--> Nothing loaded.",
            file=sys.stderr,
        )
        return

    for diag_process in process_list:
        if not os.path.exists(chosen_folder + "/" + diag_process):
            print(
                "The selected folder " + chosen_folder + " does not appear to be a proper",
                file=sys.stderr,
            )
            print(
                "configuration folder since it contains no " + diag_process + " folder " + "--> Nothing loaded.",
                file=sys.stderr,
            )
            return

    print("---> Configuration loaded from " + chosen_folder, file=sys.stdout)
    open_gui(chosen_folder + "/input_workflow.xml")


def __syspath_import_actor(actor_name, verbose):

    from importlib import import_module

    # Import the module of the actor
    try:
        _ = import_module(actor_name)  # noqa F841
    except Exception as _:  # noqa F841
        if verbose == 1:
            print("Actor " + actor_name.upper() + " not found.", file=sys.stderr)
        return [], 1

    # Import the actor function
    actor_function = getattr(import_module(actor_name + ".actor"), actor_name)()

    return actor_function, 0


#####################################################################################

# -----------------------------------
# Function to import a physics actor
# -----------------------------------


def import_actor(actor_input, verbose):

    error = 0

    # Import the actor(s) and put into a dictionary
    dictactor = {}
    if isinstance(actor_input, str):
        dictactor[actor_input], error = __syspath_import_actor(actor_input, verbose)
    else:
        for actor_name in actor_input:
            dictactor[actor_name], err = __syspath_import_actor(actor_name, verbose)
            if err == 1:
                error = 1

    # Add this dictionary into the local variables of the calling routine:
    # 1) from interactive sessions, f_locals from current frame is modified
    # 2) when called from a script, the dictionary of the calling module is modified

    # For interactive sessions
    if getmodule(stack()[1].frame) is None:
        stack()[1].frame.f_locals.update(dictactor)
    # When called from a module
    else:
        getmodule(stack()[1].frame).__dict__.update(dictactor)

    return error


def update_codeparam_file(codeparam_destination_path, codeparam_dict, verbose):

    tree = etree.parse(codeparam_destination_path)
    root = tree.getroot()
    root.tail = "\n"
    for elem in root.iter():
        if elem.tag != etree.Comment and len(elem) == 0:
            elem.text = codeparam_dict[elem.tag]
    elem.tail = "\n"
    tree.write(codeparam_destination_path, xml_declaration=True, encoding="UTF-8")

    if verbose == 1:
        print("---> Configuration saved in " + codeparam_destination_path, file=sys.stdout)

    return 0


def update_codeparam_dict_check_xsd(codeparam_dict, elem, newvalue, root=None, xmlschema=None, entry1=None):

    codeparam_dict[elem.tag] = newvalue
    if root is not None:  # Check rules of xsd file
        elem.text = codeparam_dict[elem.tag]
        if xmlschema.validate(root):
            entry1.config(bg=col.c1)
        else:
            entry1.config(bg="salmon1")
    return codeparam_dict


def update_workflow_param(workflow_param, ref, main_key, category, elem, newvalue):
    if main_key == "":
        workflow_param[ref][0][elem][0] = newvalue
    else:
        workflow_param[ref][0][main_key][0][category][0][elem][0] = newvalue
    return workflow_param


def codeparam_interface(
    frame,
    destination_file,
    codeparam_dict,
    docum_dict,
    codeparam_xml_path,
    xmlschema,
    v_scroll,
    default,
):
    tree = etree.parse(codeparam_xml_path)
    root = tree.getroot()

    rrow = 1
    ccolumn = 0

    for elem in root.iter():
        if elem.tag is not etree.Comment and len(elem) == 0:

            # Field for the name of the variable in the interface
            label_name = tk.Label(
                frame,
                text=elem.tag.strip(),
                bg=col.c1,
                wraplength="200",
                anchor="w",
                justify=tk.LEFT,
            )
            label_name.grid(row=rrow, column=ccolumn, sticky="w")

            # Field for the value of the variable: default taken from elem.txt
            entrystring = tk.StringVar()
            entrystring.set(elem.text.strip())
            entry1 = tk.Entry(frame, textvar=entrystring, bg=col.c1)
            entry1.grid(row=rrow, column=ccolumn + 1, padx=3, pady=3)

            # Catch any update of the variable from the interface, and check xsd rules
            entrystring.trace(
                "w",
                lambda name, index, mode, elem=elem, entrystring=entrystring, entry1=entry1: update_codeparam_dict_check_xsd(  # noqa E501
                    codeparam_dict, elem, entrystring.get(), root, xmlschema, entry1
                ),
            )

            # Update the codeparam dictionary accordingly
            codeparam_dict[elem.tag] = entrystring.get()

            # Display the definition of the variable from the xsd file information
            if label_name.cget("text") in docum_dict.keys():
                CreateToolTip(label_name, docum_dict[label_name.cget("text")])

            rrow += 1

            # Scrollbar
            if rrow > 10:
                v_scroll.grid(row=1, column=1, sticky="n")
            else:
                v_scroll.grid_remove()

    return codeparam_dict


def make_frame(
    category,
    process,
    fr_top,
    actor_name,
    previous_frame,
    cp_top,
    current_config_folder,
    default,
):

    # WINDOW CONFIGURATION
    canvas = tk.Canvas(cp_top, borderwidth=0, highlightthickness=0, background=col.c1)
    frame = tk.Frame(canvas, width=500, height=1500, bg=col.c1)
    v_scroll = tk.Scrollbar(cp_top, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=v_scroll.set)
    canvas.grid(row=1, column=2, sticky=" news")
    canvas.create_window((4, 4), window=frame, anchor="nw")

    # READ CODEPARAM STRUCTURE FROM XML AND XSD FILES
    (
        destination_file,
        codeparam_dict,
        docum_dict,
        codeparam_xml_path,
        xmlschema,
    ) = read_and_save_codeparam(current_config_folder, None, category, process, actor_name, default)

    # CREATE/UPDATE THE INTERFACE FOR ALL PARAMETERS, RETURN THEIR UPDATED LIST
    updated_codeparam_dict = codeparam_interface(
        frame,
        destination_file,
        codeparam_dict,
        docum_dict,
        codeparam_xml_path,
        xmlschema,
        v_scroll,
        default,
    )

    # SAVE NEW CODEPARAM CONFIGURATION
    tk.Button(
        fr_top,
        text="Save",
        bg=col.c2,
        command=lambda: update_codeparam_file(destination_file, updated_codeparam_dict, 1),
    ).grid(row=0, column=1, padx=5, pady=5)

    # RESTORE DEFAULT CODEPARAM CONFIGURATION
    tk.Button(
        fr_top,
        text="Restore default",
        bg=col.c2,
        command=lambda: make_frame(
            category,
            process,
            fr_top,
            actor_name,
            frame,
            cp_top,
            current_config_folder,
            True,
        ),
    ).grid(row=0, column=2, padx=5, pady=5)

    # EXIT THE 'EDIT CODE PARAMETERS' WINDOW
    tk.Button(fr_top, text="Exit", bg=col.c2, command=lambda: cp_top.destroy()).grid(
        row=0, column=4, padx=(20, 5), pady=5
    )


def edit_codeparam(maindict, workflow_param, current_config_folder):

    cp_top = tk.Toplevel()
    cp_top.title("Edit Code Parameters")
    cp_top.geometry("600x700")

    fr_ab = tk.Frame(cp_top, width=200, height=650, bg=col.c4)
    fr_ab.grid(row=0, column=0, rowspan=2, sticky="ns")

    fr_main = tk.Frame(cp_top, width=600, height=650, bg=col.c1)
    fr_main.grid(row=1, column=2, sticky="nwes")
    fr_main.grid_propagate(0)
    prev_frame = tk.Canvas(fr_main, width=500, height=1500)

    fr_top = tk.Frame(cp_top, width=500, height=50, bg=col.c2)
    fr_top.grid(row=0, column=1, sticky="ew", columnspan=2)

    for main_key in maindict:
        for category in maindict[main_key]:
            la_sys = tk.Label(fr_ab, text=category, bg=col.c4)
            for process in maindict[main_key][category]:
                if int(workflow_param["actor_selection"][0][main_key][0][category][0][process][0]) != 0:
                    la_sys.grid(padx=5, pady=5, sticky="ew")
                    curval = list(maindict[main_key][category][process].keys())[
                        int(workflow_param["actor_selection"][0][main_key][0][category][0][process][0]) - 1
                    ]
                    tk.Button(
                        fr_ab,
                        text=curval,
                        bg=col.c2,
                        command=lambda actor_name=curval, category=category, process=process: make_frame(
                            category,
                            process,
                            fr_top,
                            actor_name,
                            prev_frame,
                            cp_top,
                            current_config_folder,
                            False,
                        ),
                    ).grid(padx=5, pady=5, sticky="ew")


def read_and_save_codeparam(current_config_folder, previous_folder, category, process, actor_name, default):

    # NAME OF THE CODEPARAM FILE FOR THIS ACTOR IN THE CURRENT CONFIGURATION FOLDER
    codeparam_destination_path = (
        current_config_folder + "/" + category + "/" + process + "/input_" + actor_name + ".xml"
    )

    # INITIALISE INTERFACE STRINGS FOR CODEPARAM XML AND XSD FILES
    codeparam_xml_path = ""
    codeparam_xsd_path = ""

    # IMPORT THE ACTOR TO KNOW WHERE IT IS LOCATED
    import_actor(actor_name, 0)
    actor = eval(actor_name)

    # LOOK FOR ITS XML AND XSD FILES FOR USER-DEFINED PARAMETERS
    found_xml = False
    # founx_xsd = False

    # CHECK IF THE XML FILE EXISTS IN THE DESTINATION FOLDER ALREADY
    if os.path.exists(codeparam_destination_path) and default is False:
        codeparam_xml_path = codeparam_destination_path
        found_xml = True
    # IF NOT, COPY IT FROM THE ACTOR LOCATION
    else:
        try:
            codeparam_xml_path = glob.glob(actor.actor_dir + "/input/*.xml")[0]
            found_xml = True
        except Exception as _:  # noqa F841
            codeparam_xml_path = None

        if codeparam_xml_path is not None:
            copy2(
                codeparam_xml_path,
                codeparam_destination_path,
                follow_symlinks=True,
            )
            # IF DEFAULT IS NOT REQUIRED AND IF CONFIG LOADED FROM A PREVIOUS RUN,
            # REPLACE THE XML FILE BY THE ONE OF THE PREVIOUS CONFIGURATION
            if previous_folder is not None and default is False:
                xml_name = category + "/" + process + "/input_" + actor_name + ".xml"
                codeparam_xml_path = previous_folder + "/" + xml_name
                if codeparam_xml_path != codeparam_destination_path:
                    copy2(
                        codeparam_xml_path,
                        codeparam_destination_path,
                        follow_symlinks=True,
                    )
            found_xml = True
    # Do not update XSD # https://jira.iter.org/browse/IMAS-5213
    try:
        codeparam_xsd_path = glob.glob(actor.actor_dir + "/input/*.xsd")[0]
        found_xsd = True
    except Exception as _:  # noqa F841
        codeparam_xsd_path = None

    # READ THE ADDITIONAL INFORMATION FROM THE XSD FILE
    if found_xsd:
        xmlschema_doc = etree.parse(codeparam_xsd_path)
        xmlschema_doc.write(codeparam_destination_path.replace(".xml", ".xsd"), pretty_print=True)
        root_xsd = xmlschema_doc.getroot()
        xmlschema = etree.XMLSchema(xmlschema_doc)
        docum_dict = {}
        for elem in root_xsd.iter():
            if elem.tag == "{http://www.w3.org/2001/XMLSchema}element":
                for i in elem.iter():
                    if i.tag == "{http://www.w3.org/2001/XMLSchema}documentation":
                        docum_dict[elem.attrib.values()[0]] = i.text
    else:
        xmlschema = {}
        docum_dict = {}

    # LOAD THE LIST OF CODE PARAMETERS, CREATE THE LABELS AND ENTRIES
    if found_xml:
        tree = etree.parse(codeparam_destination_path)
        root = tree.getroot()
        codeparam_dict = {}
        for elem in root.iter():
            if elem.tag != etree.Comment and len(elem) == 0:
                codeparam_dict[elem.tag] = elem.text
    else:
        codeparam_dict = {}

    # IF CODE COMPILED WITH MPI: ADD NUMBER OF PROCESSORS AS EDITABLE PARAMETERS
    # TO AN ADDITIONAL XML FILE FOR THIS ACTOR
    # (ONLY WHEN FOUND_XML=TRUE, I.E. ONLY THE FIRST TIME)
    if found_xml:
        if actor.is_mpi_code is True and "nproc_actor" not in codeparam_dict.keys():
            codeparam_dict["nproc_actor"] = " 4 "
            comment = etree.Comment(" Number of processors for parallel run (parameter added by HCD wf) ")
            comment.tail = "\n  "
            nproc = etree.Element("nproc_actor")
            nproc.text = codeparam_dict["nproc_actor"]
            nproc.tail = "\n\n  "
            root.append(comment)
            root.append(nproc)
            tree.write(codeparam_destination_path, xml_declaration=True, encoding="UTF-8")

    if found_xsd:
        if actor.is_mpi_code is True and "nproc_actor" not in docum_dict.keys():
            docum_dict["nproc_actor"] = "Number of processors to run this code"
            xmltype = "{http://www.w3.org/2001/XMLSchema}"
            nproc_xsd = etree.Element(xmltype + "element")
            nproc_xsd.attrib["ref"] = "nproc_actor"
            nproc_xsd.attrib["minOccurs"] = "0"
            for elem in root_xsd.iter():
                if elem.tag != etree.Comment:
                    if "all" in elem.tag:
                        for i in elem.iterancestors():
                            if "parameters" in i.values():
                                elem.append(nproc_xsd)
            nproc_xsd_description = etree.Element(xmltype + "element")
            nproc_xsd_description.attrib["name"] = "nproc_actor"
            nproc_xsd_description.attrib["type"] = "xs:integer"
            nproc_xsd_annotation = etree.Element(xmltype + "annotation")
            nproc_xsd_documentation = etree.Element(xmltype + "documentation")
            nproc_xsd_annotation.append(nproc_xsd_documentation)
            nproc_xsd_description.append(nproc_xsd_annotation)
            root_xsd.append(nproc_xsd_description)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            if xmlschema.validate(root) is False:
                print(xmlschema.error_log.filter_from_errors()[0])
            xmlschema_doc.write(codeparam_destination_path.replace(".xml", ".xsd"), pretty_print=True)

    return (
        codeparam_destination_path,
        codeparam_dict,
        docum_dict,
        codeparam_xml_path,
        xmlschema,
    )


def dict2xml(param_dict, root):
    for child in root.iter():
        if child.tag != etree.Comment and len(child) == 0:
            for key, value in param_dict.items():
                if isinstance(value[0], dict):
                    root = dict2xml(value[0], root)
                else:
                    if child.tag == key:
                        child.text = str(value[0])
                        child.attrib["display"] = value[1]
    return root


def save_workflow_param_to_file(default_wf_param_file, current_wf_param_file, workflow_param, wfp_ref, cod_ref):

    # Copy the default workflow parameter file into the current one
    copy2(default_wf_param_file, current_wf_param_file, follow_symlinks=True)

    # Update workflow parameter file if changed from the interface
    tree = etree.parse(current_wf_param_file)
    root = tree.getroot()

    # HCD version
    if False:
        root.tail = "\n"
        rl = [wfp_ref, cod_ref]
        for iroot in range(2):
            for elem in root[iroot].iter():
                if elem.tag != etree.Comment and len(elem) == 0:
                    elem.text = workflow_param[rl[iroot]][elem.tag]
        elem.tail = "\n"

    # Add information regarding to time base edition, in case it exists
    # (special treatement because it was not there in the original workflow input file)
    root = dict2xml(workflow_param, root)
    if "time_base" in workflow_param.keys():
        comment_time_base = etree.Comment("Time base for each process")
        comment_time_base.tail = "\n  "
        time_base = etree.Element("time_base")
        time_base.attrib["display"] = "time_base"
        process = {}
        for proc in workflow_param["time_base"][0].keys():
            process[proc] = {}
            process[proc]["tree"] = etree.SubElement(time_base, proc)
            for interval in workflow_param["time_base"][0][proc][0].keys():
                process[proc][interval] = {}
                process[proc][interval]["etree"] = etree.SubElement(process[proc]["tree"], interval)

                for subkey in workflow_param["time_base"][0][proc][0][interval][0].keys():
                    process[proc][interval][subkey] = etree.SubElement(process[proc][interval]["etree"], subkey)
                    if isinstance(
                        workflow_param["time_base"][0][proc][0][interval][0][subkey][0],
                        (np.ndarray, np.generic),
                    ):
                        process[proc][interval][subkey].text = str(
                            workflow_param["time_base"][0][proc][0][interval][0][subkey][0].tolist()
                        )
                    else:
                        process[proc][interval][subkey].text = str(
                            workflow_param["time_base"][0][proc][0][interval][0][subkey][0]
                        )

        root.append(comment_time_base)
        root.append(time_base)

    tree.write(current_wf_param_file, xml_declaration=True, encoding="UTF-8")
    return 0


def save_waveforms_to_file(current_config_folder, previous_folder):

    err = -1
    if previous_folder is not None and current_config_folder != previous_folder:
        waveform_files = glob.iglob(os.path.join(previous_folder, "*.yaml"))
        for waveform_file in waveform_files:
            if os.path.isfile(waveform_file):
                copy2(waveform_file, current_config_folder, follow_symlinks=True)
    err = 0
    return err


def save_codeparam_to_file(
    current_config_folder,
    previous_folder,
    maindict,
    uncompiled_actors,
    workflow_param,
    verbose,
):

    cod_ref = list(workflow_param.keys())[1]

    for main_key in maindict:
        for category in maindict[main_key]:
            for process in maindict[main_key][category]:
                if int(workflow_param[cod_ref][0][main_key][0][category][0][process][0]) != 0:
                    actor_name = list(maindict[main_key][category][process].keys())[
                        int(workflow_param[cod_ref][0][main_key][0][category][0][process][0]) - 1
                    ]
                    if actor_name in uncompiled_actors:
                        print(
                            "ERROR:",
                            actor_name.upper(),
                            "is selected as an active actor, "
                            "but it has not been found. \n"
                            "Please change your actor selection or load",
                            actor_name.upper(),
                            "and try again",
                            file=sys.stderr,
                        )
                        return -1

                    (
                        destination_file,
                        codeparam_dict,
                        docum_dict,
                        codeparam_xml_path,
                        xmlschema,
                    ) = read_and_save_codeparam(
                        current_config_folder,
                        previous_folder,
                        category,
                        process,
                        actor_name,
                        False,
                    )

                    # Update code parameter files if changed from interface (and if exists)
                    if codeparam_dict != {}:
                        update_codeparam_file(destination_file, codeparam_dict, verbose)

    return 0


def save(
    current_config_folder,
    default_wf_param_file,
    previous_folder,
    maindict,
    uncompiled_actors,
    workflow_param,
    wfp_ref,
    cod_ref,
    process_list,
):

    from datetime import datetime

    # Define the current folder (either chosen by the system with 'save'
    # or by the user with 'save as')
    if current_config_folder is None:
        # first_save = 1
        current_config_folder = os.path.join(os.getcwd(), "data/run_" + datetime.now().strftime("%y%m%d_%H:%M:%S"))
    # else:
    # first_save = 0

    # When operation is cancelled from the interface
    if current_config_folder == () or current_config_folder == "":
        print("Save_as cancelled.", file=sys.stderr)
        return None

    # Define the workflow parameter file within the current folder
    current_wf_param_file = current_config_folder + "/input_workflow.xml"

    # Dont want to write configuration directly in $PWD or $PWD/data
    if current_config_folder == os.getcwd() + "/data" or current_config_folder == os.getcwd():
        print(
            "Refuse to write directly in folder " + current_config_folder,
            file=sys.stderr,
        )
        return None

    # Dont want to write configuration in folders called with same name as processes
    # because it would be too confusing
    folder_name = current_config_folder.split("/")[-1]
    if folder_name in process_list:
        print(
            "Refuse to write directly in a folder named "
            + folder_name
            + " because it could be mixed with sub-folders for diagnostic categories",
            file=sys.stderr,
        )
        return None

    # Read the default workflow parameters file
    # root = etree.parse(default_wf_param_file).getroot()

    # Create the current configuration folder and its sub-folders for each process
    if not os.path.exists(current_config_folder):
        os.makedirs(current_config_folder)
    for main_key in maindict:
        for category in maindict[main_key]:
            for process in maindict[main_key][category]:
                if not os.path.exists(current_config_folder + "/" + category + "/" + process):
                    os.makedirs(current_config_folder + "/" + category + "/" + process)

    # Copy/update the workflow parameter file if changed from the interface
    err = save_workflow_param_to_file(default_wf_param_file, current_wf_param_file, workflow_param, wfp_ref, cod_ref)

    # Copy waveform files
    err = save_waveforms_to_file(current_config_folder, previous_folder)

    # Copy/update code parameter files for chosen actors in their respective sub-folders
    err = save_codeparam_to_file(
        current_config_folder,
        previous_folder,
        maindict,
        uncompiled_actors,
        workflow_param,
        0,
    )

    if err == 0:
        print("---> Configuration saved in " + current_config_folder, file=sys.stdout)
    else:
        current_config_folder = None

    return current_config_folder


#####################################################################################


# ---------------------------------------------------------------------------------
# Create a python dictionary (maindict) that contains the name of all SD models,
# their input & output IDSs, their sub-category (light_spectrum, cxrs, ..),
# and the global category they belong to (magnetics, bolometry, ..)
# ---------------------------------------------------------------------------------
def create_maindict(workflow_parameters_path, verbose):

    # MEMO: STRUCTURE OF THE INPUT XML FILE
    # ROOT.ITER() = LOOP OVER ALL ELEMENTS OF THE INPUT XML FILE
    # ROOT[0] = workflow_parameters_path
    # ROOT[1] = actor_selection

    # READ THE ACTOR_SELECTION STRUCTURE FROM THE WORKFLOW INPUT XML FILE
    tree = etree.parse(workflow_parameters_path)
    root = tree.getroot()
    actor_selection = root[1]

    # --------------------------------------------------------------------------------------------
    # MAINDICT CONTAINS CATEGORIES ONE OR TWO MAIN KEYS (THE SECOND ONE IS OPTIONAL):
    # - MAIN-PROCESSING:
    #      - CATEGORIES
    #        E.G.      --> OPTICAL_IR, MAGNETICS, FUSION_PRODUCTS, ETC.
    #                  --> 4 SYSTEMS: ECRH, ICRH, NBI, NUCLEAR
    #        - PROCESS
    #          E.G.       --> TIP_SEL, DIP_SEL, ETC.
    #                     --> EC_WAVE_SOLVER, ETC.
    #            - ACTORS:
    #              E.G.      --> TIP, CASPER, ETC.
    #                        --> NEMO, ASCOT, ETC.
    #                 - [0] = [LIST OF INPUT IDSS]
    #                 - [1] = [LIST OF OUTPUT IDSS]
    # ------------------
    # - POST-PROCESSING (OPTIONAL):
    #      - CATEGORIES
    #        E.G.      --> 2 SYSTEMS: FILL_CORE_SOURCES, FILL_CORE_PROFILES
    #        - PROCESS
    #          E.G.       --> SOURCE, PROFILES
    # --------------------------------------------------------------------------------------------
    code_selection = {}
    compiled_list = []
    not_compiled_list = []
    maindict = {}
    catdict = {}

    # DISPLAY FOR TEST PURPOSES
    # for main_key in actor_selection:
    #    print('main_key',main_key)
    #    for category in main_key:
    #        print('category',category)
    #        for process in category:
    #              print('    process',process)
    #              if process.tag != etree.Comment:
    #                  for actor in process.attrib['list'].split():
    #                      print('     actor',actor)

    for main_key in actor_selection:
        dict_category = {}
        for category in main_key:
            if category.tag != etree.Comment:
                dict_process = {}
                for process in category:
                    list_actor = []
                    dict_actor = {}
                    if process.tag != etree.Comment:
                        for actor_name in process.attrib["list"].split():
                            err = 0
                            input_ids_list = []
                            output_ids_list = []
                            if actor_name in not_compiled_list:
                                verbose_eff = 0
                            else:
                                verbose_eff = verbose
                                (
                                    input_ids_list,
                                    output_ids_list,
                                    err,
                                ) = read_actor_ids(actor_name, verbose_eff)
                            if err == 0:
                                compiled_list.append(actor_name)
                            else:
                                not_compiled_list.append(actor_name)
                            dict_actor[actor_name] = [input_ids_list, output_ids_list]
                            list_actor.append(
                                {
                                    "name": actor_name,
                                    "input": input_ids_list,
                                    "output": output_ids_list,
                                    "category": category.tag,
                                }
                            )
                        # Prepend empty_* code
                        if output_ids_list == []:
                            output_ids_list.append("core_profiles")
                        list_actor.insert(
                            0,
                            {
                                "name": "empty_" + output_ids_list[0],
                                "input": ["core_profiles"],
                                "output": [output_ids_list[0]],
                                "category": category.tag,
                            },
                        )
                        if process.text != "0":
                            code_selection[process.tag] = process.attrib["list"].split(" ")[int(process.text) - 1]
                        else:
                            code_selection[process.tag] = None
                        dict_process[process.tag] = dict_actor
                        catdict[process.tag] = list_actor
                    dict_category[category.tag] = dict_process
                maindict[main_key.tag] = dict_category

    # Remove duplicates
    compiled_list = list(dict.fromkeys(compiled_list))
    not_compiled_list = list(dict.fromkeys(not_compiled_list))

    return (maindict, compiled_list, not_compiled_list, code_selection, catdict)


def read_actor_ids(name, verbose):

    # ids_list = [ids.value for ids in list(imas.IDSName)]
    input_ids_list = []
    output_ids_list = []
    err = import_actor(name, verbose)
    actor = eval(name)

    if err == 0:

        # IMAS-4679
        for ilist in actor.code_description["implementation"]["subroutines"]["main"]["arguments"]:
            if ilist["intent"] == "IN":
                input_ids_list.append(ilist["type"])
            elif ilist["intent"] == "OUT":
                output_ids_list.append(ilist["type"])

    return (input_ids_list, output_ids_list, err)


class saved_folder_name(object):
    def __init__(
        self,
        default_wf_param_file,
        global_dict,
        uncompiled_actors,
        workflow_param,
        wfp_ref,
        cod_ref,
        process_list,
    ):
        self.value = None
        self.default_wf_param_file = default_wf_param_file
        self.global_dict = global_dict
        self.uncompiled_actors = uncompiled_actors
        self.workflow_param = workflow_param
        self.wfp_ref = wfp_ref
        self.cod_ref = cod_ref
        self.process_list = process_list

    def NoAction(self):
        self.value = self.value

    def Save(self, chosen_folder, init_folder):
        previous_folder = init_folder
        if chosen_folder == init_folder:  # Very first SAVE, or SAVE after a SAVE_AS
            self.value = save(
                self.value,
                self.default_wf_param_file,
                previous_folder,
                self.global_dict,
                self.uncompiled_actors,
                self.workflow_param,
                self.wfp_ref,
                self.cod_ref,
                self.process_list,
            )
        else:
            if chosen_folder is None:
                if self.value is None:  # 1st SAVE after a LOAD
                    self.value = save(
                        init_folder,
                        self.default_wf_param_file,
                        previous_folder,
                        self.global_dict,
                        self.uncompiled_actors,
                        self.workflow_param,
                        self.wfp_ref,
                        self.cod_ref,
                        self.process_list,
                    )
                else:  # Next SAVEs after a LOAD; SAVE after a SAVE AS which is after a LOAD;
                    self.value = save(
                        self.value,
                        self.default_wf_param_file,
                        previous_folder,
                        self.global_dict,
                        self.uncompiled_actors,
                        self.workflow_param,
                        self.wfp_ref,
                        self.cod_ref,
                        self.process_list,
                    )
            else:  # SAVE AS
                if_cancelled = self.value
                previous_folder = self.value
                self.value = save(
                    chosen_folder,
                    self.default_wf_param_file,
                    previous_folder,
                    self.global_dict,
                    self.uncompiled_actors,
                    self.workflow_param,
                    self.wfp_ref,
                    self.cod_ref,
                    self.process_list,
                )
                if self.value is None:
                    self.value = if_cancelled
        return self.value
