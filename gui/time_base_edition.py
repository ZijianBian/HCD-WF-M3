# ------------------------------------------------------------------------------------------------
# Functions to enable choosing the frequency with which each model is called inside the workflow:
# - Each model can be called with a frequency independent of the others, with a maximum frequency
#   corresponding to the time step duration of the input scenario
# - Each model can be called with a frequency varying in time (e.g. more calls in the ramp-up
#   and ramp-down)
# ------------------------------------------------------------------------------------------------

import tkinter as tk
import numpy as np
import matplotlib
from .colour_definitions import bluish as colour

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from .gui_methods import CreateToolTip

#######################################################################################

# -----------------------------------------
# Definition of a time interval as a class
# -----------------------------------------

def find_nearest(a, a0):
    "Element in nd array `a` closest to the scalar value `a0`"
    idx = np.abs(a - a0).argmin()
    return a.flat[idx], idx

class Interval:
    def __init__(self):
        self.object = {}

        for key in ["name", "tmin", "tmax", "time_array", "status", "select"]:
            self.object[key] = None

    def update(self, key_to_update, value):
        self.object[key_to_update] = value


#######################################################################################

# -----------------------------------------------------------------------------------
# Function to add an home-made time interval to the GUI to edit the global time base
# -----------------------------------------------------------------------------------
def add_interval(self, new_interval):
    def add_to_gui(self):

        # When interval is selected: de-select all others in all_intervals and in the GUI
        def dict_gui_update(k):
            self.all_intervals[k]["select"] = int(var_select[k].get())
            if var_select[k].get() == 1:
                for kk in self.all_intervals.keys():
                    if kk != k:
                        var_select[kk].set(0)
                        self.all_intervals[kk]["select"] = 0

        # Display all intervals defined so far
        irow = 0
        var_select = {}
        select_check = {}
        del_button = {}
        for key in self.all_intervals.keys():
            irow += 1
            li_interval = tk.Label(
                master=self.frame_array[3],
                text=key,
                borderwidth=2,
                relief="sunken",
                padx=5,
                pady=3,
                bg=colour.c2,
            )
            li_interval.grid(
                row=irow, column=0, columnspan=1, pady=2, padx=5, sticky="w"
            )
            li_tminmax = tk.Label(
                master=self.frame_array[3],
                text=" ["
                + format("%.2f" % self.all_intervals[key]["tmin"])
                + "-"
                + format("%.2f" % self.all_intervals[key]["tmax"])
                + "] s",
                borderwidth=2,
                relief="sunken",
                padx=5,
                pady=3,
                bg=colour.c2,
            )
            li_tminmax.grid(
                row=irow, column=1, columnspan=1, pady=2, padx=5, sticky="w"
            )

            var_select[key] = tk.IntVar()
            if (
                len(self.all_intervals.keys()) == 1
            ):  # Select the interval if there is just one
                var_select[key].set(1)
                self.all_intervals[key]["select"] = 1
            select_check[key] = tk.Checkbutton(
                master=self.frame_array[3],
                text="Select",
                variable=var_select[key],
                onvalue=1,
                offvalue=0,
                command=lambda key=key: dict_gui_update(key),
            )
            select_check[key].config(bg=colour.c3, activebackground=colour.c4)
            select_check[key].grid(
                row=irow, column=2, columnspan=1, pady=2, padx=5, sticky="w"
            )

            # To synchronise the display with the actual interval selection
            for kk in self.all_intervals.keys():
                if kk in var_select:
                    var_select[kk].set(self.all_intervals[kk]["select"])

            if key != "wf_interval":
                del_button[key] = tk.Button(
                    master=self.frame_array[3], text="Delete", bg=colour.c2
                )
                del_button[key].config(activebackground=colour.c4)
                del_button[key].grid(
                    row=irow, column=3, columnspan=1, pady=2, padx=5, sticky="w"
                )
                del_button[key].configure(
                    command=lambda self=self, key=key: remove_interval(self, key)
                )

    if new_interval is None:  # for remove_interval()
        for widget in self.frame_array[3].winfo_children():
            widget.destroy()
        add_to_gui(self)
        return self

    if new_interval.object["name"] == "":
        print("Empty name")
        add_to_gui(self)
        return self

    for key in ["tmin", "tmax"]:
        try:
            new_interval.object[key] = float(new_interval.object[key])
        except:
            print("Bad value for " + key)
            add_to_gui(self)
            return self

    if new_interval.object["tmax"] <= new_interval.object["tmin"]:
        print("Tmax should be higher than Tmin")
        add_to_gui(self)
        return self

    if new_interval.object["name"] != "wf_interval":
        if new_interval.object["tmin"] < self.all_intervals["wf_interval"]["tmin"]:
            print(
                "Tmin is lower than the workflow time interval which is "
                + format("%.2f" % self.all_intervals["wf_interval"]["tmin"]),
                "s",
            )
            add_to_gui(self)
            return self

        if new_interval.object["tmax"] > self.all_intervals["wf_interval"]["tmax"]:
            print(
                "Tmax is higher than the workflow time interval which is "
                + format("%.2f" % self.all_intervals["wf_interval"]["tmax"]),
                "s",
            )
            add_to_gui(self)
            return self

    # Note: these are pointers, i.e. when one interval is changed, it automatically changes wf_interval
    # because all intervals have been created from it
    self.all_intervals[new_interval.object["name"]] = {}
    self.all_intervals[new_interval.object["name"]]["tmin"] = new_interval.object[
        "tmin"
    ]
    self.all_intervals[new_interval.object["name"]]["tmax"] = new_interval.object[
        "tmax"
    ]
    self.all_intervals[new_interval.object["name"]]["time_array"] = new_interval.object[
        "time_array"
    ]
    self.all_intervals[new_interval.object["name"]]["status"] = new_interval.object[
        "status"
    ]
    self.all_intervals[new_interval.object["name"]]["select"] = new_interval.object[
        "select"
    ]
    add_to_gui(self)

    return self


