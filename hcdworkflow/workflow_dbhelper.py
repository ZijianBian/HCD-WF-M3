import os
import sys
from contextlib import suppress

import imas

# IMAS API compatibility
if not hasattr(imas, "imasdef") and hasattr(imas, "ids_defs"):
    imas.imasdef = imas.ids_defs


def _open_or_create(entry, operation, description):
    """Accept legacy status tuples and IMAS-Python's exception-based API."""
    try:
        result = getattr(entry, operation)()
        if isinstance(result, tuple) and result[0] != 0:
            raise RuntimeError(f"IMAS returned status {result[0]}")
    except Exception as error:
        with suppress(Exception):
            entry.close()
        raise RuntimeError(f"Could not {operation} {description}: {error}") from error


class WorkflowDbHelper:
    def __init__(
        self,
        input_user_or_path,
        input_database,
        input_backend,
        ddv_backend,
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
            output_folder = os.getenv("HOME") + "/public/imasdb/" + output_database + f"/{ddv_backend}/0"
        else:
            output_folder = f"{output_user_or_path}/{output_database}/3/0"
        if os.path.isdir(output_folder) is False:
            print(
                f"-- Create local database for output file {output_folder}",
                file=sys.stdout,
            )
            os.makedirs(output_folder)

        self.input_user_or_path = input_user_or_path
        self.input_database = input_database
        self.input_backend = input_backend
        self.ddv_backend = ddv_backend
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
        _open_or_create(inputDb, "open", "input database")
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

        h5_master_file = (
            os.getenv("HOME")
            + "/public/imasdb/"
            + self.output_database
            + "/3/"
            + str(self.shot_number)
            + "/"
            + str(self.output_run)
            + "/master.h5"
        )
        if os.path.isfile(h5_master_file):  # IMAS-5428 still not fixed!!!
            os.remove(h5_master_file)

        _open_or_create(outputDb, "create", "output database")
        return outputDb

    def getMachineDatabase(self):
        machineDb = imas.DBEntry(
            imas.imasdef.MEMORY_BACKEND,  # pylint: disable=no-member
            self.output_database,
            0,
            self.output_run,
            self.output_user_or_path,
        )
        _open_or_create(machineDb, "create", "machine-description database")
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
