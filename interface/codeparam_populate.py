import os,tkinter
import colour_definitions as col
from utility_functions import update_codeparam_dict
from hcd_tools import import_actor
from lxml import etree
from shutil import copy2

def populate(frame,current_config_folder,hsys,actor_name,v_scroll,default):

    # NAME OF THE CODEPARAM FILE FOR THIS ACTOR IN THE CURRENT CONFIGURATION FOLDER
    destination_file = current_config_folder+'/'+hsys+'/input_'+actor_name+'.xml'

    # INITIALISE INTERFACE STRINGS FOR CODEPARAM XML AND XSD FILES
    codeparam_xml_path = tkinter.StringVar()
    codeparam_xsd_path = tkinter.StringVar()

    # IMPORT THE ACTOR TO KNOW WHERE IT IS LOCATED
    import_actor(actor_name,0)
    actor_python_folder = eval(actor_name+'.location')

    # LOOK FOR ITS XML AND XSD FILES FOR USER-DEFINED PARAMETERS
    found_xml = False
    found_xsd = False
    with open(actor_python_folder+'/wrapper.py') as pfile:
        for iline in pfile:
            if 'xml_location = ' in iline and '_default_xml_location' not in iline:
                # CHECK IF THE XML FILE EXISTS IN THE DESTINATION FOLDER ALREADY
                if os.path.exists(destination_file) and default is False:
                    codeparam_xml_path.set(destination_file)
                # IF NOT, OR IF DEFAULT IS REQUIRED, COPY IT FROM THE ACTOR LOCATION
                else:
                    xml_name = iline.split('+')[-1].replace("'","").replace(" ","").replace("\n","")
                    codeparam_xml_path.set(actor_python_folder+xml_name)
                    copy2(codeparam_xml_path.get(), destination_file, follow_symlinks=True)
                found_xml = True

            if 'xsd_location = ' in iline:
                xsd_name = iline.split('+')[-1].replace("'","").replace(" ","").replace("\n","")
                codeparam_xsd_path.set(actor_python_folder+xsd_name)
                found_xsd = True

            if found_xml is True and found_xsd is True:
                break

    # READ THE ADDITIONAL INFORMATION FROM THE XSD FILE
    try:
        xmlschema_doc = etree.parse(codeparam_xsd_path.get())
        root_xsd      = xmlschema_doc.getroot()
        xmlschema     = etree.XMLSchema(xmlschema_doc)
        docum_dict = {}
        for elem in root_xsd.iter():
            if elem.tag == '{http://www.w3.org/2001/XMLSchema}element':
                for i in elem.iter():
                    if i.tag == '{http://www.w3.org/2001/XMLSchema}documentation':
                        docum_dict[elem.attrib.values()[0]] = i.text
    except:
        docum_dict = {}

    # LOAD THE LIST OF CODE PARAMETERS, CREATE THE LABELS AND ENTRIES
    tree = etree.parse(codeparam_xml_path.get())
    root = tree.getroot()

    rrow = 1
    ccolumn = 0
    codeparam_dict = {}

    for elem in root.iter():
        if elem.tag is not etree.Comment and len(elem) == 0:
            l = tkinter.Label(frame,text=elem.tag.strip(),\
                      bg=col.c1,wraplength='200', anchor='w', justify=tkinter.LEFT)
            l.grid(row=rrow, column=ccolumn, sticky='w')

            entrystring = tkinter.StringVar()
            entrystring.set(elem.text.strip())
            e = tkinter.Entry(frame, textvar=entrystring, bg=col.c1)
            e.grid(row=rrow, column=ccolumn+1, padx=3, pady=3)
            codeparam_dict[elem.tag] = entrystring.get()

            entrystring.trace('w', lambda name,index,mode,elem=elem.tag,\
                              entrystring=entrystring,e=e: update_codeparam_dict\
                              (codeparam_dict,elem,root,entrystring.get(),xmlschema,e))
            try:
                CreateToolTip(l, docum_dict[l.cget('text')])
            except:
                pass

            rrow += 1

            if rrow > 20:
                v_scroll.grid(row=1, column=1, sticky='ns')
            else:
                v_scroll.grid_remove()

    return destination_file,codeparam_dict


