import logging
import os
from importlib import import_module
from inspect import getmodule, stack

import imas
from lxml import etree

logger = logging.getLogger("module")


# TODO Make generic process actor using class method which
# can initialize any actor (iwrap, muscle etc).. keep interface same
# Current implementation is only iwrap
class WorkflowActor:
    def __init__(self, actorName: str, xmlPath: str = "", verbose=False):
        self.name = actorName
        self.xmlPath = xmlPath

        self.validate()
        self.actor = self.initializeActor(actorName, xmlPath, verbose)

        self.inputIDSList = self.getInputIDSList()
        self.outputIDSList = self.getOutputIDSList()

        self.inputIDSDict = self.getIDSDict(self.inputIDSList)
        self.outputIDSDict = self.getIDSDict(self.outputIDSList)

    @classmethod
    def getObject(cls, actorName):
        return WorkflowActor(actorName)

    @classmethod
    def getObjectByXmlDirectory(cls, actorName, xmlDirectory: str):
        if not os.path.exists(xmlDirectory):
            print(f"Actor configuration not found for actor name : [{actorName}]")
            return None
        if not os.path.exists(
            os.path.join(
                xmlDirectory,
                f"input_{actorName}.xml",
            )
        ):
            print(f"Actor configuration not found for actor name : [{actorName}]")
            return None
        return WorkflowActor(
            actorName,
            os.path.join(
                xmlDirectory,
                f"input_{actorName}.xml",
            ),
        )

    def validate(self):
        if not self.name:
            logger.critical(f"ERROR! Actor name {self.name } : Actor name is not provided")
            return None

    def initializeActor(self, actorName: str, xmlPath: str, verbose=False):
        # TELL EACH ACTOR WHERE TO FIND ITS XML CODE PARAMETERS FILE AND INITIALIZE IT
        if WorkflowActor._import(actorName, verbose) != 0:
            logger.critical(f"ERROR! Couldn't import actor {self.name }")
            return None

        actor = eval(actorName)
        runtime_settings = actor.get_runtime_settings()
        imasdef = imas.ids_defs if hasattr(imas, 'ids_defs') else imas.imasdef
        runtime_settings.ids_storage.backend = imasdef.MEMORY_BACKEND
        code_parameters = actor.get_code_parameters()
        if xmlPath:
            code_parameters.parameters_path = xmlPath
            if actor.is_mpi_code is True:
                tree = etree.parse(xmlPath)
                root = tree.getroot()
                nproc_actor = 4
                for elem in root.iter():
                    if elem.tag == "nproc_actor":
                        nproc_actor = int(elem.text)
                runtime_settings.mpi.mpi_processes = nproc_actor

        # feature/repair_231017
        # TODO Need to move out and keep it separate
        if actorName == "pion":
            from pion.common.runtime_settings import SandboxLifeTime, SandboxMode

            runtime_settings.sandbox.life_time = SandboxLifeTime.PERSISTENT
            runtime_settings.sandbox.mode = SandboxMode.MANUAL
            runtime_settings.sandbox.path = (
                os.getcwd()
            )  # To be fixed later on (pion fails if it does not know where to write)
        arguments = {}
        if code_parameters is not None:
            arguments["code_parameters"] = code_parameters
        if runtime_settings is not None:
            arguments["runtime_settings"] = runtime_settings
        actor.initialize(**arguments)
        return actor

    def getActor(self):
        return self.actor

    def getInputIDSList(self):
        return self.getIDSList("IN")

    def getOutputIDSList(self):
        return self.getIDSList("OUT")

    # def getInputIDSDict(self):
    #     return self.getIDSDict("IN")

    # def getOutputIDSDict(self):
    #     return self.getIDSDict("OUT")

    def getIDSDict(self, idsData):
        idsDict = {}
        if isinstance(idsData, list):
            for idsName in idsData:
                if hasattr(imas, 'IDSFactory'):
                    idsDict[idsName] = getattr(imas.IDSFactory(), idsName)()
                else:
                    idsDict[idsName] = eval(f"imas.{idsName}()")
        else:
            if hasattr(imas, 'IDSFactory'):
                idsDict[idsData] = getattr(imas.IDSFactory(), idsData)()
            else:
                idsDict[idsData] = eval(f"imas.{idsData}()")
        return idsDict

    def getIDSList(self, intentType="IN"):
        idsList = []
        if self.actor is not None:
            idsList.extend(
                ilist["type"]
                for ilist in self.actor.code_description["implementation"]["subroutines"]["main"]["arguments"]
                if ilist["intent"] == intentType
            )
        return idsList

    # TODO Look for cleaner way of importing actors
    @staticmethod
    def _import(actorName: str, verbose=False):
        try:
            _ = import_module(actorName)
        except Exception:
            if verbose:
                print(f"WARNING! Actor {actorName.upper()} not found.")
            return 1

        actor_function = getattr(import_module(f"{actorName}.actor"), actorName)()

        actorDictionary = {actorName: actor_function}

        # Add this dictionary into the local variables of the calling routine:
        # 1) from interactive sessions, f_locals from current frame is modified
        # 2) when called from a script, the dictionary of the calling module is modified

        # For interactive sessions
        if getmodule(stack()[1].frame) is None:
            stack()[1].frame.f_locals.update(actorDictionary)
        else:
            getmodule(stack()[1].frame).__dict__.update(actorDictionary)

        return 0

    @staticmethod
    def getActorIDS(actorName: str):
        err = WorkflowActor._import(actorName)
        if err == 0:
            actor = eval(actorName)

            input_ids_list = []
            output_ids_list = []
            # IMAS-4679

            for ilist in actor.code_description["implementation"]["subroutines"]["main"]["arguments"]:
                if ilist["intent"] == "IN":
                    input_ids_list.append(ilist["type"])
                elif ilist["intent"] == "OUT":
                    output_ids_list.append(ilist["type"])

            return (input_ids_list, output_ids_list)
        return None


