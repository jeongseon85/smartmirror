# -*- coding: utf-8 -*-
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

class WebcamThread(QThread):
    # (미리보기 QImage, OCR용 원본 BGR)
    change_pixmap_signal = pyqtSignal(QImage, object)

    def __init__(self, rotate=False, mirror=False, parent=None):
        super().__init__(parent)
        self.running = True
        self.cap = None
        self.rotate = rotate
        self.mirror = mirror

    def run(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            print("Error: 웹캠을 열 수 없습니다.")
            self.running = False
            return

        while self.running:
            ret, frame_bgr = self.cap.read()
            if not ret:
                continue

            if self.rotate:
                frame_bgr = cv2.rotate(frame_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            if self.mirror:
                frame_bgr = cv2.flip(frame_bgr, 1)

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

            self.change_pixmap_signal.emit(qimg, frame_bgr)

        if self.cap:
            self.cap.release()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()
