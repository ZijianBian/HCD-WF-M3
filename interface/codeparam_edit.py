import tkinter
import colour_definitions as col
from codeparam_frame import make_frame

# MANAGE XML FILES
def edit_codeparam(maindict,actors_ref,workflow_param, \
    cod_ref,current_config_folder):

    cp_top = tkinter.Toplevel()
    cp_top.title('Edit Code Parameters')
    cp_top.geometry('600x700')

    fr_ab = tkinter.Frame(cp_top, width=200, height=650, bg=col.c4)
    fr_ab.grid(row=0, column=0, rowspan=2, sticky='ns')

    fr_main = tkinter.Frame(cp_top, width=600, height=650, bg=col.c1)
    fr_main.grid(row=1, column=2, sticky='nwes')
    fr_main.grid_propagate(0)
    prev_frame = tkinter.Canvas(fr_main, width=500, height=1500)

    fr_top = tkinter.Frame(cp_top, width=500, height=50, bg=col.c2)
    fr_top.grid(row=0, column=1, sticky='ew', columnspan=2)

    for ref in actors_ref:
        for hsys in maindict[ref]:
            la_sys = tkinter.Label(fr_ab, text=hsys, bg=col.c4)
            for cat in maindict[ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    la_sys.grid(padx=5, pady=5, sticky='ew')

                    curval = list(maindict[ref][hsys][cat].keys())\
                             [int(workflow_param[cod_ref][cat])-1]
                    tkinter.Button(fr_ab, text=curval, bg=col.c2,
                           command=lambda actor_name=curval,hsys=hsys: make_frame\
                           (hsys,fr_top,actor_name,prev_frame,cp_top, \
                            current_config_folder,False)).grid(padx=5,pady=5,sticky='ew')