#######################################################################################

# ------------------------------------------------
# Function to remove a time interval from the GUI
# ------------------------------------------------


def remove_interval(self, interval_to_remove):
    del self.all_intervals[interval_to_remove]
    add_interval(self, None)  # Re-display the shortened list of intervals
    return self


#######################################################################################

# ---------------------------------
# Class to define the master frame
# ---------------------------------


class mclass:
    # Init
    def __init__(self, frame, all_intervals):
        self.frame = frame
        self.all_intervals = all_intervals

    # Plot the status configuration for all intervals
    def plot(self):

        for widget in self.frame.winfo_children():
            widget.destroy()

        fig = Figure(linewidth=0, edgecolor="sienna", facecolor=colour.c3)
        a = fig.add_subplot(111)
        a.grid()

        col = [
            "navy",
            "firebrick",
            "green",
            "darkorange",
            "darkviolet",
            "lightseagreen",
            "orchid",
        ]
        icol = -1
        for key in self.all_intervals.keys():
            icol = min(
                icol + 1, len(col) - 1
            )  # prevent index to get beyond array dimension
            if self.all_intervals[key]["time_array"] is not None:
                a.plot(
                    self.all_intervals[key]["time_array"],
                    self.all_intervals[key]["status"],
                    ".",
                    color=col[icol],
                )
        a.set_yticks([0.0, 1.0])
        a.set_yticklabels(["Off", "On"])

        fontsize = 10

        a.set_xlabel("Time [s] ", fontsize=fontsize)
        a.set_xlim(
            self.all_intervals["wf_interval"]["time_array"][0],
            self.all_intervals["wf_interval"]["time_array"][-1],
        )

        time_tick_array = a.get_xticks()
        nticks = len(time_tick_array)
        index_tick_array = [0] * nticks
        for tick in range(nticks):
            [tc, it] = find_nearest(
                self.all_intervals["wf_interval"]["time_array"], time_tick_array[tick]
            )
            index_tick_array[tick] = it
        a2 = a.twiny()
        a2.set_xticks(index_tick_array)
        a2.set_xlabel("Indices")

        canvas = FigureCanvasTkAgg(fig, master=self.frame)
        canvas.get_tk_widget().pack()
        canvas.draw()


#######################################################################################

# ------------------------------------------------------------------------------------
# Function to apply the requested changes based on changing code status for a given
# time interval, time slice, time index or every xxx time steps or xxx time intervals
# ------------------------------------------------------------------------------------


