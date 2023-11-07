import os

from waveform_cooker import add_dynamic
from wftools.wf_tools import create_workflow_param_from_file
from importlib_resources import files
from src.workflow_dbhelper import WorkflowDbHelper
from src.workflow_globals_reader import WorkflowGlobalsReader
from src.workflow_driver import WorkflowDriver


def wf_wrapper(par_path):
    config_folder_path = os.path.abspath(par_path)

    rootPath = os.path.dirname(os.path.abspath(__file__))
    globalListPath = str(files('src.global_configuration').joinpath('global_lists.yaml'))
    inputworkflow_xml = os.path.join(config_folder_path, "input_workflow.xml")

    wf_parameters = create_workflow_param_from_file(inputworkflow_xml)[
        "workflow_parameters"
    ][0]

    input_user_or_path = wf_parameters["input_user_or_path"][0]
    input_database = wf_parameters["input_database"][0]
    output_user_or_path = wf_parameters["output_user_or_path"][0]
    output_database = wf_parameters["output_database"][0]
    shot_nr = wf_parameters["shot_nr"][0]
    run_in = wf_parameters["run_in"][0]
    run_out = wf_parameters["run_out"][0]

    dbhelper = WorkflowDbHelper(
        input_user_or_path,
        input_database,
        output_user_or_path,
        output_database,
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

    # TODO load only required by process machine descriptions
    # Prepare Memory DB, Check if Machine description is exists and write to memory db
    for idsName in inputMds:
        idsObject = inputDb.get(idsName)
        machineDb.put(idsObject)

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
                idsObject = add_dynamic(filePath)
            machineDb.put(idsObject)

    workflowWrapper = WorkflowDriver(config_folder_path)
    workflowWrapper.initialize(inputDb, outputDb, machineDb, inputIds, inputMds)

    workflowWrapper.executeTimeloop()

    inputDb.close()
    outputDb.close()
    machineDb.close()
