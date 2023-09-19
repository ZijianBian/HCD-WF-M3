import xml.etree.ElementTree as ET
import os
import sys
import functools

root_path = os.path.dirname(__file__)
sys.path.append(root_path)

from process_actor import WfActor


class XmlReader:
    def __init__(self, xmlFile: str) -> None:
        self.xmlFile = xmlFile
        self.xmlTree = None
        self.xmlRoot = None
        self.parseXml()

    def parseXml(self):
        try:
            self.xmlTree = ET.parse(self.xmlFile)
            self.xmlRoot = self.xmlTree.getroot()
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")


class WorkflowConfigReader(XmlReader):
    def __init__(self, xmlFile: str) -> None:
        super().__init__(xmlFile)
        self.workflowDirectory = os.path.dirname(xmlFile)
        self.workflow = self.initializeWorkflow()

    def initializeWorkflow(self):
        actorSelection = self.xmlRoot[1]
        workflow = {}
        for mainKey in actorSelection:
            categoryDict = {}
            for category in mainKey:
                processDict = {}
                for process in category:
                    if process.text != "0":
                        actorsList = process.attrib["list"].split()
                        if int(process.text) - 1 < len(actorsList):
                            selectedActor = actorsList[int(process.text) - 1]
                            actorConfigPath = os.path.join(
                                self.workflowDirectory, category.tag, process.tag
                            )
                            processActor = WfActor.getObject(
                                selectedActor, actorConfigPath
                            )
                            if processActor is not None:
                                processDict[process.tag] = processActor
                        else:
                            print(
                                f"Please select valid index of actor, List length : [{len(actorsList)}] and selected index is: [{int(process.text) - 1}]"
                            )
                if bool(processDict):
                    categoryDict[category.tag] = processDict
            if bool(categoryDict):
                workflow[mainKey.tag] = categoryDict

        return workflow

    def displayConfig(self):
        if self.workflow is not None:
            import pprint

            pprint.pprint(self.workflow)

    def getAllActors(self):
        if self.workflow is None:
            return None
        allActors = {}
        for _, Categories in self.workflow.items():
            for _, processes in Categories.items():
                for _, actor in processes.items():
                    allActors[actor.name] = actor.actor
        return allActors

    @functools.lru_cache(maxsize=128)
    def getAllProcesses(self):
        if self.workflow is None:
            return None
        allProcesses = {}
        for _, Categories in self.workflow.items():
            for _, processes in Categories.items():
                for process, actor in processes.items():
                    allProcesses[process] = actor.actor
        return allProcesses

    def AreProcessesEmpty(self):
        processes = self.getAllProcesses()
        if processes is not None:
            return not bool(processes)  # True if exists, False if empty

    def getProcessBundle(self):
        if self.workflow is None:
            return None
        procesBundle = {}
        for _, Categories in self.workflow.items():
            for _, processes in Categories.items():
                for process, actor in processes.items():
                    procesBundle[process] = {
                        "input": actor.inputIDSDict,
                        "output": actor.outputIDSDict,
                    }
        return procesBundle

    # def readXML(self):
    #     actor_selection = self.xmlRoot[1]
    #     for main_key in actor_selection:
    #         dict_category = {}
    #         for category in main_key:
    #             if category.tag != etree.Comment:
    #                 dict_process = {}
    #                 for process in category:
    #                     list_actor = []
    #                     dict_actor = {}
    #                     if process.tag != etree.Comment:
    #                         for actor_name in process.attrib["list"].split():
    #                             if actor_name in not_compiled_list:
    #                                 verbose_eff = 0
    #                             else:
    #                                 verbose_eff = verbose
    #                                 (
    #                                     input_ids_list,
    #                                     output_ids_list,
    #                                     err,
    #                                 ) = read_actor_ids(actor_name, verbose_eff)
    #                             if err == 0:
    #                                 compiled_list.append(actor_name)
    #                             else:
    #                                 not_compiled_list.append(actor_name)
    #                             dict_actor[actor_name] = [
    #                                 input_ids_list,
    #                                 output_ids_list,
    #                             ]
    #                             list_actor.append(
    #                                 {
    #                                     "name": actor_name,
    #                                     "input": input_ids_list,
    #                                     "output": output_ids_list,
    #                                     "category": category.tag,
    #                                 }
    #                             )
    #                         # Prepend empty_* code
    #                         if output_ids_list == []:
    #                             output_ids_list.append("core_profiles")
    #                         list_actor.insert(
    #                             0,
    #                             {
    #                                 "name": "empty_" + output_ids_list[0],
    #                                 "input": ["core_profiles"],
    #                                 "output": [output_ids_list[0]],
    #                                 "category": category.tag,
    #                             },
    #                         )
    #                         if process.text != "0":
    #                             code_selection[process.tag] = process.attrib[
    #                                 "list"
    #                             ].split(" ")[int(process.text) - 1]
    #                         else:
    #                             code_selection[process.tag] = None
    #                         dict_process[process.tag] = dict_actor
    #                         catdict[process.tag] = list_actor
    #                     dict_category[category.tag] = dict_process
    #                 maindict[main_key.tag] = dict_category

    #     # Remove duplicates
    #     compiled_list = list(dict.fromkeys(compiled_list))
    #     not_compiled_list = list(dict.fromkeys(not_compiled_list))

    #     return (maindict, compiled_list, not_compiled_list, code_selection, catdict)


if __name__ == "__main__":
    workflowConfig = WorkflowConfigReader(
        r"/home/ITER/sawantp1/git/hcd/data/DT_baseline_example/input_workflow.xml"
    )
    workflowConfig.displayConfig()
    print("getAllProcesses")
    print(workflowConfig.getAllProcesses())
    print("getProcessBundle")
    print(workflowConfig.getProcessBundle())

    print("AreProcessesEmpty")
    print(workflowConfig.AreProcessesEmpty())
