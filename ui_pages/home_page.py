# ui_pages/home_page.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen

class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.product_btn = QPushButton("제품 촬영")
        self.product_btn.setObjectName("main_menu_btn") # objectName 추가
        
        self.face_btn = QPushButton("얼굴 촬영")
        self.face_btn.setObjectName("main_menu_btn") # objectName 추가
        
        layout.addWidget(self.product_btn)
        layout.addSpacing(20)
        layout.addWidget(self.face_btn)
        
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def update_frame(self, qimg, raw_bgr):
        # 홈 페이지에는 웹캠 미리보기가 없으므로 이 함수는 필요 없지만,
        # main.py에서 update_frame을 호출할 때 오류가 발생하지 않도록
        # 빈 함수로 남겨두거나, 아예 호출 로직을 제거하는 것이 좋습니다.
        # 이전에 제안했던 main.py 수정 코드는 이미 이 문제를 해결했습니다.
        pass

    # 웹캠 프레임 업데이트 함수도 더 이상 필요 없으므로 제거
    # def update_frame(self, qimg, raw_bgr=None):
    #     if qimg is not None and not qimg.isNull():
    #         self.webcam_label.setPixmap(QPixmap.fromImage(qimg).scaled(self.webcam_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))