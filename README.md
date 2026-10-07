# dwg-text-checks

Extract the text from AutoCAD `.dwg` / `.dxf` drawings, and run a small set of
**rule-based checks that read nothing but that text**.

It answers questions a plan reviewer otherwise answers by eye, such as "did the
revised drawing add the things we asked for?":

| Check | Asks | Reads |
|---|---|---|
| **CHK-001** | Is chainage marked at every 10 m point along each named run? | `CH.C 15.510`, and markers like `CH. 10.000` that do not name their run |
| **CHK-004** | Are the start and end of each pipe to be abandoned labelled? | `START POINT OF THE PW450 TO BE ABANDONED` / `END POINT OF ...` |
| **CHK-005** | Does every connection point and bend label give north/east coordinates? | `H-BEND - 1 / CH.C 1.550 / N12345.678 / E23456.789` |

Results are **FOUND / NOT FOUND** (or CANNOT DETERMINE), never PASS / FAIL.
A text check is only as good as its reading of the wording; it tells a person
where to look, and the person confirms.

## Why text, and what "shown" means

The *correct* way to make drawings checkable is structured data -- block
attributes, standard layers. Most real drawings do not have it, and getting
there is a standards exercise. Text is already there. This is the first cut:
useful now, honest about what it cannot see.

It counts only text that the **issued paper-space layout's sheets actually
show**. Model space usually holds far more than was issued -- working copies,
other layouts' views -- and counting all of it overstates any problem several
times over. Each viewport's own transform (including rotation) decides what a
sheet shows; each sheet's plan view is told apart from its sections.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                                                 # synthetic drawings, no data needed

dwgtext extract drawing.dwg --layout "Sheet Layout" -o texts.json
dwgtext check   drawing.dwg --layout "Sheet Layout" --scope examples/scope.example.json -o out
```

`.dxf` needs nothing else. **`.dwg` needs a converter** -- LibreDWG or ODA File
Converter; see [docs/SETUP.md](docs/SETUP.md).

`check` writes `out/checks.md` (for people) and `out/checks.json` (for
programs). Every result carries its evidence, its limitations, and where on the
sheets to look.

## The scope file

Which run is "the main pipeline" and which pipes are to be abandoned is a
reviewer's reading of their comments, so it is written down rather than
guessed -- see [examples/scope.example.json](examples/scope.example.json) and
[docs/CHECKS.md](docs/CHECKS.md).

## What it does not do

- Check positions: a label saying "END POINT" is found whether or not it points
  at the true end. Coordinates are listed, not verified.
- See anything without a label, text exploded into lines, or text inside an
  unresolved external reference.
- Render drawings or produce pictures.

## For AI assistants and contributors

Start with [AGENTS.md](AGENTS.md).
