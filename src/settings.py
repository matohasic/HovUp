from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QVBoxLayout
)


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Peekaboo Settings")

        self.max_width = QSpinBox()
        self.max_width.setRange(100, 1200)
        self.max_width.setSuffix(" px")
        self.max_width.setValue(settings["max_width"])

        self.max_height = QSpinBox()
        self.max_height.setRange(100, 1000)
        self.max_height.setSuffix(" px")
        self.max_height.setValue(settings["max_height"])

        self.opacity = QSpinBox()
        self.opacity.setRange(20, 100)
        self.opacity.setSuffix("%")
        self.opacity.setValue(settings["opacity"])

        self.delay = QSpinBox()
        self.delay.setRange(0, 3000)
        self.delay.setSuffix(" ms")
        self.delay.setValue(settings["delay"])

        self.offset = QSpinBox()
        self.offset.setRange(0, 100)
        self.offset.setSuffix(" px")
        self.offset.setValue(settings["offset"])

        self.animate = QCheckBox("Play animated GIF and WebP previews")
        self.animate.setChecked(settings["animate"])

        form = QFormLayout()
        form.addRow("Maximum width:", self.max_width)
        form.addRow("Maximum height:", self.max_height)
        form.addRow("Opacity:", self.opacity)
        form.addRow("Hover delay:", self.delay)
        form.addRow("Cursor offset:", self.offset)
        form.addRow(self.animate)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def selected_settings(self):
        return {
            "max_width": self.max_width.value(),
            "max_height": self.max_height.value(),
            "opacity": self.opacity.value(),
            "delay": self.delay.value(),
            "offset": self.offset.value(),
            "animate": self.animate.isChecked(),
        }
