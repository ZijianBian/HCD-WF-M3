import os, tkinter, codeparam_properties
import colour_definitions as col
from utility_functions import update_codeparam_dict_check_xsd
from lxml import etree

# -----------------------------------------------------------------------------------
# LOAD THE LIST OF CODE PARAMETERS, CREATE THE LABELS AND ENTRIES FOR THE INTERFACE
# -----------------------------------------------------------------------------------


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
            l = tkinter.Label(
                frame,
                text=elem.tag.strip(),
                bg=col.c1,
                wraplength="200",
                anchor="w",
                justify=tkinter.LEFT,
            )
            l.grid(row=rrow, column=ccolumn, sticky="w")

            # Field for the value of the variable: default taken from elem.txt
            entrystring = tkinter.StringVar()
            entrystring.set(elem.text.strip())
            entry1 = tkinter.Entry(frame, textvar=entrystring, bg=col.c1)
            entry1.grid(row=rrow, column=ccolumn + 1, padx=3, pady=3)

            # Catch any update of the variable from the interface, and check xsd rules
            entrystring.trace(
                "w",
                lambda name, index, mode, elem=elem, entrystring=entrystring, entry1=entry1: update_codeparam_dict_check_xsd(
                    codeparam_dict, elem, entrystring.get(), root, xmlschema, entry1
                ),
            )

            # Update the codeparam dictionary accordingly
            codeparam_dict[elem.tag] = entrystring.get()

            # Display the definition of the variable from the xsd file information
            if l.cget("text") in docum_dict.keys():
                codeparam_properties.CreateToolTip(l, docum_dict[l.cget("text")])

            rrow += 1

            # Scrollbar
            if rrow > 10:
                v_scroll.grid(row=1, column=1, sticky="n")
            else:
                v_scroll.grid_remove()

    return codeparam_dict
