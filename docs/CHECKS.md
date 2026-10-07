# The checks

All three read text only, from the plan views of the issued layout, and say
**FOUND / NOT FOUND / CANNOT DETERMINE / NOT APPLICABLE**. What they ask about
comes from a scope file.

## Scope file

```json
{
 "source": "Review comments on drawing XYZ-001 Rev 1",
 "chainage":    {"interval_m": 10, "runs": {"C": "main pipeline (comment 1)"}},
 "coordinates": {"runs": {"C": "main pipeline (comment 3)"}},
 "abandonment": [{"pipe": "PW450", "note": "comment 2"},
                 {"pipe": "PW150 offtake", "match": "\\bPW150\\b"}]
}
```

- `runs` maps a run letter -- the `C` in `CH.C 15.510` -- to what it is.
- `abandonment[].match` is a regex for the pipe in a label; default is the
  pipe's first word as a whole word (`\bPW450\b`).

## CHK-001 -- chainage every N metres

**FOUND** when every multiple of the interval between the first and last
chainage shown in plan (CH 0, 10, 20 ...) has a label with exactly that value
(to the millimetre: `CH 49.987` is a fitting, not the CH 50 marker).

What counts as a chainage label:

| Text | Read as |
|---|---|
| `CH.C 15.510`, `CH C 15.510` | run C, 15.510 |
| `CH. 10.000` (the whole label) | a marker; its run is worked out, below |
| `KERB FROM CH 120 - CH 150` | nothing -- not a whole-label marker, no run letter |

**Markers with no run letter** go to the run whose lettered labels put that
station nearest the marker (interpolating between the leader tips of its
lettered labels), if within 6 m and at least 3 m nearer than any other run.
Otherwise that interval point is **CANNOT DETERMINE**.

**Contradictory labels** -- a lettered label further from both station
neighbours than the pipe between them could run, while those neighbours agree
-- are set aside for placing markers and reported as evidence. In practice
this is a station written against the wrong run.

## CHK-004 -- start and end of the pipe to be abandoned

For each pipe in the scope, **FOUND** when a plan view shows a label containing
`ABANDON`, the pipe's match, and `START` (not `END`), and another with `END`
(not `START`). One label naming both ends is **CANNOT DETERMINE**. Other
abandonment text is listed as evidence, not judged. Position is not checked.

## CHK-005 -- N/E at connection points and bends

Every label in plan matching `CONNECTION POINT` or `...BEND` (and either
carrying a chainage or at most 60 characters long, so notes about bends are
skipped) is given to a run -- by its `CH.<run>` or, failing that, by its leader
tip lying within 3 m of one run's line. **FOUND** when every such label for a
scoped run has both `N<digits>` and `E<digits>` (4+ digits; `DN600` is not a
northing). The same label in two views counts once. No labels for the run:
**CANNOT DETERMINE**. Values are listed, not verified.
