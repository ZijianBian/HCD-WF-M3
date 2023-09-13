#!/usr/bin/env python
import argparse, os
from wftools.wf_tools import (
    read_actor_ids,
    add_ids_entry_to_dict,
    create_workflow_param_from_file,
)
from src.dbhelper import DbHelper
from src.hcd_workflow import HCDWorkflow
from src.global_list_reader import GlobalListReader

# Management of input arguments
parser = argparse.ArgumentParser(
    description="---- Run the H&CD workflow without the interface"
)
parser.add_argument(
    "-c", "--config_folder", help="input configuration folder", required=True
)

args = vars(parser.parse_args())
config_folder = args["config_folder"]

config_folder_path = os.path.abspath(config_folder)
rootPath = os.path.dirname(os.path.abspath(__file__))


class Workflow:
    def __init__(self, config_folder_path) -> None:
        self.config_folder_path = config_folder_path

        # -----------------------------------------------------------------------------------------
        globalListPath = os.path.join(
            rootPath, r"global_configuration/global_lists.yaml"
        )
        self.inputworkflow_xml = os.path.join(
            self.config_folder_path, "input_workflow.xml"
        )

        # create input and output database
        wf_parameters = create_workflow_param_from_file(self.inputworkflow_xml)[
            "workflow_parameters"
        ][0]

        input_user_or_path = wf_parameters["input_user_or_path"][0]
        input_database = wf_parameters["input_database"][0]
        output_user_or_path = wf_parameters["output_user_or_path"][0]
        output_database = wf_parameters["output_database"][0]
        shot_nr = wf_parameters["shot_nr"][0]
        run_in = wf_parameters["run_in"][0]
        run_out = wf_parameters["run_out"][0]

        dbhelper = DbHelper(
            input_user_or_path,
            input_database,
            output_user_or_path,
            output_database,
            shot_nr,
            run_in,
            run_out,
        )
        self.inputDb = dbhelper.getInputDatabase()
        self.outputDb = dbhelper.getOutputDatabase()
        self.machineDb = dbhelper.getMachineDatabase()

        self.hcdWorkflowSeparate = HCDWorkflow(config_folder_path)
        # initialize dictionary_of_actors
        self.dictionary_of_actors = {}
        self.dictionary_of_actors[
            "grayscale"
        ] = self.hcdWorkflowSeparate.initializeActor(
            "grayscale",
            os.path.join(config_folder_path, "ECRH/ec_wave_solver/input_grayscale.xml"),
            os.path.join(config_folder_path, "ECRH/ec_wave_solver/input_grayscale.xsd"),
        )
        # print("------------dictionary_of_actors-----------------")
        # print(dictionary_of_actors)

        # read ids of actor
        single_input_ids_list, single_output_ids_list, err = read_actor_ids(
            "grayscale", 0
        )

        # initialize process bundle
        self.process_bundle = {}
        self.process_bundle["ec_wave_solver"] = {}
        self.process_bundle["ec_wave_solver"]["input"] = {}
        self.process_bundle["ec_wave_solver"]["output"] = {}
        add_ids_entry_to_dict(
            self.process_bundle["ec_wave_solver"]["input"], single_input_ids_list
        )
        add_ids_entry_to_dict(
            self.process_bundle["ec_wave_solver"]["output"], single_output_ids_list
        )
        self.process_bundle["ec_wave_solver"]["status"] = 1
        # print("------------process_bundle-----------------")
        # print(process_bundle)

        self.globallistReader = GlobalListReader(globalListPath)

        self.hcdWorkflowSeparate.readWorkflowConfig(self.inputworkflow_xml)
        self.common_bundle = {}
        # initialize process bundle at specific time slice at 70.00

    def initialize(self, timestamp) -> None:
        inputIds = self.globallistReader.getIdsScenarioList()

        add_ids_entry_to_dict(self.common_bundle, inputIds)

        # get Machine description database
        ids_md_list = self.globallistReader.getIdsMdList()
        waveform_presets = self.globallistReader.getWaveformPresetsList()
        reduced_md_list = self.hcdWorkflowSeparate.getMachineDescriptionData(
            ids_md_list, waveform_presets, self.process_bundle
        )
        self.hcdWorkflowSeparate.initializeIDSSlices(
            timestamp,
            inputIds,
            self.inputDb,
            self.common_bundle,
            self.process_bundle,
            reduced_md_list,
            self.machineDb,
        )

    def run(self, *args):
        self.hcdWorkflowSeparate.hcd_workflow(
            self.process_bundle, self.inputworkflow_xml, self.dictionary_of_actors
        )

    def finalize(self) -> None:
        self.hcdWorkflowSeparate.storeIDSOutput(
            self.common_bundle, self.process_bundle, self.outputDb
        )

    def get_state(self) -> str:
        ...

    def set_state(self, state: str) -> None:
        ...

    def get_timestamp(self) -> float:
        ...


if __name__ == "__main__":
    workflow = Workflow(config_folder_path)
    workflow.initialize(77.00)
    workflow.run()
    workflow.finalize()
