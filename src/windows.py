import ctypes
import os
from urllib.parse import urlparse, unquote


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


def get_explorer_folder(hwnd):
    import win32com.client

    try:
        shell = win32com.client.Dispatch("Shell.Application")

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
