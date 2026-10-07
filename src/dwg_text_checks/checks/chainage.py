"""CHK-001 -- is chainage marked at every interval point along a run?

Chainage labels name their run: ``CH.C 15.510`` is 15.510 m along run C.
The check asks for a marker at every interval point (CH 0, 10, 20 ... to the
last chainage shown) in a plan view.

**A marker need not name its run.** Drawings often mark interval points with
``CH. 10.000`` and no run letter, while the fitting callouts say
``CH.C 15.510``. A reader that only knows the lettered form reports those
markers as missing. A letterless marker is given to the run whose lettered
labels put that station nearest to it, and only when no other run comes close;
otherwise the point is CANNOT_DETERMINE, never FOUND. Station alone cannot
decide it: where a branch leaves a main at the main's CH 60, the branch's
``CH. 0.000`` and the main's ``CH. 60.000`` sit a metre or two apart.

**A lettered label can be wrong.** A station written against the wrong run
puts a point tens of metres away from where its station says it should be.
Such a label is set aside when placing markers (see ``_clean_refs``) and
reported, because it is usually a drafting error worth telling someone about.

Labels are positioned at a leader's arrow tip where there is one: that is on
the pipe, while the words sit off to one side.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from ..text import flatten
from .base import Evidence, Result, Verdict

CHECK_ID = "CHK-001"

#: ``CH.C 41.430``: a station on a named run.
_CHAINAGE = re.compile(r"\bCH[.\s]\s*([A-Z])\s+(\d+(?:\.\d+)?)", re.I)
#: ``CH. 10.000`` as the whole label: a marker that does not name its run. The
#: whole label, so a note such as ``KERB FROM CH 120 - CH 150`` -- somebody
#: else's chainage -- is never read as one.
_MARKER = re.compile(r"^\s*CH\.?\s*(\d+(?:\.\d+)?)\s*$", re.I)

#: A label counts as the marker for an interval point only if it says that
#: value to the written millimetre: CH 49.987 is a fitting, not the CH 50 marker.
MARKER_TOLERANCE_M = 0.0005
#: Slack on "a straight line is never longer than the pipe between two
#: stations". Text set beside the pipe moves a position by a few metres; a
#: station written against the wrong run moves it by tens.
CHORD_SLACK_M = 5.0
#: A letterless marker goes to a run only if that run puts its station within
#: this distance, and the next-best run is at least ASSIGN_MARGIN_M further.
ASSIGN_RADIUS_M = 6.0
ASSIGN_MARGIN_M = 3.0


def stations(text: str) -> list[tuple[str, float]]:
    """``[(run, station)]`` named in a label."""
    return [(m.group(1).upper(), float(m.group(2)))
            for m in _CHAINAGE.finditer(flatten(text))]


def marker(text: str) -> float | None:
    """The station of a letterless marker label, or None."""
    m = _MARKER.match(flatten(text))
    return float(m.group(1)) if m else None


@dataclass
class Run:
    """What the drawing says about one chainage run."""

    run: str
    #: Stations shown in a plan view.
    in_plan: list[float] = field(default_factory=list)
    #: Where each station shown in plan is written: station -> (x, y).
    where: dict[float, tuple[float, float]] = field(default_factory=dict)
    #: Lettered labels as (station, x, y) at the point they mark.
    refs: list[tuple[float, float, float]] = field(default_factory=list)
    #: Lettered labels set aside: (station, x, y, why).
    doubtful: list[tuple[float, float, float, str]] = field(default_factory=list)
    #: Letterless markers in plan that could be this run's or another's.
    unplaced: list[tuple[float, float, float]] = field(default_factory=list)
    markers_assigned: int = 0
    clean: list[tuple[float, float, float]] | None = None

    @property
    def span(self) -> tuple[float, float] | None:
        return (self.in_plan[0], self.in_plan[-1]) if self.in_plan else None


def clean_refs(entry: Run) -> list[tuple[float, float, float]]:
    """The run's labelled stations, less any that contradict their neighbours.

    Between two stations the pipe is at least as long as the straight line. A
    label further from both its station neighbours than the pipe between them
    could run, while those two agree with each other, is the one in error.
    Only neighbours are asked: against a station far along the run almost any
    position is possible, so a count over the whole run lets errors through.
    """
    if entry.clean is not None:
        return entry.clean
    refs = sorted(set(entry.refs))

    def excess(a, b) -> float:
        return math.hypot(a[1] - b[1], a[2] - b[2]) - abs(a[0] - b[0]) - CHORD_SLACK_M

    def neighbours(i: int) -> tuple[int, int]:
        if i == 0:
            return 1, 2
        if i == len(refs) - 1:
            return i - 1, i - 2
        return i - 1, i + 1

    while len(refs) > 2:
        suspects = []
        for i, ref in enumerate(refs):
            a, b = neighbours(i)
            if (excess(ref, refs[a]) > 0 and excess(ref, refs[b]) > 0
                    and excess(refs[a], refs[b]) <= 0):
                suspects.append((min(excess(ref, refs[a]), excess(ref, refs[b])), i))
        if not suspects:
            break
        bad = refs.pop(max(suspects)[1])
        nearest = min(refs, key=lambda o: abs(o[0] - bad[0]))
        entry.doubtful.append((bad[0], bad[1], bad[2], (
            "written as CH." + entry.run + " " + format(bad[0], ".3f") + ", but it is "
            + format(math.hypot(bad[1] - nearest[1], bad[2] - nearest[2]), ".1f")
            + " m from CH." + entry.run + " " + format(nearest[0], ".3f")
            + " -- further than the pipe between them can run")))
    entry.clean = refs
    return refs


def _expected(refs, station: float) -> tuple[float, float] | None:
    """Where ``station`` should be along a run, by its labelled stations."""
    if not refs or station < refs[0][0] - 1.0 or station > refs[-1][0] + 1.0:
        return None
    for a, b in zip(refs, refs[1:]):
        if a[0] <= station <= b[0]:
            if b[0] == a[0]:
                return a[1], a[2]
            f = (station - a[0]) / (b[0] - a[0])
            return a[1] + f * (b[1] - a[1]), a[2] + f * (b[2] - a[2])
    end = refs[0] if station < refs[0][0] else refs[-1]
    return end[1], end[2]


def gather(labels, in_plan) -> dict[str, Run]:
    """Sort chainage labels into runs.

    ``labels`` are ``text.PlacedText``; ``in_plan(x, y)`` says whether a plan
    view of the issued layout draws a point.
    """
    runs: dict[str, Run] = {}
    markers: list[tuple[float, float, float]] = []
    for label in labels:
        found = stations(label.text)
        if not found:
            station = marker(label.text)
            if station is not None:
                markers.append((station, label.x, label.y))
            continue
        shown = in_plan(label.x, label.y)
        px, py = label.point
        for run, station in found:
            entry = runs.setdefault(run, Run(run))
            if shown:
                # Plan positions only: a section is drawn elsewhere in model
                # space, and its labels would bend the line markers are placed on.
                entry.refs.append((station, px, py))
                entry.in_plan.append(station)
                entry.where.setdefault(station, (label.x, label.y))

    clean = {key: clean_refs(entry) for key, entry in runs.items()}
    for station, x, y in markers:
        if not in_plan(x, y):
            continue
        fits = sorted((math.hypot(w[0] - x, w[1] - y), key)
                      for key, refs in clean.items()
                      if (w := _expected(refs, station)) is not None)
        if (fits and fits[0][0] <= ASSIGN_RADIUS_M
                and (len(fits) == 1 or fits[1][0] - fits[0][0] >= ASSIGN_MARGIN_M)):
            entry = runs[fits[0][1]]
            entry.in_plan.append(station)
            entry.where.setdefault(station, (x, y))
            entry.markers_assigned += 1
        else:
            for distance, key in fits:
                if distance <= ASSIGN_RADIUS_M:
                    runs[key].unplaced.append((station, x, y))
    for entry in runs.values():
        entry.in_plan = sorted(set(entry.in_plan))
    return runs


def interval_points(entry: Run, interval_m: float) -> list[float]:
    """Multiples of the interval across the stations shown in plan."""
    if entry.span is None:
        return []
    points, p = [], -(-entry.span[0] // interval_m) * interval_m
    while p <= entry.span[1] + 1e-9:
        points.append(round(p, 6))
        p += interval_m
    return points


def judge(entry: Run, interval_m: float = 10.0, note: str = "") -> Result:
    """FOUND if every interval point shown in plan carries a marker."""
    result = Result(
        check_id=CHECK_ID,
        title="Chainage shown every " + format(interval_m, "g") + " m along the run (plan view)",
        subject="run " + entry.run + (" -- " + note if note else ""),
        verdict=Verdict.CANNOT_DETERMINE)
    if len(entry.in_plan) < 2:
        result.summary = ("A plan view shows fewer than two chainage values for "
                          "run " + entry.run + ", so there is no extent to check.")
        return result

    def near(values):
        return lambda p: any(abs(v - p) <= MARKER_TOLERANCE_M for v in values)

    points = interval_points(entry, interval_m)
    marked, maybe = near(entry.in_plan), near([u[0] for u in entry.unplaced])
    missing = [p for p in points if not marked(p) and not maybe(p)]
    unresolved = [p for p in points if not marked(p) and maybe(p)]
    span = "CH " + format(entry.span[0], ".3f") + " to " + format(entry.span[1], ".3f")

    result.evidence.append(Evidence("interval points", len(points),
                                    span + ", every " + format(interval_m, "g") + " m"))
    result.evidence.append(Evidence("chainages labelled in plan",
                                    ", ".join(format(s, ".3f") for s in entry.in_plan)))
    if entry.markers_assigned:
        result.evidence.append(Evidence(
            "markers that do not name their run", entry.markers_assigned,
            "given to run " + entry.run + " by where they sit along it"))
    for station, _x, _y, why in entry.doubtful:
        result.evidence.append(Evidence("label whose station and position disagree",
                                        "CH." + entry.run + " " + format(station, ".3f"), why))
    if unresolved:
        result.evidence.append(Evidence(
            "a marker that may be this run's or another's",
            ", ".join("CH " + format(p, ".3f") for p in unresolved)))

    if missing:
        result.verdict = Verdict.NOT_FOUND
        result.summary = ("Not found at " + str(len(missing)) + " of " + str(len(points))
                          + " points from " + span + ": "
                          + ", ".join("CH " + format(p, ".3f") for p in missing[:8])
                          + (" ..." if len(missing) > 8 else "") + ".")
    elif unresolved:
        result.summary = ("Every point has a marker except "
                          + ", ".join("CH " + format(p, ".3f") for p in unresolved)
                          + ", where a marker that does not name its run could be "
                            "this run's or another's.")
    else:
        result.verdict = Verdict.FOUND
        result.summary = ("Found: a chainage marker at every " + format(interval_m, "g")
                          + " m point from " + span + " (" + str(len(points)) + " points).")
    result.limitations.append(
        "Reads chainage text only. It does not check that a marker sits at the "
        "right place along the pipe, except to decide which run an unnamed marker "
        "belongs to.")
    return result
