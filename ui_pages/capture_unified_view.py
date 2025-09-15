# -*- coding: utf-8 -*-
# capture_unified_view_kiosk.py
# PyQt5 / Python 3.6 compatible
import os
import csv
import re
import numpy as np
import cv2
from PyQt5 import QtWidgets as QtW, QtGui as QtG, QtCore as QtC

# result_pages에서 중복 정의된 클래스 가져오기
from .result_pages import ProductDetailDialog, ClickableLabel

class SnappingSlider(QtW.QSlider):
    """클릭 시 가장 가까운 정수 값으로 이동하는 슬라이더."""
    def mousePressEvent(self, event: QtG.QMouseEvent):
        if event.button() == QtC.Qt.LeftButton:
            opt = QtW.QStyleOptionSlider()
            self.initStyleOption(opt)
            handle_rect = self.style().subControlRect(QtW.QStyle.CC_Slider, opt, QtW.QStyle.SC_SliderHandle, self)

            # 핸들이 아닌 슬라이더의 빈 공간(groove)을 클릭했을 때만 동작
            if not handle_rect.contains(event.pos()):
                groove_rect = self.style().subControlRect(QtW.QStyle.CC_Slider, opt, QtW.QStyle.SC_SliderGroove, self)
                if self.orientation() == QtC.Qt.Horizontal:
                    pos = event.pos().x() - groove_rect.x()
                    span = groove_rect.width()
                else:
                    pos = event.pos().y() - groove_rect.y()
                    span = groove_rect.height()

                if span > 0:
                    pos_ratio = pos / span
                    value_range = self.maximum() - self.minimum()

                    if self.invertedAppearance():
                        new_value = self.maximum() - (value_range * pos_ratio)
                    else:
                        new_value = self.minimum() + (value_range * pos_ratio)

                    self.setValue(round(new_value))
                    super().mousePressEvent(event)
                    return
        super().mousePressEvent(event)

def open_url_external(url):
    QtG.QDesktopServices.openUrl(QtC.QUrl(url or ""))

class MiniProductCard(QtW.QFrame):
    clicked = QtC.pyqtSignal(dict)

    def __init__(self, product=None, parent=None):
        super(MiniProductCard, self).__init__(parent)
        self.setObjectName("MiniProductCard")
        self.setFrameShape(QtW.QFrame.NoFrame)
        self.setStyleSheet("#MiniProductCard{border:none;background:transparent;}")
        self.setMinimumSize(140, 170)

        self._product = None
        self.img = QtW.QLabel("이미지", self)
        self.img.setAlignment(QtC.Qt.AlignCenter)
        self.img.setFixedSize(120, 120)
        self.img.setStyleSheet("background:transparent;")
        self.name = QtW.QLabel("제품명", self)
        self.name.setAlignment(QtC.Qt.AlignHCenter | QtC.Qt.AlignTop)
        self.name.setWordWrap(True)
        font = self.name.font()
        font.setPointSize(15)
        self.name.setFont(font)

        v = QtW.QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        v.addWidget(self.img, 0, QtC.Qt.AlignHCenter)
        v.addWidget(self.name)

        self.set_product(product)

    def mousePressEvent(self, e):
        if self._product:
            self.clicked.emit(self._product)
        super(MiniProductCard, self).mousePressEvent(e)

    def set_product(self, p):
        self._product = p
        if not p:
            self.img.setText("이미지")
            self.name.setText("제품명")
            return
        self.name.setText(p.get("name", "제품명"))
        img_path = p.get("img")
        if img_path:
            pix = QtG.QPixmap(img_path)
            if not pix.isNull():
                self.img.setPixmap(pix.scaled(self.img.size(), QtC.Qt.KeepAspectRatio, QtC.Qt.SmoothTransformation))
            else:
                self.img.setText("이미지\n로드 실패")
        else:
            self.img.setText("이미지 없음")

class Carousel(QtW.QWidget):
    cardClicked = QtC.pyqtSignal(dict)

    def __init__(self, parent=None):
        super(Carousel, self).__init__(parent)
        self.stack = QtW.QStackedWidget(self)
        self.prevBtn = QtW.QPushButton("←")
        self.nextBtn = QtW.QPushButton("→")
        self.prevBtn.setFixedWidth(50)
        self.nextBtn.setFixedWidth(50)

        self.prevBtn.clicked.connect(self.prev)
        self.nextBtn.clicked.connect(self.next)

        h = QtW.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(self.prevBtn, 0, QtC.Qt.AlignVCenter)
        h.addWidget(self.stack, 1)
        h.addWidget(self.nextBtn, 0, QtC.Qt.AlignVCenter)

        self._items = []

    def set_items(self, products):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        self._items = products or []
        if not self._items:
            self.stack.addWidget(MiniProductCard(None))
            return
        for p in self._items:
            card = MiniProductCard(p)
            card.clicked.connect(self.cardClicked)
            self.stack.addWidget(card)
        self.stack.setCurrentIndex(0)

    def prev(self):
        if self.stack.count():
            i = (self.stack.currentIndex() - 1) % self.stack.count()
            self.stack.setCurrentIndex(i)

    def next(self):
        if self.stack.count():
            i = (self.stack.currentIndex() + 1) % self.stack.count()
            self.stack.setCurrentIndex(i)

class CategorySection(QtW.QFrame):
    productClicked = QtC.pyqtSignal(dict)

    def __init__(self, title, parent=None):
        super(CategorySection, self).__init__(parent)
        self.setObjectName("CategorySection")
        self.setFrameShape(QtW.QFrame.NoFrame)
        self.setStyleSheet("QFrame#CategorySection{background:transparent;}")

        self.title = QtW.QLabel(title)
        tfont = self.title.font()
        tfont.setPointSize(16)
        tfont.setBold(True)
        self.title.setFont(tfont)

        self.carousel = Carousel()
        self.carousel.cardClicked.connect(self.productClicked)

        v = QtW.QVBoxLayout(self)
        v.setContentsMargins(8, 12, 8, 12)
        v.setSpacing(6)
        v.addWidget(self.title)
        v.addWidget(self.carousel)

    def set_items(self, products):
        # products: [{name, img, price, desc, ...}]
        self.carousel.set_items(products or [])

