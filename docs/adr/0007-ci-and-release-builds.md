# ADR 7: CI and release builds like MSIAnalyzer, plus PyPI

Status: accepted (2026-10-28)

## Context

`build_pkg.yml` only built the wheel/sdist on a `v*` tag and attached them
to a GitHub Release; nothing ran the tests, and PyPI was uploaded by hand.
libviz now has a desktop GUI, so it needs the same standalone builds as
MSIAnalyzer. MSIAnalyzer installs libviz from PyPI.

## Decision

- **`ci.yml`**: MSIAnalyzer's CI with pinned PDM 2.28.0, Qt runtime libs,
  advisory pylint and offscreen pytest. It runs on push/PR to
  `develop`/`master`. It has no docs build (libviz has no mkdocs site) and
  no retry line (the libviz suite has had no PySide flake).
- **`release-builds.yml`**: the same jobs as MSIAnalyzer. A manual run
  gives a rolling `dev-build` pre-release; a `v*` tag gives a release. The
  assets are the Windows installer (PyInstaller onedir + Inno Setup), the
  Linux AppImage (built on 22.04 for glibc 2.35) and, new here, the
  wheel + sdist. The packaging under `packaging/` is MSIAnalyzer's, with
  the same QML/Qt-library trimming in the spec.
- **PyPI**: on tags only, after every build *and both smoke tests* have
  passed, using Trusted Publishing (OIDC, no stored token).
  A PyPI version can't be re-uploaded, so a broken installer stops the
  publish. The `release` job also refuses a tag that doesn't match
  `pyproject.toml`'s version.
- **Smoke test**: MSIAnalyzer waits for a file its app writes after
  loading QML. libviz instead has `LIBVIZ_SMOKE_TEST=1`: `gui.main` loads
  Main.qml, compiles every `Views/*.qml` (pages load lazily, so a missing
  QML module would otherwise go unnoticed), creates a library (runs the
  bundled Alembic migrations) and exits 0. `tests/gui/test_main.py` runs
  the same mode in CI. On the first local frozen build it caught the
  QML directory being bundled in the wrong place.

## Consequences

- Trusted Publishing needs a one-time setup on pypi.org (docs/release.md).
  Until then the `pypi` job fails, but the release assets are still built.
- The Windows `.exe` uses PyInstaller's default icon: converting the
  placeholder PNG needs Pillow, which libviz doesn't depend on.
- The Windows and AppImage builds have only run on GitHub, not locally
  (the PyInstaller onedir build and its smoke test were checked on Linux).
