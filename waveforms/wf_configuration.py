import os, sys, imas 

from tkinter import *
from tkinter import filedialog, ttk
from lxml import etree
from datetime import datetime

from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import numpy as np
from write_to_ids_xml import ec_write_to_ids_and_xml

    

### MAKE WINDOW FOR INTERFACE    
c1 = 'white'
c2 = 'white smoke'
c3 = 'azure2'
c4 = 'ghost white'
c5 = 'azure4'
cb = 'LavenderBlush3'

window = Tk()
window.title('CONFIGURE WAVEFORMS')
window.configure(bg = c1)

#window.resizable(0,1)

runconfigfr = Frame(window, width = 600, height = 100, bg = c3)
runconfigfr.grid(row = 0, column = 0, sticky = 'nwes')

def update_ids_param_dict(newval, field):
    ids_param_dict[field] = newval


ids_param_dict = {}
userstr = StringVar()
userstr.trace('w', lambda name, index, mode, ids_param_dict_field = 'user': update_ids_param_dict(userstr.get(), ids_param_dict_field))
Label(runconfigfr, text = 'user', bg = c3).grid(row = 1, column = 1, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = userstr, bg = c1).grid(row = 1, column = 2, sticky = 'news', padx = 3, pady = 3)
userstr.set('mitterv')

machinestr = StringVar()
machinestr.trace('w', lambda name, index, mode, ids_param_dict_field = 'machine': update_ids_param_dict(machinestr.get(), ids_param_dict_field))
Label(runconfigfr, text = 'machine', bg = c3).grid(row = 2, column = 1, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = machinestr, bg = c1).grid(row = 2, column = 2, sticky = 'news', padx = 3, pady = 3)
machinestr.set('iter')

shotnrstr = StringVar()
shotnrstr.trace('w', lambda name, index, mode, ids_param_dict_field = 'shot_nr': update_ids_param_dict(int(shotnrstr.get()), ids_param_dict_field))
Label(runconfigfr, text = 'shotnr', bg = c3).grid(row = 1, column = 3, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = shotnrstr, bg = c1).grid(row = 1, column = 4, sticky = 'news', padx = 3, pady = 3)
shotnrstr.set('7897')

runinstr = StringVar()
runinstr.trace('w', lambda name, index, mode, ids_param_dict_field = 'run_in': update_ids_param_dict(int(runinstr.get()), ids_param_dict_field))
Label(runconfigfr, text = 'runin', bg = c3).grid(row = 2, column = 3, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = runinstr, bg = c1).grid(row = 2, column = 4, sticky = 'news', padx = 3, pady = 3)
runinstr.set('1')

runoutstr = StringVar()
runoutstr.trace('w', lambda name, index, mode , ids_param_dict_field = 'run_out': update_ids_param_dict(int(runoutstr.get()), ids_param_dict_field))
Label(runconfigfr, text = 'runout', bg = c3).grid(row = 3, column = 3, sticky = 'wns', padx = 3, pady = 3)
Entry(runconfigfr, textvariable = runoutstr, bg = c1).grid(row = 3, column =4, sticky = 'news', padx = 3, pady = 3)
runoutstr.set('345')


## EC

ecfr = Frame(window, width = 600, height = 200, background = c3)
ecfr.grid(row = 1, column = 0, sticky = 'nwes')

## IC
icfr = Frame(window, width = 600, height = 200, background = c3)
icfr.grid(row = 2, column = 0, sticky = 'news')

Label(icfr, text = 'IC', bg = c2,  font = '15').grid(row = 0, column = 0, sticky = 'news', columnspan = 2)

icc_fr = Frame(icfr, width = 300, height = 200, background = c3)
icc_fr.grid(row = 1, column = 0, rowspan = 2, sticky = 'news', padx = 3, pady = 3)

icb_fr = Frame(icfr, width = 300, height = 200, background = c1)
icb_fr.grid(row = 1, column = 1, rowspan = 2, sticky = 'news', padx = 3, pady = 3)

## NBI
nbifr = Frame(window, width = 600, height = 200, background = c3)
nbifr.grid(row = 3, column = 0, sticky = 'news')

