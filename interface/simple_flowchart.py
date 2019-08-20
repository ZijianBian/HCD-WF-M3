
import sys 
sys.path.append('interface')
from tkinter import *
from hover_class import *
import os
from datetime import datetime
cb = 'LavenderBlush3'
c_arr=['red', 'blue','yellow','green']


def make_flowchart(old_frame, window,  maindict,workflow_param,  c1, c2, c3, c4, c5):
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
    actors_ref = list(maindict.keys())[0]
    make_core_ids_ref = list(maindict.keys())[1]

    cod_ref = list(workflow_param.keys())[2]
    print(workflow_param)

    def click_actors(l0, l1, l2, conn_list_cur, fr):
        if l1.grid_info():
            l1.grid_remove()
            l2.grid_remove()
        else:
            l1.grid()
            l2.grid()

        fr.delete('all')
        for elem in conn_list_cur:
            connect_labels(fr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])

        base.delete('all')
        for elem in conn_list:

            connect_labels(base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])



    def click_labels(f_or_l, cur_label, cur_frame, base, conn_list):
        if f_or_l == 'l':
            cur_frame.grid()
            cur_label.grid_remove()
            base.rowconfigure(cur_frame.grid_info()['row'] +1, minsize = 0)
            cur_frame.update()
        else:
            cur_label.grid()
            base.rowconfigure(cur_frame.grid_info()['row'] +1, minsize = 20)
            cur_frame.grid_remove()
            

        base.delete('all')
        for elem in conn_list:

            connect_labels(base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])


    def connect_labels(canvas, w1, dir1, w2, dir2, arrow_yn, l, nrl ):

        canvas.update()
        ulx1  = w1.winfo_x()
        uly1  = w1.winfo_y()
        ulx2  = w2.winfo_x()
        uly2  = w2.winfo_y()

        def find_coord(dir, widget, l, nrl):
            if dir == 'n':
                l_x  = widget.winfo_x()+ (widget.winfo_width()/nrl)*(l - 0.5)
                l_y  = widget.winfo_y() 
            elif dir == 'e':
                l_x  = widget.winfo_x() + widget.winfo_width() 
                l_y  = widget.winfo_y() + (widget.winfo_height()/nrl)*(l - 0.5)
            elif dir == 's':
                l_x = widget.winfo_x() + (widget.winfo_width()/nrl)*(l - 0.5)
                l_y = widget.winfo_y() + widget.winfo_height()
            elif dir == 'w':
                l_x = widget.winfo_x()
                l_y = widget.winfo_y() +( widget.winfo_height()/nrl)*(l - 0.5)
            return(l_x, l_y)



        (line_start_x, line_start_y) = find_coord(dir1, w1, l, nrl)
        (line_end_x,   line_end_y)   = find_coord(dir2, w2, l, nrl)

        dx = line_end_x - line_start_x
        dy = line_end_y - line_start_y

        if arrow_yn:
            arrow_yn = LAST
        else:
            arrow_yn = NONE

        if ((dir1 == 'n' or dir1 == 's') and (dir2 == 'e' or dir2 == 'w')) or ((dir1 == 'e' or dir1 == 'w') and(dir2 == 'n' or dir2 == 's')):
            canvas.create_line(line_start_x, line_start_y,
                               line_start_x, line_end_y,
                               line_end_x, line_end_y, 
                               width = 2, arrow = arrow_yn, fill =c5)

        if ((dir1 == 'n' and dir2 == 's') or (dir1 == 's' and dir2 == 'n')):
            canvas.create_line(line_start_x, line_start_y,
                               line_start_x, line_start_y + dy/2,
                               line_end_x, line_start_y + dy/2,
                               line_end_x, line_end_y, 
                               width = 2, arrow = arrow_yn, fill =c5)

        if ((dir1 == 'e'and dir2 == 'w') or (dir1 == 'w'and dir2 == 'e')):
            canvas.create_line(line_start_x, line_start_y, 
                               line_start_x + dx/2, line_start_y, 
                               line_start_x + dx/2, line_end_y, 
                               line_end_x, line_end_y,
                               width = 2, arrow = arrow_yn, fill =c5)


