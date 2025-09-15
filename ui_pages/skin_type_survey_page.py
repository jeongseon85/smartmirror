# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QGroupBox, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal

class SkinTypeSurveyPage(QWidget):
    submitted = pyqtSignal(str, dict)  # (skin_type, scores)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setObjectName("SkinTypeSurveyPage")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)

        title = QLabel("피부타입 간단 설문")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("h2")
        subtitle = QLabel("아래 5문항에 답해주세요. (1 전혀 아니다 · 2 거의 없다 · 3 가끔 · 4 자주 · 5 항상)")
        subtitle.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(title)
        self.layout.addWidget(subtitle)

        questions = [
            ("Q1. 오후 3~5시 T존(이마·코) 번들거림/광택이 눈에 띕니다.", "Q1"),
            ("Q2. 세안 후 10분 이내 당김·당겨서 표정이 불편하거나 각질이 올라옵니다.", "Q2"),
            ("Q3. 새 제품 사용/마찰/자외선 노출 후 24시간 내 따가움·가려움·홍조가 생깁니다.", "Q3"),
            ("Q4. 코·볼의 모공 확장/블랙헤드가 보이고, 유분 때문에 메이크업이 무너집니다.", "Q4"),
            ("Q5. 염증성 트러블(빨갛고 아픈 뾰루지)이 주 1회 이상 생깁니다.", "Q5"),
        ]
        self.groups = {}  # key -> QButtonGroup

        for text, key in questions:
            gb = QGroupBox(text)
            hb = QHBoxLayout(gb)
            bg = QButtonGroup(self)
            for score in range(1, 6):
                rb = QRadioButton(str(score))
                if score == 3:
                    rb.setChecked(True)  # 기본값 3
                bg.addButton(rb, score)
                hb.addWidget(rb)
            self.groups[key] = bg
            self.layout.addWidget(gb)

        btn_row = QHBoxLayout()
        self.submit_btn = QPushButton("다음 (결과 보기)")
        self.submit_btn.clicked.connect(self.on_submit)
        btn_row.addStretch()
        btn_row.addWidget(self.submit_btn)
        btn_row.addStretch()
        self.layout.addLayout(btn_row)

    def set_initial_info(self, personal_color: str, tone_number: str):
        # 필요 시 상단 안내에 반영 (옵션)
        pass

    def _get_answer(self, key):
        bg = self.groups.get(key)
        return bg.checkedId() if bg else 3

    def on_submit(self):
        Q1 = self._get_answer("Q1")
        Q2 = self._get_answer("Q2")
        Q3 = self._get_answer("Q3")
        Q4 = self._get_answer("Q4")
        Q5 = self._get_answer("Q5")

        # 채점 규칙
        oily = 0.50*Q1 + 0.40*Q4 + 0.25*Q5 - 0.20*Q2 + 0.10*Q3
        dry  = 0.60*Q2 - 0.30*Q1 - 0.20*Q4 - 0.10*Q5 + 0.10*Q3
        sens = 0.60*Q3 + 0.50*Q5 + 0.20*Q2 + 0.10*Q1 + 0.10*Q4

        scores = {"지성": oily, "건성": dry, "민감성": sens}
        skin_type = max(scores, key=scores.get)  # 최고 점수 타입

        self.submitted.emit(skin_type, scores)