class MakeupTipsSection(QtW.QFrame):
    def __init__(self, parent=None):
        super(MakeupTipsSection, self).__init__(parent)
        self.setObjectName("MakeupTipsSection")
        self.setFrameShape(QtW.QFrame.NoFrame)
        self.setStyleSheet("QFrame#MakeupTipsSection{background:transparent;}")

        self.title = QtW.QLabel("추천화장법")
        tfont = self.title.font()
        tfont.setPointSize(20)
        tfont.setBold(True)
        self.title.setFont(tfont)

        self.listBox = QtW.QVBoxLayout()
        self.listBox.setSpacing(8)

        v = QtW.QVBoxLayout(self)
        v.setContentsMargins(8, 12, 8, 12)
        v.addWidget(self.title)
        holder = QtW.QWidget()
        holder.setLayout(self.listBox)
        holder.setStyleSheet("background:transparent;")
        v.addWidget(holder)

    def set_items(self, tip_items):
        while True:
            item = self.listBox.takeAt(0)
            if not item:
                break
            w = item.widget()
            if w:
                w.deleteLater()
        for tip in tip_items or []:
            row = QtW.QFrame()
            row.setFrameShape(QtW.QFrame.NoFrame)
            row.setStyleSheet("background:transparent;")
            h = QtW.QHBoxLayout(row)
            h.setContentsMargins(0,0,0,0)
            thumb = QtW.QLabel()
            thumb.setFixedSize(60, 60)
            thumb.setStyleSheet("background:transparent;")
            if tip.get("thumb"):
                pix = QtG.QPixmap(tip["thumb"])
                if not pix.isNull():
                    thumb.setPixmap(pix.scaled(thumb.size(), QtC.Qt.KeepAspectRatio, QtC.Qt.SmoothTransformation))
                else:
                    thumb.setText("썸네일\n실패")
            else:
                thumb.setText("썸네일")
            titleBtn = QtW.QPushButton(tip.get("title", "영상 보기"))
            titleBtn.clicked.connect(lambda _=False, u=tip.get("url"): open_url_external(u or ""))
            h.addWidget(thumb)
            h.addWidget(titleBtn, 1)
            self.listBox.addWidget(row)
        self.listBox.addStretch(1)

class SurveyPanel(QtW.QWidget):
    """오른쪽 패널의 피부진단 섹션(문항 → 슬라이더, 미리보기 제공)"""
    scoresChanged = QtC.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SurveyPanel")

        # 스타일시트를 개선하여 가독성과 디자인을 향상시킵니다.
        self.setStyleSheet("""
        QWidget#SurveyPanel { background: transparent; }
        QLabel#Guide   { font-size: 22px; font-weight: 600; color: #212529; }
        QLabel#Sub     { font-size: 15px; color: #6c757d; }
        QLabel#TickLabel { font-size: 13px; color: #868e96; }
        QLabel#Q       { font-size: 16px; font-weight: 500; color: #343a40; }

        QSlider::groove:horizontal {
            height: 6px;
            background: #e9ecef;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            width: 20px; height: 20px; margin: -7px 0;
            border-radius: 10px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a8c0d3, stop:1 #8faabf);
            border: 1px solid rgba(0,0,0,0.1);
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a8c0d3, stop:1 #8faabf);
            border-radius: 3px;
        }

        QFrame#PreviewContainer {
            background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f8f9fa);
            border: 1px solid #e9ecef;
            border-radius: 12px;
        }
        QLabel#PreviewTitle {
            font-size: 18px; color: #6c757d; font-weight: 500;
            padding-top: 8px;
        }
        QLabel#PreviewResult {
            /* 참고: 아래 폰트들이 시스템에 설치되어 있어야 적용됩니다. */
            /* Cafe24 Ssurround, Gmarket Sans 등 귀여운 느낌의 폰트를 우선으로 설정했습니다. */
            font-family: "Cafe24 Ssurround", "Gmarket Sans", "NanumSquareRound", "Malgun Gothic", sans-serif;
            font-size: 80px; font-weight: 700;
            color: #94B7CF;
            padding-bottom: 8px;
        }
        """)

        self.question_texts = [
            "오후 3~5시 T존(이마·코) 번들거림/광택이 눈에 띈다.",
            "세안 후 10분 이내 당김·각질이 올라온다.",
            "새 제품/자외선/마찰 후 24시간 내 따가움·가려움·홍조가 생긴다.",
            "모공 확장/블랙헤드가 보이고 유분으로 메이크업이 무너진다.",
            "염증성 트러블(빨갛고 아픈 뾰루지)이 주 1회 이상 생긴다.",
        ]
        self.sliders = []

        v = QtW.QVBoxLayout(self)
        v.setContentsMargins(15, 15, 15, 15)
        v.setSpacing(10)

        guide = QtW.QLabel("피부진단"); guide.setObjectName("Guide")
        sub   = QtW.QLabel("최근 2주 기준 · 1~5로 응답"); sub.setObjectName("Sub")
        scale_guide = QtW.QLabel("1: 전혀 아니다 · 2: 거의 없다 · 3: 가끔 · 4: 자주 · 5: 항상")
        scale_guide.setObjectName("Sub") # 부제목과 동일한 스타일 적용
        v.addWidget(guide)
        v.addWidget(sub)
        v.addWidget(scale_guide)

        v.addSpacing(20) # 제목과 질문 목록 사이에 여백을 추가합니다.
        # 질문과 질문 사이에 Stretch를 추가하여 패널 높이에 맞게 분산시킵니다.
        v.addStretch(1)

        for i, q_text in enumerate(self.question_texts):
            qlab = QtW.QLabel(f"{i+1}) {q_text}"); qlab.setObjectName("Q"); qlab.setWordWrap(True)
            v.addWidget(qlab)

            # 클릭 시 스냅 기능이 있는 커스텀 슬라이더로 교체
            sld = SnappingSlider(QtC.Qt.Horizontal)
            sld.setMinimum(1); sld.setMaximum(5); sld.setValue(3)
            sld.setTickInterval(1); sld.setSingleStep(1)
            sld.setTickPosition(QtW.QSlider.TicksBelow) # 눈금 표시 추가
            sld.valueChanged.connect(self._on_value_changed)
            v.addWidget(sld)
            self.sliders.append(sld)

            # 슬라이더 아래에 숫자 레이블 추가
            labels_layout = QtW.QHBoxLayout()
            # 좌우 여백을 줘서 슬라이더 핸들이 끝에 닿았을 때 숫자와 겹치지 않게 합니다.
            labels_layout.setContentsMargins(10, 0, 10, 0)

            lbl1 = QtW.QLabel("1"); lbl1.setObjectName("TickLabel"); lbl1.setAlignment(QtC.Qt.AlignLeft)
            lbl2 = QtW.QLabel("2"); lbl2.setObjectName("TickLabel"); lbl2.setAlignment(QtC.Qt.AlignCenter)
            lbl3 = QtW.QLabel("3"); lbl3.setObjectName("TickLabel"); lbl3.setAlignment(QtC.Qt.AlignCenter)
            lbl4 = QtW.QLabel("4"); lbl4.setObjectName("TickLabel"); lbl4.setAlignment(QtC.Qt.AlignCenter)
            lbl5 = QtW.QLabel("5"); lbl5.setObjectName("TickLabel"); lbl5.setAlignment(QtC.Qt.AlignRight)

            labels_layout.addWidget(lbl1); labels_layout.addStretch(1)
            labels_layout.addWidget(lbl2); labels_layout.addStretch(1)
            labels_layout.addWidget(lbl3); labels_layout.addStretch(1)
            labels_layout.addWidget(lbl4); labels_layout.addStretch(1)
            labels_layout.addWidget(lbl5)
            v.addLayout(labels_layout)
            v.addStretch(1)

        # 마지막 Stretch를 제거하고, 결과 미리보기와 더 많은 공간을 둡니다.
        v.takeAt(v.count() - 1)
        v.addStretch(2)

        # --- 결과 미리보기 섹션 ---
        preview_container = QtW.QFrame()
        preview_container.setObjectName("PreviewContainer")
        preview_layout = QtW.QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(20, 15, 20, 15) # 카드 내부 여백을 늘려줍니다.

        preview_title = QtW.QLabel("예상 피부 타입")
        preview_title.setObjectName("PreviewTitle")
        preview_title.setAlignment(QtC.Qt.AlignCenter)

        self.preview_result = QtW.QLabel("-")
        self.preview_result.setObjectName("PreviewResult")
        self.preview_result.setAlignment(QtC.Qt.AlignCenter)

        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.preview_result)
        v.addWidget(preview_container)

        self._update_preview()

    # ---------- 내부 로직 ----------
    def _scores(self) -> list:
        return [s.value() for s in self.sliders]

    def _score_skin_type(self, Q1, Q2, Q3, Q4, Q5):
        oily = 0.50*Q1 + 0.40*Q4 + 0.25*Q5 - 0.20*Q2 + 0.10*Q3
        dry  = 0.60*Q2 - 0.30*Q1 - 0.20*Q4 - 0.10*Q5 + 0.10*Q3
        sens = 0.60*Q3 + 0.50*Q5 + 0.20*Q2 + 0.10*Q1 + 0.10*Q4
        scores = {"지성": oily, "건성": dry, "민감성": sens}
        top = max(scores.values())
        if abs(scores["민감성"] - top) < 1e-9: skin = "민감성"
        elif abs(scores["지성"] - top) < 1e-9: skin = "지성"
        else: skin = "건성"
        return skin, scores

    def infer_skin_type(self) -> str:
        return self._score_skin_type(*self._scores())[0]

    def _update_preview(self):
        skin_type = self.infer_skin_type()
        self.preview_result.setText(skin_type or "-")

    # ---------- 시그널/외부 API ----------
    def _on_value_changed(self, _):
        vals = self._scores()
        self.scoresChanged.emit(vals)
        self._update_preview()

    def set_preview_text(self, text: str):
        self.preview_result.setText(text or "-")

