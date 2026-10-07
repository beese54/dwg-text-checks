# AGENTS.md — orientation for AI coding assistants

Read this first. It is written for any AI model or IDE (Claude, GPT/Codex,
Gemini, Copilot, Cursor ...) picking this repository up cold. `CLAUDE.md` points
here. Human-facing overview: `README.md`.

## What this is

A Python 3.11+ package, `dwg_text_checks`, with a CLI `dwgtext`:

1. **Load** a `.dwg` (via an external converter to DXF) or `.dxf` with `ezdxf`.
2. **Collect** every string in model space -- TEXT, MTEXT, MULTILEADER, block
   ATTRIBs, with blocks expanded to world coordinates and hidden text marked.
3. **Place** each string on the issued paper-space layout's views (plan /
   section), through each viewport's own transform.
4. **Check** three text rules and report FOUND / NOT FOUND.

No rendering, no web app, no database. One runtime dependency: `ezdxf`.

## Set up and verify (do this before changing anything)

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate elsewhere
pip install -e ".[dev]"
pytest                          # must be green; needs no drawings
```

Only `.dwg` input needs more: a converter (`docs/SETUP.md`). Tests never do --
they build a synthetic DXF in `tests/conftest.py`.

**No API keys or secrets are used or needed.** Never add one to the repo;
`.env` is git-ignored, `.env.example` lists the only settings.

## Map

```
src/dwg_text_checks/
  load.py           .dwg/.dxf -> ezdxf document; DWG conversion cached by SHA-256
  backends/         converters: libredwg (dwg2dxf), oda (ODA File Converter)
  text.py           collect(): every PlacedText; flatten(): MTEXT codes -> plain
  views.py          Views: sheets, plan/section viewports, where()/shows()
  checks/
    __init__.py     run(): all three checks
    scope.py        Scope: which runs / pipes the checks ask about (JSON)
    chainage.py     CHK-001, incl. run assignment of letterless markers
    abandonment.py  CHK-004
    coordinates.py  CHK-005
    base.py         Verdict, Result, Evidence, Location
  report.py         checks.json + checks.md
  cli.py            dwgtext extract | check
tests/              conftest.py builds the synthetic drawing; test_rules.py
                    pins each rule; test_end_to_end.py runs the whole pipeline
docs/SETUP.md       converters, per OS
docs/CHECKS.md      each rule: what counts, what does not, why
examples/           scope.example.json
```

## Rules that are not style preferences

Each of these was learned from a wrong result on a real drawing.

1. **Never PASS / FAIL.** Verdicts are FOUND / NOT FOUND / CANNOT DETERMINE /
   NOT APPLICABLE. A NOT FOUND names what is missing; a FOUND lists what
   matched. Missing or ambiguous input is CANNOT DETERMINE, never FOUND.
2. **Count only what the issued layout shows.** Filter by `Views.where()` /
   `shows("plan", ...)`. Model-space-wide counts overstated a real drawing's
   problem about fivefold. Never guess the layout when there are several; ask
   (`--layout`).
3. **Honour hidden text.** `PlacedText.visible` is False for the `invisible`
   flag or a layer off/frozen; checks use visible text only. On one real
   drawing 31% of entities were hidden.
4. **Expand blocks; read MULTILEADER.** Callouts are usually leaders, and a
   third of a drawing's text can sit inside blocks. `text.collect` does both.
5. **Use the leader tip for position.** The words sit off to the side; the
   arrow tip (`PlacedText.tip`) is on the pipe.
6. **Wording drifts; read generously, decide strictly.** A revision wrote
   `CH. 10.000` where the original wrote `CH.C 10.000`, and a reader that only
   knew the second form reported an answered comment as unanswered. When you
   add a wording, add a test with it -- and a test that a near-miss (a road
   note's `FROM CH 120`) is not read as one.
7. **Rotated viewports.** Place points through `entity.get_transformation_matrix()`,
   never an axis-aligned window.
8. **Never commit drawings or their outputs.** `.gitignore` covers `*.dwg`,
   `*.dxf`, `*.pdf`, `out/`. Drawings belong to whoever supplied them; tests use
   synthetic data only.
9. **Never bundle ODA File Converter.** Freeware with no redistribution grant.
   Users install their own.

## How to add a check

1. Write the rule into `docs/CHECKS.md` first: what text counts, what does not,
   what verdict each case gets.
2. Add `checks/<name>.py` with a `judge(...)` returning `list[Result]`; give it
   the next id (CHK-006). Wire it into `checks.run`.
3. Tests in `tests/test_rules.py` (hand-placed `PlacedText`) **and** a case in
   `tests/conftest.py`'s drawing plus `tests/test_end_to_end.py`, including one
   that removes the answer and expects NOT FOUND.
4. `pytest` green.

## Conventions

- Plain functions and dataclasses; no framework. Type hints throughout.
- Comments explain *why*, usually the failure that made the code necessary.
- Messages to the user are sentences a reviewer can act on.
- Units: drawing units are metres; chainage in metres.

## Known limits (good next steps)

- Positions are not verified: an END label is found wherever it points.
- N/E values are listed, not compared with the fitting's drawn position. On
  drawings in survey coordinates, the leader tip and the written N/E agree to
  millimetres, so this is a feasible next check.
- Plan-vs-section detection is a drafting convention (largest topmost
  viewport, or any rotated one); `DWG_PLAN_VIEWPORTS` overrides it.