def apply_pattern(self):
    select = 0
    print("APPLY!!!!")
    for key in self.all_intervals.keys():
        if self.all_intervals[key]["select"] == 1:
            print("----------------------------- ")
            print("Selected interval = ", key)
            pattern = self.si_option_list.get()
            status = self.si_onoff_list.get()
            print("- Pattern = ", pattern)
            print("- Status  = ", status)
            key_select = key
            select = 1
    if select == 0:
        print("No interval selected.")
        return None

    [tc_min, it_min] = find_nearest(
        self.all_intervals["wf_interval"]["time_array"],
        self.all_intervals[key_select]["tmin"],
    )
    [tc_max, it_max] = find_nearest(
        self.all_intervals["wf_interval"]["time_array"],
        self.all_intervals[key_select]["tmax"],
    )
    self.all_intervals[key_select]["time_array"] = self.all_intervals["wf_interval"][
        "time_array"
    ][it_min:it_max]
    self.all_intervals[key_select]["status"] = self.all_intervals["wf_interval"][
        "status"
    ][it_min:it_max]
    print("Number of indices =", len(self.all_intervals[key_select]["time_array"]))
    print("Actual tmin       =", format("%.2f" % tc_min), "s")
    print("Actual tmax       =", format("%.2f" % tc_max), "s")
    if len(self.all_intervals[key_select]["time_array"]) > 1:
        dt = (
            self.all_intervals[key_select]["time_array"][1]
            - self.all_intervals[key_select]["time_array"][0]
        )
        print("Time resolution   =", format("%.2f" % dt), "s")

    if status == "On":
        status_index = 1
    else:
        status_index = 0

    # At index
    if pattern == "At index":
        value = self.edit_field.get()
        if value == "":
            print("The index must be specified")
            return
        else:
            try:
                index = int(value)
            except:
                print("The index must be an integer")
                return
            if index > len(self.all_intervals[key_select]["time_array"]) - 1:
                print("The chosen index is too large")
                return
            else:
                self.all_intervals[key_select]["status"][index] = status_index
                print("--> Time interval udpated")

    # At time
    if pattern == "At time":
        value = self.edit_field.get()
        if value == "":
            print("The time slice must be specified")
            return
        else:
            try:
                time_slice = float(value)
            except:
                print("The time slice must be a number")
                return
            if time_slice > tc_max or time_slice < tc_min:
                print("The chosen time slice is beyond the selected interval")
                return
            else:
                [tc, it] = find_nearest(
                    self.all_intervals[key_select]["time_array"], time_slice
                )
                print("Actual time slice =", format("%.2f" % tc), "s")
                self.all_intervals[key_select]["status"][it] = status_index
                print("--> Time interval udpated")

    # Index step
    if pattern == "Index step":
        value = self.edit_field.get()
        if value == "":
            print("The index step must be specified")
            return
        else:
            try:
                index_step = int(value)
            except:
                print("The index step must be an integer")
                return
            if index_step > len(self.all_intervals[key_select]["time_array"]) - 1:
                print("The chosen index step is too large")
                return
            else:
                self.all_intervals[key_select]["status"][0::index_step] = status_index
                print("--> Time interval udpated")

    # Time step
    if pattern == "Time step":
        value = self.edit_field.get()
        if value == "":
            print("The time step must be specified")
            return
        else:
            try:
                time_step = float(value)
            except:
                print("The time step must be a number")
                return
            if time_step > tc_max - tc_min:
                print("The chosen time step is larger than the interval")
                return
            else:
                [tc1, it1] = find_nearest(
                    self.all_intervals[key_select]["time_array"], tc_min
                )
                [tc2, it2] = find_nearest(
                    self.all_intervals[key_select]["time_array"], tc_min + time_step
                )
                index_step = it2 - it1
                if index_step == 0:
                    print("The time step is too small")
                    return
                else:
                    print("Actual time step =", format("%.2f" % (tc2 - tc1)), "s")
                    self.all_intervals[key_select]["status"][
                        0::index_step
                    ] = status_index
                    print("--> Time interval udpated")

    # Full interval updated according to the on-off selection of the current interval
    if pattern == "Full interval":
        self.all_intervals[key_select]["status"][:] = status_index
        print("--> Time interval udpated")

    self.start.plot()

    # Save the new configuration
    if "time_base" not in self.wf_param.keys():
        self.wf_param["time_base"] = [{}, "time_base"]

    all_intervals = {}
    for interval in self.all_intervals.keys():
        all_intervals[interval] = [{}, interval]
        for key, value in self.all_intervals[interval].items():
            all_intervals[interval][0][key] = [value, key]

    self.wf_param["time_base"][0][self.process] = [all_intervals, self.process]

    return self


#######################################################################################

# ----------------------------------------------------------------------------------
# Function to reset all time intervals, i.e. to call the model for every time slice
# ----------------------------------------------------------------------------------


def soft_reset_intervals(self):
    for key in self.all_intervals.keys():
        self.all_intervals[key]["status"][:] = 1
    self.start.plot()


