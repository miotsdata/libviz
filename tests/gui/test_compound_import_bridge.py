from libviz.core.library import Library
from libviz.gui.compound_import_bridge import CompoundImportBridge
from libviz.gui.library_bridge import LibraryBridge


def test_import_compounds_with_mapping(qapp, qtbot, tmp_path):
    table = tmp_path / "compounds.csv"
    table.write_text("Sigla,Nome,formula,Mass\nCA,Cholic acid,C24H40O5,408.2876\nX,,C1,\nLYS,Lysine-CA,C30H52N2O6,536.7\n")
    Library.create(tmp_path / "lib.db", name="Bile")
    libraries = LibraryBridge(parent=qapp)
    with qtbot.waitSignal(libraries.libraryOpened, timeout=5000):
        libraries.openLibrary(str(tmp_path / "lib.db"))
    bridge = CompoundImportBridge(libraries, parent=qapp)

    with qtbot.waitSignal(bridge.tableChanged, timeout=5000):
        bridge.load(str(table))
    assert bridge.sheets == [] and bridge.columns == ["", "Sigla", "Nome", "formula", "Mass"]
    assert {f["key"]: f["column"] for f in bridge.fields}["name"] == "Nome"
    assert bridge.summary == {"total": 3, "ok": 0, "warning": 2, "error": 1, "importable": 2}
    bridge.setMapping("name", "Sigla")  # every row has a Sigla
    assert bridge.summary["error"] == 0 and bridge.rows[0]["name"] == "CA"
    assert "differs from the formula" in bridge.rows[2]["message"]

    with qtbot.waitSignal(bridge.imported, timeout=5000) as blocker:
        bridge.importInto(libraries.selectedKey)
    assert "3 added" in blocker.args[1]
    assert blocker.args[2].startswith("Imported with warnings:\nline 2 CA: no InChIKey")
    assert "Skipped" not in blocker.args[2]
    lib = libraries.manager.library(libraries.selectedKey)
    assert lib.n_compounds == 3
    for library in libraries.manager.libraries.values():
        library.close()
