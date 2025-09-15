import os
import sys, traceback
def _global_excepthook(exc_type, exc, tb):
    print("\n[UNCAUGHT]", exc_type.__name__, exc)
    traceback.print_tb(tb)
    try:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "예기치 못한 오류", f"{exc_type.__name__}: {exc}")
    except Exception:
        pass

sys.excepthook = _global_excepthook
import csv
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QStackedWidget, QMessageBox, QDesktopWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
from ui_pages.skin_type_survey_page import SkinTypeSurveyPage

# UI
from ui_pages.home_page import HomePage
from ui_pages.capture_page import ProductCapturePage, FaceCapturePage
from ui_pages.result_pages import FaceResultPage, ProductRecommendPage
from ui_pages.loading_page import LoadingPage

# Webcam
from webcam_thread.webcam import WebcamThread

# Workers
from analysis_worker import AnalysisWorker
from product_analysis_worker import ProductAnalysisWorker

# DB
from db_manager.database import DatabaseManager

from ui_pages.capture_unified_view import CaptureUnifiedView


class BeautyFinderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI 뷰티 파인더")
        from PyQt5 import QtCore
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        self.showFullScreen()
        #self.setCursor(QtCore.Qt.BlankCursor)  # 마우스 커서 숨기기 (원하면 지워도 됨)

        # 상태 변수
        self.webcam_last_frame = None
        self.webcam_thread = None
        self.db_manager = DatabaseManager()
        self.user_tone = None
        self.user_color = None
        self.user_skin_type = None

        # 레이아웃
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)

        # 페이지 생성
        self.create_pages()
        self.apply_styles()
        self.stacked_widget.setCurrentWidget(self.pages['unified_capture'])
        self.start_webcam_and_connect(self.pages['unified_capture'])


        self.is_busy = False

    # ---------------- 페이지 생성 ----------------
    def create_pages(self):
        self.pages = {}
        self.pages['unified_capture'] = CaptureUnifiedView(self)
        self.stacked_widget.addWidget(self.pages['unified_capture'])
        self.pages['home'] = HomePage(self)
        self.pages['product_capture'] = ProductCapturePage(self)
        self.pages['product_capture'].use_ocr_flow(True)  # bind OCR button
        self.pages['face_capture'] = FaceCapturePage(self)
        self.pages['face_result'] = FaceResultPage(self)
        self.pages['product_recommend'] = ProductRecommendPage(self)
        self.pages['loading'] = LoadingPage(self)
        self.pages['skin_survey'] = SkinTypeSurveyPage(self)

        for key in self.pages:
            self.stacked_widget.addWidget(self.pages[key])

        # 버튼 연결
        self.pages['home'].product_btn.clicked.connect(self.show_product_capture)
        self.pages['home'].face_btn.clicked.connect(self.show_face_capture)
        self.pages['product_capture'].home_btn.clicked.connect(self.go_home)
        self.pages['face_capture'].home_btn.clicked.connect(self.go_home)
        self.pages['face_result'].go_home_btn.clicked.connect(self.go_home)
        self.pages['product_recommend'].go_home_btn.clicked.connect(self.go_home)
        self.pages['face_capture'].capture_btn.clicked.connect(self.start_face_analysis)
        self.pages['skin_survey'].submitted.connect(self.on_skin_survey_submitted)

    # ---------------- 제품 분석 ----------------
    def start_product_analysis(self):
        if self.webcam_last_frame is None or getattr(self.webcam_last_frame, 'size', 0) == 0:
            QMessageBox.warning(self, "안내", "웹캠 프레임을 아직 받지 못했어요.")
            return

        self.stop_webcam()
        self.pages['loading'].set_message("제품을 인식하고 있어요...", "잠시만 기다려 주세요")
        self.stacked_widget.setCurrentWidget(self.pages['loading'])
        QApplication.processEvents()

        self.product_analysis_thread = ProductAnalysisWorker(self.webcam_last_frame, self.db_manager)
        self.product_analysis_thread.finished_ok.connect(self.on_product_analysis_done)
        self.product_analysis_thread.finished_err.connect(self.on_product_analysis_error)
        self.product_analysis_thread.start()

    def on_product_analysis_done(self, payload):
        try:
            # ✅ OCR 디버그 요약 (선택)
            raws = payload.get('ocr_raw', [])
            lines = []
            for v in raws:
                vname = v.get('variant', 'ocr')
                for line in v.get('lines', [])[:5]:
                    lines.append(f"[{vname}] {line['text']} (conf={line['conf']:.2f})")
            if lines:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "OCR 디버그", "\n".join(lines[:15]))
        except Exception:
            pass

        # ✅ 제품 추천 페이지 업데이트
        # ✅ 제품 추천 페이지 업데이트
        self.pages['product_recommend'].update_recommendations(payload)
        self.stacked_widget.setCurrentWidget(self.pages['product_recommend'])


    def on_product_analysis_error(self, msg):
        QMessageBox.critical(self, "OCR 분석 오류", msg)
        self.go_home()


    # ---------------- 결과 페이지 카드 표시 어댑터 ----------------
    
    def show_products_in_result_page(self, sections, title="제품 인식 결과", subtitle=""):
        # 결과 페이지(FaceResultPage)에 직접 세팅 + 값 검증/보정 + 예외 방어
        page = self.pages.get("face_result")
        if page is None:
            QMessageBox.information(self, "정보", "face_result 페이지를 찾지 못했습니다.")
            print("pages keys:", list(getattr(self, "pages", {}).keys()))
            return

        # ---- 섹션/카드 값 검증 + 보정 (여기서 절대 죽지 않게) ----
        required_keys = ("쿠션", "파운데이션", "립", "아이")
        normalized = {k: list(sections.get(k, [])) for k in required_keys}

        def fix_card(card):
            name = (card.get("name") or "").strip()
            desc = (card.get("description") or "").strip()
            img  = (card.get("image_path") or card.get("image") or "").strip()
            price_raw = card.get("price", 0)
            try:
                if isinstance(price_raw, str):
                    price_val = int(price_raw.replace(",", "").strip() or "0")
                elif isinstance(price_raw, (int, float)):
                    price_val = int(price_raw)
                else:
                    price_val = 0
            except Exception:
                price_val = 0
            return {"name": name, "description": desc, "image_path": img, "price": price_val}

        for k in required_keys:
            normalized[k] = [fix_card(c) for c in normalized[k]]

        # ---- 결과 페이지 세팅 ----
        try:
            page.set_sections(title, subtitle, normalized)
        except Exception as e:
            import traceback, pprint
            print("\n[show_products_in_result_page] set_sections 예외:", type(e).__name__, e)
            pprint.pprint(normalized)
            traceback.print_exc()
            QMessageBox.critical(self, "결과 표시 오류", f"{type(e).__name__}: {e}")
            return

        # 같은 팝업(페이지)로 전환: 메인스레드 큐에 태워 안전 전환
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.stacked_widget.setCurrentWidget(page))


    def _read_csv_any(self, path):
        for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
            try:
                import csv
                with open(path, "r", encoding=enc) as f:
                    rdr = csv.DictReader(f)
                    return [row for row in rdr]
            except Exception:
                continue
        return []

    def _load_final_products(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, "final.csv")
        return self._read_csv_any(csv_path)

    # ---------------- 카테고리/타입 판별 ----------------
    def _is_base(self, row):
        t = (row.get("type") or "").strip()
        return ("쿠션" in t) or ("파운데이션" in t)

    def _is_lip(self, row):
        t = (row.get("type") or "").strip()
        return "립" in t

    def _is_eye(self, row):
        t = (row.get("type") or "").strip()
        return "아이" in t

    # ---------------- 필터 ----------------
    def _filter_for_base(self, all_rows, number, skin_type):
        number = (number or "").strip()
        skin_type = (skin_type or "").strip()
        out = []
        for r in all_rows:
            if not self._is_base(r):
                continue
            if number and (r.get("number", "").strip() != number):
                continue
            if skin_type:
                st = (r.get("skin_types", "") or "")
                if skin_type not in st:
                    continue
            out.append(r)
        return out

    def _filter_for_color_only(self, all_rows, personal_color):
        pc = (personal_color or "").strip()
        out = []
        for r in all_rows:
            if self._is_base(r):
                continue
            if not (self._is_lip(r) or self._is_eye(r)):
                continue
            if pc:
                rc = (r.get("personal_colors", "") or "")
                if pc not in rc:
                    continue
            out.append(r)
        return out

    # ---------------- OCR 결과 → 섹션 구성 ----------------
    def _build_ocr_sections(self, recognized_row):
        all_rows = self._load_final_products()
        if not all_rows or not isinstance(recognized_row, dict):
            return {"쿠션": [], "파운데이션": [], "립": [], "아이": []}

        def norm_card(r):
            name = (r.get("name") or "").strip()
            desc = (r.get("description") or "").strip()
            img  = (r.get("image_path") or r.get("image") or "").strip()
            price_raw = (r.get("price") or "").replace(",", "").strip()
            try:
                price_val = int(price_raw or "0")
            except Exception:
                price_val = 0
            return {"name": name, "description": desc, "image_path": img, "price": price_val}

        def is_base(r):
            t = (r.get("type") or "").strip()
            return ("쿠션" in t) or ("파운데이션" in t)
        def is_lip(r):
            return "립" in (r.get("type") or "")
        def is_eye(r):
            return "아이" in (r.get("type") or "")

        # 퍼컬 표기 정규화
        def _norm_pc(s: str) -> str:
            s = (s or "").strip().replace(" ", "")
            mapping = {
                "여쿨": "여름쿨", "여름쿨": "여름쿨",
                "겨쿨": "겨울쿨", "겨울쿨": "겨울쿨",
                "봄웜": "봄웜",   "가을웜": "가을웜",
            }
            return mapping.get(s, s)

        def _pc_match(target: str, hay: str) -> bool:
            t = _norm_pc(target); h = _norm_pc(hay)
            return (not t) or (t in h)

        # 인식값 없으면 사용자 분석값으로 보완
        r_type   = (recognized_row.get("type") or "").strip()
        r_number = (recognized_row.get("number") or self.user_tone or "").strip()
        r_skin   = (recognized_row.get("skin_types") or self.user_skin_type or "").strip()
        r_pcolor = _norm_pc((recognized_row.get("personal_colors") or self.user_color or ""))

        # 먼저 전체 후보를 만들어 두고, 마지막에 '표시 규칙'에 맞춰 걸러낸다
        cushions, foundations, lips, eyes = [], [], [], []

        # 베이스: number+skin_types
        for r in all_rows:
            if not is_base(r):
                continue
            if r_number and (r.get("number", "").strip() != r_number):
                continue
            if r_skin and r_skin not in (r.get("skin_types") or ""):
                continue
            t = (r.get("type") or "")
            if "쿠션" in t:
                cushions.append(norm_card(r))
            elif "파운데이션" in t:
                foundations.append(norm_card(r))

        # 컬러: personal_colors
        for r in all_rows:
            if is_base(r):
                continue
            if not _pc_match(r_pcolor, (r.get("personal_colors") or "")):
                continue
            if is_lip(r):
                lips.append(norm_card(r))
            elif is_eye(r):
                eyes.append(norm_card(r))

        # Top1은 해당 섹션 맨 앞에
        def _prepend_if_missing(lst: list, row: dict):
            if not row:
                return lst
            card = norm_card(row)
            if not any(c["name"] == card["name"] for c in lst):
                return [card] + lst
            return lst

        # === 표시 규칙 ===
        if ("립" in r_type) or ("아이" in r_type):
            # 립/아이는 컬러만
            if "립" in r_type:
                lips = _prepend_if_missing(lips, recognized_row)
            elif "아이" in r_type:
                eyes = _prepend_if_missing(eyes, recognized_row)
            sections = {"쿠션": [], "파운데이션": [], "립": lips, "아이": eyes}
        else:
            # 쿠션/파데 → 베이스 + 컬러 동시
            if "쿠션" in r_type:
                cushions = _prepend_if_missing(cushions, recognized_row)
            elif "파운데이션" in r_type:
                foundations = _prepend_if_missing(foundations, recognized_row)
            sections = {"쿠션": cushions, "파운데이션": foundations, "립": lips, "아이": eyes}

        try:
            print("[sections sizes]", {k: len(v) for k in sections})
        except Exception:
            pass

        return sections


    # ---------------- OCR 제품 분석 ----------------
    def run_ocr_product_capture(self):
        if self.is_busy:
            return
        self.is_busy = True

        try:
            if self.webcam_last_frame is None or getattr(self.webcam_last_frame, 'size', 0) == 0:
                QMessageBox.warning(self, "안내", "웹캠 프레임을 아직 받지 못했어요.")
                return

            frame = (
                self.webcam_last_frame.copy()
                if hasattr(self.webcam_last_frame, 'copy')
                else self.webcam_last_frame
            )

            self.stop_webcam()

            from ocr.ocr_matcher import run_ocr
            result = run_ocr(frame)
            if not result or not result.get("best"):
                QMessageBox.information(self, "정보", "텍스트 인식 실패 또는 후보 없음")
                return

            recognized = result["best"]
            print("[Top1 row]", recognized)

            sections = self._build_ocr_sections(recognized)

            rtype = (recognized.get("type") or "").strip()
            rcat  = (recognized.get("category") or "").strip()
            is_color = ("립" in rtype) or ("아이" in rtype) or ("색조" in rcat)
            is_base  = ("쿠션" in rtype) or ("파운데이션" in rtype) or ("베이스" in rcat)

            if is_color and not is_base:
                sections["쿠션"] = []
                sections["파운데이션"] = []
            elif is_base and not is_color:
                sections["립"] = []
                sections["아이"] = []


            # --- fallback (필요하면 유지) ---
            # ...

            # 제목/부제 설정
            r_number = (recognized.get("number") or "").strip()
            r_skin   = (recognized.get("skin_types") or "").strip()
            r_pcolor = (recognized.get("personal_colors") or "").strip()

            if is_base and not is_color:
                title = "제품 인식 결과 (베이스)"
                subtitle = f"호수: {r_number}호 · 피부타입: {r_skin}" if (r_number or r_skin) else ""
            elif is_color and not is_base:
                title = "제품 인식 결과 (컬러)"
                subtitle = f"퍼스널컬러: {r_pcolor}" if r_pcolor else ""
            else:
                title = "제품 인식 결과"
                subtitle = ""

            # ✅ 카드 표시
            try:
                self.show_products_in_result_page(sections, title=title, subtitle=subtitle)
            except Exception as e:
                import traceback, pprint
                print("\n[run_ocr_product_capture] show_products_in_result_page 예외:", type(e).__name__, e)
                pprint.pprint(sections)
                traceback.print_exc()
                QMessageBox.critical(self, "OCR 오류", f"표시 단계 오류: {type(e).__name__}: {e}")
                return

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "OCR 오류", str(e))

        finally:
            # ✅ 무조건 busy 해제
            self.is_busy = False
            try:
                self.pages['product_capture'].capture_btn.setEnabled(True)
            except Exception:
                pass


    # ---------------- 얼굴 분석 ----------------
    def start_face_analysis(self):
        if self.webcam_last_frame is None or getattr(self.webcam_last_frame, 'size', 0) == 0:
            QMessageBox.warning(self, "안내", "웹캠 프레임을 아직 받지 못했어요.")
            return

        self.stop_webcam()

        # ★ 통합화면에서 온 호출이면 로딩 화면으로 전환하지 않음
        if not getattr(self, "intent_face_from_unified", False):
            self.pages['loading'].set_message("피부톤을 분석하고 있어요...", "잠시만 기다려 주세요")
            self.stacked_widget.setCurrentWidget(self.pages['loading'])

        QApplication.processEvents()

        self.analysis_thread = AnalysisWorker(self.webcam_last_frame)
        self.analysis_thread.finished_ok.connect(self.on_analysis_done)
        self.analysis_thread.finished_err.connect(self.on_analysis_error)
        self.analysis_thread.start()


    def on_analysis_done(self, user_tone_num, user_color, brightness):
        """얼굴 분석 성공 → 설문 또는 통합 화면"""
        try:
            self.user_tone = user_tone_num     # 예: '21', '23' 등
            self.user_color = user_color       # 예: '봄웜', '여름쿨' 등 (분석 모듈 반환값)

            # --- 통합 화면에서 요청한 경우 (unified_capture)
            if getattr(self, "intent_face_from_unified", False):
                self.intent_face_from_unified = False  # 플래그 초기화
                unified = self.pages.get('unified_capture')
                if unified:
                    try:
                        self.stacked_widget.setCurrentWidget(unified)
                    except Exception:
                        pass
                    # ✅ 통합 화면에 결과 적용 (오른쪽 패널에 추천까지 로드)
                    unified.apply_face_result(user_tone_num, user_color)
                    # 분석 중 중단했던 웹캠 복구
                    try:
                        self.start_webcam_and_connect(unified)
                    except Exception:
                        pass
                    return  # 설문으로 안 넘어가고 여기서 끝

            # --- 기본 동작 (설문 페이지로 이동)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "피부 분석 결과",
                f"피부톤: {user_tone_num}호\n퍼스널 컬러: {user_color}\n피부 밝기: {brightness:.2f}\n\n이제 간단한 5문항으로 피부타입을 판별합니다."
            )
            self.pages['skin_survey'].set_initial_info(self.user_color, self.user_tone)
            self.stacked_widget.setCurrentWidget(self.pages['skin_survey'])

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "분석 오류", f"추천 준비 중 오류: {e}")
            self.go_home()

            
    def on_skin_survey_submitted(self, skin_type: str, scores: dict):
        """설문 완료 → 타입별 추천 생성 → 결과 페이지 표시"""
        try:
            self.user_skin_type = skin_type   # '지성' / '건성' / '민감성'
            sections = self.db_manager.recommend_by_types(
                personal_color=self.user_color,
                skin_type=self.user_skin_type,
                number=self.user_tone,        # '21', '23' 등
                k_per_section=6
            )

            title = "AI 분석 결과"
            subtitle = f"퍼스널컬러: {self.user_color} · 호수: {self.user_tone}호 · 피부타입: {self.user_skin_type}"
            self.pages['face_result'].set_sections(title, subtitle, sections)
            self.stacked_widget.setCurrentWidget(self.pages['face_result'])

        except Exception as e:
            QMessageBox.critical(self, "추천 오류", f"추천 생성 중 오류: {e}")
            self.go_home()

    def on_analysis_error(self, msg):
        QMessageBox.critical(self, "분석 오류", msg)
        self.go_home()

    # ---------------- UI 스타일 ----------------
    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #fdf6f9; }
            QPushButton#main_menu_btn {
                background-color: #ff87ab;
                color: white;
                font-size: 2.5em;
                font-weight: bold;
                padding: 40px 60px;
                border: 1px solid #ff87ab;
                border-radius: 20px;
            }
            QPushButton#main_menu_btn:hover { background-color: #e67a9a; }
            QPushButton#capture_btn {
                background-color: #87e3ff;
                color: white;
                font-size: 2em;
                font-weight: bold;
                padding: 30px;
                border-radius: 50px;
            }
            QPushButton#capture_btn:hover { background-color: #7ac8e6; }
            QPushButton#home_btn {
                background-color: #ccc;
                color: white;
                font-size: 2em;
                font-weight: bold;
                padding: 30px;
                border-radius: 50px;
            }
            QPushButton#home_btn:hover { background-color: #bbb; }
        """)

    # ---------------- 네비게이션 ----------------
    def go_home(self):
        self.stop_webcam()
        self.stacked_widget.setCurrentWidget(self.pages['home'])

    def show_product_capture(self):
        self.start_webcam_and_connect(self.pages['product_capture'])
        self.stacked_widget.setCurrentWidget(self.pages['product_capture'])

    def show_face_capture(self):
        self.start_webcam_and_connect(self.pages['face_capture'])
        self.stacked_widget.setCurrentWidget(self.pages['face_capture'])

    from PyQt5.QtGui import QImage
    import numpy as np, cv2

    def _qimage_to_bgr(qimg: QImage):
        # 어떤 포맷이 와도 RGB888로 변환 후 안전하게 ndarray 뽑기
        if qimg.format() != QImage.Format_RGB888:
            qimg = qimg.convertToFormat(QImage.Format_RGB888)
        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        ptr.setsize(h * qimg.bytesPerLine())
        arr = np.frombuffer(ptr, np.uint8).reshape(h, qimg.bytesPerLine() // 3, 3)[:, :w, :]
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    
    def _stash_last(*args):
        try:
            if len(args) == 2:
                # (QImage, raw_bgr) 쌍으로 오는 경우
                self.webcam_last_frame = args[1]
            elif len(args) == 1 and isinstance(args[0], QImage):
                # QImage만 오는 경우 → 항상 RGB888로 변환해서 BGR ndarray 저장
                self.webcam_last_frame = _qimage_to_bgr(args[0])
        except Exception:
            # 변환 실패 시 None으로 두되, 앱은 죽지 않게
            self.webcam_last_frame = None



    # ---------------- 웹캠 ----------------
    def start_webcam_and_connect(self, page_widget):
        
        # 기존 스레드 정리
        if self.webcam_thread and self.webcam_thread.isRunning():
            try:
                self.webcam_thread.change_pixmap_signal.disconnect()
            except Exception:
                pass
            self.webcam_thread.stop()
            self.webcam_thread.wait(1500)

        # 새 스레드
        self.webcam_thread = WebcamThread(rotate=False, mirror=False)

        # --- 프리뷰 업데이트 핸들러 (페이지 시그니처 차이 대응) ---
        def _forward_update(*args):
            try:
                # (QImage,) 또는 (QImage, frame_bgr) 모두 지원
                page_widget.update_frame(*args)
            except TypeError:
                if args:
                    try:
                        page_widget.update_frame(args[0])
                    except Exception:
                        pass

        # --- 마지막 프레임 보관 (OCR용) ---
        def _stash_last(*args):
            try:
                if len(args) == 2:
                    # (QImage, frame_bgr) 형태
                    self.webcam_last_frame = args[1]
                elif len(args) == 1:
                    # (QImage,) 형태 → QImage를 BGR ndarray로 변환
                    qimg = args[0]
                    if isinstance(qimg, QImage):
                        w = qimg.width()
                        h = qimg.height()
                        ptr = qimg.bits()
                        ptr.setsize(h * qimg.bytesPerLine())
                        arr = np.frombuffer(ptr, np.uint8).reshape((h, qimg.bytesPerLine() // 3, 3))[:, :w, :]
                        self.webcam_last_frame = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            except Exception:
                # 변환 실패해도 앱이 죽지 않도록 무시
                pass

        # --- 시그널 연결: 반드시 QueuedConnection ---
        from PyQt5.QtCore import Qt
        self.webcam_thread.change_pixmap_signal.connect(_forward_update, type=Qt.QueuedConnection)
        self.webcam_thread.change_pixmap_signal.connect(_stash_last,     type=Qt.QueuedConnection)

        # 스레드 시작 (딱 한 번만)
        self.webcam_thread.start()


    def stop_webcam(self):
        if self.webcam_thread:
            try:
                self.webcam_thread.change_pixmap_signal.disconnect()
            except Exception:
                pass
            if self.webcam_thread.isRunning():
                self.webcam_thread.stop()
                self.webcam_thread.wait(1500)  # 1.5s 안전 대기
        self.webcam_thread = None


    # ---------------- 윈도우 ----------------
    def closeEvent(self, event):
        self.stop_webcam()
        event.accept()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_app = BeautyFinderApp()
    main_app.show()
    sys.exit(app.exec_())
