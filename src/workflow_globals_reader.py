import os
import yaml
import sys


class WorkflowGlobalsReader:
    def __init__(self, globalListPath: str) -> None:
        if not os.path.exists(globalListPath):
            raise "Global List Path doesn't exists"
        self.globalListPath = globalListPath

        with open(globalListPath, "r") as fileObject:
            self.rawData = yaml.load(fileObject, Loader=yaml.CLoader)

    def getList(self, listName: str):
        if listName not in self.rawData.keys():
            print("Error: bad listname in loadlist()", file=sys.stderr)
            outputList = []

        for key in self.rawData.keys():
            if listName == key:
                try:
                    outputList = self.rawData[key].split(" ")
                except Exception:
                    outputList = self.rawData[key]

        return outputList

    def getIdsScenarioList(self):
        return self.getList("ids_scenario_list")

    def getIdsMdList(self):
        return self.getList("ids_md_list")

    def getWaveformPresetsList(self):
        return self.getList("waveform_presets")

    def getIdsProcessList(self):
        return self.getList("ids_process_list")

    def getPrerequisites(self):
        return self.getList("prerequisites")

    def getParallelDependency(self):
        return self.getList("parallel_dependency")

    def getMergeActorList(self):
        return self.getList("merge_actor_list")

    def getAlgorithms(self):
        return self.getList("algorithm")

    def getProcessList(self):
        return self.getList("process_list")

    def getDeviceList(self):
        return self.getList("device")
