"""The three rules, one behaviour at a time, on hand-placed labels.

FOUND / NOT FOUND, never PASS / FAIL: these checks read text, and a person
confirms what they report.
"""

from __future__ import annotations

from dwg_text_checks.checks import Scope as CommentScope, Verdict, run
from dwg_text_checks.checks import chainage as chk
from dwg_text_checks.text import PlacedText


def Label(text, layer, x, y, tip=None):
    return PlacedText(text, layer, x, y, "MTEXT", True, tip)


SCOPE = CommentScope.from_dict({
    "chainage": {"runs": {"C": "main", "D": "offtake"}},
    "coordinates": {"runs": {"C": "main", "D": "offtake"}},
    "abandonment": [{"pipe": "PW450"}, {"pipe": "PW150 offtake"}],
})


def everywhere(x, y):
    return True


def leader(text, x, y):
    """A label whose leader lands where it is written."""
    return PlacedText(text, "NOTES", x, y, "MULTILEADER", True, (x, y))


def main_along_x(stations=(0.0, 15.0, 30.0, 45.0, 60.0, 69.2)):
    """Run C along y = 0: station s sits at x = s."""
    return [leader("H-BEND CH.C " + format(s, ".3f"), s, 0.0) for s in stations]


def offtake_from_60(stations=(0.0, 12.0, 25.0, 34.9)):
    """Run D leaves the main at its CH 60 and heads along +y."""
    return [leader("V-BEND CH.D " + format(s, ".3f"), 60.0, s) for s in stations]


def by(results, check_id, subject_start):
    return next(r for r in results if r.check_id == check_id
                and r.subject.startswith(subject_start))


# --------------------------------------------------------------------------
# CHK-001: chainage markers that do not name their run
# --------------------------------------------------------------------------

class TestLetterlessMarkers:
    def test_markers_go_to_the_run_they_sit_on(self):
        """The junction case: D's CH 0 and C's CH 60 are a metre apart. Only
        station and position together tell them apart."""
        markers = ([Label("CH. " + format(s, ".3f"), "T", s, 1.0)
                    for s in (0, 10, 20, 30, 40, 50, 60)]
                   + [Label("CH. " + format(s, ".3f"), "T", 61.0, s)
                      for s in (0, 10, 20, 30)])
        results = run(main_along_x() + offtake_from_60() + markers,
                      everywhere, SCOPE)
        assert by(results, "CHK-001", "run C").verdict == Verdict.FOUND
        assert by(results, "CHK-001", "run D").verdict == Verdict.FOUND

    def test_a_missing_marker_is_named(self):
        markers = [Label("CH. " + format(s, ".3f"), "T", s, 1.0)
                   for s in (0, 10, 30, 40, 50, 60)]
        result = by(run(main_along_x() + markers, everywhere, SCOPE),
                    "CHK-001", "run C")
        assert result.verdict == Verdict.NOT_FOUND
        assert "CH 20.000" in result.summary

    def test_road_chainage_in_a_note_is_not_a_marker(self):
        labels = main_along_x() + [
            Label("TO RETAIN EXT'G KERB FROM CH 10 - CH 20", "R", 10, 1)]
        runs = chk.gather(labels, everywhere)
        assert 10.0 not in runs["C"].in_plan

    def test_a_marker_two_runs_could_own_is_not_found_either_way(self):
        """Two parallel runs a metre apart: CH. 10.000 between them belongs to
        neither with confidence, so the point is CANNOT_DETERMINE."""
        twin = [leader("BEND CH.E " + format(s, ".3f"), s, 2.0)
                for s in (0.0, 15.0)]
        scope = CommentScope.from_dict({"chainage": {"runs": {"C": "main"}}})
        labels = (main_along_x((0.0, 15.0)) + twin
                  + [Label("CH. 10.000", "T", 10.0, 1.0)])
        result = by(run(labels, everywhere, scope), "CHK-001", "run C")
        assert result.verdict == Verdict.CANNOT_DETERMINE

    def test_a_station_written_against_the_wrong_run_is_set_aside(self):
        """A washout labelled CH.C 4.453 that actually sits 50 m away, on
        another run. Left in, it bends the line the markers are placed
        against, and CH 10 is reported missing."""
        stray = leader("WASHOUT CH.C 4.453", 60.0, 30.0)
        markers = [Label("CH. 10.000", "T", 10.0, 1.0),
                   Label("CH. 20.000", "T", 20.0, 1.0)]
        labels = main_along_x((0.0, 1.5, 15.0, 30.0)) + [stray] + markers
        results = run(labels, everywhere,
                      CommentScope.from_dict({"chainage": {"runs": {"C": "m"}}}))
        result = by(results, "CHK-001", "run C")
        assert result.verdict == Verdict.FOUND
        assert any(e.label == "label whose station and position disagree"
                   and e.value == "CH.C 4.453" for e in result.evidence)

    def test_runs_the_comments_do_not_name_are_not_judged(self):
        labels = main_along_x() + [leader("CH.A 0.000", 0, 50),
                                   leader("CH.A 30.000", 30, 50)]
        results = run(labels, everywhere,
                      CommentScope.from_dict({"chainage": {"runs": {"C": "m"}}}))
        other = by(results, "CHK-001", "runs A")
        assert other.verdict == Verdict.NOT_APPLICABLE

    def test_a_named_run_absent_from_the_drawing_is_not_found(self):
        results = run(main_along_x(), everywhere, SCOPE)
        assert by(results, "CHK-001", "run D").verdict == Verdict.NOT_FOUND


