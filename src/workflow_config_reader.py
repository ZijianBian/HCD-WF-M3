import xml.etree.ElementTree as ET
import os
import sys
import functools
import numpy as np

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

    def xml2dict(self, root):
        children = {}
        for child in root:
            if child.tag != ET.Comment:
                key = child.tag
                if "display" in child.attrib:
                    display = child.attrib["display"]
                else:
                    display = key
                if len(child) > 0:
                    children[key] = [self.xml2dict(child), display]
                else:
                    children[key] = [self.string2num(child.text), display]

        return children

    def string2num(self, string):
        newstring = string.replace(" ", "").replace("[", "").replace("]", "").split(",")
        if len(newstring) == 1:  # Scalars
            try:
                return int(string)  # Integer scalar
            except Exception:
                None
            try:
                return float(string)  # Float scalar
            except Exception:
                None
        else:  # Arrays
            try:
                return np.array([int(i) for i in newstring])  # Integer array
            except Exception:
                None
            try:
                return np.array([float(i) for i in newstring])  # Float array
            except Exception:
                None

        return string  # String scalar


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

    def getSelectedCategories(self):
        if self.workflow is None:
            return None
        categoryDict = {}
        for headProcess, Categories in self.workflow.items():
            for category, processes in Categories.items():
                actorList = []
                for process, actor in processes.items():
                    actorList.append(
                        {
                            "name": actor.name,
                            "input": actor.inputIDSList,
                            "output": actor.outputIDSList,
                            "category": category,
                        }
                    )
                    # Prepend empty_* code
                    if actor.outputIDSList == []:
                        actor.outputIDSList.append("core_profiles")
                    actorList.insert(
                        0,
                        {
                            "name": f"empty_{actor.outputIDSList[0]}",
                            "input": ["core_profiles"],
                            "output": [actor.outputIDSList[0]],
                            "category": category,
                        },
                    )
                categoryDict[process] = actorList
        return categoryDict

    def getParamProcess(self):
        actorSelection = self.xmlRoot[1]
        param_process = {}
        for mainKey in actorSelection:
            for category in mainKey:
                for process in category:
                    param_process[process.tag] = int(process.text)
        return param_process

    def getCategories(self):
        actorSelection = self.xmlRoot[1]
        categoryDict = {}
        for mainKey in actorSelection:
            for category in mainKey:
                actorList = []
                for process in category:
                    actorsList = process.attrib["list"].split()
                    selectedActor = actorsList[int(process.text) - 1]
                    result = WfActor.getActorIDS(selectedActor)

                    if result is not None:
                        inputIDSList, outputIDSList = result
                        actorList.append(
                            {
                                "name": selectedActor,
                                "input": inputIDSList,
                                "output": outputIDSList,
                                "category": category.tag,
                            }
                        )
                        # Prepend empty_* code
                        if outputIDSList == []:
                            outputIDSList.append("core_profiles")
                        actorList.insert(
                            0,
                            {
                                "name": f"empty_{outputIDSList[0]}",
                                "input": ["core_profiles"],
                                "output": [outputIDSList[0]],
                                "category": category.tag,
                            },
                        )
                categoryDict[process.tag] = actorList
        return categoryDict

    def getWorkflowParameters(self):
        parameters = {}
        workflowParameters = self.xmlRoot[0]
        for parameter in workflowParameters:
            print(parameter.tag)
            parameterValue = parameter.text
            if parameterValue.isdigit():
                parameters[parameter.tag] = int(parameter.text)
            elif parameterValue.replace(".", "", 1).isdigit():
                parameters[parameter.tag] = float(parameter.text)
            else:
                parameters[parameter.tag] = parameter.text
        return parameters

    def getTimeBase(self):
        try:
            timeBase = self.xmlRoot[2]
            return self.xml2dict(timeBase)
        except Exception:
            return None


if __name__ == "__main__":
    workflowConfig = WorkflowConfigReader(
        r"/home/ITER/sawantp1/git/hcd/data/DT_baseline_example/input_workflow.xml"
    )
    # workflowConfig.displayConfig()
    # print("getAllProcesses")
    # print(workflowConfig.getAllProcesses())
    # print("getProcessBundle")
    # print(workflowConfig.getProcessBundle())

    # print("AreProcessesEmpty")
    # print(workflowConfig.AreProcessesEmpty())

    # print("getCategories")
    import pprint

    # pprint.pprint(workflowConfig.getCategories())

    # print("getParamProcess")
    # pprint.pprint(workflowConfig.getParamProcess())

    print("workflowParameters")
    pprint.pprint(workflowConfig.getWorkflowParameters())

    # print("getTimeBase")
    # pprint.pprint(workflowConfig.getTimeBase())

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
