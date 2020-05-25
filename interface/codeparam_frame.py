import tkinter
import colour_definitions as col
from codeparam_populate import populate
from utility_functions import save_codeparam_to_file

# CREATE THE WINDOW TO EDIT CODE PARAMETERS
def make_frame(hsys,fr_top,actor_name,previous_frame,cp_top,current_config_folder,default):

    # WINDOW CONFIGURATION
    canvas   = tkinter.Canvas(cp_top,borderwidth=0,highlightthickness=0,background=col.c1)
    frame    = tkinter.Frame(canvas,width=500,height=1500,bg=col.c1)
    v_scroll = tkinter.Scrollbar(cp_top,orient='vertical',command=canvas.yview)
    canvas.configure(yscrollcommand=v_scroll.set)
    canvas.grid(row=1,column=2,sticky=' news')
    canvas.create_window((4,4),window=frame, anchor='nw')

    # CREATE THE INTERFACE FOR ALL PARAMETERS, RETURN THEIR LIST AND LOCATION
    destination_file,codeparam_dict = populate(frame,current_config_folder,hsys,actor_name,\
                                               v_scroll,default)

    # SAVE NEW CODEPARAM CONFIGURATION
    tkinter.Button(fr_top, text='Save', bg=col.c2, command=lambda:
           save_codeparam_to_file(destination_file, codeparam_dict))\
           .grid(row=0, column=1, padx=5, pady=5)

    # RESTORE DEFAULT CODEPARAM CONFIGURATION
    tkinter.Button(fr_top, text='Restore default', bg=col.c2, command=lambda:
           make_frame(hsys,fr_top,actor_name,frame,cp_top,current_config_folder,True))\
           .grid(row=0, column=2, padx=5, pady=5)

    # EXIT THE 'EDIT CODE PARAMETERS' WINDOW
    tkinter.Button(fr_top, text='Exit', bg=col.c2, command=lambda:
           cp_top.destroy()).grid(row=0, column=4, padx=(20, 5), pady=5)

