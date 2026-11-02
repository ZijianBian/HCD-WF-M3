import os
import pwd
import re
import sys
from contextlib import suppress
from urllib.parse import urlparse

import imas
from imas.exception import DataEntryException


def get_ids(db, ids_name, time=None):
    """Read an IDS, or its time slice closest to time, from db.

    Returns an empty IDS when db has no data for it.
    IMAS-Python raises DataEntryException in that case instead.
    """
    try:
        if time is None:
            return db.get(ids_name)
        return db.get_slice(ids_name, time, imas.ids_defs.CLOSEST_INTERP)
    except DataEntryException:
        return imas.IDSFactory(db.dd_version).new(ids_name)


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


def legacy_uri(user_or_path, database, pulse, run, backend="HDF5", data_version=None):
    """URI that the Access Layer builds from the legacy arguments, as imas.DBEntry does for
    DBEntry(backend, database, pulse, run, user_or_path, data_version): the version folder is given by
    data_version, by default by the DD version of the IMAS-Python factory of this environment."""
    from imas.backends.imas_core.imas_interface import ll_interface

    status, uri = ll_interface.build_uri_from_legacy_parameters(
        getattr(imas.ids_defs, f"{backend}_BACKEND"),
        int(pulse),
        int(run),
        str(user_or_path),
        str(database),
        str(data_version or imas.IDSFactory().dd_version),
        "",
    )
    if status != 0:
        raise RuntimeError(f"Could not build the IMAS URI of {user_or_path}/{database}/{pulse}/{run} (status {status})")
    return uri


def legacy_entry_dir(user_or_path, database, pulse, run, backend="HDF5", data_version=None):
    """Directory of the data entry given by the legacy arguments, resolved as the Access Layer does:
    <base>/<database>/<version>/<pulse>/<run>, with <version> taken from the URI (DD major version, see
    legacy_uri) and <base> = user_or_path when it is an absolute path, $IMAS_HOME/shared/imasdb for
    "public", and <home directory of the user>/public/imasdb for a user name."""
    uri = legacy_uri(user_or_path, database, pulse, run, backend, data_version)
    query = dict(item.split("=", 1) for item in re.split("[;&]", urlparse(uri).query) if "=" in item)
    user = query["user"]
    if user.startswith("/"):
        base = user
    elif user == "public":
        if not os.getenv("IMAS_HOME"):
            raise RuntimeError(f"{uri}: IMAS_HOME is not set, the public database cannot be located")
        base = os.path.join(os.environ["IMAS_HOME"], "shared", "imasdb")
    else:
        try:
            base = os.path.join(pwd.getpwnam(user).pw_dir, "public", "imasdb")
        except KeyError as error:
            raise RuntimeError(f"{uri}: unknown user {user!r}") from error
    return os.path.join(base, query["database"], query["version"], query["pulse"], query["run"])


def check_distinct_entries(input_entry, output_entry):
    """Stop when the output data entry is the input one (same directory after resolving symbolic links)."""
    if os.path.realpath(input_entry) == os.path.realpath(output_entry):
        raise ValueError(
            f"The output data entry {output_entry} is the input data entry {input_entry} "
            f"({os.path.realpath(input_entry)}): change output_user_or_path, output_database or run_out "
            "in input_workflow.xml."
        )


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

        # Input entry: the entry of the DD major of this environment; for DD 4, when that entry does not
        # exist, the DD 3 entry of the same database, pulse and run (its IDSs are read in their stored DD
        # and converted to the DD of this environment like every input IDS)
        self.input_data_version = None
        self.input_entry = legacy_entry_dir(input_user_or_path, input_database, shot_number, input_run, input_backend)
        if str(ddv_backend).split(".", 1)[0] == "4" and not os.path.isdir(self.input_entry):
            dd3_entry = legacy_entry_dir(
                input_user_or_path, input_database, shot_number, input_run, input_backend, data_version="3"
            )
            if os.path.isdir(dd3_entry):
                self.input_data_version = "3"
                self.input_entry = dd3_entry
        # The output data entry must differ from the input one; checked before any file is opened or written
        self.output_entry = legacy_entry_dir(
            output_user_or_path, output_database, shot_number, output_run, output_backend
        )
        check_distinct_entries(self.input_entry, self.output_entry)

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
            getattr(imas.ids_defs, f"{self.input_backend}_BACKEND"),
            self.input_database,
            self.shot_number,
            self.input_run,
            self.input_user_or_path,
            data_version=self.input_data_version,
        )
        _open_or_create(inputDb, "open", "input database")
        stored = f"DD {self.input_data_version} entry" if self.input_data_version else "entry"
        print(
            f"-- Input {stored} {self.input_entry} read for target DD {self.ddv_backend}",
            file=sys.stdout,
            flush=True,
        )
        return inputDb

    def getOutputDatabase(self):
        # CREATE OUTPUT DATAFILE
        outputDb = imas.DBEntry(
            getattr(imas.ids_defs, f"{self.output_backend}_BACKEND"),
            self.output_database,
            self.shot_number,
            self.output_run,
            self.output_user_or_path,
        )

        # HDF5 backend: the master file of an existing output entry is removed before the entry is created
        # again (IMAS-5428); only the resolved output entry is touched
        h5_master_file = os.path.join(self.output_entry, "master.h5")
        if self.output_backend == "HDF5" and os.path.isfile(h5_master_file):
            os.remove(h5_master_file)

        _open_or_create(outputDb, "create", "output database")
        return outputDb

    def getMachineDatabase(self):
        machineDb = imas.DBEntry(
            imas.ids_defs.MEMORY_BACKEND,
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
            time_array = inputDb.get("equilibrium", lazy=True).time.value
        except Exception:
            print(
                "  ERROR while reading the equilibrium IDS: is it really present in the input file?",
                file=sys.stderr,
            )
            print("  ----> Aborted.", file=sys.stderr)
        return time_array