class SimpleCarousel(QtW.QFrame):
    clicked = QtC.pyqtSignal(dict)

    # 카드 이미지 한 변 픽셀 (원하면 200~240 사이로 취향대로)
    IMG_SIDE = 220

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.idx = 0 # 현재 아이템 인덱스
        self.setStyleSheet("QFrame{background:transparent;}")

        # 버튼: 덜 둥글고 깔끔하게
        self.prevBtn = QtW.QToolButton(text="◀")
        self.nextBtn = QtW.QToolButton(text="▶")
        for b in (self.prevBtn, self.nextBtn):
            b.setAutoRaise(True)
            b.setFixedSize(32, 32)
            b.setStyleSheet("""
                QToolButton {
                    background: rgba(255,255,255,0.7);
                    border: 1px solid #e0e0e0;
                    border-radius: 16px;
                    font-size: 16px;
                }
                QToolButton:hover { background: white; }
            """)

        # 이미지: 고정 정사각 + 여백 있는 보더
        self.img = ClickableLabel()
        self.img.setFixedSize(self.IMG_SIDE, self.IMG_SIDE)
        self.img.setAlignment(QtC.Qt.AlignCenter)
        self.img.setStyleSheet("background:#f8f9fa; border:1px solid #e9ecef; border-radius:12px;")

        # 텍스트: 폰트 크기 명시적으로 키움
        self.name = QtW.QLabel("-", alignment=QtC.Qt.AlignCenter)
        self.name.setWordWrap(True)
        f = self.name.font(); f.setPointSize(16); f.setWeight(QtG.QFont.Medium); self.name.setFont(f)

        self.meta = QtW.QLabel("", alignment=QtC.Qt.AlignCenter)
        self.meta.setObjectName("ProductMeta")
        fm = self.meta.font(); fm.setPointSize(14); self.meta.setFont(fm)
        self.meta.setStyleSheet("color:#555;")

        # 레이아웃 (버튼을 이미지 양옆, 간격은 넉넉히)
        v = QtW.QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(6)

        row = QtW.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        row.addWidget(self.prevBtn, 0, QtC.Qt.AlignVCenter)
        row.addWidget(self.img,     0, QtC.Qt.AlignCenter)
        row.addWidget(self.nextBtn, 0, QtC.Qt.AlignVCenter)

        v.addLayout(row)
        v.addWidget(self.name)
        v.addWidget(self.meta)

        # 이벤트
        self.prevBtn.clicked.connect(lambda: self._move(-1))
        self.nextBtn.clicked.connect(lambda: self._move(+1))
        self.img.clicked.connect(self._emit_clicked)

    def set_items(self, items: list):
        self.items = items or []
        self.idx = 0
        self._render()

    def _move(self, step):
        if not self.items:
            return
        self.idx = (self.idx + step) % len(self.items)
        self._render()

    def _render(self):
        if not self.items:
            self.name.setText("-")
            self.meta.setText("")
            self.img.setPixmap(QtG.QPixmap())
            return

        it = self.items[self.idx]
        nm = it.get("name", "-")
        pr = it.get("price", "")
        try:
            pr = f"₩{int(float(pr)):,}"
        except Exception:
            pr = str(pr) if pr not in ("", None) else "-"

        path = it.get("image_path") or it.get("img") or it.get("image") or ""
        pix  = QtG.QPixmap(path) if path else QtG.QPixmap()
        if pix.isNull():
            # 비어있으면 은은한 플레이스홀더
            ph = QtG.QPixmap(self.IMG_SIDE-20, self.IMG_SIDE-20)
            ph.fill(QtC.Qt.lightGray)
            pix = ph

        self.name.setText(nm)
        self.meta.setText(pr)

        # 고정 정사각 내에서만 스케일 → 들쭉날쭉/깨짐 방지
        self.img.setPixmap(
            pix.scaled(self.IMG_SIDE-20, self.IMG_SIDE-20,
                       QtC.Qt.KeepAspectRatio, QtC.Qt.SmoothTransformation)
        )

    def _emit_clicked(self):
        if not self.items:
            return
        it = dict(self.items[self.idx])
        path = it.get("image_path") or it.get("img") or it.get("image") or ""
        it["image_path"] = it.get("image_path") or path
        it["image"]      = it.get("image") or path
        self.clicked.emit(it)

