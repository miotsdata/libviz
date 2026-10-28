# Releasing

1. Set `version` in `pyproject.toml`, add the CHANGELOG entry, commit.
2. `git tag vX.Y.Z && git push origin master vX.Y.Z`.
3. `.github/workflows/release-builds.yml` builds the wheel/sdist, the Windows
   installer and the Linux AppImage, attaches them to the GitHub Release
   and, if all of that passed, publishes to PyPI.

A test build without releasing: Actions › Release builds › Run workflow (or
`gh workflow run release-builds.yml --ref <branch>`). It replaces the
`dev-build` pre-release and never touches PyPI.

Local builds: `packaging/appimage/build.sh` (Linux) or
`packaging\windows\build.ps1` (Windows, needs Inno Setup 6). Check a build
with `LIBVIZ_SMOKE_TEST=1 QT_QPA_PLATFORM=offscreen dist/libviz-gui/libviz-gui`;
it should print `LIBVIZ_SMOKE_TEST ok` and exit 0.

## One-time PyPI setup (Trusted Publishing)

On pypi.org › project `libviz` › Settings › Publishing › Add a new publisher
› GitHub:

| Field | Value |
|---|---|
| Owner | `miotsdata` |
| Repository | `libviz` |
| Workflow | `release-builds.yml` |
| Environment | `pypi` |

GitHub creates the `pypi` environment on the first run. You can add
required reviewers to it (repo Settings › Environments) so each upload
waits for your click. No API token is stored anywhere.
