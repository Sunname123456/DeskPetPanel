import os
import sys

os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--allow-file-access-from-files")

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView


app = QApplication(sys.argv)
view = QWebEngineView()
view.resize(340, 480)


def loaded(ok):
    print(f"loadFinished={ok}", flush=True)
    QTimer.singleShot(3000, app.quit)


view.loadFinished.connect(loaded)
view.load(QUrl.fromLocalFile(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web", "pet.html"))))
view.show()
QTimer.singleShot(15000, app.quit)
raise SystemExit(app.exec())