Label(nbifr, text = 'NBI', bg = c2,  font = '15').grid(row = 0, column = 0, sticky = 'news', columnspan = 2)
nbic_fr = Frame(nbifr, width = 300, height = 200, background = c3)
nbic_fr.grid(row = 1, column = 0, rowspan = 2, sticky = 'news', padx = 3, pady = 3)

nbib_fr = Frame(nbifr, width = 300, height = 200, background = c1)
nbib_fr.grid(row = 1, column = 1, rowspan = 2, sticky = 'news', padx = 3, pady = 3)


def ec(ec_waveform_path):

    Label(ecfr, text = 'EC', bg = c2,  font = '15').grid(row = 0, column = 0, sticky = 'ew', columnspan = 50)

    ecfr.columnconfigure(0, minsize = 303)
    ecfr.columnconfigure(1, minsize = 303)

    c_fr = Frame(ecfr, width = 300, height = 200, background = c3)
    c_fr.grid(row = 1, column = 0, sticky = 'nwes') #, padx = 3, pady = 3)
    b_fr = Frame(ecfr, width = 300, height = 200, background = c1)
    b_fr.grid(row = 1, column = 1, rowspan = 2,   sticky = 'nwes') #, padx = 3, pady = 3)
    s_fr = Frame(ecfr, width = 300, height = 100, bg = c1)
    s_fr.grid(row = 2, column = 0)
    

    ## put a button in the place for the buttons

    save_button = Button(s_fr, text = 'save', bg = c2, command = lambda: ec_write_to_ids_and_xml(ec_dict, ids_param_dict))
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
                    temp_val = [i.strip() for i in temp_val]
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
                    Label(c_fr, text = elem, bg = c3, anchor = W, justify = LEFT).grid(row = rrow_l, column = 0, sticky = W)
                    entrystring = StringVar()
                    entrystring.set(ec_dict[iant][elem])
                    entrystring.trace('w', lambda name, index, mode, elem = elem, entrystring = entrystring, iant = iant: print('hi'))
                    Entry(c_fr, textvariable = entrystring,  bg = c1).grid(row = rrow_l, column =1, sticky = 'ew')
                    rrow_l +=1
        else:

            Label(b_fr, text = ec_dict[iant]['name'], bg = c1).grid(row = rrow_r, column = 1, sticky = 'ew', padx = 5, pady = 3)

            Button(b_fr, text = 'edit waveform', bg = c2, command = lambda iant = iant: edit_waveform(iant)).grid(row = rrow_r, column = 2, sticky = 'ew', padx = (50, 5), pady = 3)
            rrow_r += 1


    def edit_waveform(iant):    
     
        ewf_top = Toplevel()
        ewf_top.title('EC: Edit '+ec_dict[iant]['name'])

        rrow_t = 0
        rrow_r = 0

        
        rfr = Frame(ewf_top, width = 200, height = 500, bg = c2)
        rfr.grid(row = 0, column = 3,  sticky = 'ns')
        for param in ec_dict[iant]:
            l = Label(rfr, text = param, bg = c2, anchor = W, justify = LEFT)
            l.grid(row = rrow_r, column = 0, sticky = 'ew', padx = 5, pady = 2)
            
            entrystring = StringVar()
            entrystring.set(ec_dict[iant][param])
            entrystring.trace('w', lambda name, index, mode, param = param, entrystring = entrystring, iant = iant: update_ec_dict(iant, entrystring.get(), param))
            Entry(rfr, textvariable = entrystring,  bg = c1).grid(row = rrow_r, column =1, sticky = 'ew', padx = 5, pady = 2)
            
            if param+'_time' in ec_dict[iant]: 
                Button(rfr, text = 'edit', bg = c2, command = lambda param = param: nice_editwindow(param), padx = 1, pady = 1).grid(row = rrow_r -1, column = 2, rowspan = 2, sticky = 'wns', padx = 2, pady = 2)
            


            rrow_r +=1



        def nice_editwindow(param):
            
            try:
                lfr.grid_remove()
                lfr.grid_forget()
                mfr.grid_remove()
                mfr.grid_forget()
            except:
                pass

            if param+'_time' in ec_dict[iant]:
                
                lfr = Frame(ewf_top, width = 200, height = 500, bg = c3)
                lfr.grid(row = 0, column = 1, sticky = 'ns')
                mfr = Frame(ewf_top, width = 500, height = 500, bg = c1)
                mfr.grid(row = 0, column = 2, sticky = 'ns')



                ## power launched time: 
                

                powl_time = ec_dict[iant][param+'_time'].split()
                Label(lfr, text = 'time', bg = c3).grid(row = 1, column = 1)
                textwidget_powl_time= Text(lfr, height = len(powl_time), width = 10, bg = c1, padx = 3, pady =2)
                textwidget_powl_time.grid(row = 2, column = 1, sticky = 'nse', padx = (5, 1))
                textwidget_powl_time.bind('<Leave>', lambda event, entryelem = param+'_time', iant = iant: update_ec_dict(iant, textwidget_powl_time.get('1.0', END).replace('\n', ' '), entryelem, -999))

                for powl_time_datapoint in powl_time:
                    textwidget_powl_time.insert(END, powl_time_datapoint+'\n')

                if  isinstance(ec_dict[iant][param], str):
                    powl = ec_dict[iant][param].split()
                    Label(lfr, text = param, bg = c3).grid(row  = 1, column = 2)
                
                    textwidget_powl = Text(lfr, width = 10, padx = 3, bg = c1)
                    textwidget_powl.grid(row = 2, column = 2, sticky = 'nsw', padx = (1,5))
                    textwidget_powl.bind('<Leave>', lambda event, entryelem = param, iant = iant: update_ec_dict(iant, textwidget_powl.get('1.0', END).replace('\n', ' '), entryelem, -999))

                    for powl_datapoint in powl:
                        textwidget_powl.insert(END, powl_datapoint+'\n')
                else: 
                    
                    for id in range(len(ec_dict[iant][param])):
                        powl = ec_dict[iant][param][id].split()
                        Label(lfr, text = param, bg = c3).grid(row = 1, column = 2 + id)
                        
                        textwidget_powl = Text(lfr, width = 10, padx = 3, bg = c1)
                        textwidget_powl.grid(row = 2, column = 2 + id, sticky = 'nsw', padx = (1,1))
                        textwidget_powl.bind('<Leave>', lambda event, entryelem = param, iant = iant, id = id, textwidget_powl = textwidget_powl: update_ec_dict(iant, textwidget_powl.get('1.0', END).replace('\n', ' '), entryelem, id))
                        for powl_datapoint in powl:
                            textwidget_powl.insert(END, powl_datapoint+'\n')



                update_button = Button(lfr, text = 'update',bg = c2, command = lambda: plot_waveform())
                update_button.grid(row = 50, column = 1, columnspan = 2, pady = 10, sticky = 'ew')

                def plot_waveform():
                    fig = Figure(dpi = 100)

              
                    powl_time_int = [float(i.strip()) for i in ec_dict[iant][param+'_time'].split()]
                    try:
                        powl_int = [float(i.strip()) for i in ec_dict[iant][param].split()]
                        fig.add_subplot(111).plot(powl_time_int, powl_int)
                    except:
                    
                        for id in range(len(ec_dict[iant][param])):
                            powl_int = [float(i.strip()) for i in ec_dict[iant][param][id].split()]
                       # powl_int = np.array(ec_dict[iant][param][0].split(), ec_dict[iant][param][1].split())
                            fig.add_subplot(len(ec_dict[iant][param]), 1, id+1).plot(powl_time_int, powl_int)
                    

                    
                    
                    
                    fig.suptitle(param, fontsize=16)
                    canvas = FigureCanvasTkAgg(fig, master = mfr)
                    canvas.draw()
                    canvas.get_tk_widget().grid(row =4 , column = 4, sticky = 'news')

                plot_waveform()

        def update_ec_dict(iant, newvalue, entryelem, id):
            if id < 0:
                ec_dict[iant][entryelem] = newvalue
            else: 
                ec_dict[iant][entryelem][id] = newvalue

            print(ec_dict[iant][entryelem])


                   

ec('ec_waveforms.xml')





window.mainloop()
