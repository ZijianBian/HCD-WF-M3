import os, sys, imas 

from tkinter import *
from tkinter import filedialog, ttk
from lxml import etree
from datetime import datetime

from write_to_ids import write_to_ids
from edit_waveforms import edit_waveforms

import pdb    

### MAKE WINDOW FOR INTERFACE    
c1 = 'white'
c2 = 'white smoke'
c3 = 'white'
c4 = 'ghost white'
c5 = 'powder blue'
cb = 'LavenderBlush3'

window = Tk()
window.title('CONFIGURE WAVEFORMS')
window.configure(bg = c1)

#window.resizable(0,1)

runconfigfr = Frame(window, width = 600, height = 100, bg = c5)
runconfigfr.grid(row = 0, column = 0, sticky = 'nwes')
runconfigfr.columnconfigure(1, minsize = 130)
runconfigfr.columnconfigure(2, minsize = 130)
runconfigfr.columnconfigure(3, minsize = 130)
runconfigfr.columnconfigure(4, minsize = 130)

def update_ids_param_dict(newval, field):
    ids_param_dict[field] = newval


ids_param_dict = {}
userstr = StringVar()
userstr.trace('w', lambda name, index, mode, ids_param_dict_field = 'user': update_ids_param_dict(userstr.get(), ids_param_dict_field))
Label(runconfigfr, text = 'user', bg = c5).grid(row = 1, column = 1, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = userstr, bg = c1).grid(row = 1, column = 2, sticky = 'news', padx = 3, pady = 3)
userstr.set('public')

machinestr = StringVar()
machinestr.trace('w', lambda name, index, mode, ids_param_dict_field = 'machine': update_ids_param_dict(machinestr.get(), ids_param_dict_field))
Label(runconfigfr, text = 'machine', bg = c5).grid(row = 2, column = 1, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = machinestr, bg = c1).grid(row = 2, column = 2, sticky = 'news', padx = 3, pady = 3)
machinestr.set('iter')

shotnrstr = IntVar()
shotnrstr.trace('w', lambda name, index, mode, ids_param_dict_field = 'shot_nr': update_ids_param_dict(shotnrstr.get(), ids_param_dict_field))
Label(runconfigfr, text = 'shotnr', bg = c5).grid(row = 1, column = 3, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = shotnrstr, bg = c1).grid(row = 1, column = 4, sticky = 'news', padx = 3, pady = 3)
shotnrstr.set(130011)

runinstr = IntVar()
#pdb.set_trace()
runinstr.trace('w', lambda name, index, mode, ids_param_dict_field = 'run_in': update_ids_param_dict(runinstr.get(), ids_param_dict_field))
Label(runconfigfr, text = 'runin', bg = c5).grid(row = 2, column = 3, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = runinstr, bg = c1).grid(row = 2, column = 4, sticky = 'news', padx = 3, pady = 3)
runinstr.set(1)

runoutstr = IntVar()
runoutstr.trace('w', lambda name, index, mode , ids_param_dict_field = 'run_out': update_ids_param_dict(runoutstr.get(), ids_param_dict_field))
Label(runconfigfr, text = 'runout', bg = c5).grid(row = 3, column = 3, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = runoutstr, bg = c1).grid(row = 3, column =4, sticky = 'news', padx = 3, pady = 3)
runoutstr.set(345)

def update_sys_dict(iant, newvalue, entryelem, sys_dict):

        sys_dict[iant][entryelem] = newvalue

        #print(sys_dict[iant][entryelem])



def ec(ec_waveform_path):

