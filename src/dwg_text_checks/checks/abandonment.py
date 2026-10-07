"""CHK-004 -- are the start and end of each pipe to be abandoned labelled?

The answer usually looks like a pair of leaders::

    START POINT OF THE PW450 TO BE ABANDONED
    END POINT OF THE PW450 TO BE ABANDONED

FOUND needs one START label and one END label naming the pipe, shown in a plan
view. A single label naming both ends marks one point at most, so it counts for
neither and the result is CANNOT_DETERMINE. Whether each label points at the
true end of the abandoned stretch is geometry, not text, and is not tested.
Other abandonment text (``EXISTING DN150 WATER PIPE (ABANDONED)``) is listed,
not judged.
"""

from __future__ import annotations

import re

from .base import Evidence, Location, Result, Verdict

CHECK_ID = "CHK-004"
TITLE = "Start and end of the pipe to be abandoned labelled (plan view)"

_ABANDON = re.compile(r"\bABANDON", re.I)
_START = re.compile(r"\bSTART\b", re.I)
_END = re.compile(r"\bEND\b", re.I)


def judge(labels, scope, where=lambda x, y, layer: []) -> list[Result]:
    """One result per pipe in the scope. ``labels`` are those a plan view
    shows; ``where(x, y, layer)`` names the views that draw a point."""
    abandon = [l for l in labels if _ABANDON.search(l.flat)]
    claimed: set[int] = set()
    results = []
    for pipe in scope.abandoned:
        pattern = re.compile(pipe.match, re.I)
        named = [l for l in abandon if pattern.search(l.flat)]
        claimed.update(id(l) for l in named)
        starts = [l for l in named if _START.search(l.flat) and not _END.search(l.flat)]
        ends = [l for l in named if _END.search(l.flat) and not _START.search(l.flat)]
        both = [l for l in named if _START.search(l.flat) and _END.search(l.flat)]

        result = Result(CHECK_ID, TITLE, Verdict.NOT_FOUND,
                        subject=pipe.name + (" (" + pipe.note + ")" if pipe.note else ""))
        for kind, found in (("start", starts), ("end", ends), ("both ends", both)):
            for l in found:
                result.evidence.append(Evidence(kind, l.flat, l.layer))
                result.locations.append(Location(kind + ": " + l.flat, *l.point,
                                                 where(*l.point, l.layer)))
        missing = [k for k, f in (("start", starts), ("end", ends)) if not f]
        if not missing:
            result.verdict = Verdict.FOUND
            result.summary = ("Found: a start label and an end label for the "
                              + pipe.name + " to be abandoned.")
        elif both:
            result.verdict = Verdict.CANNOT_DETERMINE
            result.summary = ("One label names both ends of the " + pipe.name
                              + " to be abandoned; it marks one point at most.")
        else:
            result.summary = ("Not found: no " + " or ".join(missing) + " label for the "
                              + pipe.name + " to be abandoned.")
        result.limitations.append(
            "Presence only: does not check that each label points at the true end "
            "of the abandoned stretch.")
        results.append(result)

    others = [l for l in abandon if id(l) not in claimed]
    if others and results:
        results[-1].evidence.append(Evidence(
            "other abandonment text in plan, not judged", len(others),
            "; ".join(sorted({l.flat for l in others}))[:300]))
    return results
