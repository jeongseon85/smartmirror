from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class LoadingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        self.title_label = QLabel("로딩 중...")
        self.title_label.setStyleSheet("font-size: 2em; color: #ff87ab; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.loader_label = QLabel("잠시만 기다려 주세요")
        self.loader_label.setStyleSheet("font-size: 1.2em; color: #555;")
        self.loader_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.title_label)
        layout.addSpacing(20)
        layout.addWidget(self.loader_label)

    def set_message(self, title, subtitle):
        self.title_label.setText(title)
        self.loader_label.setText(subtitle)