
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

class DebugPanel(QWidget):
    cleared = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Debug Console')
        self.resize(680, 420)
        v = QVBoxLayout(self)
        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        v.addWidget(self.text)
        hb = QHBoxLayout()
        clear_btn = QPushButton('Clear')
        clear_btn.clicked.connect(self.clear)
        hb.addStretch(1); hb.addWidget(clear_btn)
        v.addLayout(hb)

    def log(self, msg: str):
        self.text.append(msg)

    def clear(self):
        self.text.clear()
        self.cleared.emit()