#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

    old_frame.grid_forget()
    base = Canvas(window, width = 100, height = 100, bg = c1)
    base.grid(row = 0, column = 2, sticky = 'news')
    base.rowconfigure(0, minsize = 30)
    base.columnconfigure(0, minsize = 30)
    base.columnconfigure(1, minsize = 600)
    base.columnconfigure(2, minsize = 30)
    base.columnconfigure(3, minsize = 40)
    
    conn_list = []


    ## CREATE BASIC LAYOUT FOR THE FLOWCHART)
    initla = Label(base, bg = c2, text = 'INITIALIZING', font = '14', relief = 'solid', pady = 5, width = 25)
    initfr = Canvas(base, bg = c1, height = 1)
    hcdla  = Label(base, bg = c2, text = 'H&CD', font = '14', relief = 'solid', pady = 5)
    hcdfr  = Canvas(base, bg = c1, height = 1)
    mergela = Label(base, bg = c2, text = 'MERGING', font = '14', relief = 'solid', pady = 5)
    mergefr = Canvas(base, bg = c1, height = 1)
    corela  = Label(base, bg = c2, text = 'MAKE CORE IDS', font = '14', relief = 'solid', pady = 5)
    corefr  = Canvas(base, bg = c1, height = 1)
    tcontla = Label(base, bg = c2, text = 'CONTROL BLOCK FOR TIMELOOP', font = '14', relief = 'solid', pady = 0)
    tcontfr = Canvas(base, bg = c1, height = 1)
    finalla = Label(base, bg = c2, text = 'FINALISING', font = '14', relief = 'solid', pady = 5)
    finalfr = Canvas(base, bg = c1, height = 1)

    conn_list.append([initla, 's', hcdla, 'n', False,  1, 1])
    conn_list.append([hcdla, 's', mergela, 'n', False, 1, 1])
    conn_list.append([mergela, 's', corela, 'n', False,1, 1])
    conn_list.append([corela, 's', tcontla, 'n', False,1, 1])
    conn_list.append([tcontla, 's', finalla, 'n', False,1, 1])

    initla.grid(row = 1, column = 1, sticky = 'ew')
    initfr.grid(row = 2, column = 1, sticky = 'ew')
    base.rowconfigure(3, minsize = 20)
    hcdla.grid(row = 4,  column = 1, sticky = 'ew')
    hcdfr.grid(row = 5, column = 1)
    hcdfr.grid_remove()
    hcdla.bind('<Button-1>', lambda event: click_labels('l', hcdla, hcdfr, base, conn_list))
    hcdfr.bind('<Button-1>', lambda event: click_labels('f',hcdla, hcdfr, base, conn_list))
    base.rowconfigure(6, minsize = 20)
    mergela.grid(row = 7, column = 1, sticky = 'ew')
    mergefr.grid(row = 8, column = 1)
    mergela.bind('<Button-1>', lambda event: click_labels('l', mergela, mergefr, base, conn_list))
    mergefr.bind('<Button-1>', lambda event: click_labels('f',mergela, mergefr, base, conn_list))
    mergefr.grid_remove()    
    base.rowconfigure(9, minsize = 20)
    corela.grid(row = 10, column = 1, sticky = 'ew')
    corefr.grid(row = 11, column = 1)
    corefr.grid_remove()
    corela.bind('<Button-1>', lambda event: click_labels('l', corela, corefr, base, conn_list))
    corefr.bind('<Button-1>', lambda event: click_labels('f', corela, corefr, base, conn_list))
    base.rowconfigure(12, minsize = 20)
    tcontla.grid(row = 13, column = 1, sticky = 'ew')
    tcontfr.grid(row = 14, column = 1)
    tcontla.bind('<Button-1>', lambda event: click_labels('l', tcontla,tcontfr,  base, conn_list))
    tcontfr.bind('<Button-1>', lambda event: click_labels('f',  tcontla,tcontfr, base, conn_list))
    tcontfr.grid_remove()
    base.rowconfigure(15, minsize = 20)
    finalla.grid(row = 16, column = 1, sticky = 'ew')
    finalfr.grid(row = 17, column = 1, sticky = 'ew')

    

    ## INITIALISE FRAME-----------------------------------------------------------------------------

    ## HCD FRAME------------------------------------------------------------------------------------
    ccol = 1
    ccol_max = 0
    rrow_max = 0
    conn_list_hcd = []
    isys = 0
    inv = Frame(hcdfr, height = 1, width = 1, bg = c5)
    inv.grid(row = 0, columnspan = 50, pady = 0)
    inv1 = []

    for hsys in maindict[actors_ref]:
        rrow = 1
 
        if sum([int(workflow_param[cod_ref][i]) for i in maindict[actors_ref][hsys]]) is not 0:
            isys += 1
            oldlabel = hcdla

            inv1.append(Frame(hcdfr, height = 1, width = 1, bg = c5))
            inv1[-1].grid(row = 50, column = ccol, pady = (50,0))

            for cat in maindict[actors_ref][hsys]:
                icat = 0
                if int(workflow_param[cod_ref][cat]) is not 0:
                    curval = list(maindict[actors_ref][hsys][cat])[int(workflow_param[cod_ref][cat])-1]
                    input_text = "\n - ".join([strv for strv in maindict[actors_ref][hsys][cat][curval][0]])
                    output_text = "\n - ".join([strv for strv in maindict[actors_ref][hsys][cat][curval][1]])

                    hcdfr.rowconfigure(rrow, minsize = 30)

                    l1 = Label(hcdfr, text = ' - '+input_text, bg = 'ivory',anchor = W,  justify = LEFT)
                    l1.grid(column = ccol, row = rrow+1, sticky = 'sew')
                    l1.grid_remove()
                    
                    l0 = Label(hcdfr, text = curval, bg = c4, relief = 'solid')
                    l0.grid(column = ccol, row = rrow+2, sticky = 'nsew')
                    
                    l2 = Label(hcdfr, text = ' - '+ output_text, bg = 'floral white',anchor = W,  justify = LEFT)
                    l2.grid(column = ccol, row = rrow+3, sticky = 'new')
                    l2.grid_remove()
                    
                    
                    l0.bind('<Button-1>', lambda event, l0 = l0, l1= l1, l2 = l2: click_actors(l0,l1,l2, conn_list_hcd, hcdfr))

                    
                    hcdfr.columnconfigure(ccol  , minsize = 120)
                    if ccol > 1:
                        hcdfr.columnconfigure(ccol-1, minsize = 20)

                   # CreateToolTip(l0,'INPUT\n - '+ input_text +'\n OUTPUT\n -'+ output_text)

                    rrow += 3
        
                   
                    if rrow == 4:
                        conn_list_hcd.append([inv, 's', l0, 'n', True,1, 1])
                    else:
                        conn_list_hcd.append([oldlabel, 's', l0, 'n', True,1, 1])
                    oldlabel = l0
                    icat += 1
                    
                    conn_list_hcd.append([oldlabel, 's', inv1[-1], 'n', False, 1, 1])

            ccol += 2

  #  for il in range(isys):
        #conn_list.append([hcdla, 's', mergela, 'n', True, il,  isys+1])

    

    for elem in conn_list_hcd:
        connect_labels(hcdfr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])
            
    # MERGER FRAME:------------------------------------------------------------------------------------
    merge_distributions = 0
    merge_waves = 0
    merge_distribution_sources = 0

    conn_list_merge = []
    conn_list_merge_others = []
    ccol = 1
    inv = {}

    invrow = Frame(mergefr, bg = c1)
    invrow.grid(row = 1, column = 1)
    isys = -1
    inv_bot = Frame(mergefr, height = 10, width = 1, bg = c1)
    inv_bot.grid(row = 50, column = 0, columnspan = 50)
    

    for hsys in maindict[actors_ref]:
        if sum([int(workflow_param[cod_ref][i]) for i in maindict[actors_ref][hsys]]) is not 0:
            isys +=1 
            if ccol > 1:
                invrow.columnconfigure(ccol, minsize = 20)
            invrow.columnconfigure(ccol+1, minsize = 120)
            inv[hsys] = Frame(invrow, height = 3, width = 10, bg = c1 )
            inv[hsys].grid(row = 1, column = ccol+1, sticky  = 'ew')
            ccol += 2
            print(hsys, isys)
            



    labelrow = Frame(mergefr, bg = c1)
    labelrow.grid(row = 3, column = 1)

    minsize_row = 40

    for hsys in maindict[actors_ref]:
        for cat in maindict[actors_ref][hsys]:
            curval = list(maindict[actors_ref][hsys][cat])[int(workflow_param[cod_ref][cat])-1]

            if((int(workflow_param[cod_ref][cat]) is not 0) and (curval.find('iccoup') is -1)):
                if ''.join(maindict[actors_ref][hsys][cat][curval][1]).find('distributions') is not -1:
                    merge_distributions += 1
                    
                if ''.join(maindict[actors_ref][hsys][cat][curval][1]).find('distribution_sources') is not -1:
                    merge_distribution_sources += 1
                    
                if ''.join(maindict[actors_ref][hsys][cat][curval][1]).find('waves') is not -1:
                    merge_waves += 1
            

    no_merge_dist = False
    no_merge_sources = False
    no_merge_waves = False
                    
                    
    
    if merge_distributions > 1:
        mdist = Label(labelrow, text = 'merge distributions', bg = c4, relief = 'solid')
        mdist.grid(row =  1, column = 0, padx = 40)
      
        if 'NBI' in inv:
            conn_list_merge.append([inv['NBI'], mdist])
        if 'NUCLEAR' in inv:
            conn_list_merge.append([inv['NUCLEAR'], mdist])
        if 'ICRH' in inv:
            conn_list_merge.append([inv['ICRH'], mdist])
        
      #  conn_list_merge.append([mdist, inv_bot])
        conn_list_merge_others.append([mdist, 's', inv_bot, 'n',True, 1, 1])
        minsize_row += 40
    else: 
        no_merge_dist = True

    if merge_distribution_sources > 1:
        msour = Label(labelrow, text = 'merge sources', bg = c4, relief = 'solid')
        msour.grid(row = 1, column = 2, padx = 40)

        conn_list_merge.append([inv['NBI'], msour])
        conn_list_merge.append([inv['NUCLEAR'], msour])
        minsize_row += 40
    #    conn_list_merge.append([msour, inv_bot])
        conn_list_merge_others.append([msour, 's', inv_bot, 'n',True, 1, 1])
    else:
        no_merge_sources = True
    

    if merge_waves > 1:
        mwave = Label(labelrow, text = 'merge waves', bg = c4, relief = 'solid')
        mwave.grid(row = 1, column = 4, padx = 40)

        conn_list_merge.append([inv['ECRH'], mwave])
        conn_list_merge.append([inv['ICRH'], mwave])
        minsize_row += 40
     
        #   conn_list_merge.append([mwave, inv_bot])
        #  ---  connect lines on the mergefr canvas
        

    else: 
        no_merge_waves = True
       
    
    if no_merge_waves == True  and no_merge_sources == True and no_merge_dist == True: 
        print('all false')
        l = Label(mergefr, text = 'no merges necessary', bg = c2)
        l.grid(row = 3, column = 0 , columnspan = 30, sticky = 'ns')
        conn_list_merge_others.append([l, 's', inv_bot, 'n', False, 1, 1])
    else:
        mergefr.rowconfigure(2, minsize = minsize_row)
        mergefr.rowconfigure(4, minsize = 40)

    def mergefr_draw_lines(inv_n, label_n):
        mergefr.update()
        
        line_start_x = inv_n.winfo_x()+ inv_n.winfo_width()/2 
        line_start_y = inv_n.winfo_y() + inv_n.winfo_height()
        line_end_x   = label_n.winfo_x() + label_n.winfo_width()/2 + labelrow.winfo_x()
        line_end_y   = label_n.winfo_y() + labelrow.winfo_y()
        
        mergefr.create_line(line_start_x, line_start_y, line_end_x, line_end_y, width = 2, arrow = None, fill = c5)

    def mergefr_draw_lines_bottom(inv_n, label_n):
            line_start_x = label_n.winfo_x() + label_n.winfo_width()/2 + labelrow.winfo_x()+labelrow.winfo_height()


    for elem in conn_list_merge:
        mergefr_draw_lines(elem[0], elem[1])

       # --- draw the remaining lines

    for elem in conn_list_merge_others:
        connect_labels(mergefr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])
   
    
    

    #MAKE CORE IDS: ------------------------------------------------------------------------------------
    isys = 0
    ccol = 1
    ccol_max = 0
    rrow_max = 0
    conn_list_core = []
    


    inv = Frame(corefr, height = 1, width = 1, bg = c5)
    inv.grid(row = 0, columnspan = 50)

    bl = Frame(corefr, height = 1, width = 1,bg = c1)
    bl.grid(row = 50, column = 0, columnspan = 50, padx = 10)


    for hsys in maindict[make_core_ids_ref]:
        
        isys += 1
        rrow = 1
        if sum([int(workflow_param[cod_ref][i]) for i in workflow_param[cod_ref]]) is not 0:
    
            oldlabel = l0
            for cat in maindict[make_core_ids_ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    curval = list(maindict[make_core_ids_ref][hsys][cat])[int(workflow_param[cod_ref][cat])-1]
                    input_text = "\n - ".join([strv for strv in maindict[make_core_ids_ref][hsys][cat][curval][0]])
                    output_text = "\n - ".join([strv for strv in maindict[make_core_ids_ref][hsys][cat][curval][1]])


                    corefr.rowconfigure(rrow, minsize = 30)

                    l1 = Label(corefr, text = input_text, bg = c1, relief = 'solid')
                    l1.grid(column = ccol, row = rrow, sticky = 'sew')
                    l1.grid_remove()
                    l0 = Label(corefr, text = curval, bg = c4, relief = 'solid')
                    l0.grid(column = ccol, row = rrow+1, sticky = 'nsew')
                    
                    l2 = Label(corefr, text = output_text, bg = c1, relief = 'solid')
                    l2.grid(column = ccol, row = rrow+2, sticky = 'new')
                    l2.grid_remove()
                    
                    rrow += 2
                    
                    
                    corefr.columnconfigure(ccol  , minsize = 120)
                    if ccol > 1:
                        corefr.columnconfigure(ccol-1, minsize = 30)

                    l0.bind('<Button-1>', lambda event, l0 = l0, l1= l1, l2 = l2: click_actors(l0,l1,l2, conn_list_core, corefr))            
                    conn_list_core.append([inv, 's', l0, 'n', True, 1, 1])
                    conn_list_core.append([l0,  's', bl, 'n', True, 1, 1])

            ccol += 2 


        corefr.rowconfigure(rrow, minsize = 50)
        
    print(len(conn_list_core))

    if len(conn_list_core) ==0 :
        
        l = Label(corefr, text = 'no actors selected', bg = c2)
        l.grid(row = rrow-1, sticky = 'ew')
        conn_list_core.append([inv, 's', l, 'n', False, 1, 1])
        conn_list_core.append([l, 's', bl, 'n', False, 1, 1])
    
    for elem in conn_list_core:
        connect_labels(corefr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])
    

    #TIME CONTROL BLOCK WINDOW

    conn_list_timec = []

    inv = Frame(base, height = 1, width = 1, bg = c1)
    inv1 = Frame(base, height = 1, width = 1, bg = c1)
    inv2 = Frame(base, height = 1, width = 1, bg = c1)
    inv3 = Frame(base, height = 1, width = 1, bg = c1)


    inv.grid(row = 13,  column = 3)
    inv1.grid(row = 13, column = 2)
    inv2.grid(row = 3,  column = 3)
    inv3.grid(row = 3, column = 1) #, columnspan = 50)

    conn_list.append([inv, 'e', inv1, 'w', False, 1, 1])
    conn_list.append([inv2, 'n', inv2, 's', False, 1, 1])
    conn_list.append([inv2, 'w', inv3, 'e', True, 1, 1])



    inv1 = Frame(tcontfr, height = 1, width = 1, bg = c1)
    inv1.grid(row = 0)
    inv2 = Frame(tcontfr, height = 1, width = 1, bg = c1)
    inv2.grid(row = 50)
    tla = Label(tcontfr, text = 'time++ \n if time < tend', bg = c2)
    tla.grid(row = 1, columnspan = 50, sticky = 'ew')


    conn_list_timec.append([inv1, 's', tla, 'n', False, 1, 1])
    conn_list_timec.append([tla, 's',inv2, 'n', False, 1, 1])

    tcontfr.rowconfigure(2, minsize = 20)

    for elem in conn_list_timec:
       connect_labels(base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5],elem[6])
       

    ### CONNECT LINE BASELEVEL
    for elem in conn_list:
        connect_labels(base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5],elem[6])
    
    
