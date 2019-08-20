import os, sys, imas 

from tkinter import *
from tkinter import filedialog, ttk
from lxml import etree
from datetime import datetime

from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

from write_to_ids_xml import ec_write_to_ids_and_xml

param = {'user': 'mitterv', 'machine': 'iter', 'shot_nr': 7897, 'run_in': 1, 'run_out': 456}

#### OPEN IDS: 
# remote and local database environment
user_in     = param['user']
local_user  = os.getenv('USER')
tokamakname = param['machine'] # assumed to be the same for remote/local DB
version     = os.getenv('IMAS_VERSION')[0]

# If the local database for the required tokamak does not exist yet: create it
if not os.path.exists(os.getenv('HOME')+'/public/imasdb/'+tokamakname):
    print('--> Create local database '+os.getenv('HOME')+'/public/imasdb/'+tokamakname)
    os.popen("imasdb "+tokamakname).read()


print('open input and output file')
input = imas.ids(param['shot_nr'], param['run_in'], 0,0)
input.open_env(user_in,tokamakname,version)
output  = imas.ids(param["shot_nr"], param["run_out"], 0,0)
output.create_env(user_in,tokamakname,version)

input.ec_antennas.get()
    

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


## EC

ecfr = Frame(window, width = 600, height = 200, background = c3)
ecfr.grid(row = 0, column = 0, sticky = 'nwes')

## IC
icfr = Frame(window, width = 600, height = 200, background = c3)
icfr.grid(row = 1, column = 0, sticky = 'news')

Label(icfr, text = 'IC', bg = c2,  font = '15').grid(row = 0, column = 0, sticky = 'news', columnspan = 2)

icc_fr = Frame(icfr, width = 300, height = 200, background = c3)
icc_fr.grid(row = 1, column = 0, rowspan = 2, sticky = 'news', padx = 3, pady = 3)

icb_fr = Frame(icfr, width = 300, height = 200, background = c1)
icb_fr.grid(row = 1, column = 1, rowspan = 2, sticky = 'news', padx = 3, pady = 3)

## NBI
nbifr = Frame(window, width = 600, height = 200, background = c3)
nbifr.grid(row = 2, column = 0, sticky = 'news')

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

    save_button = Button(s_fr, text = 'save', bg = c2, command = lambda: ec_write_to_ids_and_xml(ec_dict, input.ec_antennas))
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
                    entrystring.trace('w', lambda name, index, mode, elem = elem, entrystring = entrystring, iant = iant: print(hi))
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
            
            
            l.bind('<Button-1>', lambda event, param = param: nice_editwindow(param))

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
                powl = ec_dict[iant][param].split()
                powl_time = ec_dict[iant][param+'_time'].split()


                Label(lfr, text = param, bg = c3,).grid(row  = 1, column = 2)
                Label(lfr, text = 'time', bg = c3).grid(row = 1, column = 1)

                textwidget_powl_time= Text(lfr, height = len(powl_time), width = 10, bg = c1, padx = 3, pady =2)
                textwidget_powl_time.grid(row = 2, column = 1, sticky = 'nse', padx = (5, 1))
                textwidget_powl_time.bind('<Leave>', lambda event, entryelem = param+'_time', iant = iant: update_ec_dict(iant, textwidget_powl_time.get('1.0', END).replace('\n', ' '), entryelem))


                textwidget_powl = Text(lfr, width = 10, padx = 3, bg = c1)
                textwidget_powl.grid(row = 2, column = 2, sticky = 'nsw', padx = (1,5))
                textwidget_powl.bind('<Leave>', lambda event, entryelem = param, iant = iant: update_ec_dict(iant, textwidget_powl.get('1.0', END).replace('\n', ' '), entryelem))


                for powl_time_datapoint in powl_time:
                    textwidget_powl_time.insert(END, powl_time_datapoint+'\n')

                for powl_datapoint in powl:
                    textwidget_powl.insert(END, powl_datapoint+'\n')

                update_button = Button(lfr, text = 'update',bg = c2, command = lambda: plot_waveform())
                update_button.grid(row = 50, column = 1, columnspan = 2, pady = 10, sticky = 'ew')

                def plot_waveform(): 
                    powl_time_int = [float(i.strip()) for i in ec_dict[iant][param+'_time'].split()]
                    powl_int = [float(i.strip()) for i in ec_dict[iant][param].split()]


                    fig = Figure(dpi = 100)
                    fig.add_subplot(111).plot(powl_time_int, powl_int)
                    fig.suptitle(param, fontsize=16)
                    canvas = FigureCanvasTkAgg(fig, master = mfr)
                    canvas.draw()
                    canvas.get_tk_widget().grid(row =4 , column = 4, sticky = 'news')

                plot_waveform()

        def update_ec_dict(iant, newvalue, entryelem):

            ec_dict[iant][entryelem] = newvalue

                   

ec('ec_waveforms.xml')





window.mainloop()
