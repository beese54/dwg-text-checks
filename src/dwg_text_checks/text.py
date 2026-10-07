"""Every string a drawing places in model space, as a reader would see it.

Text in a CAD drawing lives in more places than TEXT and MTEXT:

* **MULTILEADER** keeps its words in the leader's own context, not in an MTEXT
  entity. Callouts -- "H-BEND - 1 / CH.C 1.550" -- are usually leaders.
* **Blocks** hold text too, and block attributes (ATTRIB) hold more. A block's
  text is in block-local coordinates; ``virtual_entities()`` gives it in world
  coordinates, which is what any "where is it" question needs.
* **Hidden text** is still in the file. The DXF ``invisible`` flag, or a layer
  that is off or frozen, means it is not drawn. It is kept, marked
  ``visible=False``, so callers can decide; checks ignore it.

A leader's arrow tip is kept as well: it is where the label *points*, which is
on the pipe or fitting it labels, while the text itself is placed off to one
side.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

#: MTEXT formatting codes: ``{\C5;\fArial|b0;TEXT}``. MULTILEADER stores raw
#: MTEXT markup, so these arrive verbatim and must be stripped before reading.
_FORMAT_CODE = re.compile(r"\\[A-Za-z][^;\\]*;|[{}]")


def flatten(text: str) -> str:
    """Label text as a reader sees it: no formatting codes, one line.

    ``\\P`` and ``^J`` are line breaks, ``^I`` a tab, ``%%D`` a degree sign.
    """
    text = (text or "").replace("\\P", " ").replace("^I", " ").replace("^J", " ")
    text = text.replace("%%D", "°").replace("%%d", "°")
    return " ".join(_FORMAT_CODE.sub("", text).split())


@dataclass
class PlacedText:
    """One string as placed in model space."""

    text: str
    layer: str
    x: float
    y: float
    #: Entity type it came from: TEXT, MTEXT, MULTILEADER or ATTRIB.
    kind: str
    #: False if a renderer would not draw it (invisible flag, layer off/frozen).
    visible: bool = True
    #: Where a MULTILEADER's arrow lands; None for anything else.
    tip: tuple[float, float] | None = None
    entity: Any = field(default=None, repr=False)

    @property
    def flat(self) -> str:
        return flatten(self.text)

    @property
    def point(self) -> tuple[float, float]:
        """What the label marks: the arrow tip if it has one, else itself."""
        return self.tip or (self.x, self.y)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.flat, "raw": self.text, "layer": self.layer,
                "x": round(self.x, 3), "y": round(self.y, 3), "kind": self.kind,
                "visible": self.visible,
                "tip": [round(v, 3) for v in self.tip] if self.tip else None}


def leader_tip(entity) -> tuple[float, float] | None:
    """Where a MULTILEADER's first arrow lands, or None."""
    try:
        for branch in entity.context.leaders:
            for line in branch.lines:
                if line.vertices:
                    tip = line.vertices[0]
                    return float(tip[0]), float(tip[1])
    except Exception:
        return None
    return None


def collect(doc, max_depth: int = 4) -> list[PlacedText]:
    """Every placed string in model space, block references expanded."""
    found: list[PlacedText] = []

    def layer_shown(name: str) -> bool:
        try:
            state = doc.layers.get(name)
            return state.is_on() and not state.is_frozen()
        except Exception:
            return True

    def walk(entity, depth: int, parent_layer: str, parent_visible: bool) -> None:
        kind = entity.dxftype()
        try:
            layer = str(getattr(entity.dxf, "layer", "") or "")
            # Text on layer "0" inside a block draws on the block's layer.
            if layer == "0" and parent_layer:
                layer = parent_layer
            visible = (parent_visible and not getattr(entity.dxf, "invisible", 0)
                       and layer_shown(layer))
            if kind == "MTEXT":
                p = entity.dxf.insert
                found.append(PlacedText(entity.plain_text(), layer, float(p[0]),
                                        float(p[1]), kind, visible, None, entity))
            elif kind in ("TEXT", "ATTRIB"):
                p = entity.dxf.insert
                found.append(PlacedText(str(entity.dxf.text), layer, float(p[0]),
                                        float(p[1]), kind, visible, None, entity))
            elif kind == "MULTILEADER":
                mtext = entity.context.mtext
                if mtext is not None and mtext.default_content:
                    p = mtext.insert
                    found.append(PlacedText(mtext.default_content, layer,
                                            float(p[0]), float(p[1]), kind,
                                            visible, leader_tip(entity), entity))
            elif kind == "INSERT" and depth < max_depth:
                for attrib in entity.attribs:
                    walk(attrib, depth + 1, layer, visible)
                for sub in entity.virtual_entities():
                    walk(sub, depth + 1, layer, visible)
        except Exception:
            # One malformed entity must not lose the rest of the drawing.
            return

    for entity in doc.modelspace():
        walk(entity, 0, "", True)
    return found
