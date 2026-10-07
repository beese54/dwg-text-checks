"""Open a .dwg or .dxf as an ezdxf document.

ezdxf reads DXF only, so a .dwg is first converted to DXF by an external
converter (see ``backends``). Conversions are cached by the file's SHA-256, so
running several commands on one drawing converts it once.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
import ezdxf.recover
from ezdxf.document import Drawing

from .backends import ConversionError, ConverterBackend, select_backend

__all__ = ["Loaded", "load", "ConversionError"]


@dataclass
class Loaded:
    """A parsed drawing and where it came from."""

    doc: Drawing
    source: Path
    dxf_path: Path
    converted_by: str
    warnings: list[str] = field(default_factory=list)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_dir() -> Path:
    """Where converted DXFs are kept: ``DWG_CACHE_DIR``, else ~/.cache."""
    root = os.environ.get("DWG_CACHE_DIR")
    return Path(root) if root else Path.home() / ".cache" / "dwg-text-checks"


def load(path: str | Path, backend: ConverterBackend | str | None = None) -> Loaded:
    """Convert if necessary, then parse."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")
    if path.stat().st_size == 0:
        raise ConversionError(f"{path.name} is empty (0 bytes).")

    suffix = path.suffix.lower()
    if suffix == ".dxf":
        dxf_path, converted_by = path, "none (native DXF)"
    elif suffix == ".dwg":
        chosen = backend if isinstance(backend, ConverterBackend) else \
            select_backend(backend if isinstance(backend, str) else None)
        converted_by = chosen.name
        cached = cache_dir() / f"{_sha256(path)}.{chosen.name}.dxf"
        if not cached.exists():
            work = cache_dir() / "_work"
            work.mkdir(parents=True, exist_ok=True)
            produced = chosen.to_dxf(path, work)
            shutil.move(str(produced), cached)
        dxf_path = cached
    else:
        raise ValueError(f"Unsupported input {suffix!r}; expected .dwg or .dxf")

    warnings: list[str] = []
    try:
        doc = ezdxf.readfile(dxf_path)
    except ezdxf.DXFStructureError:
        # Converters sometimes write DXF that is slightly off-spec; recover
        # reads what it can and says what it fixed.
        doc, auditor = ezdxf.recover.readfile(dxf_path)
        if auditor.has_errors:
            warnings.append(f"{len(auditor.errors)} DXF structure error(s) were "
                            "repaired while reading.")
    return Loaded(doc, path, dxf_path, converted_by, warnings)
