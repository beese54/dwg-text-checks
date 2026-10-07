"""A synthetic drawing, so the suite needs no real (and usually confidential)
CAD file.

Model space: run C runs along the x axis from (1000, 2000), 60 m long, with
bend leaders that name their station and give N/E; letterless 10 m markers;
start/end labels for an abandoned pipe. Far away, outside every viewport, a
decoy copy of a marker that must not count. Paper space: one layout, "Issued",
with a plan viewport framing the run and a smaller section viewport below it.
"""

from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest
from ezdxf.math import Vec2
from ezdxf.render import mleader

ORIGIN = (1000.0, 2000.0)


def add_leader(msp, content: str, tip, at) -> None:
    builder = msp.add_multileader_mtext("Standard")
    builder.set_content(content)
    builder.add_leader_line(mleader.ConnectionSide.left, [Vec2(tip)])
    builder.build(insert=Vec2(at))


def build(path: Path, *, markers=(0, 10, 20, 30, 40, 50, 60), with_ne=True,
          with_end=True) -> Path:
    doc = ezdxf.new("R2018", setup=True)
    msp = doc.modelspace()
    ox, oy = ORIGIN
    msp.add_line((ox, oy), (ox + 60, oy), dxfattribs={"layer": "PIPE"})

    for name, station in (("CONNECTION POINT - 1", 0.0), ("H-BEND - 1", 15.0),
                          ("V-BEND - 2", 33.0), ("CONNECTION POINT - 2", 60.0)):
        x, y = ox + station, oy
        ne = f"\\PN{y:.3f}\\PE{x:.3f}" if with_ne else ""
        add_leader(msp, f"{name}\\PCH.C {station:.3f}{ne}", (x, y), (x + 2, y + 6))
    for station in markers:
        msp.add_mtext(f"CH. {station:.3f}").set_location((ox + station, oy - 1.0))
    add_leader(msp, "START POINT OF THE PW450 TO BE ABANDONED", (ox + 5, oy + 3), (ox + 5, oy + 10))
    if with_end:
        add_leader(msp, "END POINT OF THE PW450 TO BE ABANDONED", (ox + 45, oy + 3), (ox + 45, oy + 10))
    # A copy nowhere near any viewport: in the file, on no issued sheet.
    msp.add_mtext("CH. 20.000").set_location((ox + 5000, oy + 5000))
    msp.add_mtext("END POINT OF THE PW450 TO BE ABANDONED").set_location((ox + 5000, oy + 5005))

    # ezdxf starts every drawing with "Layout1"; make it the one issued layout.
    doc.layouts.rename("Layout1", "Issued")
    layout = doc.layouts.get("Issued")
    # Plan on top: frames 80 x 40 m of model space around the run.
    layout.add_viewport(center=(200, 200), size=(320, 160),
                        view_center_point=(ox + 30, oy), view_height=40)
    # Section below it, smaller but still a view, framing somewhere else.
    layout.add_viewport(center=(200, 60), size=(320, 100),
                        view_center_point=(ox, oy - 500), view_height=25)
    doc.saveas(path)
    return path


@pytest.fixture
def drawing(tmp_path) -> Path:
    return build(tmp_path / "synthetic.dxf")


@pytest.fixture
def scope_file(tmp_path) -> Path:
    p = tmp_path / "scope.json"
    p.write_text('{"chainage": {"runs": {"C": "main"}}, '
                 '"coordinates": {"runs": {"C": "main"}}, '
                 '"abandonment": [{"pipe": "PW450"}]}', encoding="utf-8")
    return p
