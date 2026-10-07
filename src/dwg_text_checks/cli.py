"""Command line: ``dwgtext extract`` and ``dwgtext check``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import report, text
from .checks import Scope, run
from .load import load
from .views import Views, paper_layouts


def _layout(doc, asked: str | None) -> str:
    """The issued layout: as named, or the only one there is. Never guessed --
    a drawing with several tabs usually has one that was never issued."""
    layouts = paper_layouts(doc)
    if asked:
        if asked not in layouts:
            sys.exit(f"No layout {asked!r}. Layouts: {layouts}")
        return asked
    if len(layouts) == 1:
        return layouts[0]
    sys.exit(f"This drawing has {len(layouts)} paper-space layouts {layouts}; "
             "name the issued one with --layout.")


def _shown(labels, views: Views):
    return [l for l in labels if l.visible and views.where(l.x, l.y, l.layer)]


def cmd_extract(args) -> int:
    loaded = load(args.input, args.backend)
    labels = text.collect(loaded.doc)
    rows = []
    views = None
    if args.layout or len(paper_layouts(loaded.doc)) == 1:
        views = Views.from_doc(loaded.doc, _layout(loaded.doc, args.layout))
    for label in labels:
        row = label.to_dict()
        if views is not None:
            row["views"] = [v.title for v in views.where(*label.point, label.layer)]
        rows.append(row)
    out = json.dumps({"drawing": Path(args.input).name, "converted_by": loaded.converted_by,
                      "layout": views.layout if views else None, "texts": rows},
                     indent=1, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"Wrote {len(rows)} texts to {args.output}")
    else:
        print(out)
    return 0


def cmd_check(args) -> int:
    loaded = load(args.input, args.backend)
    layout = _layout(loaded.doc, args.layout)
    views = Views.from_doc(loaded.doc, layout)
    scope = Scope.load(args.scope)
    if args.interval:
        scope.interval_m = args.interval
    labels = _shown(text.collect(loaded.doc), views)

    def where(x, y, layer):
        return [v.title for v in views.where(x, y, layer)]

    results = run(labels, lambda x, y: views.shows("plan", x, y), scope, where)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = Path(args.input).name
    report.write_json(results, out / "checks.json", drawing=name, layout=layout,
                      scope=scope.source)
    report.write_markdown(results, out / "checks.md", drawing=name, layout=layout,
                          scope_source=scope.source)
    for r in results:
        print(f"{r.check_id}  {r.verdict.value.replace('_', ' ').upper():<17} "
              f"{r.subject}\n    {r.summary}")
    print(f"\nWrote {out / 'checks.md'} and {out / 'checks.json'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dwgtext", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("input", help=".dwg or .dxf")
    common.add_argument("--layout", help="the paper-space layout that was issued")
    common.add_argument("--backend", help="force a converter: libredwg | oda")

    p = sub.add_parser("extract", parents=[common],
                       help="every text in the drawing, with coordinates and views")
    p.add_argument("-o", "--output", help="write JSON here instead of stdout")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("check", parents=[common], help="run CHK-001/004/005")
    p.add_argument("--scope", required=True, help="scope JSON (see examples/)")
    p.add_argument("--interval", type=float, help="chainage interval in metres")
    p.add_argument("-o", "--output-dir", default="out")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
