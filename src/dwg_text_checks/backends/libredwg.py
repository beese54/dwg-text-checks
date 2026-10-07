"""LibreDWG backend - GPLv3, compiled into the distributable image.

This is the default backend precisely because it can be redistributed. Its
fidelity on R2018 files is verified by the regression suite rather than assumed.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import ConversionError, ConverterBackend

# LibreDWG ships two entry points and which one a given build installs varies,
# so try the purpose-built converter first and fall back to the general reader.
_CANDIDATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dwg2dxf", ("-o", "{dst}", "{src}")),
    ("dwgread", ("-O", "DXF", "-o", "{dst}", "{src}")),
)


class LibreDWGBackend(ConverterBackend):
    name = "libredwg"
    licence = "GPLv3 (redistributable)"

    def _tool(self) -> tuple[str, tuple[str, ...]] | None:
        for exe, args in _CANDIDATES:
            found = shutil.which(exe)
            if found:
                return found, args
        return None

    def is_available(self) -> bool:
        return self._tool() is not None

    def supported_inputs(self) -> list[str]:
        return [".dwg"]

    def to_dxf(self, src: Path, dst_dir: Path) -> Path:
        tool = self._tool()
        if tool is None:
            raise ConversionError(
                "LibreDWG not found. Expected 'dwg2dxf' or 'dwgread' on PATH."
            )
        exe, arg_template = tool
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / (src.stem + ".dxf")
        cmd = [exe, *(a.format(src=str(src), dst=str(dst)) for a in arg_template)]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

        # LibreDWG reports recoverable parse problems on stderr while still
        # writing valid output, so the produced file is the source of truth --
        # not the return code.
        if not dst.exists() or dst.stat().st_size == 0:
            detail = (proc.stderr or proc.stdout or "").strip()[-2000:]
            raise ConversionError(
                f"{Path(exe).name} produced no DXF for {src.name} "
                f"(exit {proc.returncode}). {detail}"
            )
        return dst
