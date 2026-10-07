"""CHK-005 -- do connection point and bend labels give north/east coordinates?

The answer usually sits in the fitting's own callout::

    PROP. DN600mm 45° H-BEND - 1
    CH.C      1.550
    N12345.678
    E23456.789

Every connection point and bend label a plan view shows is given to a run --
by the run letter of its chainage, or failing that by where its leader lands
-- and must carry both an N and an E value. NOT_FOUND names the labels without.

What it cannot see: a bend drawn with no label at all. Values are listed, not
checked against where the fitting is drawn.
"""

from __future__ import annotations

import math
import re

from . import chainage
from .base import Evidence, Location, Result, Verdict

CHECK_ID = "CHK-005"
TITLE = "North/east coordinates at every connection point and bend (plan view)"

#: A connection point or a bend. ``CBEND`` occurs: ``45%%DCBEND``.
_FEATURE = re.compile(r"CONNECTION\s+POINT|BEND\b", re.I)
#: Notes mention bends too. A fitting label is short or carries a chainage.
_MAX_UNSTATIONED_LENGTH = 60
#: N / E followed by a number of four or more digits. The look-behind stops
#: ``DN600`` reading as N 800.
_NORTH = re.compile(r"(?<![A-Z0-9])N(?:ORTHING)?\s*[:=]?\s*(\d{4,}(?:\.\d+)?)", re.I)
_EAST = re.compile(r"(?<![A-Z0-9])E(?:ASTING)?\s*[:=]?\s*(\d{4,}(?:\.\d+)?)", re.I)
#: An unstationed label goes to a run whose labelled line its leader lands
#: within this distance of.
NEAR_RUN_M = 3.0


def _distance_to(refs, x: float, y: float) -> float:
    if not refs:
        return math.inf
    if len(refs) == 1:
        return math.hypot(refs[0][1] - x, refs[0][2] - y)
    best = math.inf
    for (_, ax, ay), (_, bx, by) in zip(refs, refs[1:]):
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        f = 0.0 if length == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length))
        best = min(best, math.hypot(ax + f * dx - x, ay + f * dy - y))
    return best


def _run_of(label, runs) -> str | None:
    found = chainage.stations(label.text)
    if found:
        return found[0][0]
    if label.tip is None:
        return None
    near = sorted((_distance_to(chainage.clean_refs(e), *label.tip), k)
                  for k, e in runs.items())
    if near and near[0][0] <= NEAR_RUN_M and (len(near) == 1 or near[1][0] > NEAR_RUN_M):
        return near[0][1]
    return None


def _name(flat: str) -> str:
    head = re.split(r"\bCH\.", flat, maxsplit=1)[0].strip(" -") or flat
    found = chainage.stations(flat)
    return head + (" (CH." + found[0][0] + " " + format(found[0][1], ".3f") + ")"
                   if found else "")


def judge(labels, runs, scope, where=lambda x, y, layer: []) -> list[Result]:
    """One result per run in the scope. ``labels`` are those a plan view
    shows; ``runs`` is ``chainage.gather`` over the same drawing."""
    by_run: dict[str, dict] = {}
    unattributed: set[str] = set()
    for label in labels:
        flat = label.flat
        if not _FEATURE.search(flat):
            continue
        if not chainage.stations(label.text) and len(flat) > _MAX_UNSTATIONED_LENGTH:
            continue
        run = _run_of(label, runs)
        if run is None:
            unattributed.add(flat)
            continue
        by_run.setdefault(run, {}).setdefault(flat, label)  # one label, many views

    def order(item):
        found = chainage.stations(item[0])
        return found[0][1] if found else math.inf

    results = []
    for key in sorted(scope.coordinate_runs):
        result = Result(CHECK_ID, TITLE, Verdict.CANNOT_DETERMINE,
                        subject="run " + key + " -- " + scope.coordinate_runs[key])
        features = by_run.get(key, {})
        lacking = []
        for flat, label in sorted(features.items(), key=order):
            north, east = _NORTH.search(flat), _EAST.search(flat)
            name = _name(flat)
            if north and east:
                result.evidence.append(Evidence(name, "N" + north.group(1) + " E" + east.group(1)))
                continue
            gone = " and ".join(w for w, m in (("N", north), ("E", east)) if not m)
            lacking.append(name)
            result.evidence.append(Evidence(name, "no " + gone, "not found"))
            result.locations.append(Location(name + " -- no " + gone, *label.point,
                                             where(*label.point, label.layer)))
        if unattributed:
            result.evidence.append(Evidence(
                "connection point or bend labels not given to any run",
                len(unattributed), "; ".join(sorted(unattributed))[:300]))
        if not features:
            result.summary = ("No connection point or bend label for run " + key
                              + " is shown in a plan view.")
        elif lacking:
            result.verdict = Verdict.NOT_FOUND
            result.summary = ("Not found on " + str(len(lacking)) + " of " + str(len(features))
                              + " labels: " + "; ".join(lacking[:6])
                              + (" ..." if len(lacking) > 6 else "") + ".")
        else:
            result.verdict = Verdict.FOUND
            result.summary = ("Found: all " + str(len(features)) + " connection point "
                              "and bend labels carry N and E coordinates.")
        result.limitations.append("Counts labelled connection points and bends; one "
                                  "drawn with no label is not seen.")
        result.limitations.append("Presence only: values are listed, not checked "
                                  "against where the fitting is drawn.")
        results.append(result)
    return results
