"""ODA File Converter backend - operator-supplied, never bundled.

ODA File Converter is freeware with no redistribution grant, so shipping it
inside an image would push an unresolved licence question onto every downstream
user. The operator points ``ODA_FC_PATH`` at their own installation, having
accepted ODA's terms themselves.

Two behaviours make this backend awkward, and both are handled explicitly:
  * it is a Qt application even in CLI mode, so headless Linux needs ``xvfb-run``;
  * on Windows it detaches, returning immediately with an empty exit code while
    conversion continues -- so completion is detected by polling for output.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import time
from pathlib import Path

from .base import ConversionError, ConverterBackend

_WINDOWS_GLOB = "C:/Program Files/ODA/*/ODAFileConverter.exe"


def _discover() -> Path | None:
    explicit = os.environ.get("ODA_FC_PATH")
    if explicit and Path(explicit).exists():
        return Path(explicit)
    on_path = shutil.which("ODAFileConverter")
    if on_path:
        return Path(on_path)
    matches = sorted(glob.glob(_WINDOWS_GLOB))
    return Path(matches[-1]) if matches else None


class OdaBackend(ConverterBackend):
    name = "oda"
    licence = "Freeware, NOT redistributable - operator-supplied only"

    def is_available(self) -> bool:
        return _discover() is not None

    def supported_inputs(self) -> list[str]:
        return [".dwg"]

    def to_dxf(self, src: Path, dst_dir: Path, timeout: int = 900) -> Path:
        exe = _discover()
        if exe is None:
            raise ConversionError(
                "ODA File Converter not found. Set ODA_FC_PATH to its executable. "
                "It is deliberately not bundled: its licence grants no "
                "redistribution right."
            )
        dst_dir.mkdir(parents=True, exist_ok=True)

        # ODA operates on directories, not files, so the input is staged alone to
        # stop it converting unrelated drawings sitting alongside the target.
        stage = dst_dir / "_oda_in"
        stage.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, stage / src.name)

        cmd = [str(exe), str(stage), str(dst_dir), "ACAD2018", "DXF", "0", "1", "*.DWG"]
        if os.name != "nt" and shutil.which("xvfb-run"):
            cmd = ["xvfb-run", "-a", *cmd]

        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            pass  # The process may still have written output before being killed.

        dst = dst_dir / (src.stem + ".dxf")
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                if dst.exists() and dst.stat().st_size > 0:
                    # The file appears before it is fully written, so require its
                    # size to settle before declaring the conversion complete.
                    size = dst.stat().st_size
                    time.sleep(1.0)
                    if dst.stat().st_size == size:
                        return dst
                time.sleep(0.5)
        finally:
            shutil.rmtree(stage, ignore_errors=True)

        raise ConversionError(
            f"ODA File Converter produced no DXF for {src.name} within {timeout}s."
        )