## EC

    ecfr = Frame(window, width = 600, height = 200, background = c3)
    ecfr.grid(row = 1, column = 0, sticky = 'nwes')

    Label(ecfr, text = 'EC', bg = c2,  font = '15').grid(row = 0, column = 0, sticky = 'ew', columnspan = 50)

    ecfr.columnconfigure(0, minsize = 303)
    ecfr.columnconfigure(1, minsize = 303)

    c_fr = Frame(ecfr, width = 300, height = 200, background = c3, borderwidth = 0)
    c_fr.grid(row = 1, column = 0, sticky = 'nwes') #, padx = 3, pady = 3)
    b_fr = Frame(ecfr, width = 300, height = 200, background = c1)
    b_fr.grid(row = 1, column = 1, rowspan = 2,   sticky = 'nwes') #, padx = 3, pady = 3)
    b_fr.columnconfigure(1, minsize = 120)
    s_fr = Frame(ecfr, width = 300, height = 100, bg = c1)
    s_fr.grid(row = 2, column = 0, padx = 3, pady = 3)
    

    ## put a button in the place for the buttons

    save_button = Button(s_fr, text = 'save', bg = c2)
    save_button.configure(command = lambda: write_to_ids(ec_dict, ids_param_dict, 'ec'))
    save_button.grid()


    ### WRITE THE DATA FROM THE XML INTO A DICTIONARY

    tree = etree.parse(ec_waveform_path)
    ec_root = tree.getroot()

    ec_dict = {}

    cle = []   #key list to be able to refrence everything without hardcoding 

    for i in ec_root:

        ec_dict[i.tag] = {}
        cle.append(i.tag)

        for param in i:
            if param.tag is not etree.Comment:
                
                if '\n'in param.text: 
                    
                    temp_val = param.text.strip()
                    temp_val = param.text.split('\n')
                    temp_val = [i.strip() for i in temp_val if i.strip()]
                    ec_dict[i.tag][param.tag] = temp_val
                
                    

                else:
                    ec_dict[i.tag][param.tag] = param.text.strip()



    ## PUT THE CONFIGURATION ON THE LEFT SIDE: 
    
    rrow_l = 0
    rrow_r = 0
    for iant in ec_dict: 

        if iant is cle[0]: 

            for elem in ec_dict[iant]:
                if 'comment' not in elem: 
                    Label(c_fr, text = elem, bg = c3, anchor = W, justify = LEFT).grid(row = rrow_l, column = 0, sticky = W, pady = 2)
                    entrystring = StringVar()
                    entrystring.set(ec_dict[iant][elem])
                    entrystring.trace('w', lambda name, index, mode, elem = elem, entrystring = entrystring, iant = iant: update_sys_dict(iant, entrystring.get(), elem, ec_dict))
                    Entry(c_fr, textvariable = entrystring,  bg = c1).grid(row = rrow_l, column =1, sticky = 'ew')
                    rrow_l +=1
        else:

            Label(b_fr, text = ec_dict[iant]['name'], bg = c1,  wraplength = 110).grid(row = rrow_r, column = 1, sticky = 'ew', padx = 5, pady = 3)

            Button(b_fr, text = 'edit waveform', bg = c2, command = lambda iant = iant: edit_waveforms(iant, ec_dict)).grid(row = rrow_r, column = 2, sticky = 'ew', padx = (50, 5), pady = 3)
            rrow_r += 1

                   





def ic(ic_waveform_path): 


    ## IC
    icfr = Frame(window, width = 600, height = 200, background = c3)
    icfr.grid(row = 2, column = 0, sticky = 'news')


    Label(icfr, text = 'IC', bg = c2,  font = '15').grid(row = 0, column = 0, sticky = 'news', columnspan = 2)

    icfr.columnconfigure(0, minsize = 303)
    icfr.columnconfigure(1, minsize = 303)

    c_fr = Frame(icfr, width = 300, height = 200, background = c3)
    c_fr.grid(row = 1, column = 0, sticky = 'nwes') #, padx = 3, pady = 3)
    b_fr = Frame(icfr, width = 300, height = 200, background = c1)
    b_fr.grid(row = 1, column = 1, rowspan = 2,   sticky = 'nwes') #, padx = 3, pady = 3)
    b_fr.columnconfigure(1, minsize = 120)
    s_fr = Frame(icfr, width = 300, height = 100, bg = c1)
    s_fr.grid(row = 2, column = 0, padx = 3, pady = 3)
    
    ## put a button in the place for the buttons

    save_button = Button(s_fr, text = 'save', bg = c2)
    save_button.configure(command = lambda: write_to_ids(ic_dict, ids_param_dict, 'ic'))
    save_button.grid()
    

    ### WRITE THE DATA FROM THE XML INTO A DICTIONARY

    ic_tree = etree.parse(ic_waveform_path)
    ic_root = ic_tree.getroot()

    ic_dict = {}

    ic_cle = []   #key list to be able to refrence everything without hardcoding 

    for i in ic_root:

        ic_dict[i.tag] = {}
        ic_cle.append(i.tag)

        for param in i:
            if param.tag is not etree.Comment:
                
                if '\n'in param.text: 
                    
                    temp_val = param.text.strip()
                    temp_val = param.text.split('\n')
                    temp_val = [i.strip() for i in temp_val  if i.strip()]
                    ic_dict[i.tag][param.tag] = temp_val
                
                    

                else:
                    ic_dict[i.tag][param.tag] = param.text.strip()



    ## PUT THE CONFIGURATION ON THE LEFT SIDE: 
    
    rrow_l = 0
    rrow_r = 0
    for iant in ic_dict: 

        if iant is ic_cle[0]: 

            for elem in ic_dict[iant]:
                if 'comment' not in elem: 
                    Label(c_fr, text = elem, bg = c3, anchor = W, justify = LEFT).grid(row = rrow_l, column = 0, sticky = W, pady = 2)
                    entrystring = StringVar()
                    entrystring.set(ic_dict[iant][elem])
                    entrystring.trace('w', lambda name, index, mode, elem = elem, entrystring = entrystring, iant = iant:  update_sys_dict(iant, entrystring.get(), elem, ic_dict))
                    Entry(c_fr, textvariable = entrystring,  bg = c1).grid(row = rrow_l, column =1, sticky = 'ew')
                    rrow_l +=1
        else:

            Label(b_fr, text = ic_dict[iant]['name'], bg = c1,wraplength = 110).grid(row = rrow_r, column = 1, sticky = 'ew', padx = 5, pady = 3)

            Button(b_fr, text = 'edit waveform', bg = c2, command = lambda iant = iant: edit_waveforms(iant, ic_dict)).grid(row = rrow_r, column = 2, sticky = 'ew', padx = (50, 5), pady = 3)
            rrow_r += 1