#######################################################################################


def create_wf_interval(self):
    parameters = self.wf_param[list(self.wf_param.keys())[0]][0]

    nstep = int(
        (float(parameters["tend"][0]) - float(parameters["tbegin"][0]))
        / float(parameters["dt_required"][0])
    )
    wf_interval = Interval()
    wf_interval.update("name", "wf_interval")
    wf_interval.update("tmin", float(parameters["tbegin"][0]))
    wf_interval.update("tmax", float(parameters["tend"][0]))
    wf_interval.update(
        "time_array",
        np.linspace(
            float(parameters["tbegin"][0]), float(parameters["tend"][0]), nstep
        ),
    )
    wf_interval.update("status", np.linspace(1, 1, nstep))
    return wf_interval


#######################################################################################

# ----------------------------------------------------------------------------------
# Function to remove all intervals and reload the workflow one (in case it changed)
# ----------------------------------------------------------------------------------


def hard_reset_intervals(self):

    list_of_intervals = []
    for interval in self.all_intervals:
        list_of_intervals.append(interval)

    for interval in list_of_intervals:
        remove_interval(self, interval)

    wf_interval = create_wf_interval(self)
    self = add_interval(self, wf_interval)
    self.start.plot()


#######################################################################################

# -------------------------------------------------------------------
# Class to create the main GUI for the time edition of a given model
# -------------------------------------------------------------------


