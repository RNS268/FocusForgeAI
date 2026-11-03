from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import FocusForgeMainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FocusForgeMainWindow()
    window.show()
    sys.exit(app.exec())
