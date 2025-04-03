import os
import tkinter as tk
from shutil import copy2
from tkinter import ttk

from .colour_definitions import bluish as col

isWaveformCookerPresent = True
try:
    from waveform_cooker import add_dynamic
except Exception as _:  # noqa F841
    isWaveformCookerPresent = False

fontsize = 12

############################################################################

# -----------------------------------------------------
# Class to trigger and event when the text is modified
# -----------------------------------------------------


class CustomText(tk.Text):
    def __init__(self, *args, **kwargs):
        """A text widget that report on internal widget commands"""
        tk.Text.__init__(self, *args, **kwargs)

        # create a proxy for the underlying widget
        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, command, *args):
        cmd = (self._orig, command) + args
        result = self.tk.call(cmd)

        if command in ("insert", "delete", "replace"):
            self.event_generate("<<TextModified>>")

        return result


############################################################################

# -------------------------------------------------
# Class to define a text+scrollbar combined object
# -------------------------------------------------


class TextScrollCombo(ttk.Frame):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # Ensure a consistent GUI size
        self.grid_propagate(False)

        # Implement stretchability
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create a Text widget
        self.txt = CustomText(self, width=40, height=4, bg="black", fg="white", insertbackground="white")
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Create a Scrollbar and associate it with text
        scrollb = ttk.Scrollbar(self, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky="nsew")
        self.txt["yscrollcommand"] = scrollb.set


############################################################################

# ---------------------------------------------------
# Handler Functions for the menu of the file edition
# ---------------------------------------------------


def fileDropDownHandeler(window, txt, myfile, action):

    # Saving a file
    if action == "save":
        with open(myfile, "w") as f:
            f.write(txt.get("1.0", "end"))
            window.title(myfile)
            print("File " + myfile + " saved.")

    # Exit
    elif action == "exit":

        if "NOT SAVED" in window.title():

            message = "Your modifications have not been saved. " + "Do you really wante to leave?"
            MsgBox = tk.messagebox.askquestion("Exit Application", message)
            if MsgBox == "yes":
                window.destroy()
                print("  Exit waveform edition.")
        else:
            window.destroy()
            print("  Exit waveform edition.")


############################################################################

# -----------------------------
# Function to edit a yaml file
# -----------------------------


def edit_yaml(myfile):

    # Main Window setup
    edit_yaml_window = tk.Toplevel()
    # edit_yaml_window.option_add("*font", "Helvetica 10") # Font
    edit_yaml_window.title(myfile)  # Title
    edit_yaml_window.configure(bg=col.c4)  # Background colour
    edit_yaml_window.geometry("1000x600")  # Dimension
    edit_yaml_window.columnconfigure(0, weight=1)  # Resize frames along with main window
    edit_yaml_window.rowconfigure(0, weight=1)  # idem

    # Text + scrollbar
    combo = TextScrollCombo(edit_yaml_window)
    combo.pack(fill="both", expand=True)
    combo.config(width=600, height=600)
    combo.txt.config(font=("consolas", 10, "bold"), undo=True, wrap="word")
    combo.txt.config(borderwidth=3, relief="sunken")
    with open(myfile, "r") as f:
        combo.txt.delete(1.0, tk.END)
        combo.txt.insert(tk.INSERT, f.read())

    # Bind events in the widget to a function
    def text_modified_event(event):
        edit_yaml_window.title(myfile + " (NOT SAVED)")

    combo.txt.bind("<<TextModified>>", text_modified_event)

    def saved_event(event):
        fileDropDownHandeler(edit_yaml_window, combo.txt, myfile, "save")

    combo.txt.bind("<Control-s>", saved_event)

    def exit_event(event=[]):
        fileDropDownHandeler(edit_yaml_window, combo.txt, myfile, "exit")

    combo.txt.bind("<Control-q>", exit_event)

    edit_yaml_window.protocol("WM_DELETE_WINDOW", exit_event)

    # Set up menu and add Commands and and their callbacks
    menu = tk.Menu(edit_yaml_window)
    fileDropdown = tk.Menu(menu, tearoff=False)
    fileDropdown.add_command(
        label="Save (Ctrl-S)",
        command=lambda: fileDropDownHandeler(edit_yaml_window, combo.txt, myfile, "save"),
    )
    fileDropdown.add_command(
        label="Exit (Ctrl-Q)",
        command=lambda: fileDropDownHandeler(edit_yaml_window, combo.txt, myfile, "exit"),
    )
    menu.add_cascade(label="File", menu=fileDropdown)
    edit_yaml_window.config(menu=menu)

    # Let's go
    edit_yaml_window.mainloop()


############################################################################

# ----------------------------------------------------------------------------
# Function to copy official waveforms presets to current configuration folder
# ----------------------------------------------------------------------------


