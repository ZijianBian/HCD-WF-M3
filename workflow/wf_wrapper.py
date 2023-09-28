import os

from waveform_cooker import add_dynamic
from wftools.wf_tools import create_workflow_param_from_file

from src.workflow_dbhelper import WorkflowDbHelper
from src.workflow_globals_reader import WorkflowGlobalsReader
from src.workflow_wrapper import WorkflowWrapper


def wf_wrapper(par_path):
    config_folder_path = os.path.abspath(par_path)

    rootPath = os.path.dirname(os.path.abspath(__file__))
    globalListPath = os.path.join(
        rootPath, "..", r"global_configuration/global_lists.yaml"
    )
    print(globalListPath)
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
    inputMds = globallistReader.getIdsMdList()

    # TODO load only required by process machine descriptions
    # Prepare Memory DB, Check if Machine description is exists and write to memory db
    for idsName in inputMds:
        idsObject = inputDb.get(idsName)
        machineDb.put(idsObject)

    # Overwrite with configured waveform if it exists
    for filename in os.listdir(config_folder_path):
        filePath = os.path.join(config_folder_path, filename)
        if filePath.endswith("waveforms.yaml"):
            if os.path.exists(filePath):
                idsObject = add_dynamic(filePath)
            machineDb.put(idsObject)

    workflowWrapper = WorkflowWrapper(config_folder_path)
    workflowWrapper.initialize(inputDb, outputDb, machineDb, inputIds, inputMds)

    workflowWrapper.executeTimeloop()

    inputDb.close()
    outputDb.close()
    machineDb.close()