class RecommendationPanel(QtW.QWidget):
    productClicked = QtC.pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RecommendationPanel")
        self.setStyleSheet("background: transparent;")

        # 전체 스크롤
        self.scroll = QtW.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtW.QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        # 컨테이너 + 레이아웃
        self.container = QtW.QWidget()
        self.container.setStyleSheet("background:transparent;")
        self.scroll.setWidget(self.container)
        self.v = QtW.QVBoxLayout(self.container)
        self.v.setContentsMargins(8, 8, 8, 8)
        self.v.setSpacing(12)

        # 결과 요약 띠
        self.condLabel = QtW.QLabel("결과: -")
        cfont = self.condLabel.font(); cfont.setPointSize(14); cfont.setBold(True)
        self.condLabel.setFont(cfont)
        self.condLabel.setStyleSheet("background: rgba(255,255,255,220); border-radius: 6px; padding: 10px 12px;")
        self.v.addWidget(self.condLabel, 0, QtC.Qt.AlignTop)

        # 추천 화장법 섹션 (하단)
        self.sec_tips = MakeupTipsSection()
        self.v.addWidget(self.sec_tips)

        self.v.addStretch(1)

        # 최상위 레이아웃
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll)

    def _to_sections(self, recos_dict):
        """
        {"파데":[...], "쿠션":[...], "립":[...], "아이":[...]}
        → {"파운데이션":[...], "쿠션":[...], "립":[...], "아이":[...]}
        필드 정규화: name, price, description, image_path
        """
        def conv(lst):
            out = []
            for it in (lst or []):
                # price 정수 변환 시도(실패하면 원문 유지)
                p_raw = it.get("price")
                try:
                    price_val = int(float(p_raw))
                except Exception:
                    price_val = p_raw

                img_path = (
                    it.get("image_path")
                    or it.get("img")
                    or it.get("image")
                    or ""
                )
                out.append({
                    "name": it.get("name", ""),
                    "price": price_val,
                    "description": it.get("desc") or it.get("description", ""),
                    "image_path": img_path,
                    # 아래 두 줄은 하위 호환(상세 패널에서 어떤 키를 참조해도 보이게)
                    "img": img_path,
                    "image": img_path,
                })
            return out

        return {
            "파운데이션": conv((recos_dict or {}).get("파데")),
            "쿠션":     conv((recos_dict or {}).get("쿠션")),
            "립":       conv((recos_dict or {}).get("립")),
            "아이":     conv((recos_dict or {}).get("아이")),
        }


    # --- 유틸: 카드 섹션 하나 만들기 ---
    def _make_section(self, title: str, cards: list):
        """드래그 스크롤 대신 ◀ ▶ 버튼으로 넘기는 캐러셀 섹션"""
        if not cards:
            return

        # 섹션 타이틀 ("추천 파운데이션" 등)
        lab = QtW.QLabel(f"추천 {title}")
        lab.setObjectName("h3")

        # 캐러셀
        car = SimpleCarousel()
        car.set_items(cards)
        # 카드 클릭 → RecommendationPanel의 시그널로 중계 (하단 상세가 받음)
        car.clicked.connect(self.productClicked.emit)

        # condLabel 바로 아래, tips 섹션 위에 꽂기
        insert_at = self.v.count() - 2   # [ ... , (tips), (stretch) ]
        if insert_at < 0:
            insert_at = self.v.count()

        self.v.insertWidget(insert_at, lab)
        self.v.insertWidget(insert_at + 1, car)


    # --- 추천 데이터 세팅 ---
    def set_data(self, recos, tips):
        # condLabel + tips 외의 기존 섹션 제거
        for i in reversed(range(self.v.count())):
            w = self.v.itemAt(i).widget()
            if w and w not in (self.condLabel, self.sec_tips):
                w.setParent(None)

        # CSV recos를 섹션별로
        sections = self._to_sections(recos)
        order = ["파운데이션", "쿠션", "립", "아이"]
        any_added = False
        for k in order:
            items = sections.get(k) or []
            if items:
                self._make_section(k, items)
                any_added = True

        # 팁 섹션(있다면) 유지
        self._render_tips(tips) if hasattr(self, "_render_tips") else None

        if not any_added:
            no_results_label = QtW.QLabel("😕<br>조건에 맞는 추천 제품이 없습니다.")
            no_results_label.setAlignment(QtC.Qt.AlignCenter)
            no_results_label.setWordWrap(True)
            no_results_label.setObjectName("NoResultsLabel")
            no_results_label.setStyleSheet("""
                QLabel#NoResultsLabel {
                    font-size: 18px;
                    color: #868e96;
                    background-color: #f8f9fa;
                    border: 1px dashed #ced4da;
                    border-radius: 12px;
                    padding: 40px;
                    margin: 10px;
                }
            """)
            self.v.insertWidget(self.v.count() - 2, no_results_label)

        # 화장법 섹션 세팅
        self.sec_tips.set_items(tips or [])

    def set_condition(self, text: str):
        self.condLabel.setText(text or "결과: -")

