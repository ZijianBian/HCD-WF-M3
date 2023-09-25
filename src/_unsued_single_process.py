import logging

import imas

from src.Workflow_actor import ProcessActor

logger = logging.getLogger("module")


class SingleProcess:
    def __init__(self, processName: str, processActor: ProcessActor = None):
        self.name = processName
        self.processActor = processActor
        self.validate()
        self.inputIDSes = self.initializeIDSes(processActor.getInputIDSList())
        self.outputIDSes = self.initializeIDSes(processActor.getOutputIDSList())

    def validate(self):
        if not self.processActor:
            logger.critical("ERROR! ProcessActor parameter is not initialized")
            return None

    def initializeIDSes(self, idsList: list):
        dictVariable = {}
        if type(idsList) == list:
            for ids in idsList:
                dictVariable[ids] = eval(f"imas.{ids}()")
        else:
            dictVariable[ids] = eval(f"imas.{ids}()")
        return dictVariable
