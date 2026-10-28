import threading

from PySide6.QtCore import QObject

from libviz.gui.worker import start_task


def test_success_callback_runs_on_gui_thread(qtbot):
    owner = QObject()
    seen = {}

    def work():
        seen["worker"] = threading.get_ident()
        return 42

    def done(result):
        seen["result"] = result
        seen["callback"] = threading.get_ident()

    start_task(owner, work, on_success=done)
    qtbot.waitUntil(lambda: "result" in seen)
    assert seen["result"] == 42
    assert seen["callback"] == threading.get_ident() != seen["worker"]


def test_failure_reports_message(qtbot):
    owner = QObject()
    errors = []

    def boom():
        raise ValueError("bad file")

    start_task(owner, boom, on_error=errors.append)
    qtbot.waitUntil(lambda: bool(errors))
    assert errors == ["bad file"]


def test_progress_is_injected(qtbot):
    owner = QObject()
    steps, results = [], []

    def work(progress):
        for i in range(3):
            progress(i + 1, 3)
        return "ok"

    start_task(owner, work, on_success=results.append, on_progress=lambda d, t: steps.append((d, t)))
    qtbot.waitUntil(lambda: bool(results))
    assert steps == [(1, 3), (2, 3), (3, 3)]