def nbi(nbi_waveform_path): 

    nbifr = Frame(window, width = 600, height = 200, background = c3)
    nbifr.grid(row = 3, column = 0, sticky = 'news')


    Label(nbifr, text = 'NBI', bg = c2,  font = '15').grid(row = 0, column = 0, sticky = 'news', columnspan = 2)

    nbifr.columnconfigure(0, minsize = 303)
    nbifr.columnconfigure(1, minsize = 303)

    c_fr = Frame(nbifr, width = 300, height = 200, background = c3)
    c_fr.grid(row = 1, column = 0, sticky = 'nwes') #, padx = 3, pady = 3)
    b_fr = Frame(nbifr, width = 300, height = 200, background = c1)
    b_fr.grid(row = 1, column = 1, rowspan = 2,   sticky = 'nwes') #, padx = 3, pady = 3)
    b_fr.columnconfigure(1, minsize = 120)
    s_fr = Frame(nbifr, width = 300, height = 100, bg = c1)
    s_fr.grid(row = 2, column = 0, padx = 3, pady = 3)
    ## put a button in the place for the buttons

    save_button = Button(s_fr, text = 'save', bg = c2)
    save_button.configure(command = lambda: write_to_ids(nbi_dict, ids_param_dict, 'nbi'))
    save_button.grid()
    

    ### WRITE THE DATA FROM THE XML INTO A DICTIONARY

    nbi_tree = etree.parse(nbi_waveform_path)
    nbi_root = nbi_tree.getroot()

    nbi_dict = {}

    nbi_cle = []   #key list to be able to refrence everything without hardcoding 

    for i in nbi_root:

        nbi_dict[i.tag] = {}
        nbi_cle.append(i.tag)

        for param in i:
            if param.tag is not etree.Comment:
                
                if '\n'in param.text: 
                    
                    temp_val = param.text.strip()
                    temp_val = param.text.split('\n')
                    temp_val = [i.strip() for i in temp_val  if i.strip()]
                    nbi_dict[i.tag][param.tag] = temp_val
                
                    

                else:
                    nbi_dict[i.tag][param.tag] = param.text.strip()



    ## PUT THE CONFIGURATION ON THE LEFT SIDE: 
    
    rrow_l = 0
    rrow_r = 0
    for iant in nbi_dict: 

        if iant is nbi_cle[0]: 

            for elem in nbi_dict[iant]:
                if 'comment' not in elem: 
                    Label(c_fr, text = elem, bg = c3, anchor = W, justify = LEFT).grid(row = rrow_l, column = 0, sticky = W, pady = 2)
                    entrystring = StringVar()
                    entrystring.set(nbi_dict[iant][elem])
                    entrystring.trace('w', lambda name, index, mode, elem = elem, entrystring = entrystring, iant = iant: update_sys_dict(iant, entrystring.get(), elem, nbi_dict))
                    Entry(c_fr, textvariable = entrystring,  bg = c1).grid(row = rrow_l, column =1, sticky = 'ew')
                    rrow_l +=1
        else:

            Label(b_fr, text = nbi_dict[iant]['name'], bg = c1, wraplength = 110).grid(row = rrow_r, column = 1, sticky = 'ew', padx = 5, pady = 3)

            Button(b_fr, text = 'edit waveform', bg = c2, command = lambda iant = iant: edit_waveforms(iant, nbi_dict)).grid(row = rrow_r, column = 2, sticky = 'ew', padx = (50, 5), pady = 3)
            rrow_r += 1

ec('ec_waveforms.xml')
ic('ic_waveforms.xml')
nbi('nb_waveforms.xml')

button_exit = Button(window, text = 'Exit', bg = 'light grey')
button_exit.grid(column=0, sticky='W', padx = 5, pady = 5)
button_exit.configure(command = lambda: sys.exit())


window.mainloop()
