# Peekaboo

Peekaboo is a lightweight Windows 10 utility that shows an image preview when
you hover over an image file in File Explorer. Previews appear beside the cursor
and are scaled to fit within a maximum of 350 × 300 pixels by default.

Supported formats: JPG/JPEG, PNG, GIF, BMP, TIFF, and WebP. Animated GIF and
WebP previews play from memory, so the original file can still be moved or
deleted while its preview is visible.

Peekaboo runs in the system tray. Use its context menu to enable or disable
previews, or exit the application.

Open **Settings** from the tray menu to adjust the maximum preview dimensions,
opacity, hover delay, cursor offset, and animated GIF/WebP playback. Settings
are saved for the next launch in the current user's Windows Registry at
`HKEY_CURRENT_USER\Software\Peekaboo\Peekaboo`.

## Development

### Source files

- [`application.py`](./src/application.py) — application entry point, tray menu,
  and main event handling.
- [`config.py`](./src/config.py) — preview defaults, timing values, and supported
  image extensions.
- [`detection.py`](./src/detection.py) — worker that identifies the image under
  the cursor in File Explorer.
- [`icons.py`](./src/icons.py) — system tray application icon.
- [`preview.py`](./src/preview.py) — image preview window and rendering.
- [`settings.py`](./src/settings.py) — settings dialog and its controls.
- [`windows.py`](./src/windows.py) — Windows API calls and Explorer folder
  detection.

### Run from source

From the repository root, install the dependencies and start Peekaboo:

```powershell
python -m pip install PySide6 pywin32 psutil pywinauto pyinstaller
python .\src\application.py
```

### Build and start the executable

Build the standalone Windows executable from the repository root:

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name Peekaboo src\application.py
```

The executable is created at `dist\Peekaboo.exe`. Start it with:

```powershell
.\dist\Peekaboo.exe
```

## Nightly Windows build

GitHub Actions builds `Peekaboo.exe` every day at 02:00 UTC. You can also start
a build from the **Actions** tab using **Run workflow**. Download the executable
from the completed workflow run's **Artifacts** section; artifacts are kept for
7 days.
