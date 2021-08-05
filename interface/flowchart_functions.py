import tkinter

import colour_definitions as col

############################################################################################


def find_coord(dir, widget, l, nrl):
    if dir == "n":
        l_x = widget.winfo_x() + (widget.winfo_width() / nrl) * (l - 0.5)
        l_y = widget.winfo_y()
    elif dir == "e":
        l_x = widget.winfo_x() + widget.winfo_width()
        l_y = widget.winfo_y() + (widget.winfo_height() / nrl) * (l - 0.5)
    elif dir == "s":
        l_x = widget.winfo_x() + (widget.winfo_width() / nrl) * (l - 0.5)
        l_y = widget.winfo_y() + widget.winfo_height()
    elif dir == "w":
        l_x = widget.winfo_x()
        l_y = widget.winfo_y() + (widget.winfo_height() / nrl) * (l - 0.5)
    return (l_x, l_y)


#################################################################################


def connect_labels(canvas, w1, dir1, w2, dir2, arrow_yn, l, nrl):

    canvas.update()
    ulx1 = w1.winfo_x()
    uly1 = w1.winfo_y()
    ulx2 = w2.winfo_x()
    uly2 = w2.winfo_y()

    (line_start_x, line_start_y) = find_coord(dir1, w1, l, nrl)
    (line_end_x, line_end_y) = find_coord(dir2, w2, l, nrl)

    dx = line_end_x - line_start_x
    dy = line_end_y - line_start_y

    if arrow_yn:
        arrow_yn = tkinter.LAST
    else:
        arrow_yn = tkinter.NONE

    if ((dir1 == "n" or dir1 == "s") and (dir2 == "e" or dir2 == "w")) or (
        (dir1 == "e" or dir1 == "w") and (dir2 == "n" or dir2 == "s")
    ):
        canvas.create_line(
            line_start_x,
            line_start_y,
            line_start_x,
            line_end_y,
            line_end_x,
            line_end_y,
            width=2,
            arrow=arrow_yn,
            fill=col.c5,
        )

    if (dir1 == "n" and dir2 == "s") or (dir1 == "s" and dir2 == "n"):
        canvas.create_line(
            line_start_x,
            line_start_y,
            line_start_x,
            line_start_y + dy / 2,
            line_end_x,
            line_start_y + dy / 2,
            line_end_x,
            line_end_y,
            width=2,
            arrow=arrow_yn,
            fill=col.c5,
        )

    if (dir1 == "e" and dir2 == "w") or (dir1 == "w" and dir2 == "e"):
        canvas.create_line(
            line_start_x,
            line_start_y,
            line_start_x + dx / 2,
            line_start_y,
            line_start_x + dx / 2,
            line_end_y,
            line_end_x,
            line_end_y,
            width=2,
            arrow=arrow_yn,
            fill=col.c5,
        )


############################################################################################


def merge_bottom_lines(label_n, inv_i, mergefr, labelrow):

    mergefr.update()
    labelrow.update()

    line_start_x = label_n.winfo_x() + label_n.winfo_width() / 2 + labelrow.winfo_x()
    line_start_y = label_n.winfo_y() + labelrow.winfo_y()
    line_end_x = inv_i.winfo_x()
    line_end_y = inv_i.winfo_y()

    dx = line_end_x - line_start_x
    dy = line_end_y - line_start_y

    mergefr.create_line(
        line_start_x,
        line_start_y,
        line_start_x,
        line_start_y + dy / 2,
        line_end_x,
        line_start_y + dy / 2,
        line_end_x,
        line_end_y,
        width=2,
        arrow=None,
        fill=col.c5,
    )


############################################################################################


def mergefr_draw_lines(inv_n, label_n, color_line, mergefr, labelrow):
    mergefr.update()
    labelrow.update()
    line_start_x = inv_n.winfo_x() + inv_n.winfo_width() / 2
    line_start_y = inv_n.winfo_y()
    line_end_x = label_n.winfo_x() + label_n.winfo_width() / 2 + labelrow.winfo_x()
    line_end_y = label_n.winfo_y() + labelrow.winfo_y()

    mergefr.create_line(
        line_start_x,
        line_start_y,
        line_end_x,
        line_end_y,
        width=2,
        arrow=None,
        fill=color_line,
    )


############################################################################################


def hide_display(removed_by_close_button):
    for b in removed_by_close_button:
        b.grid_remove()
        b.grid_forget()


############################################################################################


def click_actors(l0, l1, l2, conn_list_cur, fr, base, conn_list):

    if l1.grid_info():
        l1.grid_remove()
        l2.grid_remove()
    else:
        l1.grid()
        l2.grid()
    fr.delete("all")

    for elem in conn_list_cur:
        connect_labels(
            fr, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6]
        )

    base.delete("all")
    for elem in conn_list:
        connect_labels(
            base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6]
        )


############################################################################################


def click_labels(f_or_l, cur_label, cur_frame, base, conn_list):

    if "l" in f_or_l:
        cur_frame.grid()
        cur_label.grid_remove()
        if "i" not in f_or_l:
            base.rowconfigure(cur_frame.grid_info()["row"] + 1, minsize=0)
        if "m" in f_or_l:
            base.rowconfigure(6, minsize=0)
        cur_frame.update()
    else:
        cur_label.grid()
        if "m" in f_or_l:
            base.rowconfigure(6, minsize=20)
        base.rowconfigure(cur_frame.grid_info()["row"] + 1, minsize=20)
        cur_frame.grid_remove()

    base.delete("all")
    for elem in conn_list:
        base.update()
        connect_labels(
            base, elem[0], elem[1], elem[2], elem[3], elem[4], elem[5], elem[6]
        )
