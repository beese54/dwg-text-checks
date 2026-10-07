"""Converter backend contract.

DWG is a proprietary, compressed format that no pure-Python library can read, so
a native converter must produce DXF before ezdxf can do anything. Which converter
is available differs by deployment: the distributable image ships LibreDWG
(GPLv3), while ODA File Converter is freeware whose redistribution rights are not
granted, so it can only ever be supplied by the operator. Hence an interface
rather than a hardcoded dependency.
"""

from __future__ import annotations

import abc
from pathlib import Path


class ConversionError(RuntimeError):
    """Raised when a backend cannot produce a usable DXF."""


class ConverterBackend(abc.ABC):
    """Converts a native CAD file into a DXF that ezdxf can parse."""

    name: str = "abstract"
    #: Shown by ``dwg backends`` so licence posture is never a surprise.
    licence: str = "unknown"

    @abc.abstractmethod
    def is_available(self) -> bool:
        """True if this backend can actually run in the current environment."""

    @abc.abstractmethod
    def supported_inputs(self) -> list[str]:
        """Lower-case suffixes this backend accepts, e.g. ``[".dwg"]``."""

    @abc.abstractmethod
    def to_dxf(self, src: Path, dst_dir: Path) -> Path:
        """Convert ``src`` into a DXF inside ``dst_dir`` and return its path.

        Raises:
            ConversionError: if conversion fails or produces no readable output.
        """

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return f"<{type(self).__name__} name={self.name!r} available={self.is_available()}>"
