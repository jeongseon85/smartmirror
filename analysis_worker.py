import sys
import cv2
import tempfile
import os
import json
from PyQt5.QtCore import QThread, pyqtSignal
from personal_color_analysis.detect_face import DetectFace
from personal_color_analysis.color_extract import DominantColors
from personal_color_analysis.tone_analysis import is_warm, is_spr, is_smr
from colormath.color_objects import LabColor, sRGBColor, HSVColor
from colormath.color_conversions import convert_color
import numpy as np
from ocr.product_ocr import process_ocr
from ocr.ocr_matcher import load_products, best_match_robust


class AnalysisWorker(QThread):
    finished_ok = pyqtSignal(str, str, float)
    finished_err = pyqtSignal(str)

    def __init__(self, img_bgr, parent=None):
        super().__init__(parent)
        self.img_bgr = img_bgr
    
    # --- Compatibility wrapper: use ocr_matcher APIs but keep the old name ---
    def match_ocr_to_db(ocr_texts, csv_path, top_k=3):
        """
        ocr_matcher에 match_ocr_to_db가 없으므로
        load_products + best_match_robust로 동일 인터페이스를 제공하는 래퍼.
        반환 딕셔너리 키는 기존 코드와 호환:
        ok, texts, score, detail, best, top
        """
        products = load_products(csv_path)  # 리스트[{"row":row, "name_norm":..., ...}]
        best, score, top, ok, detail = best_match_robust(ocr_texts, products, top_k=top_k)

        if best:
            row = best["row"]
            return {
                "ok": ok,
                "texts": ocr_texts,
                "score": score,
                "detail": detail,         # {"base","partial_bonus","num_matches","num_bonus","token_hits","tok_bonus","q_raw"}
                "best": row,              # CSV 한 행(dict)
                "top": [p["row"] for (_, p) in top],  # 상위 후보들 CSV 행(dict) 리스트
            }
        else:
            return {"ok": False, "reason": "no_candidate", "texts": ocr_texts, "best": None, "top": []}


    def run(self):
        tmp_path = None
        try:
            # 윈도우 환경에 맞춰 회전 로직 제거
            rotated_bgr = self.img_bgr
            
            (h, w) = rotated_bgr.shape[:2]
            if w > 640:
                r = 640 / float(w)
                dim = (640, int(h * r))
                resized_bgr = cv2.resize(rotated_bgr, dim, interpolation=cv2.INTER_AREA)
            else:
                resized_bgr = rotated_bgr
            
            lab = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            final_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
            os.close(fd)
            cv2.imwrite(tmp_path, final_bgr)
            
            df = DetectFace(tmp_path)
            face = [df.left_cheek, df.right_cheek, df.left_eyebrow, df.right_eyebrow, df.left_eye, df.right_eye]
            temp = []
            clusters = 4
            for f in face:
                dc = DominantColors(f, clusters)
                face_part_color, _ = dc.getHistogram()
                temp.append(np.array(face_part_color[0]))
            
            cheek = np.mean([temp[0], temp[1]], axis=0)
            eyebrow = np.mean([temp[2], temp[3]], axis=0)
            eye = np.mean([temp[4], temp[5]], axis=0)

            Lab_l, Lab_b, hsv_s = [], [], []
            color = [cheek, eyebrow, eye]
            for i in range(3):
                rgb = sRGBColor(color[i][0], color[i][1], color[i][2], is_upscaled=True)
                lab_color = convert_color(rgb, LabColor, through_rgb_type=sRGBColor)
                hsv = convert_color(rgb, HSVColor, through_rgb_type=sRGBColor)
                Lab_l.append(float(format(lab_color.lab_l, ".2f")))
                Lab_b.append(float(format(lab_color.lab_b, ".2f")))
                hsv_s.append(float(format(hsv.hsv_s, ".2f")) * 100)

            Lab_weight = [30, 20, 5]
            hsv_weight = [10, 1, 1]
            
            if is_warm(Lab_b, Lab_weight):
                if is_spr(hsv_s, hsv_weight):
                    personal_color = 'spring_warm'
                else:
                    personal_color = 'fall_warm'
            else:
                if is_smr(hsv_s, hsv_weight):
                    personal_color = 'summer_cool'
                else:
                    personal_color = 'winter_cool'
            
            avg_lab_l = np.mean(Lab_l)
            
            if avg_lab_l >= 80:
                user_tone_num = '20'
            elif avg_lab_l >= 60:
                user_tone_num = '21'
            elif avg_lab_l >= 40:
                user_tone_num = '22'
            else:
                user_tone_num = '23'
            
            brightness = float(avg_lab_l)

            self.finished_ok.emit(user_tone_num, personal_color, brightness)
            
        except RuntimeError as e:
            if str(e) == "No face detected in the image.":
                cv2.imwrite('dlib_error.jpg', self.img_bgr)
                self.finished_err.emit("이미지에서 얼굴을 찾을 수 없어요. 조명과 얼굴 위치를 확인해주세요.")
            else:
                self.finished_err.emit(str(e))
        except Exception as e:
            self.finished_err.emit(f"분석 중 오류가 발생했습니다: {str(e)}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass