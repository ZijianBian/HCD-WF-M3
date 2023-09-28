import copy
import logging
import os
import sys
from multiprocessing import Pool
from time import time

import imas
import numpy as np
from lxml import etree
from src.hcd_workflow import HCDWorkflow
from waveform_cooker import add_dynamic
from wftools.wf_tools import (
    add_ids_entry_to_dict,
    find_nearest,
)


log = logging.getLogger()
log.setLevel(logging.ERROR)


root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class WorkflowWrapper:
    def __init__(self, workflowConfigPath: str):
        self.workflowObject = HCDWorkflow()
        self.workflowObject.initialize(workflowConfigPath)
        self.workflowConfigPath = workflowConfigPath

    def initialize(self, inputdb, outputdb, machineDb, inputIds, inputMds):
        self.inputDb = inputdb
        self.outputDb = outputdb
        self.md = machineDb
        self.inputMds = inputMds

        # DEFINE LIST OF SELECTED ACTORS AND INVOLVED IDSS
        # CREATE THE DICTIONARY CONTAINING THE INFORMATION OF ALL CHOSEN ACTORS
        # (SYSTEM, CATEGORY, ACTOR NAME, INPUT/OUTPUT IDSS)

        self.ids_scenario_list = inputIds

        self.common_bundle = {}
        add_ids_entry_to_dict(self.common_bundle, self.ids_scenario_list)

        # IMAS DB VERSION
        version = os.getenv("IMAS_VERSION")[0]

    def run(self, one_time_slice=None, tbegin=None, tend=None, dt_required=None):
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
            try:
                time_array = self.inputDb.partial_get(
                    ids_name="equilibrium", data_path="time"
                )
            except:
                print(
                    "  ERROR while reading the core_profiles IDS: is it really present in the input file?",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return

            # CHECK & ADJUST CHOSEN TIME TO CORE_PROFILES IF NECESSARY
            if self.workflowObject.workflowData.tbegin < 0:
                self.workflowObject.workflowData.tbegin = time_array[0]
                print(
                    "Initial time tbegin set to core_profiles first time slice. tbegin = ",
                    self.workflowObject.workflowData.tbegin,
                    file=sys.stdout,
                )

            if (
                self.workflowObject.workflowData.tbegin > 0
                and self.workflowObject.workflowData.tbegin < time_array[0]
            ):
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

            if (
                self.workflowObject.workflowData.tend > 0
                and self.workflowObject.workflowData.tend > time_array[-1]
            ):
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
                self.workflowObject.workflowData.tbegin
                + self.workflowObject.workflowData.dt_required
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
                (
                    self.workflowObject.workflowData.tend
                    - self.workflowObject.workflowData.tbegin
                )
                / self.workflowObject.workflowData.dt_required
            )
        else:
            nsteps = 1
        if (
            self.workflowObject.workflowData.dt_required * nsteps
            < int(
                (
                    self.workflowObject.workflowData.tend
                    - self.workflowObject.workflowData.tbegin
                )
                * 10**5
            )
            / 10**5
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

            # READ ALL INPUT IDSS FROM THE SCENARIO FOR THE CURRENT TIME SLICE
            # self.initializeIDSSlices(
            #     timenow,
            #     self.ids_scenario_list,
            #     self.inputDb,
            #     self.common_bundle,
            # )
            idsSlices = self.getIDSSlices(
                timenow, self.ids_scenario_list, self.inputDb, self.common_bundle
            )
            idsData = self.workflowObject.run(
                equilibrium=idsSlices["equilibrium"],
                core_profiles=idsSlices["core_profiles"],
                timenow=timenow,
                # nbi=idsSlices["nbi"],
                # ic_antennas=idsSlices["ic_antennas"],
                ec_launchers=idsSlices["ec_launchers"],
                # lh_antennas=idsSlices["lh_antennas"],
                # wall=idsSlices["wall"],
            )

            process_bundle_out = self.storeIDSOutput(
                self.common_bundle,
                self.workflowObject.workflowData.process_bundle,
                self.outputDb,
            )

            for ids in process_bundle_out.keys():
                if (
                    len(process_bundle_out[ids].time) > 0
                ):  # Empty if process deactivated by an is_xx_on function
                    if (
                        process_bundle_out[ids].time[0] > 0
                        or "merge" in process_bundle_out[ids].code.name
                    ):
                        previous_time[ids] = process_bundle_out[ids].time[0]
            # ------------------------------------------------------------------------------------------
            # PREPARE FOR THE NEXT TIME STEP: COPY OUTPUT IDS IN INPUT OF ACTORS FOR THE NEXT TIME STEP
            # ------------------------------------------------------------------------------------------
            timenow = timenow * 1.0 + self.workflowObject.workflowData.dt_required * 1.0
            for process in self.workflowObject.workflowData.process_bundle.keys():
                if "merge_" not in process:
                    for ids in self.workflowObject.workflowData.process_bundle[process][
                        "output"
                    ].keys():
                        if (
                            type(
                                self.workflowObject.workflowData.process_bundle[
                                    process
                                ]["input"]
                            )
                            is dict
                            and ids
                            in self.workflowObject.workflowData.process_bundle[process][
                                "input"
                            ].keys()
                        ):
                            print(
                                "Copy "
                                + ids
                                + " from output to input for "
                                + process
                                + " for next time slice"
                            )
                            self.workflowObject.workflowData.process_bundle[process][
                                "input"
                            ][ids] = self.workflowObject.workflowData.process_bundle[
                                process
                            ][
                                "output"
                            ][
                                ids
                            ]

    def getIDSSlices(
        self,
        timenow,
        ids_scenario_list,
        inputDb,
        common_bundle,
    ):
        idsSlices = {}
        for ids in ids_scenario_list:
            print("  Get", ids, file=sys.stdout)
            try:
                common_bundle[ids] = inputDb.get_slice(ids, timenow, 1)
                idsSlices[ids] = inputDb.get_slice(ids, timenow, 1)
                # if common_bundle[ids] == 'equilibrium': # when equilibrium misses phi(r,z)
                #  if len(common_bundle[ids].time_slice[0].profiles_2d[0].phi)==0:
                #    print('   --- Interpolate missing phi(R,Z) ---')
                #    r1d_eq   = common_bundle[ids].time_slice[0].profiles_2d[0].grid.dim1
                #    z1d_eq   = common_bundle[ids].time_slice[0].profiles_2d[0].grid.dim2
                #    rho1d_eq = common_bundle[ids].time_slice[0].profiles_1d.rho_tor_norm
                #    psi1d_eq = common_bundle[ids].time_slice[0].profiles_1d.psi
                #    psi2d_eq = common_bundle[ids].time_slice[0].profiles_2d[0].psi
                #    rho_from_psi = interpolate.interp1d(psi1d_eq,rho1d_eq,kind='linear')
                #    phi2d_eq = np.zeros(np.shape(psi2d_eq))
                #    for ir in range(len(r1d_eq)):
                #      for iz in range(len(z1d_eq)):
                #        try: # Inside LCFS
                #          phi2d_eq[ir,iz] = rho_from_psi(psi2d_eq[ir,iz])
                #        except: # Outside LCFS
                #          phi2d_eq[ir,iz] = 1.
                #    common_bundle[ids].time_slice[0].profiles_2d[0].phi = phi2d_eq
            except:
                print("  ERROR while reading the " + ids + " IDS:", file=sys.stderr)
                print(
                    "  ----> Check the version of the Data Dictionary between the"
                    + " input and the loaded IMAS version.",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return

        # READ ALL MACHINE DESCRITPTION IDSS FOR THE CURRENT TIME SLICE
        for ids in self.inputMds:
            print("  Get", ids, file=sys.stdout)
            try:
                idsSlices[ids] = self.md.get_slice(ids, timenow, 1)
            except:
                print("  ERROR while reading the " + ids + " IDS:", file=sys.stderr)
                print(
                    "  ----> Check the version of the Data Dictionary between the"
                    + " input and the loaded IMAS version.",
                    file=sys.stderr,
                )
                print("  ----> Aborted.", file=sys.stderr)
                return
        return idsSlices
        # ---------------------------------------------------------------------
        # FIND OUT WHETHER EACH PROCESS IS ACTIVATED OR NOT FOR THIS TIME SLICE
        # ---------------------------------------------------------------------
        # time_base = self.workflowData.getTimeBase()

        # for process in self.workflowData.process_bundle.keys():
        #     if time_base is not None:
        #         if process in time_base:
        #             [tc, it] = find_nearest(
        #                 np.array(
        #                     time_base[process][0]["wf_interval"][0]["time_array"][0]
        #                 ),
        #                 timenow,
        #             )
        #             self.workflowData.process_bundle[process]["status"] = time_base[
        #                 process
        #             ][0]["wf_interval"][0]["status"][0][it]
        #         else:
        #             self.workflowData.process_bundle[process]["status"] = 1
        #     else:
        #         self.workflowData.process_bundle[process]["status"] = 1

    def setIDSes(self, idsSlices, mdIdsSlices, timenow):
        for idsName, idsData in idsSlices.items():
            print("  Loading slice", idsName, file=sys.stdout)
            for process in self.workflowObject.workflowData.process_bundle.keys():
                if (
                    "merge_" not in process
                    and idsName
                    in self.workflowObject.workflowData.process_bundle[process][
                        "input"
                    ].keys()
                ):
                    self.workflowObject.workflowData.process_bundle[process]["input"][
                        idsName
                    ] = idsData

        # READ ALL MACHINE DESCRITPTION IDSS FOR THE CURRENT TIME SLICE
        for idsName, idsData in mdIdsSlices.items():
            print("  Get", idsName, file=sys.stdout)
            for process in self.workflowObject.workflowData.process_bundle.keys():
                if (
                    idsName
                    in self.workflowObject.workflowData.process_bundle[process][
                        "input"
                    ].keys()
                ):
                    self.workflowObject.workflowData.process_bundle[process]["input"][
                        idsName
                    ] = idsData

        # ---------------------------------------------------------------------
        # FIND OUT WHETHER EACH PROCESS IS ACTIVATED OR NOT FOR THIS TIME SLICE
        # ---------------------------------------------------------------------
        time_base = self.workflowObject.workflowData.getTimeBase()

        for process in self.workflowObject.workflowData.process_bundle.keys():
            if time_base is not None:
                if process in time_base:
                    [tc, it] = find_nearest(
                        np.array(
                            time_base[process][0]["wf_interval"][0]["time_array"][0]
                        ),
                        timenow,
                    )
                    self.workflowObject.workflowData.process_bundle[process][
                        "status"
                    ] = time_base[process][0]["wf_interval"][0]["status"][0][it]
                else:
                    self.workflowObject.workflowData.process_bundle[process][
                        "status"
                    ] = 1
            else:
                self.workflowObject.workflowData.process_bundle[process]["status"] = 1

    def storeIDSOutput(self, common_bundle, process_bundle, outputDb):
        # ------------------------------
        # COMMON BUNDLE TO SAVE TO DISK
        # ------------------------------
        for ids in common_bundle.keys():
            if common_bundle[ids].ids_properties.homogeneous_time >= 0:
                outputDb.put_slice(common_bundle[ids])

        # ------------------------------
        # OUTPUT BUNDLE TO SAVE TO DISK
        # ------------------------------
        process_bundle_out = {}

        # TAKE THE MERGER OUTPUT IDS IF THERE IS ANY
        for process in process_bundle.keys():
            if "merge_" in process:
                key, value = list(process_bundle[process]["output"].items())[0]
                process_bundle_out[key] = value

        # TAKE ALL OTHER OUTPUT IDS BUT ONLY IF IT WAS NOT A MERGER OUTPUT ALREADY
        for process in process_bundle.keys():
            for key, value in process_bundle[process]["output"].items():
                if key not in process_bundle_out.keys():
                    process_bundle_out[key] = value

        # SAVE TO DISK
        for ids in process_bundle_out.keys():
            if (
                len(process_bundle_out[ids].time) > 0
            ):  # Empty if process deactivated by an is_xx_on function
                if (
                    process_bundle_out[ids].time[0] > 0
                    or "merge" in process_bundle_out[ids].code.name
                ):
                    outputDb.put_slice(process_bundle_out[ids])

        return process_bundle_out

    def getIDSes(self):
        # ------------------------------
        # COMMON BUNDLE TO SAVE TO DISK
        # ------------------------------
        idsOut = {}

        # TAKE THE MERGER OUTPUT IDS IF THERE IS ANY
        for process in self.workflowObject.workflowData.process_bundle.keys():
            if "merge_" in process:
                key, value = list(
                    self.workflowObject.workflowData.process_bundle[process][
                        "output"
                    ].items()
                )[0]
                idsOut[key] = value

        # TAKE ALL OTHER OUTPUT IDS BUT ONLY IF IT WAS NOT A MERGER OUTPUT ALREADY
        for process in self.workflowObject.workflowData.process_bundle.keys():
            for key, value in self.workflowObject.workflowData.process_bundle[process][
                "output"
            ].items():
                if key not in idsOut.keys():
                    idsOut[key] = value

        return idsOut
