import tkinter

import interface.colour_definitions as col
from interface.flowchart_functions import (
    merge_bottom_lines,
    mergefr_draw_lines,
    hide_display,
    click_actors,
    click_labels,
    connect_labels,
)

cb = "LavenderBlush3"
c_arr = ["red", "blue", "yellow", "green"]
mergec = ["red4", "blue4", "yellow4"]


def make_flowchart(removed_by_close_button, window, maindict, workflow_param):

    infolabelcolor = col.c2

    actors_ref = list(maindict.keys())[1]
    make_core_ids_ref = list(maindict.keys())[2]

    ## abbreviations for the keys - makes it easier to change them in the xml file
    wfp_ref = list(workflow_param.keys())[0]
    cod_ref = list(workflow_param.keys())[1]

    base = tkinter.Canvas(window, width=100, height=100, bg=col.c1)
    base.grid(row=0, column=2, sticky="news")
    base.rowconfigure(0, minsize=30)
    base.columnconfigure(0, minsize=30)
    base.columnconfigure(1, minsize=600)
    base.columnconfigure(2, minsize=30)
    base.columnconfigure(3, minsize=40)

    conn_list = []

    exitbutton = tkinter.Button(base, text="close")
    exitbutton.grid(row=0, column=3, padx=2, pady=2)
    exitbutton.configure(command=lambda: hide_display(removed_by_close_button))

    # --------------------------------------
    # CREATE BASIC LAYOUT FOR THE FLOWCHART
    # --------------------------------------
    initla = tkinter.Label(
        base,
        bg=col.c2,
        text="INITIALIZING",
        font="14",
        relief="solid",
        pady=5,
        width=25,
    )
    initfr = tkinter.Canvas(base, bg=col.c1, height=1)
    hcdla = tkinter.Label(
        base, bg=col.c2, text="H&CD", font="14", relief="solid", pady=5
    )
    hcdfr = tkinter.Canvas(base, bg=col.c1, height=1)
    mergela = tkinter.Label(base, bg=col.c2, text="MERGING", font="14", relief="solid")
    mergefr = tkinter.Canvas(base, bg=col.c1, height=1)
    corela = tkinter.Label(
        base, bg=col.c2, text="MAKE CORE IDS", font="14", relief="solid", pady=5
    )
    corefr = tkinter.Canvas(base, bg=col.c1, height=1)
    tcontla = tkinter.Label(
        base, bg=col.c2, text="TIMELOOP CONTROL", font="14", relief="solid", pady=0
    )
    tcontfr = tkinter.Canvas(base, bg=col.c1, height=1)
    finalla = tkinter.Label(
        base, bg=col.c2, text="FINALISING", font="14", relief="solid", pady=5
    )
    finalfr = tkinter.Canvas(base, bg=col.c1, height=1)

    conn_list.append([initla, "s", hcdla, "n", False, 1, 1])
    conn_list.append([hcdla, "s", mergela, "n", False, 1, 1])
    conn_list.append([mergela, "s", corela, "n", False, 1, 1])
    conn_list.append([corela, "s", tcontla, "n", False, 1, 1])
    conn_list.append([tcontla, "s", finalla, "n", False, 1, 1])

    initla.grid(row=1, column=1, sticky="ew")
    initfr.grid(row=2, column=1, sticky="ew")
    initla.bind(
        "<Button-1>", lambda event: click_labels("il", initla, initfr, base, conn_list)
    )
    initfr.bind(
        "<Button-1>", lambda event: click_labels("if", initla, initfr, base, conn_list)
    )
    initfr.grid_remove()

    base.rowconfigure(3, minsize=20)
    hcdla.grid(row=4, column=1, sticky="ew")
    hcdfr.grid(row=5, column=1)
    hcdfr.grid_remove()
    hcdla.bind(
        "<Button-1>", lambda event: click_labels("l", hcdla, hcdfr, base, conn_list)
    )
    hcdfr.bind(
        "<Button-1>", lambda event: click_labels("f", hcdla, hcdfr, base, conn_list)
    )

    base.rowconfigure(6, minsize=20)
    mergela.grid(row=7, column=1, sticky="ew")
    mergefr.grid(row=8, column=1)
    mergela.bind(
        "<Button-1>",
        lambda event: click_labels("ml", mergela, mergefr, base, conn_list),
    )
    mergefr.bind(
        "<Button-1>",
        lambda event: click_labels("mf", mergela, mergefr, base, conn_list),
    )
    mergefr.grid_remove()

    base.rowconfigure(9, minsize=20)
    corela.grid(row=10, column=1, sticky="ew")
    corefr.grid(row=11, column=1)
    corefr.grid_remove()
    corela.bind(
        "<Button-1>", lambda event: click_labels("l", corela, corefr, base, conn_list)
    )
    corefr.bind(
        "<Button-1>", lambda event: click_labels("f", corela, corefr, base, conn_list)
    )

    base.rowconfigure(12, minsize=20)
    tcontla.grid(row=13, column=1, sticky="ew")
    tcontfr.grid(row=14, column=1, sticky="ew")
    tcontla.bind(
        "<Button-1>",
        lambda event: click_labels("il", tcontla, tcontfr, base, conn_list),
    )
    tcontfr.bind(
        "<Button-1>",
        lambda event: click_labels("if", tcontla, tcontfr, base, conn_list),
    )
    tcontfr.grid_remove()

    base.rowconfigure(15, minsize=20)
    finalla.grid(row=16, column=1, sticky="ew")
    finalfr.grid(row=17, column=1, sticky="ew")
    finalla.bind(
        "<Button-1>", lambda event: click_labels("l", finalla, finalfr, base, conn_list)
    )
    finalfr.bind(
        "<Button-1>", lambda event: click_labels("f", finalla, finalfr, base, conn_list)
    )
    finalfr.grid_remove()

    # -----------------
    # INITIALISE FRAME
    # -----------------

    il = tkinter.Label(
        initfr,
        text="reading input from database\n- shot:   "
        + workflow_param[wfp_ref]["shot_nr"]
        + "\n- run:   "
        + workflow_param[wfp_ref]["run_in"]
        + "\n- machine:   "
        + workflow_param[wfp_ref]["input_database"]
        + " \n- start time:   "
        + workflow_param[wfp_ref]["tbegin"]
        + "s \n- timestep:   "
        + workflow_param[wfp_ref]["dt_required"]
        + "s \n- end time:   "
        + workflow_param[wfp_ref]["tend"]
        + "s",
        bg=infolabelcolor,
        anchor=tkinter.W,
        justify=tkinter.LEFT,
        padx=4,
        pady=4,
    )

    il.pack(side=tkinter.TOP)

    # ----------
    # HCD FRAME
    # ----------
    ccol = 1
    ccol_max = 0
    rrow_max = 0
    conn_list_hcd = []
    isys = 0
    inv = tkinter.Frame(hcdfr, height=1, width=1, bg=col.c5)
    inv.grid(row=0, columnspan=50, pady=0)
    inv1 = []

    for hsys in maindict[actors_ref]:
        rrow = 1

        if (
            sum([int(workflow_param[cod_ref][i]) for i in maindict[actors_ref][hsys]])
            is not 0
        ):
            isys += 1
            oldlabel = hcdla

            inv1.append(tkinter.Frame(hcdfr, height=1, width=1, bg=col.c5))
            inv1[-1].grid(row=50, column=ccol, pady=(50, 0))

            for cat in maindict[actors_ref][hsys]:
                icat = 0
                if int(workflow_param[cod_ref][cat]) is not 0:
                    curval = list(maindict[actors_ref][hsys][cat])[
                        int(workflow_param[cod_ref][cat]) - 1
                    ]
                    input_text = "\n - ".join(
                        [strv for strv in maindict[actors_ref][hsys][cat][curval][0]]
                    )
                    output_text = "\n - ".join(
                        [strv for strv in maindict[actors_ref][hsys][cat][curval][1]]
                    )

                    hcdfr.rowconfigure(rrow, minsize=30)

                    l1 = tkinter.Label(
                        hcdfr,
                        text=" - " + input_text,
                        bg="ivory",
                        anchor=tkinter.W,
                        justify=tkinter.LEFT,
                    )
                    l1.grid(column=ccol, row=rrow + 1, sticky="sew")
                    l1.grid_remove()

                    l0 = tkinter.Label(hcdfr, text=curval, bg=col.c4, relief="solid")
                    l0.grid(column=ccol, row=rrow + 2, sticky="nsew")

                    l2 = tkinter.Label(
                        hcdfr,
                        text=" - " + output_text,
                        bg="floral white",
                        anchor=tkinter.W,
                        justify=tkinter.LEFT,
                    )
                    l2.grid(column=ccol, row=rrow + 3, sticky="new")
                    l2.grid_remove()

                    l0.bind(
                        "<Button-1>",
                        lambda event, l0=l0, l1=l1, l2=l2: click_actors(
                            l0, l1, l2, conn_list_hcd, hcdfr, base, conn_list
                        ),
                    )

                    hcdfr.columnconfigure(ccol, minsize=127)
                    if ccol > 1:
                        hcdfr.columnconfigure(ccol - 1, minsize=20)

                    rrow += 3

                    if rrow == 4:
                        conn_list_hcd.append([inv, "s", l0, "n", True, 1, 1])
                    else:
                        conn_list_hcd.append([oldlabel, "s", l0, "n", True, 1, 1])
                    oldlabel = l0
                    icat += 1

                    conn_list_hcd.append([oldlabel, "s", inv1[-1], "n", False, 1, 1])

            ccol += 2

    for elem in conn_list_hcd:
        connect_labels(
            hcdfr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6]
        )

    # -------------
    # MERGER FRAME
    # -------------
    merge_distributions = 0
    merge_waves = 0
    merge_distribution_sources = 0

    conn_list_merge = []
    conn_list_merge_others = []
    conn_list_merge_bottom = []
    ccol = 1
    inv = {}

    invrow = tkinter.Frame(mergefr, bg=col.c1)
    invrow.grid(row=1, column=1, sticky="ew")
    isys = -1
    inv_bot = tkinter.Frame(mergefr, height=1, width=2, bg=col.c5)
    inv_bot.grid(row=50, column=0, columnspan=50)

    for hsys in maindict[actors_ref]:
        if (
            sum([int(workflow_param[cod_ref][i]) for i in maindict[actors_ref][hsys]])
            is not 0
        ):
            isys += 1
            if ccol > 1:
                invrow.columnconfigure(ccol, minsize=20)
            invrow.columnconfigure(ccol + 1, minsize=127)
            inv[hsys] = tkinter.Frame(invrow, height=2, width=10, bg=col.c1)
            inv[hsys].grid(row=1, column=ccol + 1, sticky="ew")
            ccol += 2

    labelrow = tkinter.Frame(mergefr, bg=col.c1)
    labelrow.grid(row=3, column=1)

    minsize_row = 40

    for hsys in maindict[actors_ref]:
        for cat in maindict[actors_ref][hsys]:
            curval = list(maindict[actors_ref][hsys][cat])[
                int(workflow_param[cod_ref][cat]) - 1
            ]

            if (int(workflow_param[cod_ref][cat]) is not 0) and (
                curval.find("iccoup") is -1
            ):
                if (
                    "".join(maindict[actors_ref][hsys][cat][curval][1]).find(
                        "distributions"
                    )
                    is not -1
                ):
                    merge_distributions += 1

                if (
                    "".join(maindict[actors_ref][hsys][cat][curval][1]).find(
                        "distribution_sources"
                    )
                    is not -1
                ):
                    merge_distribution_sources += 1

                if (
                    "".join(maindict[actors_ref][hsys][cat][curval][1]).find("waves")
                    is not -1
                ):
                    merge_waves += 1

    no_merge_dist = False
    no_merge_sources = False
    no_merge_waves = False

    if merge_waves > 1:
        mwave = tkinter.Label(
            labelrow, text="merge waves", bg=col.c4, relief="solid", padx=2, pady=4
        )
        mwave.grid(row=1, column=0)
        conn_list_merge.append([inv["ECRH"], mwave, mergec[2]])
        conn_list_merge.append([inv["ICRH"], mwave, mergec[2]])
        minsize_row += 20
        conn_list_merge_bottom.append([mwave, inv_bot])

    else:
        no_merge_waves = True

    if merge_distributions > 1:
        mdist = tkinter.Label(
            labelrow,
            text="merge distributions",
            bg=col.c4,
            relief="solid",
            padx=2,
            pady=4,
        )
        mdist.grid(row=1, column=2)

        if int(workflow_param[cod_ref]["nbi_fp"]) is not 0:
            conn_list_merge.append([inv["NBI"], mdist, mergec[0]])

        if int(workflow_param[cod_ref]["nuclear_fp"]) is not 0:
            conn_list_merge.append([inv["NUCLEAR"], mdist, mergec[0]])

        if int(workflow_param[cod_ref]["ic_wave_fp"]) is not 0:
            conn_list_merge.append([inv["ICRH"], mdist, mergec[0]])

        conn_list_merge_bottom.append([mdist, inv_bot])
        minsize_row += 20

    else:
        no_merge_dist = True

    if merge_distribution_sources > 1:
        msour = tkinter.Label(
            labelrow, text="merge sources", bg=col.c4, relief="solid", padx=2, pady=4
        )
        msour.grid(row=1, column=4)
        conn_list_merge.append([inv["NBI"], msour, mergec[1]])
        conn_list_merge.append([inv["NUCLEAR"], msour, mergec[1]])
        conn_list_merge_bottom.append([msour, inv_bot])

    else:
        no_merge_sources = True

    if no_merge_waves == True and no_merge_sources == True and no_merge_dist == True:
        l = tkinter.Label(
            mergefr, text="no merges necessary", bg=infolabelcolor, padx=4, pady=4
        )
        l.grid(row=3, column=0, columnspan=30, sticky="ns")
        conn_list_merge_others.append([l, "s", inv_bot, "n", False, 1, 1])
        invrow.grid(column=0)
        if len(inv) > 0:
            for i in inv:
                conn_list_merge_others.append([inv[i], "s", l, "n", False, 1, 1])
        else:
            conn_list_merge_others.append([invrow, "s", l, "n", False, 1, 1])

    mergefr.rowconfigure(2, minsize=minsize_row)
    mergefr.rowconfigure(4, minsize=50)

    if no_merge_waves == False and no_merge_sources == False and no_merge_dist == False:
        labelrow.columnconfigure(1, minsize=40)
        labelrow.columnconfigure(3, minsize=40)
    elif no_merge_waves == False and (
        no_merge_sources == False or no_merge_dist == False
    ):
        labelrow.columnconfigure(1, minsize=40)
    elif no_merge_sources == False and no_merge_dist == False:
        labelrow.columnconfigure(3, minsize=40)

    for elem in conn_list_merge:
        mergefr_draw_lines(elem[0], elem[1], elem[2], mergefr, labelrow)

    # --- draw the remaining lines

    for elem in conn_list_merge_others:
        connect_labels(
            mergefr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6]
        )

    for elem in conn_list_merge_bottom:
        merge_bottom_lines(elem[0], elem[1], mergefr, labelrow)

    # --------------
    # MAKE CORE IDS
    # --------------
    isys = 0
    ccol = 1
    ccol_max = 0
    rrow_max = 0
    conn_list_core = []

    inv = tkinter.Frame(corefr, height=2, width=2, bg=col.c5)
    inv.grid(row=0, column=0, columnspan=50)

    bl = tkinter.Frame(corefr, height=1, width=1, bg=col.c1)
    bl.grid(row=50, column=0, columnspan=50, padx=10)

    for hsys in maindict[make_core_ids_ref]:

        isys += 1
        rrow = 1
        if (
            sum([int(workflow_param[cod_ref][i]) for i in workflow_param[cod_ref]])
            is not 0
        ):

            oldlabel = l0
            for cat in maindict[make_core_ids_ref][hsys]:
                if int(workflow_param[cod_ref][cat]) is not 0:
                    curval = list(maindict[make_core_ids_ref][hsys][cat])[
                        int(workflow_param[cod_ref][cat]) - 1
                    ]
                    input_text = "\n - ".join(
                        [
                            strv
                            for strv in maindict[make_core_ids_ref][hsys][cat][curval][
                                0
                            ]
                        ]
                    )
                    output_text = "\n - ".join(
                        [
                            strv
                            for strv in maindict[make_core_ids_ref][hsys][cat][curval][
                                1
                            ]
                        ]
                    )

                    corefr.rowconfigure(rrow, minsize=25)

                    l1 = tkinter.Label(
                        corefr, text=input_text, bg=col.c1, relief="solid"
                    )
                    l1.grid(column=ccol, row=rrow, sticky="sew")
                    l1.grid_remove()
                    l0 = tkinter.Label(corefr, text=curval, bg=col.c4, relief="solid")
                    l0.grid(column=ccol, row=rrow + 1, sticky="nsew")

                    l2 = tkinter.Label(
                        corefr, text=output_text, bg=col.c1, relief="solid"
                    )
                    l2.grid(column=ccol, row=rrow + 2, sticky="new")
                    l2.grid_remove()

                    rrow += 2

                    corefr.columnconfigure(ccol, minsize=120)
                    corefr.columnconfigure(ccol + 1, minsize=30)

                    l0.bind(
                        "<Button-1>",
                        lambda event, l0=l0, l1=l1, l2=l2: click_actors(
                            l0, l1, l2, conn_list_core, corefr, base, conn_list
                        ),
                    )
                    conn_list_core.append([inv, "s", l0, "n", True, 1, 1])
                    conn_list_core.append([l0, "s", bl, "n", False, 1, 1])

                    ccol += 2

        corefr.rowconfigure(rrow, minsize=20)

    corefr.columnconfigure(ccol - 1, minsize=0)

    if len(conn_list_core) == 0:

        l = tkinter.Label(
            corefr,
            text="no make core ids actors selected",
            bg=infolabelcolor,
            padx=4,
            pady=4,
        )
        l.grid(row=2, sticky="ew")
        conn_list_core.append([inv, "s", l, "n", False, 1, 1])
        conn_list_core.append([l, "s", bl, "n", False, 1, 1])
        corefr.rowconfigure(1, minsize=20)
        corefr.rowconfigure(3, minsize=30)

    for elem in conn_list_core:
        connect_labels(
            corefr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6]
        )

    # --------------------------
    # TIME CONTROL BLOCK WINDOW
    # --------------------------

    conn_list_timec = []

    tcontfr.columnconfigure(1, minsize=100)
    tcontfr.columnconfigure(2, minsize=400)
    tcontfr.columnconfigure(3, minsize=100)

    inv = tkinter.Frame(base, height=1, width=1, bg=col.c1)
    inv1 = tkinter.Frame(base, height=1, width=1, bg=col.c1)
    inv2 = tkinter.Frame(base, height=1, width=1, bg=col.c1)
    inv3 = tkinter.Frame(base, height=1, width=1, bg=col.c1)

    inv.grid(row=13, column=2, sticky="nsw", rowspan=2)
    inv1.grid(row=13, column=3, sticky="w", rowspan=2)
    inv2.grid(row=3, column=3, sticky="w")
    inv3.grid(row=3, column=1, padx=3)  # , columnspan=50)

    conn_list.append([inv, "e", inv1, "w", False, 1, 1])
    conn_list.append([inv1, "n", inv2, "s", False, 1, 1])
    conn_list.append([inv2, "w", inv3, "e", True, 1, 1])

    inv5 = tkinter.Frame(tcontfr, height=3, width=3, bg=col.c5)
    inv5.grid(row=1, column=3, sticky="e")

    tla = tkinter.Label(
        tcontfr,
        text="increase timestep \n test if workflow time is smaller than tend",
        bg=infolabelcolor,
        padx=4,
        pady=4,
    )

    tla.grid(row=1, column=2)

    line_start_x = tla.winfo_x() + tla.winfo_width()
    line_start_y = tla.winfo_y() + tla.winfo_height() / 2
    line_end_x = inv5.winfo_x() + inv5.winfo_width()
    line_end_y = inv5.winfo_y()

    connect_labels(tcontfr, tla, "e", inv5, "w", False, 1, 1)

    # ---------
    # FINALISE
    # ---------
    il = tkinter.Label(
        finalfr,
        text="saving output to database\n- output run nr:   "
        + workflow_param[wfp_ref]["run_out"],
        bg=infolabelcolor,
        padx=4,
        pady=4,
    )
    il.pack(side=tkinter.TOP)

    # ------------------------
    # CONNECT LINE BASE LEVEL
    # ------------------------
    for elem in conn_list:
        connect_labels(
            base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6]
        )

    return base
