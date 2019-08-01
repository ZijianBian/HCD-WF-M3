
import sys 
sys.path.append('interface')
from tkinter import *
from hover_class import *
import os
from datetime import datetime
cb = 'LavenderBlush3'
c_arr=['red', 'blue','yellow','green']


def make_flowchart(old_frame, window,  maindict, c1, c2, c3, c4, c5):
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------------

    def click_labels(f_or_l, cur_label, cur_frame, base, conn_list):
        if f_or_l == 'l':
            cur_frame.grid()
            cur_label.grid_remove()
            cur_frame.update()
        else:
            cur_label.grid()
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
                               line_end_x + dx/2, line_start_y, 
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
    base.columnconfigure(1, minsize = 500)
    
    conn_list = []


    ## CREATE BASIC LAYOUT FOR THE FLOWCHART)
    initla = Label(base, bg = c2, text = 'INITIALIZING', font = '16')
    initfr = Canvas(base, bg = c1, height = 1)
    hcdla  = Label(base, bg = c2, text = 'H&CD', font = '16')
    hcdfr  = Canvas(base, bg = c1, height = 1)
    mergela = Label(base, bg = c2, text = 'MERGING', font = '16')
    mergefr = Canvas(base, bg = c2, height = 1)
    corela  = Label(base, bg = c2, text = 'MAKE CORE IDS', font = '16')
    corefr  = Canvas(base, bg = c1, height = 1)
    tcontla = Label(base, bg = c2, text = 'CONTROL BLOCK FOR TIMELOOP', font = '16')
    tcontfr = Canvas(base, bg = c1, height = 1)
    finalla = Label(base, bg = c2, text = 'FINALISING', font = '16')
    finalfr = Canvas(base, bg = c1, height = 1)

    conn_list.append([initla, 's', hcdla, 'n', False,  1, 1])
    conn_list.append([hcdla, 's', mergela, 'n', False, 1, 1])
    conn_list.append([mergela, 's', corela, 'n', False,1, 1])
    conn_list.append([corela, 's', tcontla, 'n', False,1, 1])
    conn_list.append([tcontla, 's', finalla, 'n', False,1, 1])

    initla.grid(row = 1, column = 1, sticky = 'ew')
    initfr.grid(row = 2, column = 1, sticky = 'ew')
    initla.bind('<Button-1>', lambda event: click_labels('l', initla, initfr, base, conn_list))
    initfr.bind('<Button-1>', lambda event: click_labels('f', initla, initfr, base, conn_list))
    base.rowconfigure(3, minsize = 20)
    hcdla.grid(row = 4,  column = 1, sticky = 'ew')
    hcdfr.grid(row = 5, column = 1)
    hcdfr.grid_remove()
    hcdla.bind('<Button-1>', lambda event: click_labels('l', hcdla, hcdfr, base, conn_list))
    hcdfr.bind('<Button-1>', lambda event: click_labels('f',hcdla, hcdfr, base, conn_list))
    base.rowconfigure(6, minsize = 20)
    mergela.grid(row = 7, column = 1, sticky = 'ew')
    mergefr.grid(row = 8, column = 1)
    mergefr.grid_remove()
    mergela.bind('<Button-1>', lambda event: click_labels('l', mergela, mergefr, base, conn_list))
    mergefr.bind('<Button-1>', lambda event: click_labels('f',mergela, mergefr, base, conn_list))
    base.rowconfigure(9, minsize = 20)
    corela.grid(row = 10, column = 1, sticky = 'ew')
    corefr.grid(row = 11, column = 1)
    corefr.grid_remove()
    corela.bind('<Button-1>', lambda event: click_labels('l', corela, corefr, base, conn_list))
    corefr.bind('<Button-1>', lambda event: click_labels('f', corela, corefr, base, conn_list))
    base.rowconfigure(12, minsize = 20)
    tcontla.grid(row = 13, column = 1, sticky = 'ew')
    tcontfr.grid(row = 14, column = 1, sticky = 'ew')
    tcontfr.grid_remove()
    tcontla.bind('<Button-1>', lambda event: click_labels('l', tcontla, tcontfr, base, conn_list))
    tcontla.bind('<Button-1>', lambda event: click_labels('f', tcontla, tcontfr, base, conn_list))
    base.rowconfigure(15, minsize = 20)
    finalla.grid(row = 16, column = 1, sticky = 'ew')
    finalfr.grid(row = 17, column = 1, sticky = 'ew')
    finalfr.grid_remove()
    finalla.bind('<Button-1>', lambda event: click_labels('l', finalla, finalfr, base, conn_list))
    finalla.bind('<Button-1>', lambda event: click_labels('f', finalla, finalfr, base, conn_list))

    ## INITIALISE FRAME-----------------------------------------------------------------------------
    Label(initfr, text = 'information',bg = c1).grid(row = 0, column = 0, sticky = 'nsew')
    initfr.columnconfigure(0, minsize = 500)
    
    ## HCD FRAME------------------------------------------------------------------------------------
    ccol = 1
    ccol_max = 0
    rrow_max = 0
    conn_list_hcd = []
    isys = 0
    inv = Frame(hcdfr, height = 1, width = 1, bg = c1)
    inv.grid(row = 0, columnspan = 50, pady = 2)

    for sys in maindict['systems']:
        rrow = 1
        if sum([int(maindict['systems'][sys][i][1]) for i in maindict['systems'][sys]]) is not 0:
            isys += 1
            oldlabel = hcdla
            for cat in maindict['systems'][sys]:
                icat = 0
                if int(maindict['systems'][sys][cat][1]) is not 0:
                    curval = list(maindict['systems'][sys][cat][0])[int(maindict['systems'][sys][cat][1])-1]
                    input_text = "\n - ".join([strv for strv in maindict['systems'][sys][cat][0][curval][0]])
                    output_text = "\n - ".join([strv for strv in maindict['systems'][sys][cat][0][curval][1]])

                    l0 = Label(hcdfr, text = curval, bg = c4, relief = 'solid')
                    l0.grid(column = ccol, row = rrow, sticky = 'nsew', pady = (40,0))
                    

                    hcdfr.rowconfigure(rrow, minsize = 30)
                    hcdfr.columnconfigure(ccol  , minsize = 120)
                    if ccol > 1:
                        hcdfr.columnconfigure(ccol-1, minsize = 30)

                    CreateToolTip(l0,'INPUT\n - '+ input_text +'\n OUTPUT\n -'+ output_text)

                    rrow += 3
                   
                    if rrow == 4:
                        conn_list_hcd.append([inv, 's', l0, 'n', True,1, 1])
                    else:
                        conn_list_hcd.append([oldlabel, 's', l0, 'n', True,1, 1])
                    oldlabel = l0
                    icat += 1
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
    ccol = 1
    inv = {}

    for sys in maindict['systems']:
        if sum([int(maindict['systems'][sys][i][1]) for i in maindict['systems'][sys]]) is not 0:
            print(sys)
            inv[sys] = Frame(mergefr, height = 10, width = 10, bg = 'black')
            inv[sys].grid(row = 0, column = ccol, pady = 2)

            mergefr.columnconfigure(ccol  , minsize = 120)
            if ccol > 1:
                mergefr.columnconfigure(ccol-1, minsize = 30)        

       
            ccol +=2
            


    for sys in maindict['systems']:
        for cat in maindict['systems'][sys]:
            curval = list(maindict['systems'][sys][cat][0])[int(maindict['systems'][sys][cat][1])-1]

            if((int(maindict['systems'][sys][cat][1]) is not 0) and (curval.find('iccoup') is -1)):
                if ''.join(maindict['systems'][sys][cat][0][curval][1]).find('distributions') is not -1:
                    merge_distributions += 1
                if ''.join(maindict['systems'][sys][cat][0][curval][1]).find('distribution_sources') is not -1:
                    merge_distribution_sources += 1
                if ''.join(maindict['systems'][sys][cat][0][curval][1]).find('waves') is not -1:
                    merge_waves += 1

    #mergefr.rowconfigure(0, minsize = 30)

    b = Label(mergefr, text = 'bundle', bg = cb, relief = 'solid')
    b.grid(row = 3,column = 0, columnspan = 5)
    mergefr.rowconfigure(2, minsize = 30)
            
    if merge_distributions > 1:
        mdist = Label(mergefr, text = 'merge distributions', bg = c4, relief = 'solid')
        mdist.grid(row = 1, column = 0, sticky = 'nsew', pady = 40)
        


        conn_list_merge.append([inv['NBI'], 's', mdist, 'n', True, 1,3])
        conn_list_merge.append([inv['ALPHA'], 's', mdist, 'n', True, 2,3])
        conn_list_merge.append([inv['ICRH'], 's', mdist, 'n', True, 3, 3])

        conn_list_merge.append([mdist, 's', b, 'n', True, 1, 1])
       
    else:
        merge_distributions = 0
        
    if merge_distribution_sources > 1:
        msour = Label(mergefr, text = 'merge sources', bg = c4, relief = 'solid')
        msour.grid(row = 1, column = 2, sticky = 'nsew', pady = 40)



        conn_list_merge.append([inv['NBI'], 's', msour, 'n', True, 1,2])
        conn_list_merge.append([inv['ALPHA'], 's', msour, 'n', True, 2,2])

        conn_list_merge.append([msour, 's', b, 'n', True, 1,1])


    else:
        merge_distribution_sources = 0
        
    if merge_waves > 1:
        mwave = Label(mergefr, text = 'merge_waves', bg = c4, relief = 'solid')
        mwave.grid(row = 1, column = 4, sticky = 'nsew', pady = 40)



        conn_list_merge.append([inv['ECRH'], 's', mwave, 'n', True, 1,2])
        conn_list_merge.append([inv['ICRH'], 's', mwave, 'n', True, 2,2])
        conn_list_merge.append([mwave, 's', b, 'n', True, 1,1])
    else:
        merge_waves = 0
    
    if (merge_waves + merge_distribution_sources + merge_distributions) == 0:
        Label(mergefr, text = '(no merges necessary)', bg = c1).grid(sticky = 'ew')
    
        mergefr.columnconfigure(0, minsize = 500)
        mergefr.rowconfigure(0, minsize = 0)




    for elem in conn_list_merge:
        connect_labels(mergefr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])
          
    
     

    #MAKE CORE IDS: ------------------------------------------------------------------------------------
    isys = 0
    ccol = 1
    ccol_max = 0
    rrow_max = 0
    conn_list_core = []
    


    inv = Frame(corefr, height = 1, width = 1, bg = c1)
    inv.grid(row = 0, columnspan = 50, pady = 2)

    bl = Label(corefr, text = 'bundle', bg = cb, relief = 'solid')
    bl.grid(row = 50, column = 0, columnspan = 50, padx = 10, pady = (50,0))


    for sys in maindict['post_process']:
        
        isys += 1
        rrow = 1
        if sum([int(maindict['post_process'][sys][i][1]) for i in maindict['post_process'][sys]]) is not 0:
    
            oldlabel = l0
            for cat in maindict['post_process'][sys]:
                if int(maindict['post_process'][sys][cat][1]) is not 0:
                    curval = list(maindict['post_process'][sys][cat][0])[int(maindict['post_process'][sys][cat][1])-1]
                    input_text = "\n - ".join([strv for strv in maindict['post_process'][sys][cat][0][curval][0]])
                    output_text = "\n - ".join([strv for strv in maindict['post_process'][sys][cat][0][curval][1]])

                    l0 = Label(corefr, text = curval, bg = c4, relief = 'solid')
                    l0.grid(column = ccol, row = rrow, sticky = 'nsew', pady = 40)

                    corefr.rowconfigure(rrow, minsize = 30)
                    corefr.columnconfigure(ccol  , minsize = 120)
                    if ccol > 1:
                        corefr.columnconfigure(ccol-1, minsize = 30)

                    CreateToolTip(l0,'INPUT\n - '+ input_text +'\n OUTPUT\n -'+ output_text)

                    rrow += 3
                   
            ccol += 2 

            conn_list_core.append([inv, 's', l0, 'n', True, 1, 1])
            conn_list_core.append([l0,  's', bl, 'n', True, isys, len(maindict['post_process'])])

    
    for elem in conn_list_core:
        connect_labels(corefr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6])
    

    #TIME CONTROL BLOCK WINDOW


    ### CONNECT LINE BASELEVEL
    for elem in conn_list:
        connect_labels(base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5],elem[6])
    
    

