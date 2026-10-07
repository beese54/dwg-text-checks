"""Backend registry.

Order is deliberate: the redistributable backend is preferred so the shipped
image's default behaviour carries no licence caveat. ``DWG_CONVERTER`` lets an
operator force a specific backend.
"""

from __future__ import annotations

import os

from .base import ConversionError, ConverterBackend
from .libredwg import LibreDWGBackend
from .oda import OdaBackend

#: Preference order, most-redistributable first.
REGISTRY: tuple[type[ConverterBackend], ...] = (LibreDWGBackend, OdaBackend)


def all_backends() -> list[ConverterBackend]:
    return [cls() for cls in REGISTRY]


def select_backend(name: str | None = None) -> ConverterBackend:
    """Return a usable backend, honouring ``DWG_CONVERTER`` unless overridden."""
    wanted = (name or os.environ.get("DWG_CONVERTER") or "").strip().lower()
    backends = all_backends()

    if wanted:
        for backend in backends:
            if backend.name == wanted:
                if not backend.is_available():
                    raise ConversionError(
                        f"Backend {wanted!r} was requested but is not available "
                        "in this environment."
                    )
                return backend
        known = ", ".join(b.name for b in backends)
        raise ConversionError(f"Unknown backend {wanted!r}. Known: {known}")

    for backend in backends:
        if backend.is_available():
            return backend

    raise ConversionError(
        "No DWG converter available. Install LibreDWG, or set ODA_FC_PATH to an "
        "operator-supplied ODA File Converter."
    )


__all__ = [
    "ConversionError",
    "ConverterBackend",
    "LibreDWGBackend",
    "OdaBackend",
    "REGISTRY",
    "all_backends",
    "select_backend",
]
