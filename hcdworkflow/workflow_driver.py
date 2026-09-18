"""Compatibility interface for callers of the original in-process driver."""

from hcdworkflow.hcd_workflow import HCDWorkflow
from workflow.workflow_driver import get_ids_slices, run_traditional, store_ids_slices


class WorkflowDriver:
    def __init__(self, workflowConfigPath: str):
        self.workflowObject = HCDWorkflow()
        self.workflowObject.initialize(workflowConfigPath)
        self.workflowConfigPath = workflowConfigPath

    def initialize(self, inputdb, outputdb, machineDb, inputIds, inputMds):
        self.inputDb = inputdb
        self.outputDb = outputdb
        self.md = machineDb
        self.inputIds = inputIds
        self.inputMds = inputMds

    def executeTimeloop(self, one_time_slice=None, tbegin=None, tend=None, dt_required=None):
        for name, value in (
            ("one_time_slice", one_time_slice),
            ("tbegin", tbegin),
            ("tend", tend),
            ("dt_required", dt_required),
        ):
            if value is not None:
                setattr(self.workflowObject.workflowData, name, value)
        run_traditional(
            self.workflowConfigPath,
            self.inputDb,
            self.outputDb,
            self.md,
            self.inputIds,
            self.inputMds,
            self.workflowObject.workflowData.getParamProcess(),
            workflow=self.workflowObject,
        )

    def getIDSSlices(self, timenow):
        return get_ids_slices(self.inputDb, self.md, self.inputIds, self.inputMds, timenow)

    def storeIDSSlices(self, inputSlices):
        output_ids = self.workflowObject._getIDSes()
        profiles = inputSlices.get("core_profiles")
        timenow = profiles.time[0] if profiles is not None and len(profiles.time) else None
        store_ids_slices(
            self.outputDb,
            self.inputMds,
            inputSlices,
            output_ids,
            param_process=self.workflowObject.workflowData.getParamProcess(),
            timenow=timenow,
            config_folder_path=self.workflowConfigPath,
        )
        return output_ids
