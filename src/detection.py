import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from config import IMAGE_EXTENSIONS
from windows import (
    get_explorer_folder, get_process_id, get_root_window, get_window_at
)


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
