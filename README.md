# LibViz

Build, inspect and curate MS/MS spectral libraries.

- **Build** libraries from mzML files (DDA, DIA, imaging) and a target list: one spectrum per compound/adduct/CE, you pick the best scan.
- **Import** MSP libraries (MoNA, MS-DIAL, NIST-style exports).
- **Inspect** libraries: search compounds, view spectra and metadata, even with 500k+ spectra.
- **Curate**: edit/delete compounds, spectra and metadata; export MSP; merge libraries.

## Install

```bash
pdm install -G gui          # or: pip install "libviz[gui]"
pdm run libviz-gui
pdm run libviz build targets.csv run.mzML -o standards.db   # headless
```

Python 3.13, PySide6 ≥ 6.12.

## Use as a library

```python
from pathlib import Path
from libviz.core.library import Library

lib = Library.load_from_msp(Path("MoNA.msp"))
lib.save_as_db(Path("mona.db"))
lib = Library.load_from_db(Path("mona.db"))
lib.get_spectra_in_mz_range(195.08, 195.09, "POSITIVE")
```

## Development

```bash
pdm install -G :all
pdm run pytest
```

Docs: [user guide](docs/user-guide.md), [architecture](docs/architecture.md), [decisions](docs/adr/), [changelog](CHANGELOG.md).
