"""Text-based rule checks: CHK-001 chainage, CHK-004 abandoned-pipe ends,
CHK-005 N/E coordinates. ``run`` does all three."""

from __future__ import annotations

from . import abandonment, chainage, coordinates
from .base import Evidence, Location, Result, Verdict
from .scope import Pipe, Scope

__all__ = ["run", "Evidence", "Location", "Result", "Verdict", "Pipe", "Scope"]


def run(labels, in_plan, scope: Scope, where=lambda x, y, layer: []) -> list[Result]:
    """All three checks.

    ``labels`` -- ``text.PlacedText`` the issued layout's sheets show (visible
    ones). ``in_plan(x, y)`` -- does a plan view draw this point.
    ``where(x, y, layer)`` -- names of the views that draw it, for locations.
    """
    runs = chainage.gather(labels, in_plan)
    plan_labels = [l for l in labels if in_plan(l.x, l.y)]
    results: list[Result] = []
    for key in sorted(scope.chainage_runs):
        note = scope.chainage_runs[key]
        if key in runs:
            result = chainage.judge(runs[key], scope.interval_m, note)
            for station, (x, y) in sorted(runs[key].where.items()):
                result.locations.append(Location("CH " + format(station, ".3f"), x, y,
                                                 where(x, y, None)))
        else:
            result = Result(chainage.CHECK_ID, "Chainage shown along the run",
                            Verdict.NOT_FOUND, subject="run " + key + " -- " + note,
                            summary="Not found: no label names run " + key + " (CH."
                                    + key + " ...) in a plan view.")
        results.append(result)
    others = sorted(set(runs) - set(scope.chainage_runs))
    if others:
        results.append(Result(chainage.CHECK_ID, "Chainage shown along the run",
                              Verdict.NOT_APPLICABLE, subject="runs " + ", ".join(others),
                              summary="Not in the scope file."))
    results += abandonment.judge(plan_labels, scope, where)
    results += coordinates.judge(plan_labels, runs, scope, where)
    return results