def preset_copy(waveform_folder, config_folder, process, preset_file, custom_file):

    # Copy the default workflow parameter file into the current one
    def CopyWaveform(waveform_folder, preset_file, config_folder, custom_file):

        if os.path.isfile(waveform_folder + "/" + preset_file):

            copy2(
                waveform_folder + "/" + preset_file,
                config_folder + "/" + custom_file,
                follow_symlinks=True,
            )
            print(
                "  --> "
                + waveform_folder
                + "/"
                + preset_file
                + "\n"
                + "      copied into "
                + config_folder
                + "/"
                + custom_file
                + "."
            )
            edit_yaml(config_folder + "/" + custom_file)

        else:
            print("The file " + waveform_folder + "/" + preset_file + " does not exist.")
            print("--> Preset copy aborted.")

    # Check that the user is happy with overwriting the file
    def AreYouSure_preset_copy(process, waveform_folder, preset_file, config_folder, custom_file):
        message = (
            "A custom file for "
            + process.upper()
            + " already exists.\n"
            + "This will overwrite your existing\nwaveform configuration.\n"
            + "Do you want to continue?"
        )
        MsgBox = tk.messagebox.askquestion("Exit Application", message)
        if MsgBox == "yes":
            CopyWaveform(waveform_folder, preset_file, config_folder, custom_file)
        else:
            # tk.messagebox.showinfo('Return','Preset overwrite cancelled')
            print("Preset overwrite cancelled.")

    # If the file exists, check that the user is happy with overwriting,
    # then copy preset file to custom file
    if os.path.exists(config_folder + "/" + custom_file):
        AreYouSure_preset_copy(process, waveform_folder, preset_file, config_folder, custom_file)
    else:
        CopyWaveform(waveform_folder, preset_file, config_folder, custom_file)


############################################################################

# -----------------------------------------------------
# Function to launch the waveform configuration editor
# -----------------------------------------------------


def waveform_custom_configure(config_folder, process, custom_file):
    if not os.path.exists(config_folder + "/" + custom_file):
        tk.messagebox.showinfo(
            title="Waveform configuration",
            message="No "
            + process.upper()
            + " custom configuration found:\n"
            + "First create it from one of the presets",
        )
    else:
        edit_yaml(config_folder + "/" + custom_file)


############################################################################

# -----------------------------------------------------
# Function to restore waveform from scenario (if any)
# -----------------------------------------------------


def use_waveform_from_scenario(config_folder, custom_file):

    # Check that the user is happy with overwriting the file
    def AreYouSure_use_waveform_from_scenario(config_folder, custom_file):
        message = "This will remove your existing\nwaveform configuration.\n" + "Do you want to continue?"
        MsgBox = tk.messagebox.askquestion("Exit Application", message)
        if MsgBox == "yes":
            os.remove(config_folder + "/" + custom_file)
            print("  --> " + config_folder + "/" + custom_file + " removed.")
        else:
            # tk.messagebox.showinfo('Return','Reset cancelled')
            print("Reset cancelled.")

    if os.path.exists(config_folder + "/" + custom_file):
        AreYouSure_use_waveform_from_scenario(config_folder, custom_file)
    else:
        print("  --> Not custom configuration file found: nothing to remove.")


############################################################################

# ------------------------
# Class to edit waveforms
# ------------------------


