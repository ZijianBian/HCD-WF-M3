import inspect
import os
from pathlib import Path

import imas

import hcdworkflow
from gui.gui_methods import create_workflow_param_from_file
from hcdworkflow.workflow_dbhelper import WorkflowDbHelper
from hcdworkflow.workflow_driver import WorkflowDriver
from hcdworkflow.workflow_globals_reader import WorkflowGlobalsReader

isWaveformCookerPresent = True
try:
    from waveform_cooker import add_dynamic
except Exception as _:  # noqa F841
    isWaveformCookerPresent = False


def wf_wrapper(par_path):
    config_folder_path = os.path.abspath(par_path)

    pathGlobalConfiguration = Path(inspect.getfile(hcdworkflow)).parent / "global_configuration"

    globalListPath = str(pathGlobalConfiguration / "global_lists.yaml")

    inputworkflow_xml = os.path.join(config_folder_path, "input_workflow.xml")
    print("path of the input workflow", inputworkflow_xml)
    wf_parameters = create_workflow_param_from_file(inputworkflow_xml)["workflow_parameters"][0]

    input_user_or_path = wf_parameters["input_user_or_path"][0]
    input_database = wf_parameters["input_database"][0]
    input_backend = "MDSPLUS"
    if "input_backend" in wf_parameters:
        input_backend = wf_parameters["input_backend"][0]
    output_user_or_path = wf_parameters["output_user_or_path"][0]
    output_database = wf_parameters["output_database"][0]
    output_backend = "MDSPLUS"
    if "output_backend" in wf_parameters:
        output_backend = wf_parameters["output_backend"][0]
    shot_nr = wf_parameters["shot_nr"][0]
    run_in = wf_parameters["run_in"][0]
    run_out = wf_parameters["run_out"][0]

    dbhelper = WorkflowDbHelper(
        input_user_or_path,
        input_database,
        input_backend,
        output_user_or_path,
        output_database,
        output_backend,
        shot_nr,
        run_in,
        run_out,
    )
    inputDb = dbhelper.getInputDatabase()
    outputDb = dbhelper.getOutputDatabase()
    machineDb = dbhelper.getMachineDatabase()

    globallistReader = WorkflowGlobalsReader(globalListPath)
    inputIds = globallistReader.getIdsScenarioList()
    inputIds.append("workflow")
    inputMds = globallistReader.getIdsMdList()
    wall_md = globallistReader.getWallMD()

    # TODO load only required by process machine descriptions
    # Prepare Memory DB, Check if Machine description is exists and write to memory db
    for idsName in inputMds:
        idsObject = inputDb.get(idsName)
        if idsObject.ids_properties.homogeneous_time != imas.imasdef.EMPTY_INT:
            machineDb.put(idsObject)
        else:
            if idsName == "wall":
                wall = imas.DBEntry(
                    getattr(imas.ids_defs, f"{wall_md['backend']}_BACKEND"),
                    wall_md["database"],
                    wall_md["shot"],
                    wall_md["run"],
                    wall_md["user_or_path"],
                )
                wall.open()
                machineDb.put(wall.get("wall"))
            print(f"{idsName} is not present in the scenario data, you can provide it with waveform cooker if required")

    # feature/repair_231017
    # TODO This change is not needed as input slices are separate from process
    # flag_multiple_md = 0 # has to be in the loop of processes,
    # otherwise the waveform is not read for all processes which use the same IDS:
    # e.g. ic_antennas both for ic_wave_solver and ic_wave_fp
    # Overwrite with configured waveform if it exists
    for filename in os.listdir(config_folder_path):
        filePath = os.path.join(config_folder_path, filename)
        if filePath.endswith("waveforms.yaml"):
            if os.path.exists(filePath):
                idsObject = add_dynamic(filePath) if isWaveformCookerPresent else None
            if idsObject is not None:
                machineDb.put(idsObject)

    workflowWrapper = WorkflowDriver(config_folder_path)
    workflowWrapper.initialize(inputDb, outputDb, machineDb, inputIds, inputMds)

    workflowWrapper.executeTimeloop()

    inputDb.close()
    outputDb.close()
    machineDb.close()

    print("End of wf_wrapper")
