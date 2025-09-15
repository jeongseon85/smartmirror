import os
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QFrame, QGridLayout,
    QHBoxLayout, QDialog, QDialogButtonBox
)
from PyQt5.QtGui import QImageReader
from PyQt5.QtWidgets import QScrollArea, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QImage, QCursor

class DragScrollArea(QScrollArea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWidgetResizable(True)
        self._drag_active = False
        self._drag_start_x = 0
        self._drag_start_scroll = 0

    def mousePressEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._drag_active = True
            self._drag_start_x = e.globalX()
            self._drag_start_scroll = self.horizontalScrollBar().value()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_active:
            dx = e.globalX() - self._drag_start_x
            self.horizontalScrollBar().setValue(self._drag_start_scroll - dx)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_active = False
        super().mouseReleaseEvent(e)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, e):
        self.clicked.emit()

class ProductDetailDialog(QDialog):
    def __init__(self, card: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(card.get("name","상세 정보"))
        v = QVBoxLayout(self)
        img = QLabel()
        pix = QPixmap(card.get("image_path",""))
        if not pix or pix.isNull():
            # placeholder
            pix = QPixmap(200, 200); pix.fill(Qt.lightGray)
        img.setPixmap(pix.scaled(360, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        img.setAlignment(Qt.AlignCenter)

        name = QLabel(card.get("name",""))
        name.setObjectName("ProductTitle")
        price = card.get("price")
        price_lbl = QLabel(f"₩{price:,}" if isinstance(price,int) else "")

        desc = QLabel(card.get("description",""))
        desc.setWordWrap(True)

        v.addWidget(img)
        v.addWidget(name, alignment=Qt.AlignCenter)
        v.addWidget(price_lbl, alignment=Qt.AlignCenter)
        v.addWidget(desc)

        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        v.addWidget(btns)

class FaceResultPage(QWidget):
    """얼굴 분석 결과 + 타입별 추천 섹션"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.base_dir = Path(__file__).resolve().parents[1]  # 프로젝트 루트 추정

        main_layout = QVBoxLayout(self); main_layout.setAlignment(Qt.AlignTop)
        self.title = QLabel("분석 결과"); self.title.setObjectName("h2"); self.title.setAlignment(Qt.AlignCenter)
        self.subtitle = QLabel(""); self.subtitle.setAlignment(Qt.AlignCenter); self.subtitle.setObjectName("desc")

        # 스크롤
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.container = QWidget(); self.vbox = QVBoxLayout(self.container); self.vbox.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.container)

        self.go_home_btn = QPushButton("처음으로")
        self.go_home_btn.setObjectName("main_menu_btn")

        main_layout.addWidget(self.title)
        main_layout.addWidget(self.subtitle)
        main_layout.addWidget(scroll, stretch=1)
        main_layout.addWidget(self.go_home_btn)

    def _clear_sections(self):
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _resolve_image_path(self, image_name: str) -> str:
        if not image_name:
            return ""
        # 절대경로면 그대로, 아니면 프로젝트/image 밑에서 찾기
        p = Path(image_name)
        if p.is_file():
            return str(p)
        guess = self.base_dir / "image" / image_name
        return str(guess) if guess.is_file() else str(guess)  # 없으면 그냥 경로 전달

    def _make_section(self, title: str, cards: list):
        # 섹션 타이틀
        lab = QLabel(title); lab.setObjectName("h3")
        self.vbox.addWidget(lab)

        # === 가로 스크롤 영역 (드래그로 좌우 이동) ===
        sa = DragScrollArea()
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setFrameShape(QFrame.NoFrame)

        row = QWidget()
        hbox = QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(16)

        # 카드들 생성 (가로로 나열)
        for card in cards:
            box = QFrame(); box.setStyleSheet("QFrame { border:1px solid #E6E6E6; border-radius:12px; }")
            box.setFixedWidth(240)
            lay = QVBoxLayout(box)

            # 이미지
            img = ClickableLabel()
            resolved_path = self._resolve_image_path(card.get("image_path") or card.get("image") or "")

            # ✅ 안전 로딩: QImageReader로 읽고 RGB로 변환 (ICC/CMYK 이슈 회피)
            pix = None
            try:
                reader = QImageReader(resolved_path)
                reader.setAutoTransform(True)
                qimg = reader.read()
                if not qimg.isNull():
                    qimg = qimg.convertToFormat(QImage.Format_ARGB32)
                    pix = QPixmap.fromImage(qimg)
            except Exception:
                pix = None

            if (pix is None) or pix.isNull():
                pix = QPixmap(220, 220)
                pix.fill(Qt.lightGray)

            img.setPixmap(pix.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            img.setAlignment(Qt.AlignCenter)
            img.setCursor(QCursor(Qt.PointingHandCursor))

            # 텍스트
            name = QLabel(card.get("name","")); name.setWordWrap(True); name.setAlignment(Qt.AlignCenter)
            name.setObjectName("ProductTitle")
            price = card.get("price")
            meta = QLabel(f"₩{price:,}" if isinstance(price, int) else ""); meta.setAlignment(Qt.AlignCenter)
            meta.setObjectName("ProductMeta")

            lay.addWidget(img); lay.addWidget(name); lay.addWidget(meta)

            # 클릭 시 상세 (해결된 이미지 경로를 card에 주입해서 전달)
            def _open(card=card, resolved=resolved_path):
                enriched = dict(card)
                enriched["image_path"] = resolved
                enriched["image"] = resolved  # 상세가 image 키만 볼 수도 있으니 둘 다 채움
                dlg = ProductDetailDialog(enriched, self); dlg.exec_()

            img.clicked.connect(_open)

            def _name_click(event, card=card, resolved=resolved_path):
                if event.button() == Qt.LeftButton:
                    _open(card, resolved)
            name.mousePressEvent = _name_click

            # 가로 레이아웃에 카드 추가
            hbox.addWidget(box)

        # 끝에 여백을 위해 stretch
        hbox.addStretch(1)

        sa.setWidget(row)
        self.vbox.addWidget(sa)

    def set_sections(self, title: str, subtitle: str, sections: dict):
        """
        sections: {
           "쿠션": [ {name, price, image_path, description, ...}, ... ],
           "파운데이션": [...],
           "립": [...],
           "아이": [...]
        }
        """
        self._clear_sections()
        self.title.setText(title or "분석 결과")
        self.subtitle.setText(subtitle or "")

        order = ["쿠션", "파운데이션", "립", "아이"]
        for key in order:
            items = sections.get(key, [])
            if items:
                self._make_section(f"추천 {key}", items)

class ProductRecommendPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)
        
        self.recommend_title = QLabel("📦 추천 제품", objectName="h2")
        self.product_grid = QGridLayout()
        product_container = QWidget()
        product_container.setLayout(self.product_grid)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(product_container)
        
        self.go_home_btn = QPushButton("처음으로")
        self.go_home_btn.setFixedSize(300, 100)
        self.go_home_btn.setObjectName("home_btn")

        main_layout.addWidget(self.recommend_title)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(self.go_home_btn)
    def update_recommendations(self, payload):
        """
        payload 형태를 전부 흡수해서 페이지에 추천을 뿌려준다.
        - dict: {'products': [...]} 또는 {'items': [...]} 모두 지원
        - list: [{brand,name,price,image|image_path,...}, ...] 도 지원
        최종적으로 self.set_results(...) 또는 self.grid에 직접 렌더링.
        """
        # 1) products 리스트 뽑기
        products = []
        if isinstance(payload, dict):
            if 'products' in payload and isinstance(payload['products'], list):
                products = payload['products']
            elif 'items' in payload and isinstance(payload['items'], list):
                # items => products 형식으로 변환
                for it in payload['items']:
                    products.append({
                        'brand': it.get('brand',''),
                        'name': it.get('name',''),
                        'price': it.get('price'),
                        'image_path': it.get('image_path') or it.get('image',''),
                        'tags': it.get('tags', []),
                    })
        elif isinstance(payload, list):
            products = payload  # 이미 리스트면 그대로

        # 2) 카드 포맷으로 변환(brand, name, price, image_path, tags)
        items = []
        for p in products:
            price_raw = p.get('price')
            try:
                price_val = int(price_raw) if price_raw is not None and str(price_raw).isdigit() else None
            except Exception:
                price_val = None
            items.append({
                'brand': p.get('brand',''),
                'name':  p.get('name',''),
                'price': price_val,
                'image_path': p.get('image_path') or p.get('image','') or '',
                'tags': p.get('tags', []),
            })

        # 3) 이 페이지에 이미 set_results(...)가 있으면 그걸 사용
        if hasattr(self, "set_results") and callable(self.set_results):
            self.set_results(items)
            return

        # 4) set_results가 없다면, 기본 그리드 렌더링(필요시 조정)
        from PyQt5.QtWidgets import QLabel, QFrame, QVBoxLayout
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPixmap

        # grid 레이아웃이 없다면 만들어 둔다
        if not hasattr(self, "grid"):
            from PyQt5.QtWidgets import QGridLayout
            self.grid = QGridLayout(self)
            self.setLayout(self.grid)

        # 기존 위젯 삭제
        while self.grid.count():
            it = self.grid.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

        # 간단 카드 렌더링
        r = c = 0
        for card in items:
            box = QFrame()
            box.setObjectName("Card")
            v = QVBoxLayout(box)
            # 이미지
            img_path = card.get('image_path') or ''
            if img_path:
                pix = QPixmap(img_path)
                if not pix.isNull():
                    img = QLabel()
                    img.setPixmap(pix.scaledToWidth(180, Qt.SmoothTransformation))
                    v.addWidget(img, alignment=Qt.AlignCenter)
            # 텍스트
            t1 = QLabel(card.get('brand',''))
            t2 = QLabel(card.get('name',''))
            t3 = QLabel(f"₩{card['price']:,}" if isinstance(card.get('price'), int) else "")
            t1.setObjectName("ProductMeta")
            t2.setObjectName("ProductTitle")
            t3.setObjectName("ProductMeta")
            v.addWidget(t1); v.addWidget(t2); v.addWidget(t3)
            # 그리드에 추가
            self.grid.addWidget(box, r, c)
            c += 1
            if c >= 3:
                r += 1
                c = 0