class edit_waveforms:
    def __init__(self, waveform_presets={}, waveform_folder="", config_folder=""):

        self.master = tk.Toplevel()
        self.master.option_add("*font", "Helvetica 10")
        self.master.title("Edit Waveforms")
        self.master.configure(bg=col.c4)
        self.master.geometry("450x500")
        self.waveform_presets = waveform_presets
        self.waveform_folder = waveform_folder
        self.config_folder = config_folder

        # 3 columns = process, presets, custom
        ncol = 5

        # Number of rows = total number of presets + 1 for names + 1 for exit line + 1 for general info line
        maxname = 0
        npresets = 0
        for process in waveform_presets.keys():
            npresets = npresets + len(waveform_presets[process]) - 1
            for preset_key in waveform_presets[process]:
                if len(waveform_presets[process][preset_key][1]) > maxname:
                    maxname = len(waveform_presets[process][preset_key][1])
        nrow = npresets + 3

        # Minimum column width and row height
        mincolumnsize = maxname
        minrowsize = 5

        # Define the grid of frames nrow*ncol
        frame_array = [0] * nrow * ncol
        k = -1
        for irow in range(nrow):
            self.master.rowconfigure(irow, weight=1, minsize=minrowsize)
            for jcol in range(ncol):
                k = k + 1
                self.master.columnconfigure(jcol, weight=1, minsize=mincolumnsize)
                if k < nrow * ncol - 1 and irow > 1 and jcol > 0:
                    frame_array[k] = tk.Frame(master=self.master, relief=tk.RAISED, borderwidth=2, bg=col.c3)
                else:
                    frame_array[k] = tk.Frame(master=self.master, bg=col.c4)
                if k > 0:
                    frame_array[k].grid(row=irow, column=jcol, padx=2, pady=2, sticky="nw")
                else:
                    frame_array[k].grid(
                        row=irow,
                        column=jcol,
                        columnspan=5,
                        padx=2,
                        pady=2,
                        sticky="news",
                    )

        self.frame_array = frame_array
        self.create_gui(ncol, nrow, config_folder, waveform_presets, waveform_folder)

    def create_gui(self, ncol, nrow, config_folder, waveform_presets, waveform_folder):

        # General information
        general_info = tk.Label(
            master=self.frame_array[0],
            text="Do not configure if you plan to read waveforms from     "
            "\ninput scenario (can be restored with scenario reset)",
            bg=col.c3,
            font=("Arial", fontsize, "bold"),
        )
        general_info.grid(row=0, column=0, columnspan=5, sticky="news")

        # Title line, 1st column
        process_name = tk.Label(
            master=self.frame_array[5],
            text="Process",
            bg=col.c4,
            font=("Arial", fontsize, "bold"),
        )
        process_name.grid(row=1, column=0, sticky="we")

        # Title line, 2nd column
        preset_name = tk.Label(
            master=self.frame_array[6],
            text="Presets",
            bg=col.c4,
            font=("Arial", fontsize, "bold"),
        )
        preset_name.grid(row=1, column=1, sticky="we")

        # Title line, 3rd column
        preset_name = tk.Label(
            master=self.frame_array[7],
            text="Custom",
            bg=col.c4,
            font=("Arial", fontsize, "bold"),
        )
        preset_name.grid(row=1, column=2, sticky="we")

        # Title line, 4th column
        preset_name = tk.Label(
            master=self.frame_array[8],
            text="Scenario",
            bg=col.c4,
            font=("Arial", fontsize, "bold"),
        )
        preset_name.grid(row=1, column=3, sticky="we")

        # Title line, 5th column
        preset_name = tk.Label(
            master=self.frame_array[9],
            text="Display",
            bg=col.c4,
            font=("Arial", fontsize, "bold"),
        )
        preset_name.grid(row=1, column=4, sticky="we")

        irow = 2
        # iprocess = 1
        for process in waveform_presets.keys():

            # Labels for processes (1st column)
            add_label_process = tk.Label(
                master=self.frame_array[irow * ncol],
                text=process.upper(),
                bg=col.c4,
                font=("Arial", fontsize, "bold"),
            )
            add_label_process.grid(sticky="we")

            # Buttons for custom edition (3rd column)
            add_button_custom = tk.Button(
                master=self.frame_array[irow * ncol + 2],
                text="Edit",
                height=1,
                bg=col.c2,
            )
            add_button_custom.grid(padx=2, pady=2, sticky="we")
            add_button_custom.configure(
                command=lambda waveform_presets=waveform_presets, process=process, config_folder=config_folder: waveform_custom_configure(  # noqa E501
                    config_folder, process, waveform_presets[process]["custom"][0]
                )
            )

            # Buttons to reset and use waveform from input scenario (4th column)
            add_button_reset = tk.Button(
                master=self.frame_array[irow * ncol + 3],
                text="Reset",
                height=1,
                bg=col.c2,
            )
            add_button_reset.grid(padx=2, pady=2, sticky="we")
            add_button_reset.configure(
                command=lambda waveform_presets=waveform_presets, process=process, config_folder=config_folder: use_waveform_from_scenario(  # noqa E501
                    config_folder, waveform_presets[process]["custom"][0]
                )
            )

            # Buttons to plot the configured waveform (5th column)
            add_button_plot = tk.Button(
                master=self.frame_array[irow * ncol + 4],
                text="Plot",
                height=1,
                bg=col.c2,
            )
            add_button_plot.grid(padx=2, pady=2, sticky="we")
            if isWaveformCookerPresent:
                add_button_plot.configure(
                    command=lambda waveform_presets=waveform_presets, process=process, config_folder=config_folder: add_dynamic(  # noqa E501
                        config_folder + "/" + waveform_presets[process]["custom"][0],
                        kplot=1,
                    )
                )

            # Buttons for presets (2nd column)
            for preset_key in waveform_presets[process]:
                if preset_key != "custom":
                    add_button_preset = tk.Button(
                        master=self.frame_array[irow * ncol + 1],
                        text=waveform_presets[process][preset_key][1],
                        height=1,
                        bg=col.c2,
                    )
                    add_button_preset.grid(padx=2, pady=2, sticky="we")
                    add_button_preset.configure(
                        command=lambda waveform_presets=waveform_presets, waveform_folder=waveform_folder, preset_key=preset_key, process=process, config_folder=config_folder: preset_copy(  # noqa E501
                            waveform_folder,
                            config_folder,
                            process,
                            waveform_presets[process][preset_key][0],
                            waveform_presets[process]["custom"][0],
                        )
                    )
                    irow += 1

        # Exit the 'edit waveforms' window
        tk.Button(
            master=self.frame_array[-1],
            text="Exit",
            bg=col.c2,
            command=lambda: self.master.destroy(),
        ).grid(padx=(2, 2), pady=2)


############################################################################
