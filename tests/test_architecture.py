"""Architecture rules: layer direction and import cycles (ArchUnitPython)."""

from pathlib import Path

from archunitpython import CheckOptions, assert_passes, project_files, project_layers

SRC = str(Path(__file__).parents[1] / "src" / "libviz")

OPTIONS = CheckOptions(ignore_type_checking_imports=True)


def test_layers():
    # core is the library MSIAnalyzer imports: it must never pull in Qt/GUI.
    rule = (
        project_layers(SRC)
        .layer("core").defined_by("**/libviz/core/**")
        .layer("cli").defined_by("**/libviz/cli/**")
        .layer("gui").defined_by("**/libviz/gui/**")
        .where_layer("core").may_not_depend_on_layers("cli", "gui")
        .where_layer("cli").may_not_depend_on_layers("gui")
    )
    assert_passes(rule, OPTIONS)


def test_no_cycles():
    violations = project_files(SRC).should().have_no_cycles().check(OPTIONS)
    assert not violations, violations