class time_base_edition:

    # Init
    def __init__(self, master, process={}, wf_param={}):
        self.master = tk.Toplevel(master)
        self.master.option_add("*font", "Helvetica 10")
        self.master.title("Time Edition")
        self.master.configure(bg=colour.c4)
        self.process = process
        self.wf_param = wf_param

        mincolumnsize = 75
        minrowsize = 50
        nrow = 4
        ncol = 2

        # Define the grid of frames nrow*ncol
        frame_array = [0] * nrow * ncol
        k = -1
        for irow in range(nrow):
            self.master.rowconfigure(irow, weight=1, minsize=minrowsize)
            for jcol in range(ncol):
                k = k + 1
                self.master.columnconfigure(jcol, weight=1, minsize=mincolumnsize)
                if k == 0:
                    frame_array[k] = tk.Frame(
                        master=self.master, relief=tk.GROOVE, borderwidth=2
                    )
                    frame_array[k].grid(
                        row=irow, column=jcol, columnspan=2, padx=2, pady=2
                    )
                else:
                    if k == 3:
                        frame_array[k] = tk.Frame(
                            master=self.master, relief=tk.RAISED, borderwidth=2
                        )
                        frame_array[k].grid(
                            row=irow,
                            column=jcol,
                            rowspan=3,
                            padx=2,
                            pady=2,
                            sticky="nw",
                        )
                    else:
                        frame_array[k] = tk.Frame(
                            master=self.master, relief=tk.RAISED, borderwidth=2
                        )
                        frame_array[k].grid(
                            row=irow, column=jcol, padx=2, pady=2, sticky="nw"
                        )
                frame_array[k].config(bg=colour.c3)

        self.frame_array = frame_array

        # parameters = self.wf_param[list(self.wf_param.keys())[0]][0]

        # nstep = int((float(parameters["tend"][0]) - float(parameters["tbegin"][0])) \
        #            / float(parameters["dt_required"][0]))

        self.all_intervals = {}

        # First initialisation of the workflow interval
        wf_interval = create_wf_interval(self)
        self = add_interval(self, wf_interval)

        # Restore all intervals from a previous configuration if any
        if "time_base" in self.wf_param:
            if process in self.wf_param["time_base"][0]:
                for interval_name in self.wf_param["time_base"][0][process][0]:
                    interval = Interval()
                    interval.update("name", interval_name)
                    interval.update(
                        "tmin",
                        self.wf_param["time_base"][0][process][0][interval_name][0][
                            "tmin"
                        ][0],
                    )
                    interval.update(
                        "tmax",
                        self.wf_param["time_base"][0][process][0][interval_name][0][
                            "tmax"
                        ][0],
                    )
                    interval.update(
                        "time_array",
                        np.array(
                            wf_param["time_base"][0][process][0][interval_name][0][
                                "time_array"
                            ][0]
                        ),
                    )
                    interval.update(
                        "status",
                        np.array(
                            wf_param["time_base"][0][process][0][interval_name][0][
                                "status"
                            ][0]
                        ),
                    )
                    interval.update("select", 0)
                    self = add_interval(self, interval)

        self.create_gui()

    # Create the main gui
    def create_gui(self):

        new_interval = Interval()

        # --------
        # FRAME 0
        # --------
        self.start = mclass(self.frame_array[0], self.all_intervals)
        self.start.plot()

        # --------
        # FRAME 2
        # --------
        ni_label_general = tk.Label(master=self.frame_array[2], text="New Interval:")
        ni_label_general.config(bg=colour.c3)
        ni_label_general.grid(
            row=0, column=0, columnspan=1, pady=2, padx=5, sticky="we"
        )

        # Name
        ni_label_name = tk.Label(master=self.frame_array[2], text="Name:")
        ni_label_name.config(bg=colour.c3)
        ni_label_name.grid(row=1, column=0, columnspan=1, pady=5, padx=5, sticky="we")
        ni_name = tk.StringVar()
        ni_name.trace(
            "w",
            lambda name, index, mode, ni_name=ni_name: new_interval.update(
                "name", ni_name.get()
            ),
        )
        ni_entry_name = tk.Entry(master=self.frame_array[2], textvariable=ni_name)
        ni_entry_name.config(bg=colour.c2)
        ni_entry_name.grid(row=1, column=1, columnspan=1, pady=5, padx=5, sticky="we")

        # Tmin
        ni_label_tmin = tk.Label(master=self.frame_array[2], text="Tmin [s]:")
        ni_label_tmin.config(bg=colour.c3)
        ni_label_tmin.grid(row=2, column=0, columnspan=1, pady=2, padx=5, sticky="we")
        ni_tmin = tk.StringVar()
        ni_tmin.trace(
            "w",
            lambda name, index, mode, ni_tmin=ni_tmin: new_interval.update(
                "tmin", ni_tmin.get()
            ),
        )
        ni_entry_tmin = tk.Entry(master=self.frame_array[2], textvariable=ni_tmin)
        ni_entry_tmin.config(bg=colour.c2)
        ni_entry_tmin.grid(row=2, column=1, columnspan=1, pady=2, padx=5, sticky="we")

        # Tmax
        ni_label_tmax = tk.Label(master=self.frame_array[2], text="Tmax [s]:")
        ni_label_tmax.config(bg=colour.c3)
        ni_label_tmax.grid(row=3, column=0, columnspan=1, pady=2, padx=5, sticky="we")
        ni_tmax = tk.StringVar()
        ni_tmax.trace(
            "w",
            lambda name, index, mode, ni_tmax=ni_tmax: new_interval.update(
                "tmax", ni_tmax.get()
            ),
        )
        ni_entry_tmax = tk.Entry(master=self.frame_array[2], textvariable=ni_tmax)
        ni_entry_tmax.config(bg=colour.c2)
        ni_entry_tmax.grid(row=3, column=1, columnspan=1, pady=2, padx=5, sticky="we")

        ni_add_button = tk.Button(
            master=self.frame_array[2], text="Add", height=3, bg=colour.c2
        )
        ni_add_button.config(activebackground=colour.c4)
        ni_add_button.grid(row=1, column=2, rowspan=3, pady=2, padx=5, sticky="we")
        ni_add_button.configure(command=lambda: add_interval(self, new_interval))

        # --------
        # FRAME 3
        # --------
        li_label_general = tk.Label(
            master=self.frame_array[3], text="List of intervals:"
        )
        li_label_general.config(bg=colour.c3)
        li_label_general.grid(row=0, column=0, columnspan=2, pady=2, padx=5, sticky="w")
        # The rest is displayed by the add_interval function

        # --------
        # FRAME 4
        # --------
        si_label_general = tk.Label(
            master=self.frame_array[4], text="Edit selected interval:"
        )
        si_label_general.config(bg=colour.c3)
        si_label_general.grid(row=0, column=0, columnspan=3, pady=2, padx=5, sticky="w")

        si_label_interval = tk.Label(master=self.frame_array[4], text="Pattern:")
        si_label_interval.config(bg=colour.c3)
        si_label_interval.grid(
            row=1, column=0, columnspan=1, pady=2, padx=5, sticky="w"
        )
        OptionList = ["At index", "At time", "Index step", "Time step", "Full interval"]
        OptionList = ["Full interval", "Time step", "At time", "Index step", "At index"]
        self.si_option_list = tk.StringVar()
        self.si_option_list.set(OptionList[0])
        opt_option = tk.OptionMenu(
            self.frame_array[4], self.si_option_list, *OptionList
        )
        opt_option.config(bg=colour.c2, activebackground=colour.c4)
        opt_option["menu"].config(bg=colour.c2)
        opt_option.grid(row=2, column=0, columnspan=1, pady=2, padx=5, sticky="w")

        self.edit_field = tk.StringVar()
        entry_field = tk.Entry(
            master=self.frame_array[4], textvariable=self.edit_field, width=6
        )
        entry_field.config(bg=colour.c2)
        entry_field.grid(row=2, column=1, columnspan=1, pady=2, padx=5, sticky="w")

        si_label_setto = tk.Label(master=self.frame_array[4], text="Set to:")
        si_label_setto.config(bg=colour.c3)
        si_label_setto.grid(row=1, column=2, columnspan=1, pady=2, padx=5, sticky="w")
        OnOffList = ["On", "Off"]
        self.si_onoff_list = tk.StringVar()
        self.si_onoff_list.set(OnOffList[0])
        opt_onoff = tk.OptionMenu(self.frame_array[4], self.si_onoff_list, *OnOffList)
        opt_onoff.config(bg=colour.c2, activebackground=colour.c4)
        opt_onoff["menu"].config(bg=colour.c2)
        opt_onoff.grid(row=2, column=2, columnspan=1, pady=2, padx=5, sticky="w")
        si_apply_button = tk.Button(
            master=self.frame_array[4], text="Apply", height=2, bg=colour.c2
        )
        si_apply_button.config(activebackground=colour.c4)
        si_apply_button.grid(row=1, column=3, rowspan=2, pady=2, padx=5, sticky="we")
        si_apply_button.configure(command=lambda: apply_pattern(self))

        # --------
        # FRAME 5
        # --------
        gl_sreset = tk.Button(
            master=self.frame_array[6], text="Soft Reset", height=1, bg=colour.c2
        )
        gl_sreset.config(activebackground=colour.c4)
        gl_sreset.grid(row=0, column=0, rowspan=1, pady=2, padx=5, sticky="se")
        gl_sreset.configure(command=lambda: soft_reset_intervals(self))
        CreateToolTip(
            gl_sreset,
            "Reset all time intervals such that the model is called for all time slices",
        )

        gl_hreset = tk.Button(
            master=self.frame_array[6], text="Hard Reset", height=1, bg=colour.c2
        )
        gl_hreset.config(activebackground=colour.c4)
        gl_hreset.grid(row=0, column=1, rowspan=1, pady=2, padx=5, sticky="se")
        gl_hreset.configure(command=lambda: hard_reset_intervals(self))
        CreateToolTip(
            gl_hreset,
            "Remove all intervals and reload the workflow one (in case it changed",
        )

        gl_close = tk.Button(
            master=self.frame_array[6], text="Close", height=1, bg=colour.c2
        )
        gl_close.config(activebackground=colour.c4)
        gl_close.grid(row=0, column=2, rowspan=1, pady=2, padx=5, sticky="se")
        gl_close.configure(command=lambda: self.master.destroy())

        # Make it nicer
        self.frame_array[2].config(height=120, width=350)
        self.frame_array[3].config(height=258, width=400)
        self.frame_array[4].config(height=90, width=350)
        self.frame_array[6].config(height=40, width=350)
        self.frame_array[2].grid_propagate(0)
        self.frame_array[3].grid_propagate(0)
        self.frame_array[4].grid_propagate(0)
        self.frame_array[6].grid_propagate(0)


# --------------------------------------------------------------

# --------------------------
# Main for standalone tests
# --------------------------

if __name__ == "__main__":

    param = {}
    param["WORKFLOW PARAMETERS (STANDALONE)"] = {}
    param["WORKFLOW PARAMETERS (STANDALONE)"][0] = {}
    param["WORKFLOW PARAMETERS (STANDALONE)"][0]["tbegin"] = {}
    param["WORKFLOW PARAMETERS (STANDALONE)"][0]["tend"] = {}
    param["WORKFLOW PARAMETERS (STANDALONE)"][0]["dt_required"] = {}
    param["WORKFLOW PARAMETERS (STANDALONE)"][0]["tbegin"][0] = 1.21
    param["WORKFLOW PARAMETERS (STANDALONE)"][0]["tend"][0] = 149.0
    param["WORKFLOW PARAMETERS (STANDALONE)"][0]["dt_required"][0] = 1.0
    cat = "myprocess"

    master = tk.Tk()
    master.title("Main Window")
    new_param = time_base_edition(master, cat, param)
    master.mainloop()
