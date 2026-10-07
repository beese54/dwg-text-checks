"""Which sheet, and which view on it, shows a point in model space.

A drawing's model space usually holds more than was issued: working copies,
other layouts' views, superseded options. Counting every label in model space
can overstate a problem several times over. A check should count what the
**issued layout's sheets show**, and that is decided here.

A paper-space layout carries VIEWPORTs, each a window onto model space with
its own transform (scale, centre, and twist -- plans are often rotated).
Viewports close together on the paper form one sheet. On each sheet, the
largest topmost viewport is taken as the plan, any rotated large viewport is
a plan too, and the remaining large viewports are sections. That is a drafting
convention, not a rule; ``DWG_PLAN_VIEWPORTS=3,6`` overrides it with explicit
viewport ids.

Placement goes through each viewport's own model-to-paper matrix. An
axis-aligned window around a rotated viewport covers the wrong ground.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from ezdxf.math import Vec3

#: Viewports this close (as a fraction of the median viewport size) are on the
#: same sheet.
_GAP_FRACTION = 0.15
#: A viewport smaller than this fraction of the sheet's largest is a key plan or
#: inset, not a view.
_VIEW_AREA_FRACTION = 0.4


@dataclass
class View:
    """One viewport on one sheet."""

    sheet: int
    viewport: int
    #: "plan", "section" or "other".
    kind: str
    #: Paper-space rectangle (x0, x1, y0, y1).
    rect: tuple[float, float, float, float]
    matrix: object = field(default=None, repr=False)
    #: Layers frozen in this viewport only: text on them is not drawn here.
    frozen: frozenset[str] = frozenset()

    @property
    def title(self) -> str:
        name = {"plan": "Plan", "section": "Section"}.get(
            self.kind, "Viewport " + str(self.viewport))
        return "Sheet " + str(self.sheet) + " - " + name

    def inside(self, x: float, y: float) -> tuple[float, float] | None:
        """(u, v) of a model point in this view, 0..1 left-right and
        top-bottom, or None if the view does not show it."""
        p = self.matrix.transform(Vec3(x, y, 0.0))
        x0, x1, y0, y1 = self.rect
        if not (x0 <= p.x <= x1 and y0 <= p.y <= y1):
            return None
        return (p.x - x0) / (x1 - x0), (y1 - p.y) / (y1 - y0)


def _is_rotated(dxf) -> bool:
    twist = float(getattr(dxf, "view_twist_angle", 0.0) or 0.0) % 360.0
    return min(twist, 360.0 - twist) > 1e-6


def _viewports(doc, layout: str) -> list:
    """The layout's real viewports. Id 1 is the paper space itself."""
    return [e for e in doc.layouts.get(layout)
            if e.dxftype() == "VIEWPORT" and int(getattr(e.dxf, "id", 0) or 0) != 1
            and float(e.dxf.width) > 0 and float(e.dxf.height) > 0]


def _sheets(viewports) -> list[list]:
    """Viewports clustered by paper-space proximity, in reading order."""
    if not viewports:
        return []

    def rect(e):
        cx, cy = float(e.dxf.center[0]), float(e.dxf.center[1])
        w, h = float(e.dxf.width), float(e.dxf.height)
        return [cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2]

    sizes = sorted(max(float(e.dxf.width), float(e.dxf.height)) for e in viewports)
    gap = sizes[len(sizes) // 2] * _GAP_FRACTION
    clusters: list[tuple[list[float], list]] = []
    for entity in viewports:
        box = rect(entity)
        for bounds, members in clusters:
            if not (box[0] > bounds[1] + gap or box[1] < bounds[0] - gap
                    or box[2] > bounds[3] + gap or box[3] < bounds[2] - gap):
                bounds[:] = [min(bounds[0], box[0]), max(bounds[1], box[1]),
                             min(bounds[2], box[2]), max(bounds[3], box[3])]
                members.append(entity)
                break
        else:
            clusters.append((box, [entity]))
    # Reading order: top row first, then left to right.
    clusters.sort(key=lambda c: (-round(c[0][3], -2), c[0][0]))
    return [members for _bounds, members in clusters]


def _classify(members) -> dict[int, str]:
    """viewport id -> "plan" / "section" / "other" for one sheet."""
    override = os.environ.get("DWG_PLAN_VIEWPORTS", "").strip()
    area = {int(e.dxf.id): float(e.dxf.width) * float(e.dxf.height) for e in members}
    largest = max(area.values())
    views = [e for e in members if area[int(e.dxf.id)] >= largest * _VIEW_AREA_FRACTION]
    if override:
        plans = {int(p) for p in override.replace(" ", "").split(",") if p.isdigit()}
    else:
        top = max(views, key=lambda e: float(e.dxf.center[1]))
        plans = {int(top.dxf.id)} | {int(e.dxf.id) for e in views
                                     if _is_rotated(e.dxf)}
    kinds = {}
    for entity in members:
        vp_id = int(entity.dxf.id)
        kinds[vp_id] = ("plan" if vp_id in plans
                        else "section" if entity in views else "other")
    return kinds


class Views:
    """The views of one paper-space layout, and what each shows."""

    def __init__(self, views: list[View], layout: str):
        self.views = views
        self.layout = layout

    @classmethod
    def from_doc(cls, doc, layout: str) -> "Views":
        if layout == "Model" or layout not in doc.layouts.names():
            raise ValueError(f"No paper-space layout named {layout!r}. "
                             f"Layouts: {paper_layouts(doc)}")
        views: list[View] = []
        for index, members in enumerate(_sheets(_viewports(doc, layout)), start=1):
            kinds = _classify(members)
            for entity in members:
                dxf = entity.dxf
                cx, cy = float(dxf.center[0]), float(dxf.center[1])
                w, h = float(dxf.width), float(dxf.height)
                views.append(View(
                    sheet=index, viewport=int(dxf.id), kind=kinds[int(dxf.id)],
                    rect=(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2),
                    matrix=entity.get_transformation_matrix(),
                    frozen=frozenset(n.upper() for n in entity.frozen_layers)))
        return cls(views, layout)

    def where(self, x: float, y: float, layer: str | None = None) -> list[View]:
        """Every view that draws the point, plans first."""
        found = [v for v in self.views
                 if not (layer and layer.upper() in v.frozen)
                 and v.inside(x, y) is not None]
        rank = {"plan": 0, "section": 1, "other": 2}
        return sorted(found, key=lambda v: (rank[v.kind], v.sheet))

    def shows(self, kind: str, x: float, y: float) -> bool:
        """True if any view of this kind draws the point."""
        return any(v.inside(x, y) is not None for v in self.views if v.kind == kind)


def paper_layouts(doc) -> list[str]:
    return [name for name in doc.layouts.names() if name != "Model"]