if __name__ == "__main__":
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(root_path)
    procesActor = WorkflowActor(
        "torbeam",
        os.path.join(root_path, "data/DT_baseline_example/ECRH/ec_wave_solver/input_torbeam.xml"),
        os.path.join(root_path, "data/DT_baseline_example/ECRH/ec_wave_solver/input_torbeam.xsd"),
    )
    # procesActor = WfActor(
    #     "grayscale",
    #     os.path.join(
    #         root_path,
    #         "data/run_230825_18:42:34/ECRH/ec_wave_solver/input_grayscale.xml",
    #     ),
    #     os.path.join(
    #         root_path,
    #         "data/run_230825_18:42:34/ECRH/ec_wave_solver/input_grayscale.xsd",
    #     ),
    # )

    print(procesActor.getInputIDSList())
    print(procesActor.getOutputIDSList())
    print(procesActor.getActor())
    print(type(procesActor.getActor()))
    # error = 0

    # # Import the actor(s) and put into a dictionary
    # dictactor = {}
    # if type(actor_input) == str:
    #     dictactor[actor_input], error = __syspath_import_actor(actor_input, verbose)
    # else:
    #     for actor_name in actor_input:
    #         dictactor[actor_name], err = __syspath_import_actor(actor_name, verbose)
    #         if err == 1:
    #             error = 1

    # # Add this dictionary into the local variables of the calling routine:
    # # 1) from interactive sessions, f_locals from current frame is modified
    # # 2) when called from a script, the dictionary of the calling module is modified

    # # For interactive sessions
    # if getmodule(stack()[1].frame) == None:
    #     stack()[1].frame.f_locals.update(dictactor)
    # # When called from a module
    # else:
    #     getmodule(stack()[1].frame).__dict__.update(dictactor)

    # return error

    # def __syspath_import_actor(actor_name, verbose):
    #     from importlib import import_module

    #     # Import the module of the actor
    #     try:
    #         actor_module = import_module(actor_name)
    #     except:
    #         if verbose == 1:
    #             print("Actor " + actor_name.upper() + " not found.", file=sys.stderr)
    #         return [], 1

    #     # Import the actor function
    #     actor_function = getattr(import_module(actor_name + ".actor"), actor_name)()

    #     return actor_function, 0

    # self.dictionary_of_actors = {}
    # process_actor = {}
    # for main_key in self.maindict:
    #     for category in self.maindict[main_key]:
    #         for process in self.maindict[main_key][category]:
    #             for actor_name in self.maindict[main_key][category][process]:
    #                 if (
    #                     self.code_selection[process] is not None
    #                     and actor_name == self.code_selection[process]
    #                 ):
    #                     process_actor[process] = actor_name
    #                     xmlPath = (
    #                         self.workflowConfigPath
    #                         + "/"
    #                         + category
    #                         + "/"
    #                         + process
    #                         + "/input_"
    #                         + actor_name
    #                         + ".xml"
    #                     )
    #                     xsdPath = (
    #                         self.workflowConfigPath
    #                         + "/"
    #                         + category
    #                         + "/"
    #                         + process
    #                         + "/input_"
    #                         + actor_name
    #                         + ".xsd"
    #                     )
    #                     actor = self.initializeActor(actor_name, xmlPath, xsdPath)
    #                     self.dictionary_of_actors[actor_name] = actor
