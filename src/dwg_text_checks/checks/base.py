"""What every check returns."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    #: What the comment asked for is in the drawing's text.
    FOUND = "found"
    #: It is not. A NOT_FOUND always names what is missing.
    NOT_FOUND = "not_found"
    #: The text needed was absent or ambiguous. Never silently a FOUND.
    CANNOT_DETERMINE = "cannot_determine"
    #: The rule does not apply to this subject.
    NOT_APPLICABLE = "not_applicable"


# FOUND / NOT FOUND, not PASS / FAIL: these checks read text, and a text check
# is only as good as its reading of the wording. They say what was found; a
# person confirms whether the drawing complies.


@dataclass
class Evidence:
    """One fact behind a verdict, in the drawing's own terms."""

    label: str
    value: Any
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Location:
    """Where a label is: model coordinates and the views that draw it."""

    what: str
    x: float
    y: float
    views: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"what": self.what, "x": round(self.x, 3), "y": round(self.y, 3),
                "views": list(self.views)}


@dataclass
class Result:
    """The outcome of one check against one subject."""

    check_id: str
    title: str
    verdict: Verdict
    subject: str = ""
    summary: str = ""
    evidence: list[Evidence] = field(default_factory=list)
    #: What would make this verdict wrong.
    limitations: list[str] = field(default_factory=list)
    #: Where to look on the sheets.
    locations: list[Location] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"check_id": self.check_id, "title": self.title,
                "subject": self.subject, "verdict": self.verdict.value,
                "summary": self.summary,
                "evidence": [e.to_dict() for e in self.evidence],
                "limitations": list(self.limitations),
                "locations": [l.to_dict() for l in self.locations]}
