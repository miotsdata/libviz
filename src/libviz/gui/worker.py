import logging
from typing import Callable

from PySide6.QtCore import QObject, Qt, QThread, Signal

logger = logging.getLogger(__name__)


class Task(QThread):
    """Run ``fn(*args, **kwargs)`` off the GUI thread (ADR 2).

    The one worker every bridge uses: anything touching a DB or a file runs
    here, the result comes back through ``succeeded`` on the GUI thread.
    With ``with_progress=True``, ``fn`` also gets ``progress=callback`` and
    may call ``callback(done, total)``.

    One-shot: the task deletes itself when finished. Callers that need to
    keep it alive while running use :func:`start_task`.
    """

    succeeded = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)  # done, total

    def __init__(self, fn: Callable, *args, with_progress: bool = False, parent: QObject | None = None, **kwargs):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        if with_progress:
            self._kwargs["progress"] = self.progress.emit
        self.finished.connect(self.deleteLater)

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("task %s failed", getattr(self._fn, "__name__", self._fn))
            self.failed.emit(str(e) or type(e).__name__)
            return
        self.succeeded.emit(result)


def start_task(owner: QObject, fn: Callable, *args, on_success=None, on_error=None, on_progress=None,
               **kwargs) -> Task:
    """Create, wire and start a :class:`Task` parented to ``owner``.

    Callbacks are connected queued: a plain function/lambda has no thread of
    its own, and a direct call would run it on the worker thread. Queued, it
    runs in the task object's thread — the GUI thread.
    """
    task = Task(fn, *args, with_progress=on_progress is not None, parent=owner, **kwargs)
    queued = Qt.ConnectionType.QueuedConnection
    for signal, callback in ((task.succeeded, on_success), (task.failed, on_error),
                             (task.progress, on_progress)):
        if callback is not None:
            signal.connect(callback, queued)
    task.start()
    return task
