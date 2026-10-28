# LibViz

Build, inspect and curate MS/MS spectral libraries.

- **Import** MSP libraries (MoNA, MS-DIAL, NIST-style exports).
- **Inspect** libraries: browse compounds and spectra, view spectra.

## Install

```bash
pdm install -G gui          # or: pip install "libviz[gui]"
pdm run libviz-gui
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

Docs: [architecture](docs/architecture.md), [decisions](docs/adr/), [changelog](CHANGELOG.md).
