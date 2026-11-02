"""Equilibrium extension outside the LCFS for the H&CD actors, applied by HCDWorkflow.run().

The extension itself is workflow/extend_equilibrium.py (matched scheme). This module decides, per
time slice, whether the input equilibrium is extended, and gives the actors an extended copy while
the caller's equilibrium object stays unchanged.

Setting: workflow parameter ``eq_extension`` of input_workflow.xml (``extend_equilibrium`` is read
when ``eq_extension`` is absent), or the ``eq_extension`` keyword of HCDWorkflow.run(). Values
(case-insensitive, surrounding whitespace ignored):

* ``auto`` (default when no setting is given; also ``1`` and ``matched``): a slice is extended when
  extend_equilibrium.needs_extension() says so: more than half of the original grid nodes clearly
  outside the LCFS have psi clamped to psi_boundary, or no grid node is clearly outside the LCFS;
  otherwise, e.g. for a free-boundary equilibrium whose psi varies outside the LCFS, the slice is
  left unchanged.
* ``forced``: every slice is extended.
* ``disabled`` (also ``0`` and ``none``): no slice is extended.

The box covered by the extended grid is the workflow parameter ``extend_equilibrium_box``
("Rmin,Rmax,Zmin,Zmax" in m, or the ``eq_extension_box`` keyword of HCDWorkflow.run()); when absent,
DEFAULT_BOX of extend_equilibrium.py.
"""

import copy

MODES = ("auto", "forced", "disabled")
DEFAULT_MODE = "auto"
# Values of the eq_extension / extend_equilibrium settings that select one of MODES
ALIASES = {"1": "auto", "matched": "auto", "0": "disabled", "none": "disabled"}
# Workflow parameters holding the setting, in order of precedence
SETTING_KEYS = ("eq_extension", "extend_equilibrium")


def parse_mode(value):
    """One of MODES from a setting value (MODES or ALIASES, case-insensitive); None -> DEFAULT_MODE."""
    if value is None:
        return DEFAULT_MODE
    text = str(value).strip().lower()
    if text in MODES:
        return text
    if text in ALIASES:
        return ALIASES[text]
    accepted = ", ".join(MODES + tuple(ALIASES))
    raise ValueError(f"equilibrium extension setting {value!r}: accepted values are {accepted}")


def mode_from_parameters(parameters):
    """(mode, description) from the workflow parameters: the first of SETTING_KEYS present, else
    DEFAULT_MODE. description names the key and value used."""
    for key in SETTING_KEYS:
        if key in parameters:
            return parse_mode(parameters[key]), f"{key} = {parameters[key]!r}"
    return DEFAULT_MODE, f"default ({' and '.join(SETTING_KEYS)} absent)"


def parse_box(value):
    """[Rmin, Rmax, Zmin, Zmax] from "Rmin,Rmax,Zmin,Zmax" (or a sequence); None -> DEFAULT_BOX."""
    if value is None:
        from workflow.extend_equilibrium import DEFAULT_BOX

        return list(DEFAULT_BOX)
    items = value.split(",") if isinstance(value, str) else value
    box = [float(x) for x in items]
    if len(box) != 4:
        raise ValueError(f"extend_equilibrium_box = {value!r}: expected Rmin,Rmax,Zmin,Zmax")
    return box


def _slice_time(equilibrium, k, ts):
    if hasattr(ts.time, "has_value") and ts.time.has_value:
        return float(ts.time)
    return float(equilibrium.time[k]) if len(equilibrium.time) > k else float("nan")


def prepare_equilibrium(equilibrium, mode=DEFAULT_MODE, box=None, source=""):
    """Equilibrium for the actors: equilibrium itself when no slice is extended, else a deep copy with
    the selected slices extended (extend_equilibrium.extend_slice) and the caveat appended to
    ids_properties.comment. Prints exactly one line per time slice with the decision and its reason."""
    mode = parse_mode(mode)
    decisions = []
    if mode == "disabled":
        decisions = [(k, False, "disabled") for k in range(len(equilibrium.time_slice))]
    else:
        import imas

        # The generated IMAS-AL API has neither has_value nor convert_ids (same test as
        # workflow.ids_prep._smart_convert); the extension needs IMAS-Python IDSs.
        if not hasattr(imas, "IDSFactory"):
            if mode == "forced":
                raise RuntimeError("equilibrium extension forced: needs an IMAS-Python equilibrium IDS")
            decisions = [(k, False, "auto: not an IMAS-Python IDS") for k in range(len(equilibrium.time_slice))]
        else:
            from workflow.extend_equilibrium import needs_extension

            for k, ts in enumerate(equilibrium.time_slice):
                if mode == "forced":
                    decisions.append((k, True, "forced"))
                else:
                    extend, reason = needs_extension(ts)
                    decisions.append((k, extend, f"auto: {reason}" if extend else f"auto: {reason}, not needed"))

    result = equilibrium
    if any(extend for _, extend, _ in decisions):
        from workflow.extend_equilibrium import append_caveat, extend_slice, format_info

        box = parse_box(box)
        result = copy.deepcopy(equilibrium)
    for k, extend, reason in decisions:
        t = _slice_time(equilibrium, k, equilibrium.time_slice[k])
        if extend:
            info, _ = extend_slice(result.time_slice[k], box)
            info["t"] = t
            print(f"[equilibrium] t={t:.4f}s extension: applied ({reason}): {format_info(info)}", flush=True)
        else:
            print(f"[equilibrium] t={t:.4f}s extension: not applied ({reason})", flush=True)
    if result is not equilibrium:
        append_caveat(result, source=source)
    return result