class RightSlidePanel(QtW.QFrame):
    def __init__(self, parent=None):
        super(RightSlidePanel, self).__init__(parent)
        self.setObjectName("RightSlidePanel")
        self.setFrameShape(QtW.QFrame.NoFrame)
        # 패널 스타일: 덜 둥글게, 미세한 테두리 추가
        self.setStyleSheet("""
            QFrame#RightSlidePanel {
                background: rgba(255, 255, 255, 230);
                border-left: 1px solid #dee2e6;
                border-radius: 0px;
            }
        """)

        # 핸들 버튼: 세로 탭 형태로 변경
        self.handleBtn = QtW.QPushButton("▶")
        self.handleBtn.setFixedSize(28, 80)
        self.handleBtn.setStyleSheet("""
            QPushButton {
                font-size: 16px; font-weight: bold; color: #fff;
                background-color: #94B7CF;
                border: none;
                border-top-left-radius: 12px; border-bottom-left-radius: 12px;
            }
            QPushButton:hover { background-color: #a5c8e0; }
        """)
        self.handleBtn.clicked.connect(self.toggle)

        self.stack = QtW.QStackedWidget()
        self.pageSurvey = SurveyPanel()
        self.pageReco   = RecommendationPanel()
        self.pageReco.setStyleSheet("background:transparent;")
        self.stack.addWidget(self.pageSurvey)
        self.stack.addWidget(self.pageReco)

        h = QtW.QHBoxLayout(self)
        h.setContentsMargins(6, 6, 6, 6)    # ← 여백 최소
        h.setSpacing(6)                     # ← 버튼과 스택 간격 축소
        h.addWidget(self.stack, 1)
        h.addWidget(self.handleBtn, 0, QtC.Qt.AlignVCenter)

        # ✅ 가로는 넓게, 세로는 레이아웃에 맞춰 자동으로
        self.setMinimumWidth(600)           # 원하는 최소 폭 (560~620 추천)
        self.setMaximumWidth(1000)           # 과도하게 커지지 않게 상한
        self.setMinimumHeight(0)            # ❌ 고정 높이 금지 (기존 1200 제거)
        self.setSizePolicy(QtW.QSizePolicy.Preferred, QtW.QSizePolicy.Expanding)

        # 자식 위젯도 세로로는 충분히 늘어나게
        pol = QtW.QSizePolicy(QtW.QSizePolicy.Preferred, QtW.QSizePolicy.Expanding)
        self.stack.setSizePolicy(pol)
        self.pageSurvey.setSizePolicy(pol)
        self.pageReco.setSizePolicy(pol)

        self._opened = True

    def toggle(self):
        self._opened = not self._opened
        if self._opened:
            self.setMinimumWidth(600)
            self.handleBtn.setText("▶")
        else:
            self.setMinimumWidth(self.handleBtn.width())
            self.handleBtn.setText("◀")

    def show_survey(self):
        self.stack.setCurrentWidget(self.pageSurvey)

    def show_recommendations(self):
        self.stack.setCurrentWidget(self.pageReco)

class BottomDetailView(QtW.QFrame):
    def __init__(self, parent=None):
        super(BottomDetailView, self).__init__(parent)
        self.setObjectName("BottomDetailView")
        self.setFrameShape(QtW.QFrame.NoFrame)
        # 더 깔끔하고 가독성 높은 스타일로 변경
        self.setStyleSheet("""
        QFrame#BottomDetailView {
            background: transparent;
            border: none;
        }
        QLabel { background: transparent; }
        QLabel#DetailName {
            font-size: 28px;
            font-weight: 600;
            color: #212529;
        }
        QLabel#DetailPrice {
            font-size: 24px;
            font-weight: 500;
            color: #94B7CF;
            padding-bottom: 10px;
        }
        QLabel#DetailDesc {
            font-size: 17px;
            color: #495057;
        }
        QLabel#DetailImage {
            background-color: #f1f3f5;
            border: 1px solid #e9ecef;
            border-radius: 12px;
        }
        """)

        # 높이를 늘려 여유 공간 확보
        self.setMinimumHeight(260)

        self.img = QtW.QLabel("제품 이미지를\n표시할 공간입니다.")
        self.img.setObjectName("DetailImage")
        self.img.setAlignment(QtC.Qt.AlignCenter)
        self.img.setFixedSize(200, 200) # 이미지 크기 증가

        self.name = QtW.QLabel("제품을 선택해주세요")
        self.name.setObjectName("DetailName")

        self.price = QtW.QLabel("")
        self.price.setObjectName("DetailPrice")

        self.desc = QtW.QLabel("")
        self.desc.setObjectName("DetailDesc")
        self.desc.setWordWrap(True)
        self.desc.setAlignment(QtC.Qt.AlignTop) # 설명이 위쪽에 붙도록

        # 텍스트 영역 레이아웃
        text_layout = QtW.QVBoxLayout()
        text_layout.setSpacing(4) # 텍스트 간 간격 축소
        text_layout.addWidget(self.name)
        text_layout.addWidget(self.price)
        text_layout.addWidget(self.desc, 1) # 설명이 남은 공간을 모두 차지하도록

        # 전체 레이아웃
        main_layout = QtW.QHBoxLayout(self)
        # 여백을 늘려 시원한 느낌을 줍니다.
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        main_layout.addWidget(self.img)
        main_layout.addLayout(text_layout, 1)

        # 초기 상태 설정
        self.show_product(None)

    def show_product(self, p):
        if not p:
            self.name.setText("제품을 선택해주세요")
            self.price.setText("")
            self.desc.setText("오른쪽 추천 목록에서 제품을 누르면 상세 정보가 표시됩니다.")
            self.img.setText("이미지 없음")
            self.img.setPixmap(QtG.QPixmap()) # 기존 이미지 제거
            return

        self.name.setText(p.get("name", "이름 정보 없음"))

        # 가격 포맷팅 개선
        price_val = p.get("price")
        try:
            # 숫자형 문자열, 정수, 실수를 모두 처리
            price_str = f"₩{int(float(price_val)):,}" if price_val not in (None, "") else ""
        except (ValueError, TypeError):
            price_str = str(price_val) if price_val not in (None, "") else ""
        self.price.setText(price_str)

        self.desc.setText(p.get("description") or p.get("desc") or "")

        # 이미지 로드 및 표시
        img_path = p.get("image_path") or p.get("img") or p.get("image")
        if img_path:
            pix = QtG.QPixmap(img_path)
            if not pix.isNull():
                # 이미지를 부드럽게 스케일링하여 표시
                self.img.setPixmap(pix.scaled(self.img.size(), QtC.Qt.KeepAspectRatio, QtC.Qt.SmoothTransformation))
            else:
                self.img.setText("이미지\n로드 실패")
                self.img.setPixmap(QtG.QPixmap())
        else:
            self.img.setText("이미지 없음")
            self.img.setPixmap(QtG.QPixmap())

# NOTE: DragScrollArea, ClickableLabel, ProductDetailDialog 클래스는
# 이 파일에서 제거하고 result_pages.py에서 import하여 사용합니다.
# DragScrollArea는 이 뷰에서 사용되지 않으므로 완전히 제거합니다.

