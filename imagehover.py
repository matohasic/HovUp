
import sys
import os
import time
import ctypes
import traceback

from pathlib import Path
from urllib.parse import urlparse, unquote

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QSystemTrayIcon, QMenu
)

from PySide6.QtGui import (
    QPixmap, QMovie, QAction, QIcon,
    QPainter, QColor, QPen, QBrush,
    QLinearGradient, QPolygon, QImageReader
)

from PySide6.QtCore import (
    Qt, QTimer, QPoint, QSize,
    QThread, Signal, QObject
)


# =====================================================
# WINDOWS API
# =====================================================

user32 = ctypes.windll.user32


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long)
    ]


def get_cursor_position():
    point = POINT()
    if user32.GetCursorPos(ctypes.byref(point)):
        return point.x, point.y
    return None


def get_window_at(x, y):
    return user32.WindowFromPoint(POINT(x, y))


def get_root_window(hwnd):
    return user32.GetAncestor(hwnd, 2)


def get_process_id(hwnd):
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


# =====================================================
# IMAGEHOVER ICON
# =====================================================

def create_app_icon():

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, 64, 64)
    gradient.setColorAt(0, QColor("#4285F4"))
    gradient.setColorAt(1, QColor("#7138D8"))

    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 15, 15)

    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(11, 12, 36, 30, 5, 5)

    painter.setBrush(QColor("#DCEBFF"))
    painter.drawRoundedRect(14, 15, 30, 24, 3, 3)

    painter.setBrush(QColor("#4285F4"))
    painter.drawPolygon(QPolygon([
        QPoint(14, 37),
        QPoint(24, 24),
        QPoint(31, 32),
        QPoint(37, 26),
        QPoint(44, 37)
    ]))

    painter.setBrush(QColor("#FFC857"))
    painter.drawEllipse(34, 18, 6, 6)

    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#FFFFFF"), 5))
    painter.drawEllipse(31, 30, 22, 22)

    painter.setPen(QPen(QColor("#FFFFFF"), 6))
    painter.drawLine(48, 48, 57, 57)

    painter.end()

    return QIcon(pixmap)


# =====================================================
# CONFIGURATION
# =====================================================

PREVIEW_MAX_WIDTH = 350
PREVIEW_MAX_HEIGHT = 300

HOVER_DELAY = 100
POLL_INTERVAL = 100
DETECTION_INTERVAL = 200

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif",
    ".bmp", ".tif", ".tiff", ".webp"
}


# =====================================================
# SIZE CALCULATION
# =====================================================

def calculate_preview_size(size):

    if not size.isValid():
        return QSize(200, 150)

    return size.scaled(
        PREVIEW_MAX_WIDTH - 4,
        PREVIEW_MAX_HEIGHT - 4,
        Qt.AspectRatioMode.KeepAspectRatio
    )


# =====================================================
# EXPLORER FOLDER DETECTION
# =====================================================

def get_explorer_folder(hwnd):

    import win32com.client

    try:
        shell = win32com.client.Dispatch(
            "Shell.Application"
        )

        for window in shell.Windows():

            try:
                if int(window.HWND) != int(hwnd):
                    continue

                parsed = urlparse(window.LocationURL)

                if parsed.scheme.lower() != "file":
                    return None

                path = unquote(parsed.path)

                if parsed.netloc:
                    path = "\\\\" + parsed.netloc + path

                elif (
                    len(path) >= 3
                    and path[0] == "/"
                    and path[2] == ":"
                ):
                    path = path[1:]

                return os.path.normpath(path)

            except Exception:
                continue

    except Exception as error:
        print("Shell folder error:", error)

    return None


# =====================================================
# DETECTION WORKER
# =====================================================

class DetectionWorker(QThread):

    result = Signal(object, int, int)

    def __init__(self, x, y):
        super().__init__()
        self.x = x
        self.y = y

    def run(self):

        import pythoncom
        initialized = False
        result = None

        try:
            pythoncom.CoInitializeEx(
                pythoncom.COINIT_APARTMENTTHREADED
            )
            initialized = True

            import psutil
            from pywinauto import Desktop

            hwnd = get_window_at(self.x, self.y)

            if not hwnd:
                return

            root = get_root_window(hwnd)
            pid = get_process_id(root)

            if not pid:
                return

            if psutil.Process(pid).name().lower() != "explorer.exe":
                return

            folder = get_explorer_folder(root)

            if not folder or not os.path.isdir(folder):
                return

            desktop = Desktop(backend="uia")
            element = desktop.from_point(self.x, self.y)

            for _ in range(12):

                if element is None:
                    break

                try:
                    name = (
                        element.element_info.name or ""
                    ).strip()

                    candidate = Path(name)

                    if not candidate.is_absolute():
                        candidate = Path(folder) / name

                    if (
                        candidate.is_file()
                        and candidate.suffix.lower() in IMAGE_EXTENSIONS
                    ):
                        result = str(candidate.resolve())
                        break

                except Exception:
                    pass

                try:
                    element = element.parent()
                except Exception:
                    break

        except Exception as error:
            print("Detection worker error:", error)

        finally:
            if initialized:
                pythoncom.CoUninitialize()

            self.result.emit(result, self.x, self.y)


