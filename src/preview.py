import os
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel, QWidget
from PySide6.QtGui import QImageReader, QMovie, QPixmap
from PySide6.QtCore import (
    QByteArray, QBuffer, QIODevice, QPoint, QSize, Qt
)


def calculate_preview_size(size, max_width, max_height):
    if not size.isValid():
        return QSize(
            min(200, max_width - 4),
            min(150, max_height - 4)
        )

    return size.scaled(
        max_width - 4,
        max_height - 4,
        Qt.AspectRatioMode.KeepAspectRatio
    )


class Preview(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings.copy()

        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: 2px solid #333333;
                border-radius: 4px;
                padding: 0px;
            }
        """)

        self.movie = None
        self.movie_buffer = None
        self.current_file = None
        self.static_pixmap = None
        self.source_size = QSize()
        self.last_position = (0, 0)

        self.resize(200, 150)
        self.setWindowOpacity(self.settings["opacity"] / 100)

    def apply_settings(self, settings):
        animate_was_enabled = self.settings["animate"]
        self.settings = settings.copy()
        self.setWindowOpacity(self.settings["opacity"] / 100)

        if animate_was_enabled and not self.settings["animate"] and self.movie:
            frame = self.movie.currentImage()
            self._release_movie()
            self.static_pixmap = QPixmap.fromImage(frame)
            self.source_size = self.static_pixmap.size()
            self.image_label.setPixmap(self.static_pixmap)
        elif (
            not animate_was_enabled
            and self.settings["animate"]
            and self.current_file
            and self.current_file.lower().endswith((".gif", ".webp"))
            and os.path.isfile(self.current_file)
        ):
            path = self.current_file
            self.current_file = None
            self.display(path, *self.last_position)

        self._update_image_size()
        if self.isVisible():
            self._position_at(*self.last_position)

    def display(self, path, x, y):
        if not os.path.isfile(path):
            self.close_preview()
            return

        self.last_position = (x, y)

        try:
            if self.current_file != path:
                self._release_movie()
                self.image_label.clear()
                self.current_file = path
                self.static_pixmap = None
                self.source_size = QSize()

                if (
                    self.settings["animate"]
                    and path.lower().endswith((".gif", ".webp"))
                ):
                    reader = QImageReader(path)
                    self.source_size = reader.size()

                    self.movie_buffer = QBuffer(self)
                    self.movie_buffer.setData(
                        QByteArray(Path(path).read_bytes())
                    )

                    if not self.movie_buffer.open(
                        QIODevice.OpenModeFlag.ReadOnly
                    ):
                        raise OSError(
                            f"Unable to read animated image: {path}"
                        )

                    self.movie = QMovie(self.movie_buffer)
                    self.image_label.setMovie(self.movie)
                    self._update_image_size()
                    self.movie.start()
                else:
                    pixmap = QPixmap(path)
                    if pixmap.isNull():
                        self.close_preview()
                        return

                    self.static_pixmap = pixmap
                    self.source_size = pixmap.size()
                    self._update_image_size()

            self._position_at(x, y)
            self.show()

        except Exception:
            traceback.print_exc()
            self.close_preview()

    def close_preview(self):
        self._release_movie()
        self.image_label.clear()
        self.static_pixmap = None
        self.source_size = QSize()
        self.hide()
        self.current_file = None

    def _release_movie(self):
        if self.movie:
            movie = self.movie
            self.movie = None
            movie.stop()
            self.image_label.setMovie(None)
            movie.setDevice(None)
            movie.deleteLater()

        if self.movie_buffer:
            buffer = self.movie_buffer
            self.movie_buffer = None
            buffer.close()
            buffer.deleteLater()

    def _update_image_size(self):
        if (
            not self.source_size.isValid()
            and not self.movie
            and not self.static_pixmap
        ):
            return

        target_size = calculate_preview_size(
            self.source_size,
            self.settings["max_width"],
            self.settings["max_height"]
        )

        if self.movie:
            self.movie.setScaledSize(target_size)
        elif self.static_pixmap:
            self.image_label.setPixmap(
                self.static_pixmap.scaled(
                    target_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

        self.setFixedSize(
            target_size.width() + 4,
            target_size.height() + 4
        )
        self.image_label.setGeometry(
            0, 0, self.width(), self.height()
        )

    def _position_at(self, x, y):
        screen = QApplication.screenAt(QPoint(int(x), int(y)))
        if not screen:
            return

        area = screen.availableGeometry()
        offset = self.settings["offset"]
        px = x + offset
        py = y + offset

        if px + self.width() > area.right():
            px = x - self.width() - offset

        if py + self.height() > area.bottom():
            py = y - self.height() - offset

        px = max(area.left(), px)
        py = max(area.top(), py)
        self.move(int(px), int(py))
