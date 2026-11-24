import sys
import time
import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QDialog, QMenu, QMessageBox, QSystemTrayIcon
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import QObject, QPoint, QSettings, QTimer

from config import (
    DEFAULT_SETTINGS, DETECTION_INTERVAL, POLL_INTERVAL
)
from detection import DetectionWorker
from preview import Preview
from settings import SettingsDialog
from windows import get_cursor_position


def load_app_icon():
    app_dir = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)
    )
    return QIcon(str(app_dir / "assets" / "peekaboo.ico"))


class Peekaboo(QObject):
    def __init__(self, app, app_icon):
        super().__init__()

        self.app = app
        self.enabled = True
        self.settings_store = QSettings()
        self.settings = {
            key: self.settings_store.value(
                key, value, type=type(value)
            )
            for key, value in DEFAULT_SETTINGS.items()
        }
        self.preview = Preview(self.settings)
        self.pending_file = None
        self.last_position = (0, 0)
        self.last_detection = 0
        self.worker = None
        self.closing = False

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(self.settings["delay"])
        self.hover_timer.timeout.connect(self.show_preview)

        self.mouse_timer = QTimer(self)
        self.mouse_timer.setInterval(POLL_INTERVAL)
        self.mouse_timer.timeout.connect(self.check_mouse)
        self.mouse_timer.start()

        self.app_icon = app_icon
        self.tray = QSystemTrayIcon(self.app_icon)
        self.tray.setToolTip("Peekaboo - Enabled")

        menu = QMenu()
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.open_settings)

        self.toggle_action = QAction("Disable Peekaboo", self)
        self.toggle_action.triggered.connect(self.toggle)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit)

        menu.addAction(self.settings_action)
        menu.addSeparator()
        menu.addAction(self.toggle_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.show()

    def open_settings(self):
        dialog = SettingsDialog(self.settings)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.settings = dialog.selected_settings()
        self.preview.apply_settings(self.settings)
        self.hover_timer.setInterval(self.settings["delay"])

        for key, value in self.settings.items():
            self.settings_store.setValue(key, value)

        self.settings_store.sync()
        if self.settings_store.status() != QSettings.Status.NoError:
            QMessageBox.warning(
                dialog,
                "Peekaboo Settings",
                "Settings were applied, but could not be saved."
            )

    def check_mouse(self):
        if not self.enabled or self.closing:
            return

        position = get_cursor_position()
        if position is None:
            return

        x, y = position
        self.last_position = (x, y)

        if self.preview.isVisible():
            if self.preview.geometry().contains(QPoint(x, y)):
                return

        now = time.monotonic()
        if now - self.last_detection < DETECTION_INTERVAL / 1000:
            return

        self.last_detection = now
        if self.worker and self.worker.isRunning():
            return

        self.start_detection(x, y)

    def start_detection(self, x, y):
        worker = DetectionWorker(x, y)
        self.worker = worker

        worker.result.connect(self.handle_result)
        worker.finished.connect(
            lambda w=worker: self.worker_finished(w)
        )

        worker.start()

    def worker_finished(self, worker):
        if self.worker is worker:
            self.worker = None

        worker.deleteLater()

    def handle_result(self, path, x, y):
        if not self.enabled or self.closing:
            return

        current = get_cursor_position()
        if current is None:
            return

        if abs(current[0] - x) > 30 or abs(current[1] - y) > 30:
            return

        if not path:
            self.pending_file = None
            self.hover_timer.stop()
            self.preview.close_preview()
            return

        if path != self.pending_file:
            self.pending_file = path
            self.hover_timer.stop()
            self.hover_timer.start()

    def show_preview(self):
        if not self.enabled or self.closing:
            return

        if not self.pending_file:
            return

        position = get_cursor_position()
        if position is None:
            return

        self.preview.display(
            self.pending_file,
            position[0],
            position[1]
        )

    def toggle(self):
        self.enabled = not self.enabled
        self.pending_file = None

        self.hover_timer.stop()
        self.preview.close_preview()

        if self.enabled:
            self.toggle_action.setText("Disable Peekaboo")
            self.tray.setToolTip("Peekaboo - Enabled")
        else:
            self.toggle_action.setText("Enable Peekaboo")
            self.tray.setToolTip("Peekaboo - Disabled")

    def quit(self):
        if self.closing:
            return

        self.closing = True
        self.enabled = False

        self.mouse_timer.stop()
        self.hover_timer.stop()
        self.preview.close_preview()
        self.tray.hide()

        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        self.app.quit()


def main(argv=None):
    app = QApplication(sys.argv if argv is None else argv)
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName("Peekaboo")
    app.setApplicationName("Peekaboo")

    icon = load_app_icon()
    app.setWindowIcon(icon)

    application = Peekaboo(app, icon)

    try:
        return app.exec()
    except Exception:
        traceback.print_exc()
    finally:
        application.mouse_timer.stop()
        application.hover_timer.stop()

        if application.worker and application.worker.isRunning():
            application.worker.wait()

        application.preview.close_preview()
        application.tray.hide()


if __name__ == "__main__":
    sys.exit(main())
