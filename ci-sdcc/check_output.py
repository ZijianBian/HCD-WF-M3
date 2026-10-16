#!/usr/bin/env python
"""Check the IDSs written by a workflow run.

Usage: check_output.py [--reference-dir DIR] [--update] [--rtol RTOL] <config_folder> <ids> [<ids> ...]

Each IDS must be written with at least one time slice. When --reference-dir is given, all numerical
values of the IDS (except ids_properties and code) are also compared with DIR/<ids>.json:
each array must match within RTOL relative to the largest absolute value of its reference.
With --update, the reference files are (re)written from this run instead.

To keep the references small enough for the repository, arrays with more than MAX_FULL_SIZE values
(e.g. ray tracing trajectories) are stored as a summary (shape, min, max, mean, rms) instead of in full.

The output entry is read from <config_folder>/input_workflow.xml, the same way the workflow opens it.
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np

import imas
from imas import ids_defs

SKIPPED = ("ids_properties", "code")
MAX_FULL_SIZE = 100
SUMMARY_KEYS = ("min", "max", "mean", "rms")


def summary(value):
    """Fingerprint of a large array: its shape and a few statistics"""
    return {
        "shape": list(value.shape),
        "min": float(np.min(value)),
        "max": float(np.max(value)),
        "mean": float(np.mean(value)),
        "rms": float(np.sqrt(np.mean(np.square(value, dtype=float)))),
    }


def workflow_parameters(config_folder):
    root = ET.parse(os.path.join(config_folder, "input_workflow.xml")).getroot()
    return {child.tag: (child.text or "").strip() for child in root.find("workflow_parameters")}


def open_output(config_folder):
    par = workflow_parameters(config_folder)
    user_or_path = os.getenv("USER") if par["output_user_or_path"] == "default" else par["output_user_or_path"]
    database = par["input_database"] if par["output_database"] == "default" else par["output_database"]
    backend = getattr(ids_defs, f"{par.get('output_backend', 'MDSPLUS')}_BACKEND")
    shot, run = int(par["shot_nr"]), int(par["run_out"])

    print(f"> Checking output {user_or_path} {database} shot={shot} run={run}")
    entry = imas.DBEntry(backend, database, shot, run, user_or_path)
    entry.open()
    return entry


def numerical_values(ids):
    """All filled numerical leaves of an IDS as {path with indices: list or summary}, e.g. coherent_wave[0]/..."""
    values = {}
    for node in imas.util.tree_iter(ids, leaf_only=True):
        path = str(node.metadata.path)
        if path.startswith(SKIPPED):
            continue
        value = np.asarray(node.value)
        if value.dtype.kind not in "if":
            continue
        # Index of each array of structures in the path, e.g. coherent_wave[0]/global_quantities[3]/power
        path = imas.util.get_full_path(node)
        values[path] = {"summary": summary(value)} if value.size > MAX_FULL_SIZE else value.tolist()
    return values


def compare_summary(path, value, reference, rtol):
    """Compare the summary of a large array, stored as {"summary": {...}}, with its reference"""
    if not (isinstance(value, dict) and isinstance(reference, dict)):
        print(f"    {path}: stored in full in one and as a summary in the other, regenerate the reference")
        return 1
    new, ref = value["summary"], reference["summary"]
    if new["shape"] != ref["shape"]:
        print(f"    {path}: shape {tuple(new['shape'])} differs from reference {tuple(ref['shape'])}")
        return 1
    scale = max(abs(ref["min"]), abs(ref["max"]))
    for key in SUMMARY_KEYS:
        if abs(new[key] - ref[key]) > rtol * scale:
            print(f"    {path}: {key} {new[key]:.6e} differs from reference {ref[key]:.6e} (> {rtol:g} x {scale:.3e})")
            return 1
    return 0


def compare(name, values, reference, rtol):
    failed = 0
    for path in sorted(set(reference) | set(values)):
        if path not in values:
            print(f"    {path}: MISSING in output")
            failed = 1
            continue
        if path not in reference:
            print(f"    {path}: NOT in reference")
            failed = 1
            continue
        if isinstance(reference[path], dict) or isinstance(values[path], dict):
            failed |= compare_summary(path, values[path], reference[path], rtol)
            continue
        new, ref = np.asarray(values[path], dtype=float), np.asarray(reference[path], dtype=float)
        if new.shape != ref.shape:
            print(f"    {path}: shape {new.shape} differs from reference {ref.shape}")
            failed = 1
            continue
        scale = np.max(np.abs(ref)) if ref.size else 0.0
        diff = np.max(np.abs(new - ref)) if ref.size else 0.0
        if diff > rtol * scale:
            print(f"    {path}: max difference {diff:.3e} > {rtol:g} x {scale:.3e}")
            failed = 1
    print(f"  {name}: values {'DIFFER from' if failed else 'match'} reference ({len(reference)} quantities)")
    return failed


def main():
    argp = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    argp.add_argument("config_folder")
    argp.add_argument("ids", nargs="+")
    argp.add_argument("--reference-dir", help="Directory with <ids>.json reference values")
    argp.add_argument("--update", action="store_true", help="Write the reference files from this run")
    argp.add_argument("--rtol", type=float, default=1e-6, help="Relative tolerance (default: %(default)g)")
    args = argp.parse_args()

    try:
        entry = open_output(args.config_folder)
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR: cannot open output entry ({exc})")
        return 1

    failed = 0
    for name in args.ids:
        try:
            ids = entry.get(name)
            written = ids.ids_properties.homogeneous_time != ids_defs.EMPTY_INT
            n_time = len(ids.time) if written else 0
        except Exception as exc:  # noqa: BLE001 - report any read error as a failed check
            print(f"  {name}: ERROR while reading ({exc})")
            failed = 1
            continue
        if n_time == 0:
            print(f"  {name}: EMPTY")
            failed = 1
            continue
        print(f"  {name}: OK ({n_time} time slices)")

        if not args.reference_dir:
            continue
        ref_file = os.path.join(args.reference_dir, f"{name}.json")
        values = numerical_values(ids)
        if args.update:
            os.makedirs(args.reference_dir, exist_ok=True)
            with open(ref_file, "w", encoding="utf-8") as stream:
                json.dump({"dd_version": ids._dd_version, "values": values}, stream, indent=1)
                stream.write("\n")
            print(f"  {name}: reference written to {ref_file} ({len(values)} quantities)")
        elif not os.path.isfile(ref_file):
            print(f"  {name}: no reference {ref_file}, values not checked")
        else:
            with open(ref_file, encoding="utf-8") as stream:
                failed |= compare(name, values, json.load(stream)["values"], args.rtol)
    entry.close()
    return failed


if __name__ == "__main__":
    sys.exit(main())
