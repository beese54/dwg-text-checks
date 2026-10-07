"""Write check results as JSON (for programs) and Markdown (for people)."""

from __future__ import annotations

import json
from pathlib import Path

from .checks import Result

_WORD = {"found": "FOUND", "not_found": "NOT FOUND",
         "cannot_determine": "CANNOT DETERMINE", "not_applicable": "N/A"}


def write_json(results: list[Result], path: Path, **meta) -> None:
    path.write_text(json.dumps({**meta, "results": [r.to_dict() for r in results]},
                               indent=1, ensure_ascii=False), encoding="utf-8")


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_markdown(results: list[Result], path: Path, *, drawing: str,
                   layout: str, scope_source: str = "") -> None:
    lines = [f"# Text checks: {drawing}", "",
             f"Layout reviewed: **{layout}**" + (f" · scope: {scope_source}" if scope_source else ""),
             "",
             "FOUND / NOT FOUND say whether the drawing's **text** contains what was "
             "asked for. They are a first pass for a person to confirm, not a "
             "compliance verdict. CANNOT DETERMINE is never a pass.", "",
             "| Check | Subject | Verdict | Finding |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.check_id} | {_cell(r.subject)} | "
                     f"**{_WORD.get(r.verdict.value, r.verdict.value)}** | {_cell(r.summary)} |")
    for r in results:
        lines += ["", f"## {r.check_id} — {_cell(r.subject)}: "
                      f"{_WORD.get(r.verdict.value, r.verdict.value)}", "", r.summary, ""]
        if r.evidence:
            lines += ["| | |", "|---|---|"]
            lines += [f"| {_cell(e.label)} | {_cell(e.value)}"
                      + (f" — {_cell(e.detail)}" if e.detail else "") + " |"
                      for e in r.evidence]
            lines.append("")
        if r.locations:
            lines += ["Where to look:", ""]
            lines += [f"- {l.what} — {', '.join(l.views) or 'on no issued view'} "
                      f"(E {l.x:.3f}, N {l.y:.3f})" for l in r.locations]
            lines.append("")
        lines += [f"> Limitation: {lim}" for lim in r.limitations]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
