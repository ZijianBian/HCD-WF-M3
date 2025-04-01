import imas
import os
import sys


class WorkflowDbHelper:
    def __init__(
        self,
        input_user_or_path,
        input_database,
        input_backend,
        output_user_or_path,
        output_database,
        output_backend,
        shot_number,
        input_run,
        output_run,
    ):
        # DEFAULT OUTPUT USER_OR_PATH IS $USER
        if output_user_or_path == "default":
            output_user_or_path = os.getenv("USER")

        # DEFAULT OUTPUT LOCAL DB NAME IS EQUAL TO THE INPUT ONE
        if output_database == "default":
            output_database = input_database

        # IF THE OUTPUT DATABASE DOES NOT EXIST: CREATE IT
        if output_user_or_path == os.getenv("USER"):
            output_folder = (
                os.getenv("HOME") + "/public/imasdb/" + output_database + "/3/0"
            )
        else:
            output_folder = f"{output_user_or_path}/{output_database}/3/0"
        if os.path.isdir(output_folder) == False:
            print(
                f"-- Create local database for output file {output_folder}",
                file=sys.stdout,
            )
            os.makedirs(output_folder)

        self.input_user_or_path = input_user_or_path
        self.input_database = input_database
        self.input_backend = input_backend

        self.output_user_or_path = output_user_or_path
        self.output_database = output_database
        self.output_backend = output_backend
        self.shot_number = shot_number
        self.input_run = input_run
        self.output_run = output_run

    def getInputDatabase(self):
        # OPEN INPUT DATAFILE
        print("-- Open input and output file --", file=sys.stdout)
        inputDb = imas.DBEntry(
            getattr(imas.imasdef, f"{self.input_backend}_BACKEND"),
            self.input_database,
            self.shot_number,
            self.input_run,
            self.input_user_or_path,
        )
        retstatus, idx_in = inputDb.open()
        if retstatus != 0:
            print(
                "   ERROR while reading the inputDb shot="
                + str(self.shot_number)
                + " and run="
                + str(self.input_run)
                + "\n   for user_or_path = "
                + self.input_user_or_path
                + " and database = "
                + self.input_database,
                file=sys.stderr,
            )
            print("   Please check that the file exists.", file=sys.stderr)
        return inputDb

    def getOutputDatabase(self):
        # CREATE OUTPUT DATAFILE
        outputDb = imas.DBEntry(
            getattr(imas.imasdef, f"{self.output_backend}_BACKEND"),
            self.output_database,
            self.shot_number,
            self.output_run,
            self.output_user_or_path,
        )
        
        h5_master_file = os.getenv('HOME')+'/public/imasdb/'\
            +self.output_database+'/3/'+str(self.shot_number)\
            +'/'+str(self.output_run)+'/master.h5'
        if os.path.isfile(h5_master_file): # IMAS-5428 still not fixed!!!
            os.remove(h5_master_file)

        retstatus, idx_out = outputDb.create()
        if retstatus != 0:
            print(
                "   ERROR while creating the output shot="
                + str(self.shot_number)
                + " and run="
                + str(self.output_run)
                + "\n   for user_or_path = "
                + self.output_user_or_path
                + " and database = "
                + self.output_database,
                file=sys.stderr,
            )
            print("   --> Aborted.", file=sys.stderr)
        return outputDb

    def getMachineDatabase(self):
        machineDb = imas.DBEntry(
            imas.imasdef.MEMORY_BACKEND,
            self.output_database,
            0,
            self.output_run,
            self.output_user_or_path,
        )
        machineDb.create()
        return machineDb

    def getTimeArray(self, inputDb):
        time_array = None
        try:
            time_array = inputDb.partial_get(ids_name="equilibrium", data_path="time")
        except Exception:
            print(
                "  ERROR while reading the equilibrium IDS: is it really present in the input file?",
                file=sys.stderr,
            )
            print("  ----> Aborted.", file=sys.stderr)
        return time_array
