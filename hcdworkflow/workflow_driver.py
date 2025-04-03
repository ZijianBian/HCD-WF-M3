import logging
import os
import sys

from hcdworkflow.hcd_workflow import HCDWorkflow

log = logging.getLogger()
log.setLevel(logging.ERROR)


root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class WorkflowDriver:
    def __init__(self, workflowConfigPath: str):
        self.workflowObject = HCDWorkflow()
        self.workflowObject.initialize(workflowConfigPath)
        self.workflowConfigPath = workflowConfigPath

    def initialize(self, inputdb, outputdb, machineDb, inputIds, inputMds):
        self.inputDb = inputdb
        self.outputDb = outputdb
        self.md = machineDb
        self.inputMds = inputMds
        self.inputIds = inputIds

    def executeTimeloop(self, one_time_slice=None, tbegin=None, tend=None, dt_required=None):
        if one_time_slice is not None:
            self.workflowObject.workflowData.one_time_slice = one_time_slice
        if tbegin is not None:
            self.workflowObject.workflowData.tbegin = tbegin
        if tend is not None:
            self.workflowObject.workflowData.tend = tend
        if dt_required is not None:
            self.workflowObject.workflowData.dt_required = dt_required
        # -----------------------------------------
        # PREPARE THE TIME RANGE FOR THE TIME LOOP
        # -----------------------------------------
        if self.workflowObject.workflowData.one_time_slice == 0:
            # INPUT TIME ARRAY
            # try:
            time_array = self.inputDb.partial_get(ids_name="equilibrium", data_path="time")
            # except:
            #     print(
            #         "  ERROR while reading the equilibrium IDS: is it really present in the input file?",
            #         file=sys.stderr,
            #     )
            #     print("  ----> Aborted.", file=sys.stderr)
            #     return

            # CHECK & ADJUST CHOSEN TIME TO CORE_PROFILES IF NECESSARY
            if self.workflowObject.workflowData.tbegin < 0:
                self.workflowObject.workflowData.tbegin = time_array[0]
                print(
                    "Initial time tbegin set to core_profiles first time slice. tbegin = ",
                    self.workflowObject.workflowData.tbegin,
                    file=sys.stdout,
                )

            if self.workflowObject.workflowData.tbegin > 0 and self.workflowObject.workflowData.tbegin < time_array[0]:
                print(
                    "ERROR: tbegin out of range: "
                    + str(self.workflowObject.workflowData.tbegin)
                    + " s is less than first time in core_profiles =",
                    "{:.2f}".format(time_array[0]),
                    "s",
                    file=sys.stderr,
                )
                return

            if self.workflowObject.workflowData.tend < 0:
                self.tend = time_array[-1]
                print(
                    "Final time tend set to core_profiles final time slice, tend = ",
                    self.tend,
                    file=sys.stdout,
                )

            if self.workflowObject.workflowData.tend > 0 and self.workflowObject.workflowData.tend > time_array[-1]:
                print(
                    "ERROR: tend out of range: "
                    + str(self.workflowObject.workflowData.tend)
                    + " s is greater than last time in core_profiles =",
                    "{:.2f}".format(time_array[-1]),
                    "s",
                    file=sys.stderr,
                )
                return
        else:
            self.workflowObject.workflowData.tend = (
                self.workflowObject.workflowData.tbegin + self.workflowObject.workflowData.dt_required
            )

        ##################################################################

        # -----------------
        # BEGIN TIME LOOP
        # -----------------

        print("---------------------------------------------", file=sys.stdout)
        print("---- Enter time loop of the H&CD wrapper ----", file=sys.stdout)

        timenow = self.workflowObject.workflowData.tbegin

        if self.workflowObject.workflowData.one_time_slice == 0:
            nsteps = int(
                (self.workflowObject.workflowData.tend - self.workflowObject.workflowData.tbegin)
                / self.workflowObject.workflowData.dt_required
            )
        else:
            nsteps = 1
        if (
            self.workflowObject.workflowData.dt_required * nsteps
            < int((self.workflowObject.workflowData.tend - self.workflowObject.workflowData.tbegin) * 10**5) / 10**5
        ):
            nsteps = nsteps + 1

        step = 0
        previous_time = {}

        while timenow < self.workflowObject.workflowData.tend:
            step += 1

            print("---------------------------------------------", file=sys.stdout)
            print("Step = " + str(step) + "/" + str(nsteps), file=sys.stdout)
            print("Time = %5.2f" % timenow, "s", file=sys.stdout)
            print(
                "dt   = %5.2f" % self.workflowObject.workflowData.dt_required,
                "s",
                file=sys.stdout,
            )

            idsSlices = self.getIDSSlices(timenow)
            nonmandatoryIDSes = {
                k: v for k, v in idsSlices.items() if k not in ["equilibrium", "core_profiles", "workflow"]
            }

            self.workflowObject.setProcessStatus(timenow)

            idsData = self.workflowObject.run(
                equilibrium=idsSlices["equilibrium"],
                core_profiles=idsSlices["core_profiles"],
                workflow=idsSlices["workflow"],
                **nonmandatoryIDSes,
            )
            # self.workflowObject.finalize()

            idsOut = {}
            for idsName, idsData in idsSlices.items():
                if idsName not in self.inputMds:
                    idsOut[idsName] = idsData

            process_bundle_out = self.storeIDSSlices(idsOut)

            for ids in process_bundle_out.keys():
                if len(process_bundle_out[ids].time) > 0:  # Empty if process deactivated by an is_xx_on function
                    if process_bundle_out[ids].time[0] > 0 or "merge" in process_bundle_out[ids].code.name:
                        previous_time[ids] = process_bundle_out[ids].time[0]
            # ------------------------------------------------------------------------------------------
            # PREPARE FOR THE NEXT TIME STEP: COPY OUTPUT IDS IN INPUT OF ACTORS FOR THE NEXT TIME STEP
            # ------------------------------------------------------------------------------------------
            timenow = timenow * 1.0 + self.workflowObject.workflowData.dt_required * 1.0
            for process in self.workflowObject.workflowData.process_bundle.keys():
                if "merge_" not in process:
                    for ids in self.workflowObject.workflowData.process_bundle[process]["output"].keys():
                        if (
                            type(self.workflowObject.workflowData.process_bundle[process]["input"]) is dict
                            and ids in self.workflowObject.workflowData.process_bundle[process]["input"].keys()
                        ):
                            print("Copy " + ids + " from output to input for " + process + " for next time slice")
                            self.workflowObject.workflowData.process_bundle[process]["input"][ids] = (
                                self.workflowObject.workflowData.process_bundle[process]["output"][ids]
                            )

    def getIDSSlices(self, timenow):
        idsSlices = {}
        for ids in self.inputIds:
            print("  Get", ids, file=sys.stdout)
            try:
                idsSlices[ids] = self.inputDb.get_slice(ids, timenow, 1)
            except Exception:
                print(f"  ERROR while reading the {ids} IDS:", file=sys.stderr)
                print(
                    "  ----> Check the version of the Data Dictionary between the"
                    + " input and the loaded IMAS version.",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return

        # READ ALL MACHINE DESCRITPTION IDSS FOR THE CURRENT TIME SLICE
        for ids in self.inputMds:
            # print("  Get", ids, file=sys.stdout)
            try:
                # feature/repair_231017
                # TODO This change is not needed as input slices are separate from process
                # if 'merge_' not in process:
                idsSlices[ids] = self.md.get_slice(ids, timenow, 1)
            except Exception:
                print(f"  ERROR while reading the {ids} IDS:", file=sys.stderr)
                print(
                    "  ----> Check the version of the Data Dictionary between the"
                    + " input and the loaded IMAS version.",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return
        return idsSlices

    def storeIDSSlices(self, inputSlices):
        # Store input IDSes to disk
        for idsName, idsData in inputSlices.items():
            if idsData.ids_properties.homogeneous_time >= 0:
                self.outputDb.put_slice(idsData)

        # Save output IDSes to disk
        process_bundle_out = {}

        # TAKE THE MERGER OUTPUT IDS IF THERE IS ANY
        for process in self.workflowObject.workflowData.process_bundle.keys():
            if "merge_" in process:
                key, value = list(self.workflowObject.workflowData.process_bundle[process]["output"].items())[0]
                process_bundle_out[key] = value

        # TAKE ALL OTHER OUTPUT IDS BUT ONLY IF IT WAS NOT A MERGER OUTPUT ALREADY
        for process in self.workflowObject.workflowData.process_bundle.keys():
            for key, value in self.workflowObject.workflowData.process_bundle[process]["output"].items():
                if key not in process_bundle_out.keys():
                    process_bundle_out[key] = value

        # SAVE TO DISK
        for ids in process_bundle_out:
            if len(process_bundle_out[ids].time) > 0:  # Empty if process deactivated by an is_xx_on function
                if process_bundle_out[ids].time[0] > 0 or "merge" in process_bundle_out[ids].code.name:
                    if ids != "equilibrium":
                        self.outputDb.put_slice(process_bundle_out[ids])
        return process_bundle_out
