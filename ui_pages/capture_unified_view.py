# -*- coding: utf-8 -*-
# capture_unified_view_kiosk.py
# PyQt5 / Python 3.6 compatible
from __future__ import print_function
from PyQt5 import QtCore, QtGui, QtWidgets as QtW
from PyQt5 import QtCore as QtC, QtGui as QtG


def open_url_external(url):
    QtGui.QDesktopServices.openUrl(QtCore.QUrl(url or ""))


class MiniProductCard(QtW.QFrame):
    clicked = QtCore.pyqtSignal(dict)

    def __init__(self, product=None, parent=None):
        super(MiniProductCard, self).__init__(parent)
        self.setObjectName("MiniProductCard")
        self.setFrameShape(QtW.QFrame.NoFrame)
        self.setStyleSheet("#MiniProductCard{border:none;background:transparent;}")
        self.setMinimumSize(140, 170)

        self._product = None
        self.img = QtW.QLabel("이미지", self)
        self.img.setAlignment(QtCore.Qt.AlignCenter)
        self.img.setFixedSize(120, 120)
        self.img.setStyleSheet("background:transparent;")
        self.name = QtW.QLabel("제품명", self)
        self.name.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.name.setWordWrap(True)
        font = self.name.font()
        font.setPointSize(11)  # 작게
        self.name.setFont(font)

        v = QtW.QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        v.addWidget(self.img, 0, QtCore.Qt.AlignHCenter)
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
            pix = QtGui.QPixmap(img_path)
            if not pix.isNull():
                self.img.setPixmap(pix.scaled(self.img.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            else:
                self.img.setText("이미지\n로드 실패")
        else:
            self.img.setText("이미지 없음")


class Carousel(QtW.QWidget):
    cardClicked = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super(Carousel, self).__init__(parent)
        self.stack = QtW.QStackedWidget(self)
        self.prevBtn = QtW.QPushButton("←")
        self.nextBtn = QtW.QPushButton("→")
        self.prevBtn.setFixedWidth(32)
        self.nextBtn.setFixedWidth(32)

        self.prevBtn.clicked.connect(self.prev)
        self.nextBtn.clicked.connect(self.next)

        h = QtW.QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(self.prevBtn, 0, QtCore.Qt.AlignVCenter)
        h.addWidget(self.stack, 1)
        h.addWidget(self.nextBtn, 0, QtCore.Qt.AlignVCenter)

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
    productClicked = QtCore.pyqtSignal(dict)

    def __init__(self, title, parent=None):
        super(CategorySection, self).__init__(parent)
        self.setObjectName("CategorySection")
        self.setFrameShape(QtW.QFrame.NoFrame)
        self.setStyleSheet("QFrame#CategorySection{background:transparent;}")

        self.title = QtW.QLabel(title)
        tfont = self.title.font()
        tfont.setPointSize(13)
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
        tfont.setPointSize(13)
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
                pix = QtGui.QPixmap(tip["thumb"])
                if not pix.isNull():
                    thumb.setPixmap(pix.scaled(thumb.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
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

        # 폰트 큼 / 줄간격(라인하이트) 키움 / 여백 최소화
        self.setStyleSheet("""
            QLabel#Guide   { font-size:20px; font-weight:800; letter-spacing:0.2px; }
            QLabel#Sub     { font-size:13px; color:#666; margin:0 0 8px 0; }
            QLabel#Q       { font-size:16px; font-weight:700; line-height:130%; }   /* 줄간격 ↑ */
            QLabel#Preview { font-size:16px; font-weight:800; margin-top:6px; }

            QSlider { margin:0; }
            QSlider::groove:horizontal { height:8px; background:#ead5d1; border-radius:4px; }
            QSlider::sub-page:horizontal { background:#c57c73; border-radius:4px; }
            QSlider::handle:horizontal {
                width:20px; height:20px; margin:-8px 0; border-radius:10px;
                background:#c57c73; border:1px solid #b96e65;
            }
        """)

        self.question_texts = [
            "1) 오후 3~5시 T존(이마·코) 번들거림/광택이 눈에 띈다.",
            "2) 세안 후 10분 이내 당김·각질이 올라온다.",
            "3) 새 제품/자외선/마찰 후 24시간 내 따가움·가려움·홍조가 생긴다.",
            "4) 모공 확장/블랙헤드가 보이고 유분으로 메이크업이 무너진다.",
            "5) 염증성 트러블(빨갛고 아픈 뾰루지)이 주 1회 이상 생긴다.",
        ]
        self.sliders = []

        v = QtW.QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)   # ← 패널 내부 여백 최소
        v.setSpacing(10)                  # ← 문항/슬라이더 간격도 작게

        guide = QtW.QLabel("피부진단"); guide.setObjectName("Guide")
        sub   = QtW.QLabel("최근 2주 기준 · 1~5로 응답"); sub.setObjectName("Sub")
        v.addWidget(guide); v.addWidget(sub)

        for q in self.question_texts:
            qlab = QtW.QLabel(q); qlab.setObjectName("Q"); qlab.setWordWrap(True)
            v.addWidget(qlab)

            sld = QtW.QSlider(QtC.Qt.Horizontal)
            sld.setMinimum(1); sld.setMaximum(5); sld.setValue(3)
            sld.setTickInterval(1); sld.setSingleStep(1)
            sld.valueChanged.connect(self._on_value_changed)
            v.addWidget(sld)
            self.sliders.append(sld)

        self.preview = QtW.QLabel("미리보기: -"); self.preview.setObjectName("Preview")
        v.addWidget(self.preview)
        v.addStretch(1)

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
        self.set_preview_text(self.infer_skin_type())

    # ---------- 시그널/외부 API ----------
    def _on_value_changed(self, _):
        vals = self._scores()
        self.scoresChanged.emit(vals)
        self._update_preview()

    def set_preview_text(self, text: str):
        self.preview.setText(f"미리보기: {text or '-'}")


class SimpleCarousel(QtW.QFrame):
    """◀ ▶ 버튼으로 아이템 넘기기 (이미지 고정 크기, 미니멀 카드)"""
    clicked = QtC.pyqtSignal(dict)

    # 카드 이미지 한 변 픽셀 (원하면 200~240 사이로 취향대로)
    IMG_SIDE = 220

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.idx = 0
        self.setStyleSheet("QFrame{background:transparent;}")

        # 버튼: 작게/미니멀
        self.prevBtn = QtW.QToolButton(text="◀")
        self.nextBtn = QtW.QToolButton(text="▶")
        for b in (self.prevBtn, self.nextBtn):
            b.setAutoRaise(True)
            b.setFixedSize(28, 28)
            b.setStyleSheet(
                "QToolButton{background: rgba(255,255,255,220);"
                "border:1px solid #ddd; border-radius:14px;}"
                "QToolButton:hover{background:white;}"
            )

        # 이미지: 고정 정사각 + 여백 있는 보더
        self.img = ClickableLabel()
        self.img.setFixedSize(self.IMG_SIDE, self.IMG_SIDE)
        self.img.setAlignment(QtC.Qt.AlignCenter)
        self.img.setStyleSheet(
            "background:#fafafa; border:1px solid #e8e8e8; border-radius:12px;"
        )

        # 텍스트: 작게/두 줄까지만
        self.name = QtW.QLabel("-", alignment=QtC.Qt.AlignCenter)
        self.name.setWordWrap(True)
        f = self.name.font(); f.setPointSize(max(9, f.pointSize()-1)); self.name.setFont(f)

        self.meta = QtW.QLabel("", alignment=QtC.Qt.AlignCenter)
        self.meta.setObjectName("ProductMeta")
        fm = self.meta.font(); fm.setPointSize(max(8, fm.pointSize()-2)); self.meta.setFont(fm)
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
        cfont = self.condLabel.font(); cfont.setPointSize(11); cfont.setBold(True)
        self.condLabel.setFont(cfont)
        self.condLabel.setStyleSheet("background: rgba(255,255,255,210); border-radius: 8px; padding: 6px;")
        self.v.addWidget(self.condLabel)

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
        order = ["파운데이션","쿠션","립","아이"]
        any_added = False
        for k in order:
            items = sections.get(k) or []
            if items:
                self._make_section(k, items)
                any_added = True

        # 팁 섹션(있다면) 유지
        self._render_tips(tips) if hasattr(self, "_render_tips") else None

        if not any_added:
            self.v.addWidget(QtW.QLabel("조건에 맞는 추천이 없어요."))

        # 화장법 섹션 세팅
        self.sec_tips.set_items(tips or [])

    def set_condition(self, text: str):
        self.condLabel.setText(text or "결과: -")




class RightSlidePanel(QtW.QFrame):
    def __init__(self, parent=None):
        super(RightSlidePanel, self).__init__(parent)
        self.setObjectName("RightSlidePanel")
        self.setFrameShape(QtW.QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame#RightSlidePanel{
                background:rgba(255,255,255,210);
                border:none; border-radius:8px;
            }
        """)

        self.handleBtn = QtW.QPushButton("▶")
        self.handleBtn.setFixedWidth(24)
        self.handleBtn.clicked.connect(self.toggle)

        self.stack = QtW.QStackedWidget()
        self.pageSurvey = SurveyPanel()
        self.pageReco   = RecommendationPanel()
        # 내부 위젯은 투명 배경 유지
        self.pageSurvey.setStyleSheet("background:transparent;")
        self.pageReco.setStyleSheet("background:transparent;")
        self.stack.addWidget(self.pageSurvey)
        self.stack.addWidget(self.pageReco)

        h = QtW.QHBoxLayout(self)
        h.setContentsMargins(6, 6, 6, 6)    # ← 여백 최소
        h.setSpacing(6)                     # ← 버튼과 스택 간격 축소
        h.addWidget(self.stack, 1)
        h.addWidget(self.handleBtn, 0, QtCore.Qt.AlignVCenter)

        # ✅ 가로는 넓게, 세로는 레이아웃에 맞춰 자동으로
        self.setMinimumWidth(560)           # 원하는 최소 폭 (560~620 추천)
        self.setMaximumWidth(900)           # 과도하게 커지지 않게 상한
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
            self.setMinimumWidth(320)
            self.handleBtn.setText("▶")
        else:
            self.setMinimumWidth(24)
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
        self.setStyleSheet("""
        QFrame#BottomDetailView { background: rgba(255,255,255,210); border-radius: 12px; }
        QLabel { background: transparent; }
        """)

        self.setFixedHeight(220)

        self.name = QtW.QLabel("이름")
        nfont = self.name.font(); nfont.setPointSize(12); nfont.setBold(True)
        self.name.setFont(nfont)

        self.img = QtW.QLabel("이미지")
        self.img.setAlignment(QtCore.Qt.AlignCenter)
        self.img.setFixedSize(160, 160)
        self.img.setStyleSheet("background:transparent;")

        self.price = QtW.QLabel("가격: -")
        self.desc = QtW.QLabel("설명: -")
        self.desc.setWordWrap(True)

        left = QtW.QVBoxLayout()
        left.addWidget(self.name)
        left.addWidget(self.price)
        left.addWidget(self.desc)
        left.addStretch(1)

        lay = QtW.QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(10)
        lay.addWidget(self.img, 0, QtCore.Qt.AlignLeft)
        lay.addLayout(left, 1)

    def show_product(self, p):
        if not p:
            self.name.setText("이름")
            self.price.setText("가격: -")
            self.desc.setText("설명: -")
            self.img.setText("이미지")
            return
        self.name.setText(p.get("name", "이름"))
        self.price.setText("가격: %s" % p.get("price", "-"))
        self.desc.setText("설명: %s" % p.get("description", "-"))

        img_path = p.get("img")
        if img_path:
            pix = QtGui.QPixmap(img_path)
            if not pix.isNull():
                self.img.setPixmap(pix.scaled(self.img.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
            else:
                self.img.setText("이미지\n로드 실패")
        else:
            self.img.setText("이미지 없음")

# === from result_pages.py 참고: 가로 드래그 스크롤 ===
class DragScrollArea(QtW.QScrollArea):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.setWidgetResizable(True)
        self._drag = False; self._sx = 0; self._sv = 0
    def mousePressEvent(self, e):
        if e.buttons() & QtC.Qt.LeftButton:
            self._drag = True; self._sx = e.globalX(); self._sv = self.horizontalScrollBar().value()
        super().mousePressEvent(e)
    def mouseMoveEvent(self, e):
        if self._drag:
            dx = e.globalX() - self._sx
            self.horizontalScrollBar().setValue(self._sv - dx)
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self, e):
        self._drag = False
        super().mouseReleaseEvent(e)

class ClickableLabel(QtW.QLabel):
    clicked = QtC.pyqtSignal()
    def mousePressEvent(self, e):
        if e.button() == QtC.Qt.LeftButton:
            self.clicked.emit()

class ProductDetailDialog(QtW.QDialog):
    def __init__(self, card: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(card.get("name","상세 정보"))
        v = QtW.QVBoxLayout(self)

        img = QtW.QLabel()
        pix = QtG.QPixmap(card.get("image_path",""))
        if not pix or pix.isNull():
            pix = QtG.QPixmap(240, 240); pix.fill(QtC.Qt.lightGray)
        img.setPixmap(pix.scaled(360, 360, QtC.Qt.KeepAspectRatio, QtC.Qt.SmoothTransformation))
        img.setAlignment(QtC.Qt.AlignCenter)

        name = QtW.QLabel(card.get("name","")); name.setObjectName("ProductTitle")
        price = card.get("price"); price_lbl = QtW.QLabel(f"₩{price:,}" if isinstance(price,int) else "")
        desc = QtW.QLabel(card.get("desc") or card.get("description","")); desc.setWordWrap(True)

        v.addWidget(img); v.addWidget(name, alignment=QtC.Qt.AlignCenter)
        v.addWidget(price_lbl, alignment=QtC.Qt.AlignCenter); v.addWidget(desc)

        btns = QtW.QDialogButtonBox(QtW.QDialogButtonBox.Close); btns.rejected.connect(self.reject)
        v.addWidget(btns)


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

        topBar = QtW.QHBoxLayout()
        topBar.setContentsMargins(8, 6, 8, 6)
        topBar.addWidget(self.btnFace)
        topBar.addWidget(self.btnProduct)
        topBar.addStretch(1)
        topBar.addWidget(self.mirrorToggle)
        topBar.addWidget(self.settingsBtn)

        # === 카메라(배경) ===
        self.cameraView = QtW.QLabel("카메라 미리보기")
        self.cameraView.setAlignment(QtCore.Qt.AlignCenter)
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
        self.shotBtn = QtW.QPushButton("● 촬영")
        self.roiBtn = QtW.QPushButton("영역지정"); self.roiBtn.setCheckable(True)

        self.detail = BottomDetailView()

        # Overlay 컨테이너
        root = QtW.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(topBar)

        bg = QtW.QWidget()
        bg_layout = QtW.QVBoxLayout(bg)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.addWidget(self.cameraView)

        overlay = QtW.QWidget()
        overlay.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        overlay.setStyleSheet("background: transparent;")
        grid = QtW.QGridLayout(overlay)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)

        grid.addWidget(self.rightPanel, 0, 1, 1, 1, QtCore.Qt.AlignTop)
        

        bottomWrap = QtW.QWidget()
        bvl = QtW.QVBoxLayout(bottomWrap)
        bvl.setContentsMargins(0, 0, 0, 0)
        bvl.setSpacing(6)
        bbar = QtW.QHBoxLayout()
        bbar.setContentsMargins(8, 6, 8, 6)
        bbar.addStretch(1)
        bbar.addWidget(self.shotBtn)
        bbar.addWidget(self.roiBtn)
        bvl.addLayout(bbar)
        bvl.addWidget(self.detail)
        bottomWrap.setStyleSheet("QWidget { background: rgba(255,255,255,210); border-radius:12px; }")

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
        QtW.QShortcut(QtGui.QKeySequence("Ctrl+R"), self, activated=self._toggle_rotate)

        # === 데모 데이터 ===
        self._inject_demo_data()
    


    def _resolve_image_path(self, fname: str) -> str:
        """CSV의 image 파일명을 실제 경로로 치환"""
        import os
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
        import os
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        candidates = [
            os.path.join(base, "data", filename),   # smartmirror/data/final.csv
            os.path.join(base, filename),           # smartmirror/final.csv (루트)
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None
    
    def _to_qimage(self, frame):
        # 이미 QImage면 그대로
        if isinstance(frame, QtG.QImage):
            return frame
        # numpy BGR -> QImage
        if isinstance(frame, np.ndarray):
            if frame.ndim == 3:
                h, w, _ = frame.shape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return QtG.QImage(rgb.data, w, h, 3*w, QtG.QImage.Format_RGB888).copy()
            elif frame.ndim == 2:
                h, w = frame.shape
                return QtG.QImage(frame.data, w, h, w, QtG.QImage.Format_Grayscale8).copy()
        # 마지막 보루: 빈 이미지
        return QtG.QImage()

    # ✅ 카메라 신호에 직접 물릴 슬롯 (프레임을 받고 미리보기+보관까지)
    @QtC.pyqtSlot(object)
    def on_webcam_frame(self, frame):
        """카메라에서 들어오는 프레임(np.ndarray BGR 또는 QImage)을 받아
        - 미리보기에 띄우고
        - parent.webcam_last_frame에 numpy BGR로 보관한다(제품 OCR용).
        """
        qimg = self._to_qimage(frame)
        if not qimg.isNull():
            self.update_frame(qimg)

        # OCR은 BGR ndarray가 편하므로 저장은 ndarray 기준으로
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

    # (선택) update_frame도 프레임을 보관하도록 강화 — QImage만 들어오는 환경 대비
    def update_frame(self, qimg, *args):
        if isinstance(qimg, QtG.QImage):
            if self.rotate90:
                qimg = qimg.transformed(QtG.QTransform().rotate(90))
            if self.mirrorToggle.isChecked():
                qimg = qimg.mirrored(True, False)
            pix = QtG.QPixmap.fromImage(qimg).scaled(
                self.cameraView.size(),
                QtCore.Qt.KeepAspectRatioByExpanding,
                QtCore.Qt.SmoothTransformation
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




    # ----- 이벤트 핸들러 -----
    def _on_mode_changed(self, checked):
        if checked:
            self.rightPanel.show_survey()
        else:
            self.rightPanel.show_recommendations()  # 이후 OCR 옵션 패널로 교체 예정

    def _compute_skin_preview(self, scores):
        # scores: [1..5] * 5
        if not scores:
            return "미리보기: -"
        oily = (scores[0] + scores[2]) / 2.0
        dry  = (scores[1] + scores[3]) / 2.0
        sens = scores[4]
        skin = max([("지성", oily), ("건성", dry), ("민감성", sens)], key=lambda x: x[1])[0]
        return f"{skin} 피부"
    
    def _current_skin_type(self):
        try:
            survey = self.rightPanel.pageSurvey
            return survey.infer_skin_type()
        except Exception:
            return None

    def apply_face_result(self, user_tone_num: str, user_color: str):
        import re
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

        # 내부 상태로 저장(추천 조건에서 사용)
        self._last_user_tone  = _tone
        self._last_user_color = _pc
        self._last_skin_type  = _skin

        # 추천 로드
        recos, tips = self._load_face_recommendations_safe()

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
        self.rightPanel.pageSurvey.set_preview_text(self._compute_skin_preview(scores))


    def _on_shot_clicked(self):
        appwin = self.window()   # BeautyFinderApp

        # 얼굴/제품 모드 확인
        is_face_mode = True
        try:
            is_face_mode = self.faceRadio.isChecked()
        except Exception:
            pass

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
                key = "파데" if t == "파운데이션" else t
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
        """웹캠 프레임을 미리보기 QLabel에만 표시(가벼움)."""
        from PyQt5 import QtGui, QtCore
        if isinstance(qimg, QtGui.QImage):
            if getattr(self, "rotate90", False):
                qimg = qimg.transformed(QtGui.QTransform().rotate(90))
            if hasattr(self, "mirrorToggle") and self.mirrorToggle.isChecked():
                qimg = qimg.mirrored(True, False)

            pix = QtGui.QPixmap.fromImage(qimg).scaled(
                self.cameraView.size(),
                QtCore.Qt.KeepAspectRatioByExpanding,
                QtCore.Qt.SmoothTransformation
            )
            self.cameraView.setPixmap(pix)



    # ----- 데모 데이터 -----
    def _collect_face_conditions(self):
        parent = self.window()
        if not parent: return {}
        number = getattr(parent, "user_tone", None)
        try: number = int(number) if number is not None else None
        except: number = None
        return {
            "skin_type":      getattr(parent, "user_skin_type", None),
            "personal_color": getattr(parent, "user_color", None),
            "number":         number,
        }


    def _load_face_recommendations_safe(self):
        """
        CSV에서 추천 로드. 실패/예외일 때만 최소 백업(타입별 몇 개) 사용.
        '데모 하드코딩'은 사용하지 않는다.
        """
        try:
            cond = self._collect_face_conditions()
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
                recos = self._fetch_recos_by_category({"skin_type": None, "personal_color": None, "number": None})

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
        import os, csv

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

        type_to_cat = {"파운데이션":"파데","쿠션":"쿠션","립":"립","아이":"아이"}

        # --- 읽기: 인코딩 자동 시도 ---
        with self._open_csv(csv_path) as f:
            r = csv.DictReader(f)
            for row in r:
                t = (row.get("type") or row.get("category") or "").strip()
                cat = type_to_cat.get(t)
                if not cat:
                    continue

                ok = True
                if want_skin and row.get("skin_types"):
                    ok &= (row["skin_types"].strip() == str(want_skin).strip())
                if want_pc and row.get("personal_colors"):
                    ok &= (row["personal_colors"].strip() == str(want_pc).strip())
                if want_num is not None and row.get("number"):
                    try:
                        row_num = int(float(str(row["number"]).strip()))
                        ok &= (row_num == int(want_num))
                    except Exception:
                        pass

                if ok:
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


    def _inject_demo_data(self):
        demo = {
            "파데": [
                {"name": "프레시 파운데이션 21", "price": 32000, "desc": "가벼운 커버", "img": ""},
                {"name": "롱웨어 파운데이션 22", "price": 38000, "desc": "지속력 강화", "img": ""},
            ],
            "쿠션": [
                {"name": "광채 쿠션 20", "price": 42000, "desc": "촉촉 글로우", "img": ""},
                {"name": "보송 쿠션 21", "price": 39000, "desc": "픽싱 보송", "img": ""},
            ],
            "립": [
                {"name": "벨벳 립 04", "price": 19000, "desc": "부드러운 발림", "img": ""},
            ],
            "아이": [
                {"name": "뉴트럴 팔레트", "price": 29000, "desc": "데일리 음영", "img": ""},
            ],
        }
        tips = [
            {"title": "여쿨 메이크업 베이스", "thumb": "", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            {"title": "속광 표현 팁", "thumb": "", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        ]
        self.rightPanel.pageReco.set_data(demo, tips)
