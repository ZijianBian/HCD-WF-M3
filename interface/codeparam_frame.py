import tkinter

import interface.colour_definitions as col
from interface.codeparam_populate import codeparam_interface
from wf_tools import update_codeparam_file, read_and_save_codeparam

# CREATE THE WINDOW TO EDIT CODE PARAMETERS
def make_frame(
        category, process, fr_top, actor_name, previous_frame, cp_top, current_config_folder, default
):

    # WINDOW CONFIGURATION
    canvas = tkinter.Canvas(
        cp_top, borderwidth=0, highlightthickness=0, background=col.c1
    )
    frame = tkinter.Frame(canvas, width=500, height=1500, bg=col.c1)
    v_scroll = tkinter.Scrollbar(cp_top, orient="vertical", command=canvas.yview)
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
    tkinter.Button(
        fr_top,
        text="Save",
        bg=col.c2,
        command=lambda: update_codeparam_file(
            destination_file, updated_codeparam_dict, 1
        ),
    ).grid(row=0, column=1, padx=5, pady=5)

    # RESTORE DEFAULT CODEPARAM CONFIGURATION
    tkinter.Button(
        fr_top,
        text="Restore default",
        bg=col.c2,
        command=lambda: make_frame(
            category, process, fr_top, actor_name, frame, cp_top, current_config_folder, True
        ),
    ).grid(row=0, column=2, padx=5, pady=5)

    # EXIT THE 'EDIT CODE PARAMETERS' WINDOW
    tkinter.Button(
        fr_top, text="Exit", bg=col.c2, command=lambda: cp_top.destroy()
    ).grid(row=0, column=4, padx=(20, 5), pady=5)
