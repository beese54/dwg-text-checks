"""What the checks are asked to look for, read from a small JSON file.

A review comment names pipes, not entities: "indicate the chainage along the
diverted pipeline", "indicate the start and end of the PW450 to be abandoned".
Which run letter is "the diverted pipeline", and which pipes were to be
abandoned, is a reviewer's reading of the comments. So it is written down
rather than inferred from the drawing -- a pipe the drawing leaves out
entirely would otherwise never be missed.

See ``examples/scope.example.json``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Pipe:
    """A pipe whose start and end must be labelled as abandoned."""

    name: str
    #: Regex that finds this pipe in a label; defaults to its first word.
    match: str
    note: str = ""


@dataclass
class Scope:
    source: str = ""
    interval_m: float = 10.0
    #: run letter -> what it is ("PW600 main (comment 1)").
    chainage_runs: dict[str, str] = field(default_factory=dict)
    coordinate_runs: dict[str, str] = field(default_factory=dict)
    abandoned: list[Pipe] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "Scope":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scope":
        def runs(section: str) -> dict[str, str]:
            return {k.upper(): str(v) for k, v in
                    ((data.get(section) or {}).get("runs") or {}).items()}

        pipes = []
        for item in data.get("abandonment") or []:
            name = str(item["pipe"])
            pipes.append(Pipe(name, item.get("match")
                              or r"\b" + re.escape(name.split()[0]) + r"\b",
                              str(item.get("note") or item.get("comment") or "")))
        return cls(source=str(data.get("source") or ""),
                   interval_m=float((data.get("chainage") or {}).get("interval_m") or 10.0),
                   chainage_runs=runs("chainage"),
                   coordinate_runs=runs("coordinates"),
                   abandoned=pipes)
