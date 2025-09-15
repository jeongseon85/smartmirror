# personal_color_analysis/skin_tone_estimator.py

import os
import tempfile
import cv2
import numpy as np

# pip install skin-tone-classifier
# 패키지 내부 모듈명은 stone
import stone

def hex_to_bgr(hex_code: str):
    hex_code = hex_code.lstrip('#')
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    return (b, g, r)

def bgr_to_lab_L(bgr: tuple) -> float:
    """BGR(0-255) 1픽셀을 OpenCV Lab로 변환해 L(0-255)만 반환"""
    arr = np.uint8([[list(bgr)]])  # (1,1,3)
    lab = cv2.cvtColor(arr, cv2.COLOR_BGR2LAB)
    return float(lab[0, 0, 0])

def map_L_to_shade(L: float) -> str:
    """
    L(0~255) 기준으로 20~23호 구간화.
    카메라/조명에 따라 아래 경계값을 조금씩 튜닝하세요.
    """
    if L >= 195:
        return '20'
    elif L >= 175:
        return '21'
    elif L >= 155:
        return '22'
    else:
        return '23'

def estimate_shade_from_bgr(img_bgr: np.ndarray, palette: str = 'perla') -> dict:
    """
    입력:  BGR 이미지 (numpy)
    출력:  {'shade': '20'|'21'|'22'|'23', 'hex': '#RRGGBB', 'L': float, 'tone_label': str, 'accuracy': float}
    실패 시 RuntimeError
    """
    fd, tmp = tempfile.mkstemp(suffix=".png"); os.close(fd)
    try:
        cv2.imwrite(tmp, img_bgr)

        # image_type: 'color' 고정, palette: 'perla'/'yadon-ostfeld'/'proder' 등
        result = stone.process(tmp, 'color', palette, return_report_image=False)
        faces = result.get('faces') or []
        if not faces:
            raise RuntimeError("No face detected by SkinToneClassifier")

        f0 = faces[0]
        hex_skin   = f0.get('skin_tone')       # "#RRGGBB"
        tone_label = f0.get('tone_label')      # "CF" 등
        acc        = float(f0.get('accuracy', 0.0))

        if not hex_skin:
            raise RuntimeError("SkinToneClassifier returned no hex")

        L = bgr_to_lab_L(hex_to_bgr(hex_skin))
        shade = map_L_to_shade(L)

        return {'shade': shade, 'hex': hex_skin, 'L': L, 'tone_label': tone_label, 'accuracy': acc}
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
