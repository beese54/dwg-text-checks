# Setup

## Python

Python **3.11 or newer**.

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

That is everything for `.dxf` drawings and for the test suite. Python
packages: `ezdxf` (runtime) and `pytest` (tests) -- see `pyproject.toml` /
`requirements.txt`.

## A DWG converter (only for `.dwg` input)

`ezdxf` reads DXF, not DWG. A `.dwg` is converted to DXF first by one of two
external programs. Install either; the tool uses the first it finds, or the
one named by `DWG_CONVERTER=libredwg|oda` / `--backend`.

### Option A -- ODA File Converter (Windows, macOS, Linux)

Free download from the Open Design Alliance (registration may be required):
<https://www.opendesign.com/guestfiles/oda_file_converter>.

- Windows: installs to `C:\Program Files\ODA\ODAFileConverter <version>\`,
  which is found automatically.
- Elsewhere, or a non-default location: set `ODA_FC_PATH` to the executable.
- Headless Linux needs `xvfb-run` (it is a Qt application).

It is freeware **without a redistribution grant**: install your own copy and
never commit or bundle it.

### Option B -- LibreDWG (open source, GPLv3)

Provides `dwg2dxf`, which must be on `PATH`.

- Debian/Ubuntu: build from source (<https://www.gnu.org/software/libredwg/>);
  distribution packages are often too old for recent DWG versions.
- macOS: `brew install libredwg`.

LibreDWG and ODA produce slightly different DXF from the same drawing. For
text extraction both work; if a label you can see in AutoCAD is missing, try
the other converter before suspecting the checks.

### Verify

```bash
dwgtext extract your.dwg -o texts.json     # prints "Wrote N texts"
```

Converted DXFs are cached in `~/.cache/dwg-text-checks` (or `DWG_CACHE_DIR`),
keyed by the drawing's SHA-256, so the second run is fast.

## Settings

All optional; see `.env.example`.

| Variable | Meaning |
|---|---|
| `DWG_CONVERTER` | `libredwg` or `oda`; unset = first available |
| `ODA_FC_PATH` | path to the ODA executable |
| `DWG_CACHE_DIR` | where converted DXFs are cached |
| `DWG_PLAN_VIEWPORTS` | comma-separated viewport ids to treat as plans, overriding detection |
