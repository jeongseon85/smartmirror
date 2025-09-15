import cv2, logging
from PyQt5.QtCore import QThread, pyqtSignal
from ocr.product_ocr import process_ocr
from ocr import product_ocr, ocr_matcher

try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
    RAPID = True
except Exception:
    RAPID = False

log = logging.getLogger(__name__)

class ProductAnalysisWorker(QThread):
    finished_ok = pyqtSignal(dict)
    finished_err = pyqtSignal(str)

    def __init__(self, img_bgr, db_manager, parent=None):
        super().__init__(parent)
        self.img_bgr = img_bgr
        self.db = db_manager

    def _fuzzy_lookup(self, text, limit=5):
        try:
            names = self.db.get_all_product_names() or []
        except Exception as e:
            log.exception('get_all_product_names failed: %s', e)
            names = []
        if not (RAPID and names and text):
            return []
        matches = rf_process.extract(text, names, scorer=rf_fuzz.token_set_ratio, limit=limit)
        rows = []
        for name, score, _ in matches:
            try:
                row = self.db.get_product_by_name(name, limit=1)
                if row: rows.append(row)
            except Exception as e:
                log.exception('get_product_by_name fuzzy failed: %s', e)
        return rows

    def run(self):
        try:
            if self.img_bgr is None:
                self.finished_err.emit('카메라 프레임이 비어있습니다.')
                return

            frame = cv2.resize(self.img_bgr, (640, 480), interpolation=cv2.INTER_AREA)

            MIRROR_INPUT = True
            if MIRROR_INPUT:
                frame = cv2.flip(frame, 1)

            # 0) 사전 (있으면 인식 품질↑)
            try:
                brands = self.db.get_all_brands()
            except Exception as e:
                log.warning('get_all_brands failed: %s', e)
                brands = []
            try:
                prods  = self.db.get_all_product_names()
            except Exception as e:
                log.warning('get_all_product_names failed: %s', e)
                prods = []

            # 1) OCR (+ 디버그 수집)
            dbg = {}
            ocr = process_ocr(frame, brand_lex=brands, product_lex=prods, debug=dbg)
            log.info('OCR result: %s', ocr)

            text = (ocr.get('text') if isinstance(ocr, dict) else str(ocr)).strip()
            if not text:
                self.finished_err.emit('이미지에서 텍스트가 인식되지 않았습니다. 라벨을 정면·밝게 비춰주세요.')
                return

            # 2) DB direct match
            try:
                direct_rows = self.db.get_product_by_name(text, limit=5) or []
            except Exception as e:
                log.exception('get_product_by_name direct failed: %s', e)
                direct_rows = []

            # 3) Fuzzy fallback
            fuzzy_rows = self._fuzzy_lookup(text, limit=5) if not direct_rows else []

            # 4) Recommendations (항상 무언가 제공)
            personal_color = None
            skin_type = None
            picked = direct_rows[0] if direct_rows else (fuzzy_rows[0] if fuzzy_rows else None)
            if picked:
                pc = (picked.get('personal_colors') or '').split(',')
                st = (picked.get('skin_types') or '').split(',')
                personal_color = (pc[0] or None) if pc else None
                skin_type = (st[0] or None) if st else None
            try:
                recs = self.db.get_products_by_filter(personal_color=personal_color, skin_type=skin_type, limit=9)
            except Exception as e:
                log.exception('get_products_by_filter failed: %s', e)
                recs = []

            # 5) 표준 페이로드 (UI가 무엇을 기대하든 최소 products는 보장)
            payload = {
                'ok': True,
                'ocr_text': text,
                'ocr_detail': (ocr.get('detail') if isinstance(ocr, dict) else None),
                'ocr_debug_dir': dbg.get('dir'),
                'ocr_overlays': ocr.get('overlays', []),
                'ocr_raw': ocr.get('raw', []),
                'found_product': picked,
                'direct_hits': direct_rows,
                'fuzzy_hits': fuzzy_rows,
                'recommendations': recs,
                'products': direct_rows or fuzzy_rows or recs
            }
            self.finished_ok.emit(payload)

        except Exception as e:
            log.exception('ProductAnalysisWorker crashed: %s', e)
            self.finished_err.emit(f'제품 분석 중 오류가 발생했습니다: {e}')