# =====================================================
# PREVIEW WINDOW
# =====================================================

class Preview(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)

        self.image_label = QLabel(self)

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: 2px solid #333333;
                border-radius: 4px;
                padding: 0px;
            }
        """)

        self.movie = None
        self.current_file = None

        self.resize(200, 150)

    def display(self, path, x, y):

        if not os.path.isfile(path):
            self.close_preview()
            return

        try:

            if self.current_file != path:

                if self.movie:
                    self.movie.stop()

                self.movie = None
                self.image_label.clear()
                self.current_file = path

                if path.lower().endswith(".gif"):

                    reader = QImageReader(path)
                    target_size = calculate_preview_size(reader.size())

                    self.movie = QMovie(path)
                    self.movie.setScaledSize(target_size)

                    self.image_label.setMovie(self.movie)

                    self.setFixedSize(
                        target_size.width() + 4,
                        target_size.height() + 4
                    )

                    self.image_label.setGeometry(
                        0, 0, self.width(), self.height()
                    )

                    self.movie.start()

                else:

                    pixmap = QPixmap(path)

                    if pixmap.isNull():
                        self.close_preview()
                        return

                    target_size = calculate_preview_size(pixmap.size())

                    scaled = pixmap.scaled(
                        target_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )

                    self.image_label.setPixmap(scaled)

                    self.setFixedSize(
                        scaled.width() + 4,
                        scaled.height() + 4
                    )

                    self.image_label.setGeometry(
                        0, 0, self.width(), self.height()
                    )

            screen = QApplication.screenAt(QPoint(int(x), int(y)))

            if screen:

                area = screen.availableGeometry()

                px = x + 25
                py = y + 25

                if px + self.width() > area.right():
                    px = x - self.width() - 25

                if py + self.height() > area.bottom():
                    py = y - self.height() - 25

                px = max(area.left(), px)
                py = max(area.top(), py)

                self.move(int(px), int(py))

            self.show()

        except Exception:
            traceback.print_exc()
            self.close_preview()

    def close_preview(self):

        if self.movie:
            self.movie.stop()
            self.movie = None

        self.hide()
        self.current_file = None


# =====================================================
# MAIN APPLICATION
# =====================================================

class ImageHover(QObject):

    def __init__(self, app):
        super().__init__()

        self.app = app
        self.enabled = True
        self.preview = Preview()
        self.pending_file = None
        self.last_position = (0, 0)
        self.last_detection = 0
        self.worker = None
        self.closing = False

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(HOVER_DELAY)
        self.hover_timer.timeout.connect(self.show_preview)

        self.mouse_timer = QTimer(self)
        self.mouse_timer.setInterval(POLL_INTERVAL)
        self.mouse_timer.timeout.connect(self.check_mouse)
        self.mouse_timer.start()

        self.app_icon = create_app_icon()

        self.tray = QSystemTrayIcon(self.app_icon)
        self.tray.setToolTip("ImageHover - Enabled")

        menu = QMenu()

        self.toggle_action = QAction(
            "Disable ImageHover", self
        )
        self.toggle_action.triggered.connect(self.toggle)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit)

        menu.addAction(self.toggle_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.show()

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
            self.toggle_action.setText("Disable ImageHover")
            self.tray.setToolTip("ImageHover - Enabled")
        else:
            self.toggle_action.setText("Enable ImageHover")
            self.tray.setToolTip("ImageHover - Disabled")

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


# =====================================================
# START APPLICATION
# =====================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("ImageHover")

    icon = create_app_icon()
    app.setWindowIcon(icon)

    application = ImageHover(app)

    try:
        sys.exit(app.exec())

    except Exception:
        traceback.print_exc()

    finally:
        application.mouse_timer.stop()
        application.hover_timer.stop()

        if application.worker and application.worker.isRunning():
            application.worker.wait()

        application.preview.close_preview()
        application.tray.hide()
