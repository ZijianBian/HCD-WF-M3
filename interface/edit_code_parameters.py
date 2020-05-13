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
        canvas.grid(row=1, column=2, sticky=' news')
        canvas.create_window((4, 4), window=fr, anchor='nw')

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