class CaptureUnifiedView(QtW.QWidget):
    def __init__(self, parent=None):
        super(CaptureUnifiedView, self).__init__(parent)
        self.setObjectName("CaptureUnifiedView")

        # === 상단 바 ===
        self.btnFace = QtW.QRadioButton("얼굴 촬영")
        self.btnProduct = QtW.QRadioButton("제품 촬영")
        self.btnFace.setChecked(True)
        self.mirrorToggle = QtW.QCheckBox("거울모드")
        self.settingsBtn = QtW.QPushButton("설정")

        # --- 상단 바 스타일링 및 레이아웃 ---
        topBarContainer = QtW.QWidget()
        topBarContainer.setObjectName("TopBarContainer")
        # 여기에 고정 높이를 직접 지정하여, 레이아웃 문제와 관계없이 항상 원하는 높이를 갖도록 합니다.
        # 이 값을 조절하여 원하시는 높이로 변경할 수 있습니다. (예: 80)
        topBarContainer.setFixedHeight(70)

        # QSS(CSS와 유사)를 사용하여 상단 바의 스타일을 지정합니다.
        topBarContainer.setStyleSheet("""#TopBarContainer {
    background-color: #ffffff;
    border-bottom: 1px solid #dee2e6;
}
#TopBarContainer QRadioButton,
#TopBarContainer QCheckBox {
    font-size: 17px;
    font-weight: 500;
    color: #495057;
    padding: 8px 12px;
    border: none;
    background-color: transparent;
}
#TopBarContainer QRadioButton:checked {
    color: #94B7CF;
    font-weight: 600;
}
#TopBarContainer QRadioButton::indicator,
#TopBarContainer QCheckBox::indicator {
    width: 22px; height: 22px;
}
#TopBarContainer QPushButton {
    font-size: 16px;
    font-weight: 500;
    color: #343a40;
    background-color: #f1f3f5;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 8px 20px;
}
#TopBarContainer QPushButton:hover { background-color: #e9ecef; }""")

        topBar = QtW.QHBoxLayout(topBarContainer)
        topBar.setContentsMargins(15, 0, 15, 0) # 좌우 여백
        topBar.setSpacing(15) # 위젯 간 간격을 조금 더 넓게
        topBar.addWidget(self.btnFace)
        topBar.addWidget(self.btnProduct)
        topBar.addStretch(1)
        topBar.addWidget(self.mirrorToggle)
        topBar.addWidget(self.settingsBtn)

        # === 카메라(배경) ===
        self.cameraView = QtW.QLabel("카메라 미리보기")
        self.cameraView.setAlignment(QtC.Qt.AlignCenter)
        self.cameraView.setMinimumHeight(360)
        self.cameraView.setSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding)
        self.cameraView.setScaledContents(False)
        cfont = self.cameraView.font(); cfont.setPointSize(14)
        self.cameraView.setFont(cfont)
        self.cameraView.setStyleSheet("background:#111; color:#aaa;")

        # === 우측 패널 ===
        self.rightPanel = RightSlidePanel()
        self.rightPanel.show_survey()

        # === 하단 바(촬영/ROI) + 상세 ===
        self.shotBtn = QtW.QPushButton("촬영")
        self.roiBtn = QtW.QPushButton("영역지정"); self.roiBtn.setCheckable(True)

        self.detail = BottomDetailView()

        # Overlay 컨테이너
        root = QtW.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(topBarContainer) # 레이아웃 대신 스타일이 적용된 컨테이너 위젯을 추가

        bg = QtW.QWidget()
        bg_layout = QtW.QVBoxLayout(bg)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.addWidget(self.cameraView)

        overlay = QtW.QWidget()
        overlay.setAttribute(QtC.Qt.WA_StyledBackground, True)
        overlay.setStyleSheet("background: transparent;")
        grid = QtW.QGridLayout(overlay)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)

        # AlignTop을 제거하여 패널이 할당된 셀의 세로 공간을 모두 채우도록 합니다.
        grid.addWidget(self.rightPanel, 0, 1, 1, 1)

        # 하단 패널: QFrame으로 변경하여 스타일 적용
        bottomWrap = QtW.QFrame()
        bottomWrap.setObjectName("BottomPanel")
        bvl = QtW.QVBoxLayout(bottomWrap)
        bvl.setContentsMargins(0, 0, 0, 0)
        bvl.setSpacing(0) # 버튼 바와 상세 뷰 사이 간격 제거

        # 버튼들을 담을 바
        bbar_widget = QtW.QWidget()
        bbar = QtW.QHBoxLayout()
        bbar_widget.setLayout(bbar)
        bbar.setContentsMargins(12, 12, 12, 12)
        bbar.addStretch(1)
        bbar.addWidget(self.shotBtn)
        bbar.addWidget(self.roiBtn)
        bbar.addStretch(1)

        bvl.addWidget(bbar_widget)
        bvl.addWidget(self.detail)

        # 하단 패널 및 내부 버튼 스타일
        bottomWrap.setStyleSheet("""
        QFrame#BottomPanel {
            background: rgba(255, 255, 255, 240);
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
            border: 1px solid #dee2e6;
            border-bottom: none;
        }
        QFrame#BottomPanel QPushButton {
            min-height: 60px; font-size: 20px; font-weight: bold;
            border-radius: 12px; padding: 0 30px;
        }
        """)
        self.shotBtn.setStyleSheet("color: white; background-color: #94B7CF; border: none;")
        self.roiBtn.setStyleSheet("color: #343a40; background-color: #e9ecef; border: 1px solid #dee2e6;")

        grid.addWidget(bottomWrap, 1, 0, 1, 2)
        grid.setRowStretch(0, 1)
        grid.setColumnStretch(0, 1)

        stackHost = QtW.QStackedLayout()
        stackHost.setStackingMode(QtW.QStackedLayout.StackAll)
        host = QtW.QWidget(); host.setLayout(stackHost)
        stackHost.addWidget(bg)       # 배경
        stackHost.addWidget(overlay)  # 오버레이
        stackHost.setCurrentIndex(1)

        root.addWidget(host, 1)

        # === 연결 ===
        self.rightPanel.pageReco.productClicked.connect(self.detail.show_product)
        self.btnFace.toggled.connect(self._on_mode_changed)
        self.shotBtn.clicked.connect(self._on_shot_clicked)
        self.rightPanel.pageSurvey.scoresChanged.connect(self._on_scores_changed)

        # === 회전/거울 토글 ===
        self.rotate90 = False  # Jetson 세로 모드에서 필요하면 True
        QtW.QShortcut(QtG.QKeySequence("Ctrl+R"), self, activated=self._toggle_rotate)

        # NOTE: __init__에서 데모 데이터를 주입하는 _inject_demo_data() 호출을 제거했습니다.

    def _resolve_image_path(self, fname: str) -> str:
        """CSV의 image 파일명을 실제 경로로 치환"""
        if not fname:
            return ""
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        candidates = [
            os.path.join(base, "assets", "images", fname),
            os.path.join(base, "assets", fname),
            os.path.join(base, "data", "images", fname),
            os.path.join(base, "image", fname),        # ← result_pages.py가 쓰던 경로(이미 있으면 생략)
            os.path.join(base, fname),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return ""  # 못 찾으면 빈값(=이미지 없음으로 표시)
    
    def _open_csv(self, path):
        """CSV를 cp949/utf-8-sig/utf-8 순으로 시도해서 열기"""
        for enc in ("cp949", "utf-8-sig", "utf-8"):
            try:
                return open(path, "r", encoding=enc)
            except Exception:
                continue
        return open(path, "r")

    
    def _find_csv(self, filename="final.csv"):
        """루트(main.py 옆) 또는 data/ 폴더에서 CSV 찾기"""
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        candidates = [
            os.path.join(base, "data", filename),   # smartmirror/data/final.csv
            os.path.join(base, filename),           # smartmirror/final.csv (루트)
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    # ✅ 카메라 신호에 직접 물릴 슬롯 (프레임을 받고 미리보기+보관까지)
    @QtC.pyqtSlot(object)
    def on_webcam_frame(self, frame):
        """카메라에서 들어오는 프레임(np.ndarray BGR 또는 QImage)을 받아
        - 미리보기에 띄우고
        - parent.webcam_last_frame에 numpy BGR로 보관한다(제품 OCR용).
        """
        # 1. 프레임을 QImage로 변환
        qimg = None
        if isinstance(frame, QtG.QImage):
            qimg = frame
        elif isinstance(frame, np.ndarray):
            if frame.ndim == 3: # 컬러
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                qimg = QtG.QImage(rgb.data, w, h, 3 * w, QtG.QImage.Format_RGB888).copy()
            elif frame.ndim == 2: # 흑백
                h, w = frame.shape
                qimg = QtG.QImage(frame.data, w, h, w, QtG.QImage.Format_Grayscale8).copy()

        # 2. QImage가 유효하면 화면 업데이트
        if not qimg.isNull():
            self.update_frame(qimg)

        # 3. OCR을 위해 BGR numpy 배열로 변환하여 저장
        bgr = None
        if isinstance(frame, np.ndarray):
            bgr = frame
        elif isinstance(frame, QtG.QImage) and not frame.isNull():
            # QImage -> BGR ndarray
            qimg_rgb = frame.convertToFormat(QtG.QImage.Format_RGB888)
            w, h = qimg_rgb.width(), qimg_rgb.height()
            ptr = qimg_rgb.bits(); ptr.setsize(h * w * 3)
            rgb = np.frombuffer(ptr, np.uint8).reshape((h, w, 3))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        parent = self.parent() or self.window()
        if parent is not None and bgr is not None:
            setattr(parent, "webcam_last_frame", bgr)


    # ----- 이벤트 핸들러 -----
    def _on_mode_changed(self, checked):
        if checked:
            self.rightPanel.show_survey()
        else:
            self.rightPanel.show_recommendations()  # 이후 OCR 옵션 패널로 교체 예정

    def _current_skin_type(self):
        try:
            survey = self.rightPanel.pageSurvey
            return survey.infer_skin_type()
        except Exception:
            return None

    def apply_face_result(self, user_tone_num: str, user_color: str):
        # --- 결과 정규화 ---
        _tone = None
        if user_tone_num is not None:
            m = re.search(r"\d+", str(user_tone_num))
            if m:
                try: _tone = int(m.group(0))
                except: _tone = None

        key = str(user_color or "").strip().lower().replace("-", "_").replace(" ", "_")
        cmap = {
            "sp":"봄웜","spring":"봄웜","spring_warm":"봄웜","봄웜":"봄웜",
            "su":"여름쿨","summer":"여름쿨","summer_cool":"여름쿨","여름쿨":"여름쿨",
            "fa":"가을웜","fall":"가을웜","fall_warm":"가을웜","autumn":"가을웜","가을웜":"가을웜",
            "wi":"겨울쿨","winter":"겨울쿨","winter_cool":"겨울쿨","겨울쿨":"겨울쿨",
        }
        _pc = cmap.get(key, user_color)
        _skin = self._current_skin_type()

        # 추천 로드 (분석 결과를 직접 전달)
        recos, tips = self._load_face_recommendations_safe(skin_type=_skin, personal_color=_pc, number=_tone)

        # ★★★ 여기! pageReco에 넣어야 함 ★★★
        rp = getattr(self.rightPanel, "pageReco", None)
        if rp is not None:
            rp.set_data(recos, tips)
            if hasattr(rp, "set_condition"):
                rp.set_condition(f"결과: {(_tone if _tone is not None else '-') }호 · {(_pc or '-') } · {(_skin or '-')}")
            self.rightPanel.show_recommendations()
        else:
            print("[UI] rightPanel.pageReco 가 없습니다.")

    def _on_scores_changed(self, scores):
        # SurveyPanel의 자체 진단 로직을 사용하여 일관성 유지
        skin_type = self.rightPanel.pageSurvey.infer_skin_type()
        self.rightPanel.pageSurvey.set_preview_text(skin_type)

    def _on_shot_clicked(self):
        appwin = self.window()   # BeautyFinderApp

        # 얼굴/제품 모드 확인 (올바른 변수명으로 수정)
        is_face_mode = self.btnFace.isChecked()
        if is_face_mode:
            try:
                # 통합 화면에서 얼굴 분석 시작한다는 '의도' 플래그를 켬
                setattr(appwin, "intent_face_from_unified", True)

                # (선택) 통합 화면에서 마지막 프레임을 메인으로 넘기고 싶다면:
                # if hasattr(self, "last_frame") and self.last_frame is not None:
                #     appwin.webcam_last_frame = self.last_frame

                appwin.start_face_analysis()
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "안내", f"얼굴 분석 시작 실패: {e}")
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "안내", "제품 OCR 기능은 준비 중입니다.")

    def on_product_ocr_ok(self, payload: dict):
        """
        OCR 완료 → 추천 패널에 적용
        payload 구조:
        - ocr_text (str)
        - found_product (dict|None)
        - products (list[dict])
        - recommendations (list[dict])
        """
        txt = payload.get("ocr_text") or "-"
        prod = payload.get("found_product")

        # 추천 섹션으로 세팅
        items = payload.get("products") or []
        recos = {"파데": [], "쿠션": [], "립": [], "아이": []}
        for row in items:
            t = row.get("type", "")
            if t in ("파운데이션", "쿠션", "립", "아이"):
                key = {"파운데이션": "파데", "쿠션": "쿠션", "립": "립", "아이": "아이"}.get(t)
                recos[key].append({
                    "name": row.get("name",""),
                    "price": row.get("price",""),
                    "desc": row.get("description",""),
                    "img": self._resolve_image_path(row.get("image","")),
                })

        tips = []  # 화장법 팁은 별도 CSV에서 로딩 가능

        self.rightPanel.pageReco.set_condition(f"OCR 인식: {txt}")
        self.rightPanel.pageReco.set_data(recos, tips)
        self.rightPanel.show_recommendations()

    def on_product_ocr_err(self, msg: str):
        QtW.QMessageBox.critical(self, "OCR 오류", msg)

    def _toggle_rotate(self):
        self.rotate90 = not self.rotate90

    # ----- 외부에서 프레임 주입 -----
    def update_frame(self, qimg, *args):
        """웹캠 프레임을 미리보기에 표시하고, 다른 모듈용으로 BGR 프레임을 저장합니다."""
        if isinstance(qimg, QtG.QImage):
            if self.rotate90:
                qimg = qimg.transformed(QtG.QTransform().rotate(90))
            if self.mirrorToggle.isChecked():
                qimg = qimg.mirrored(True, False)

            pix = QtG.QPixmap.fromImage(qimg).scaled(
                self.cameraView.size(),
                QtC.Qt.KeepAspectRatioByExpanding,
                QtC.Qt.SmoothTransformation
            )
            self.cameraView.setPixmap(pix)

            # ✅ 여기서도 parent.webcam_last_frame 채워주기 (QImage만 주입되는 경우 대비)
            try:
                qimg_rgb = qimg.convertToFormat(QtG.QImage.Format_RGB888)
                w, h = qimg_rgb.width(), qimg_rgb.height()
                ptr = qimg_rgb.bits(); ptr.setsize(h * w * 3)
                rgb = np.frombuffer(ptr, np.uint8).reshape((h, w, 3))
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                parent = self.parent() or self.window()
                if parent is not None:
                    setattr(parent, "webcam_last_frame", bgr)
            except Exception:
                pass

    def _load_face_recommendations_safe(self, skin_type=None, personal_color=None, number=None):
        """
        CSV에서 추천 로드. 실패/예외일 때만 최소 백업(타입별 몇 개) 사용.
        '데모 하드코딩'은 사용하지 않는다.
        """
        try:
            cond = {"skin_type": skin_type, "personal_color": personal_color, "number": number}
            # 디버깅: cond 확인
            print("[RECO] cond =", cond)

            recos = self._fetch_recos_by_category(cond) or {}
            tips  = self._load_makeup_tips_csv(cond) or []

            # 카테고리 키 보정
            for k in ("파데", "쿠션", "립", "아이"):
                recos.setdefault(k, [])

            # 전부 비었으면: 타입 기준 백업만 (CSV에서) 시도
            if not any(len(v) for v in recos.values()):
                print("[RECO] primary empty -> using type-only backup from CSV")
                recos = self._fetch_recos_by_category({})

            # 그래도 비면 그냥 빈 그대로 반환 (데모 금지)
            return recos, (tips or [])

        except Exception as e:
            print("[RECO] error:", e)
            # 진짜 실패(파일 깨짐 등)일 때만 아주 최소 백업
            return {"파데": [], "쿠션": [], "립": [], "아이": []}, (tips if 'tips' in locals() else [])

    def _fetch_recos_by_category(self, cond):
        """
        final.csv에서 카테고리별 추천 로드.
        필터: skin_types / personal_colors / number
        CSV 위치: 프로젝트 루트(main.py 옆) 또는 data/ 폴더
        """
        recos = {"파데": [], "쿠션": [], "립": [], "아이": []}

        # --- CSV 경로: 루트 최우선, 없으면 data/ ---
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        candidates = [
            os.path.join(base, "final.csv"),             # 루트/final.csv  ← 네가 원하는 구조
            os.path.join(base, "data", "final.csv"),     # 루트/data/final.csv
        ]
        csv_path = next((p for p in candidates if os.path.exists(p)), None)
        if not csv_path:
            print("[warn] CSV not found in:", candidates)
            return recos

        # --- cond 정규화(퍼컬 약어/영문 → 한글), number는 int ---
        pc_raw = (cond or {}).get("personal_color")
        key = str(pc_raw or "").strip().lower().replace("-", "_").replace(" ", "_")
        pc_map = {
            "sp": "봄웜", "spring": "봄웜", "spring_warm": "봄웜",
            "su": "여름쿨", "summer": "여름쿨", "summer_cool": "여름쿨",
            "fa": "가을웜", "fall": "가을웜", "fall_warm": "가을웜", "autumn": "가을웜",
            "wi": "겨울쿨", "winter": "겨울쿨", "winter_cool": "겨울쿨",
            "봄웜": "봄웜", "여름쿨": "여름쿨", "가을웜": "가을웜", "겨울쿨": "겨울쿨",
        }
        want_pc   = pc_map.get(key, pc_raw)
        want_skin = (cond or {}).get("skin_type")
        want_num  = (cond or {}).get("number")
        try:
            want_num = int(want_num) if want_num is not None else None
        except Exception:
            want_num = None

        # --- 읽기: 인코딩 자동 시도 ---
        with self._open_csv(csv_path) as f:
            r = csv.DictReader(f)
            for row in r:
                t = (row.get("type") or row.get("category") or "").strip()

                # 카테고리 판별 로직 강화 (부분 일치 허용)
                cat = None
                if '파운데이션' in t or '파데' in t: cat = '파데'
                elif '쿠션' in t: cat = '쿠션'
                elif '립' in t or '틴트' in t or '립스틱' in t: cat = '립'
                elif '아이' in t or '섀도우' in t: cat = '아이'

                if not cat:
                    continue

                # 카테고리별로 필터링 규칙을 다르게 적용
                is_match = False
                if cat in ("파데", "쿠션"):  # 베이스 제품: 피부타입과 호수로 필터링
                    skin_ok = (not want_skin) or (not row.get("skin_types")) or (want_skin in row.get("skin_types", ""))
                    num_ok = (want_num is None) or (not row.get("number"))
                    if want_num is not None and row.get("number"):
                        try:
                            num_ok = (int(float(row.get("number", "0"))) == want_num)
                        except (ValueError, TypeError):
                            num_ok = False
                    if skin_ok and num_ok:
                        is_match = True
                elif cat in ("립", "아이"):  # 색조 제품: 퍼스널컬러로 필터링
                    pc_ok = (not want_pc) or (not row.get("personal_colors")) or (want_pc in row.get("personal_colors", ""))
                    if pc_ok:
                        is_match = True

                if is_match:
                    recos[cat].append({
                        "name": row.get("name", ""),
                        "price": row.get("price", ""),
                        "desc": row.get("description", ""),
                        "img": self._resolve_image_path(row.get("image", "")),
                    })

        # 개수 제한
        for k in recos:
            recos[k] = recos[k][:10]
        return recos

    def _load_makeup_tips_csv(self, cond):
        """
        현재 final.csv에는 화장법/유튜브 데이터가 없으므로,
        더미 데이터를 리턴하도록 고정.
        """
        return [
            {"title": "속광 표현 팁", "thumb": "", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            {"title": "데일리 음영 메이크업", "thumb": "", "url": "https://www.youtube.com/watch?v=ysz5S6PUM-U"},
        ]
