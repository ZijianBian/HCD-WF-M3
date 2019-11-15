from tkinter import *
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import numpy as np

def edit_waveforms(iant, sys_dict):    

    c1 = 'white'
    c2 = 'white smoke'
    c3 = 'azure2'
    c4 = 'ghost white'
    c5 = 'azure4'
    cb = 'LavenderBlush3'

    ewf_top = Toplevel(bg = c1)
    ewf_top.title('Edit '+sys_dict[iant]['name'])

    rrow_t = 0
    rrow_r = 0


    rfr = Frame(ewf_top, width = 200, height = 500, bg = c1, relief = SOLID)
    rfr.grid(row = 0, column =0,  sticky = 'ns')
    for param in sys_dict[iant]:
        l = Label(rfr, text = param, bg = c1, anchor = W, justify = LEFT)
        l.grid(row = rrow_r, column = 0, sticky = 'ew', padx = 5, pady = 2)


        entrystring = StringVar()
        entrystring.set(sys_dict[iant][param])
        entrystring.trace('w', lambda name, index, mode, param = param, entrystring = entrystring, iant = iant: update_sys_dict(iant, entrystring.get(), param,-999, sys_dict))
        le = Entry(rfr, textvariable = entrystring,  bg = c1)
        le.grid(row = rrow_r, column =1, sticky = 'ew', padx = 5, pady = 2)


        if param+'_time' in sys_dict[iant]: 
            Button(rfr, text = 'edit', bg = c2, command = lambda param = param: nice_editwindow(param, sys_dict), padx = 1, pady = 1).grid(row = rrow_r -1, column = 3, rowspan = 2, sticky = 'wns', padx = 2, pady = 2)
            
            
        

        rrow_r +=1



    def nice_editwindow(param, sys_dict):

        try:
            lfr.grid_remove()
            lfr.grid_forget()
            mfr.grid_remove()
            mfr.grid_forget()
        except:
            pass

        if param+'_time' in sys_dict[iant]:

            lfr = Frame(ewf_top, width = 200, height = 500, bg = c3)
            lfr.grid(row = 0, column = 1, sticky = 'nsew', padx = 5)
            mfr = Frame(ewf_top, width = 500, height = 500, bg = c1)
            mfr.grid(row = 0, column = 2, sticky = 'ns', padx = 5)



            ## power launched time: 


            powl_time = sys_dict[iant][param+'_time'].split()
            Label(lfr, text = 'time', bg = c3).grid(row = 1, column = 1)
            textwidget_powl_time= Text(lfr, height = len(powl_time), width = 10, bg = 'gray95', padx = 3, pady =2)
            textwidget_powl_time.grid(row = 2, column = 1, sticky = 'nse', padx = (5, 1))
            textwidget_powl_time.bind('<Leave>', lambda event, entryelem = param+'_time', iant = iant: update_sys_dict(iant, textwidget_powl_time.get('1.0', END).replace('\n', ' '), entryelem, -999, sys_dict))

            for powl_time_datapoint in powl_time:
                textwidget_powl_time.insert(END, powl_time_datapoint+'\n')

            if  isinstance(sys_dict[iant][param], str):
                powl = sys_dict[iant][param].split()
                Label(lfr, text = param, bg = c3 , wraplength = 100).grid(row  = 1, column = 2)

                textwidget_powl = Text(lfr, width = 10, padx = 3, bg = c1)
                textwidget_powl.grid(row = 2, column = 2, sticky = 'nsw', padx = (1,5))
                textwidget_powl.bind('<Leave>', lambda event, entryelem = param, iant = iant: update_sys_dict(iant, textwidget_powl.get('1.0', END).replace('\n', ' '), entryelem, -999, sys_dict))

                for powl_datapoint in powl:
                    textwidget_powl.insert(END, powl_datapoint+'\n')
            else: 
                Label(lfr, text = param, bg = c3, wraplength = 100).grid(row = 0, column = 2, columnspan = len(sys_dict[iant][param]))

                for i_d in range(len(sys_dict[iant][param])):
                    powl = sys_dict[iant][param][i_d].split()
                    Label(lfr, text = 'dimension '+str(i_d+1), bg = c3).grid(row = 1, column = 2 + i_d)
                    textwidget_powl = Text(lfr, width = 10, padx = 3, bg = c1)
                    textwidget_powl.grid(row = 2, column = 2 + i_d, sticky = 'nsw', padx = 2)
                    textwidget_powl.bind('<Leave>', lambda event, entryelem = param, iant = iant, i_d = i_d, textwidget_powl = textwidget_powl: update_sys_dict(iant, textwidget_powl.get('1.0', END).replace('\n', ' '), entryelem, i_d, sys_dict))
                    for powl_datapoint in powl:
                        textwidget_powl.insert(END, powl_datapoint+'\n')



            update_button = Button(lfr, text = 'update',bg = c2, command = lambda: plot_waveform())
            update_button.grid(row = 50, column = 1, columnspan = 2, pady = 10, sticky = 'ew')

            def plot_waveform():
                fig = Figure(dpi = 100)


                powl_time_int = [float(i.strip()) for i in sys_dict[iant][param+'_time'].split()]
                try:
                    powl_int = [float(i.strip()) for i in sys_dict[iant][param].split()]
                    fig.add_subplot(111).plot(powl_time_int, powl_int)
                except:

                    for i_d in range(len(sys_dict[iant][param])):
                        powl_int = [float(i.strip()) for i in sys_dict[iant][param][i_d].split()]
                   # powl_int = np.array(sys_dict[iant][param][0].split(), sys_dict[iant][param][1].split())
                        fig.add_subplot(len(sys_dict[iant][param]), 1, i_d+1).plot(powl_time_int, powl_int)





                fig.suptitle(param, fontsize=16)
                canvas = FigureCanvasTkAgg(fig, master = mfr)
                canvas.draw()
                canvas.get_tk_widget().grid(row =4 , column = 4, sticky = 'news')

            plot_waveform()

    def update_sys_dict(iant, newvalue, entryelem, i_d, sys_dict):
        if i_d < 0:
            sys_dict[iant][entryelem] = newvalue
        else: 
            sys_dict[iant][entryelem][i_d] = newvalue

        #print(sys_dict[iant][entryelem])

    def close_window(): 
        ewf_top.destroy()

    button_close = Button(rfr, text = 'Close', bg = 'light grey', command = close_window)
    button_close.grid(column=0, sticky='W', padx = 5, pady = 5)