# --------------------------------------------------------------------------
# CHK-004: start and end of the pipe to be abandoned
# --------------------------------------------------------------------------

class TestAbandonment:
    def test_start_and_end_found(self):
        labels = [leader("{\\C30;START POINT OF\\PTHE PW450 TO BE ABANDONED}", 0, 0),
                  leader("END POINT OF THE PW450 TO BE ABANDONED", 9, 0)]
        result = by(run(labels, everywhere, SCOPE), "CHK-004", "PW450")
        assert result.verdict == Verdict.FOUND

    def test_a_missing_end_is_named(self):
        labels = [leader("START POINT OF THE PW150 OFFTAKE TO BE ABANDONED", 0, 0)]
        result = by(run(labels, everywhere, SCOPE), "CHK-004", "PW150")
        assert result.verdict == Verdict.NOT_FOUND
        assert "no end label" in result.summary

    def test_another_pipe_does_not_answer_for_this_one(self):
        """EXISTING DN450mm WATER PIPE (ABANDONED) names a different thing:
        it is not PW450's start or end."""
        labels = [leader("EXISTING DN450mm WATER PIPE (ABANDONED)", 0, 0),
                  leader("START POINT OF THE PW150 OFFTAKE TO BE ABANDONED", 0, 0),
                  leader("END POINT OF THE PW150 OFFTAKE TO BE ABANDONED", 5, 0)]
        results = run(labels, everywhere, SCOPE)
        assert by(results, "CHK-004", "PW450").verdict == Verdict.NOT_FOUND
        assert by(results, "CHK-004", "PW150").verdict == Verdict.FOUND

    def test_one_label_for_both_ends_is_for_the_officer(self):
        labels = [leader("START/END POINT OF PW450 TO BE ABANDONED", 0, 0)]
        result = by(run(labels, everywhere, SCOPE), "CHK-004", "PW450")
        assert result.verdict == Verdict.CANNOT_DETERMINE

    def test_text_off_the_plan_does_not_count(self):
        labels = [leader("START POINT OF THE PW450 TO BE ABANDONED", 0, 0),
                  leader("END POINT OF THE PW450 TO BE ABANDONED", 500, 0)]
        result = by(run(labels, lambda x, y: x < 100, SCOPE), "CHK-004", "PW450")
        assert result.verdict == Verdict.NOT_FOUND


# --------------------------------------------------------------------------
# CHK-005: N/E at connection points and bends
# --------------------------------------------------------------------------

class TestCoordinates:
    def test_every_label_with_n_and_e_is_found(self):
        labels = [leader("CONNECTION POINT - 1\\PCH.C 0.000^JN12000.664\\PE23000.194", 0, 0),
                  leader("PROP.^IDN600mm 45%%D H-BEND - 1\\PCH.C 1.550\\PN12001.061\\PE23001.818", 1.5, 0)]
        result = by(run(labels, everywhere, SCOPE), "CHK-005", "run C")
        assert result.verdict == Verdict.FOUND
        assert "2 connection point and bend labels" in result.summary

    def test_a_label_without_them_is_named(self):
        labels = [leader("CONNECTION POINT - 1\\PCH.C 0.000\\PN12000.664\\PE23000.194", 0, 0),
                  leader("PROP. DN600mm 45%%D V-BEND - 3\\PCH.C 31.470\\PN12030.130", 31, 0)]
        result = by(run(labels, everywhere, SCOPE), "CHK-005", "run C")
        assert result.verdict == Verdict.NOT_FOUND
        assert "V-BEND - 3" in result.summary
        assert any(e.value == "no E" for e in result.evidence)

    def test_a_bore_is_not_a_northing(self):
        """DN600 must not read as N 800, nor a long number in a size."""
        labels = [leader("PROP. DN6000mm H-BEND CH.C 5.000 E23000.1", 5, 0)]
        result = by(run(labels, everywhere, SCOPE), "CHK-005", "run C")
        assert result.verdict == Verdict.NOT_FOUND

    def test_a_note_about_bends_is_not_a_bend(self):
        labels = main_along_x((0.0, 15.0))
        labels = [leader(l.text + " N12000.000 E23000.000", l.x, l.y) for l in labels]
        labels.append(Label("NOTE: THE BENDS CONNECTION DETAIL SHALL FOLLOW THE "
                            "STANDARD DRAWING FOR ALL PIPES", "N", 5, 5))
        result = by(run(labels, everywhere, SCOPE), "CHK-005", "run C")
        assert result.verdict == Verdict.FOUND

    def test_an_unstationed_bend_goes_to_the_run_its_leader_lands_on(self):
        labels = main_along_x((0.0, 15.0, 30.0)) + [
            Label("PROP. DN600mm 45° H-BEND -2", "T", 20.0, 6.0, (20.0, 0.2))]
        labels = [l if "-2" in l.text else
                  leader(l.text + " N1000.0 E2000.0", l.x, l.y) for l in labels]
        result = by(run(labels, everywhere, SCOPE), "CHK-005", "run C")
        assert result.verdict == Verdict.NOT_FOUND
        assert "H-BEND -2" in result.summary

    def test_no_labels_cannot_be_judged(self):
        result = by(run([], everywhere, SCOPE), "CHK-005", "run D")
        assert result.verdict == Verdict.CANNOT_DETERMINE

    def test_the_same_label_in_two_views_counts_once(self):
        text = "H-BEND - 1\\PCH.C 1.550\\PN12001.061\\PE23001.818"
        labels = [leader(text, 0, 0), leader(text, 400, 400)]
        result = by(run(labels, everywhere, SCOPE), "CHK-005", "run C")
        assert "all 1 connection" in result.summary
