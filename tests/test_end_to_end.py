"""A whole drawing through the pipeline: load, collect text, place it on the
issued layout's views, check, report."""

from __future__ import annotations

import json

from conftest import build

from dwg_text_checks import text
from dwg_text_checks.checks import Scope, Verdict, run
from dwg_text_checks.cli import main
from dwg_text_checks.load import load
from dwg_text_checks.views import Views


def check(path, scope_file):
    loaded = load(path)
    views = Views.from_doc(loaded.doc, "Issued")
    labels = [l for l in text.collect(loaded.doc)
              if l.visible and views.where(l.x, l.y, l.layer)]
    results = run(labels, lambda x, y: views.shows("plan", x, y),
                  Scope.load(scope_file),
                  lambda x, y, layer: [v.title for v in views.where(x, y, layer)])
    return {r.check_id: r for r in results}


def test_text_is_collected_from_leaders_and_mtext(drawing):
    flats = [l.flat for l in text.collect(load(drawing).doc)]
    assert "CH. 20.000" in flats
    assert any(f.startswith("H-BEND - 1 CH.C 15.000 N2000.000") for f in flats)


def test_leaders_keep_their_arrow_tip(drawing):
    bend = next(l for l in text.collect(load(drawing).doc) if "H-BEND" in l.flat)
    assert bend.tip == (1015.0, 2000.0)


def test_views_find_the_plan_and_the_section(drawing):
    views = Views.from_doc(load(drawing).doc, "Issued")
    assert sorted(v.kind for v in views.views) == ["plan", "section"]
    assert views.shows("plan", 1030, 2000)
    assert not views.shows("plan", 6000, 7000)


def test_a_complete_drawing_is_found_on_all_three(drawing, scope_file):
    results = check(drawing, scope_file)
    assert {k: r.verdict for k, r in results.items()} == {
        "CHK-001": Verdict.FOUND, "CHK-004": Verdict.FOUND, "CHK-005": Verdict.FOUND}


def test_each_missing_answer_is_not_found(tmp_path, scope_file):
    """The decoys off every sheet must not stand in for what is missing."""
    no_20 = check(build(tmp_path / "a.dxf", markers=(0, 10, 30, 40, 50, 60)), scope_file)
    assert no_20["CHK-001"].verdict == Verdict.NOT_FOUND
    assert "CH 20.000" in no_20["CHK-001"].summary

    no_ne = check(build(tmp_path / "b.dxf", with_ne=False), scope_file)
    assert no_ne["CHK-005"].verdict == Verdict.NOT_FOUND

    no_end = check(build(tmp_path / "c.dxf", with_end=False), scope_file)
    assert no_end["CHK-004"].verdict == Verdict.NOT_FOUND
    assert "no end label" in no_end["CHK-004"].summary


def test_results_say_where_to_look(drawing, scope_file):
    chainage = check(drawing, scope_file)["CHK-001"]
    assert any(l.what == "CH 20.000" and l.views == ["Sheet 1 - Plan"]
               for l in chainage.locations)


def test_cli_writes_both_reports(drawing, scope_file, tmp_path, capsys):
    out = tmp_path / "out"
    assert main(["check", str(drawing), "--scope", str(scope_file), "-o", str(out)]) == 0
    data = json.loads((out / "checks.json").read_text(encoding="utf-8"))
    assert [r["verdict"] for r in data["results"]] == ["found"] * 3
    assert "**FOUND**" in (out / "checks.md").read_text(encoding="utf-8")


def test_cli_extract_lists_views(drawing, tmp_path):
    out = tmp_path / "texts.json"
    assert main(["extract", str(drawing), "-o", str(out)]) == 0
    rows = json.loads(out.read_text(encoding="utf-8"))["texts"]
    decoy = [r for r in rows if r["x"] > 5000]
    assert decoy and all(r["views"] == [] for r in decoy)
