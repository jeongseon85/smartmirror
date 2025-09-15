# -*- coding: utf-8 -*-
import os, cv2, numpy as np, time, json, pathlib

from typing import List, Tuple, Dict, Any
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ = True
except Exception:
    RAPIDFUZZ = False

import easyocr
try:
    import torch
    TORCH_OK = True
except Exception:
    torch = None
    TORCH_OK = False

_READER = None

# ---------------- Jetson 감지 ----------------
def _is_jetson():
    try:
        return os.path.isfile('/etc/nv_tegra_release')
    except Exception:
        return False

def get_reader(model_dir='./.easyocr'):
    """
    - 모델 캐시 경로 고정(첫 실행 이후 재다운로드 방지)
    - Jetson은 메모리/안정성 고려해 GPU 기본 비활성 권장
    """
    global _READER
    if _READER is None:
        for_jetson = _is_jetson()

        use_gpu = False
        if TORCH_OK and getattr(torch, "cuda", None):
            use_gpu = (torch.cuda.is_available() and not for_jetson)

        try:
            os.makedirs(model_dir, exist_ok=True)
        except Exception:
            pass

        _READER = easyocr.Reader(
            ['ko', 'en'],
            gpu=bool(use_gpu),
            model_storage_directory=model_dir
        )
    return _READER

# ---------- JSON 직렬화 안전 변환 ----------
def _json_safe(o):
    import numpy as _np
    if isinstance(o, (_np.integer,)):
        return int(o)
    if isinstance(o, (_np.floating,)):
        return float(o)
    if isinstance(o, _np.ndarray):
        return o.tolist()
    return o

def _deskew(gray):
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi/180, 120)
    if lines is None: return gray
    angles = []
    for rho, theta in lines[:,0]:
        ang = (theta*180/np.pi) - 90
        if -45 < ang < 45: angles.append(ang)
    if not angles: return gray
    m = float(np.median(angles))
    h, w = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w//2, h//2), m, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def _binarize(gray):
    gray = cv2.GaussianBlur(gray, (3,3), 0)
    clahe = cv2.createCLAHE(2.0, (8,8))
    g2 = clahe.apply(gray)
    bw = cv2.adaptiveThreshold(g2,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,31,7)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((2,2),np.uint8), 1)
    return bw

def _largest_text_roi(bw):
    cnts,_ = cv2.findContours(255-bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        h,w = bw.shape[:2]; return 0,0,w,h
    c = max(cnts, key=cv2.contourArea)
    x,y,w,h = cv2.boundingRect(c)
    pad = int(0.06*max(w,h))
    return max(0,x-pad), max(0,y-pad), min(w+2*pad, bw.shape[1]-x+pad), min(h+2*pad, bw.shape[0]-y+pad)

def _illumination_correct(gray):
    # 배경 조명 성분 제거(광택/그림자 완화)
    bg = cv2.morphologyEx(gray, cv2.MORPH_OPEN, np.ones((25,25), np.uint8))
    norm = cv2.normalize(cv2.subtract(gray, bg), None, 0, 255, cv2.NORM_MINMAX)
    return norm

def _clahe_bgr(bgr):
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    y2 = clahe.apply(y)
    return cv2.cvtColor(cv2.merge([y2, cr, cb]), cv2.COLOR_YCrCb2BGR)

def _gamma(img, g=1.3):
    table = np.array([(i/255.0)**(1.0/g)*255 for i in range(256)]).astype("uint8")
    return cv2.LUT(img, table)

def _largest_text_roi_relaxed(bw, k=3, pad_ratio=0.10):
    # 상위 k개 외곽영역을 합쳐 더 넓게 ROI (광택으로 분절된 텍스트 대응)
    cnts,_ = cv2.findContours(255-bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        h,w = bw.shape[:2]; return 0,0,w,h
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:max(1,k)]
    x0,y0,x1,y1 = 1e9,1e9, -1,-1
    for c in cnts:
        x,y,w,h = cv2.boundingRect(c)
        x0,y0 = min(x0,x), min(y0,y)
        x1,y1 = max(x1,x+w), max(y1,y+h)
    H,W = bw.shape[:2]
    pad = int(pad_ratio*max(W,H))
    x0 = max(0, x0-pad); y0 = max(0, y0-pad)
    x1 = min(W, x1+pad); y1 = min(H, y1+pad)
    return x0,y0,(x1-x0),(y1-y0)

def preprocess_for_ocr(bgr):
    # 1) 기울기 보정은 기존대로 gray 기준
    base = bgr.copy()
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    gray = _deskew(gray)

    # 2) 조명 보정 + 부드럽게 + 이진화
    illum = _illumination_correct(gray)
    den  = cv2.bilateralFilter(illum, 7, 50, 50)   # 가장자리 보존 노이즈 완화
    cla  = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(den)
    bw   = cv2.adaptiveThreshold(cla,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,35,7)
    bw   = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((2,2),np.uint8), 1)

    # 3) ROI: 상위 컨투어 합쳐 넓게 + 여유 패딩
    x,y,w,h = _largest_text_roi_relaxed(bw, k=3, pad_ratio=0.12)
    roi = base[y:y+h, x:x+w]

    # 4) 추가 변형(광택/저대비 보완용)과 함께 앙상블
    v1 = roi
    v2 = _clahe_bgr(roi)
    v3 = _gamma(roi, 1.4)
    v4 = cv2.cvtColor(bw[y:y+h, x:x+w], cv2.COLOR_GRAY2BGR)

    # ★ Top-hat으로 밝은 배경 위 어두운 텍스트 부각
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21,21))
    tophat = cv2.morphologyEx(gray_roi, cv2.MORPH_TOPHAT, kernel)
    tophat = cv2.normalize(tophat, None, 0, 255, cv2.NORM_MINMAX)
    v5 = cv2.cvtColor(tophat, cv2.COLOR_GRAY2BGR)

    # ★ Unsharp mask로 에지 선명화
    blur = cv2.GaussianBlur(roi, (0,0), 1.2)
    v6 = cv2.addWeighted(roi, 1.5, blur, -0.5, 0)


    return [
        ("orig", v1),
        ("clahe", v2),
        ("gamma", v3),
        ("bin",   v4),
        ("tophat", v5),     # ★ 추가
        ("sharp",  v6),     # ★ 추가
        ("rot90",  cv2.rotate(v1, cv2.ROTATE_90_CLOCKWISE)),
        ("rot180", cv2.rotate(v1, cv2.ROTATE_180)),
        ("rot270", cv2.rotate(v1, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ]



# ---------- 후처리/스코어 ----------
_KR = set(range(ord('가'), ord('힣')+1))
def korean_ratio(s): return 0.0 if not s else sum(1 for ch in s if ord(ch) in _KR)/max(1,len(s))

# 전각/유사문자 치환 확장
_FULLWIDTH = {
    '０':'0','１':'1','２':'2','３':'3','４':'4','５':'5','６':'6','７':'7','８':'8','９':'9',
    'Ｏ':'O','ｏ':'o','Ｉ':'I','ｌ':'l','（':'(', '）':')','〔':'(','〕':')','［':'[','］':']','｛':'{','｝':'}'
}
_SIMILAR = {'O':'0','o':'0','I':'1','l':'1','|':'1','B':'8','S':'5','Z':'2'}

def normalize_errors(s):
    if not s: return s
    for a,b in _FULLWIDTH.items():
        s = s.replace(a, b)
    s = s.replace('rn','m')
    return s.translate(str.maketrans(_SIMILAR))

def fuzzy(a,b):
    if not RAPIDFUZZ: return 0.0
    return fuzz.token_set_ratio(a,b)/100.0

def _draw_detections(bgr, res):
    vis = bgr.copy()
    import numpy as _np
    for it in (res or []):
        if isinstance(it, (list,tuple)) and len(it)>=3:
            box, t, c = it[:3]
        elif isinstance(it, dict):
            box, t, c = it.get('box'), it.get('text',''), it.get('conf',0)
        else:
            continue
        if box is None: continue
        box = _np.asarray(box, dtype=_np.int32)
        cv2.polylines(vis, [box], True, (0,255,0), 2)
        x = int(box[:,0].min()); y = int(box[:,1].min())
        cv2.putText(vis, "{} ({:.2f})".format(str(t), float(c)), (x, max(0,y-4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1, cv2.LINE_AA)
    return vis

def select_best(preds, brands, products):
    def _penalty(s):
        s2 = (s or "").strip()
        if len(s2) <= 1:
            return 0.25
        if len(s2) <= 3:
            return 0.12
        # 허용 문자 외 비율이 높으면 감점
        ok = set(" +-.,/&")  # 허용 특수
        non_ok = sum(1 for ch in s2 if not ('0'<=ch<='9' or 'A'<=ch<='Z' or 'a'<=ch<='z' or '가'<=ch<='힣' or ch in ok))
        return min(0.15, non_ok / max(1, len(s2)) * 0.2)

    best = {"text":"","score":0.0,"detail":[]}
    for txt, conf in preds:
        t = normalize_errors(txt)
        k = korean_ratio(t)
        b = max((fuzzy(t,x) for x in brands), default=0.0) if brands else 0.0
        p = max((fuzzy(t,x) for x in products), default=0.0) if products else 0.0
        score = 0.5*conf + 0.2*k + 0.2*b + 0.1*p
        score -= _penalty(t)  # ★ 단문자/기호 과다 시 감점
        best["detail"].append({"text":txt,"conf":conf,"k_ratio":k,"brand":b,"prod":p,"score":score})
        if score > best["score"]:
            best["text"], best["score"] = txt, score
    return best


def read_product_text(bgr, brand_lex=None, product_lex=None, allowlist="가-힣A-Za-z0-9()+&- .,[] ", debug=None):
    """
    debug(dict)를 넘기면:
      - debug['dir']에 디버그 폴더 경로 기록
      - 각 전처리/회전 버전 오버레이 이미지를 저장하고 경로를 결과에 포함
      - 결과 dict에 'raw' / 'overlays' / 'detail' 포함
    """
    reader = get_reader()

    # 디버그 준비
    ts = time.strftime("%Y%m%d_%H%M%S")
    dbg_dir = pathlib.Path("logs/ocr") / ts
    if debug is not None:
        dbg_dir.mkdir(parents=True, exist_ok=True)
        debug["dir"] = str(dbg_dir)
        debug["variants"] = []

    preds = []
    raw_all = []
    overlays = []

    for vname, im in preprocess_for_ocr(bgr):
        # --- EasyOCR 파라미터 튜닝 (정확도 강화 / Jetson 안전값) ---
        for_jetson = _is_jetson()
        params = dict(
            contrast_ths=0.03,         # 경계 과강조 완화
            adjust_contrast=0.6,
            text_threshold=0.50,
            low_text=0.18,
            link_threshold=0.25,       # 파편 연결 좀 더 느슨
            canvas_size=2048 if not for_jetson else 1280,
            mag_ratio=1.7  if not for_jetson else 1.4,
            slope_ths=0.2, ycenter_ths=0.5, height_ths=0.6, width_ths=0.7,
            decoder='beamsearch',
            paragraph=True,            # ★ 단문자 분절 줄이기
            rotation_info=[0, 90, 180, 270],
        )
        # 괄호/대괄호/중괄호 등 노이즈 억제
        allowlist = "가-힣A-Za-z0-9+&- .,/"   # ()[]{} 제거
        blocklist  = "`~|{}[]<>^_=#:;\\"

        res = reader.readtext(
            im,
            detail=1,
            allowlist=allowlist,   # 한/영/숫자 위주
            blocklist=blocklist,
            **params
        )

        # 라인 정리 (JSON-safe로 캐스팅)
        lines, confs = [], []
        for it in (res or []):
            if isinstance(it,(list,tuple)) and len(it)>=3:
                box, t, c = it[:3]
            elif isinstance(it,dict):
                box, t, c = it.get('box'), it.get('text',''), it.get('conf',0)
            else:
                continue

            # box -> list[list[int,int]]
            try:
                pts = np.asarray(box).tolist() if box is not None else None
            except Exception:
                pts = box
            if pts is not None:
                box_py = [[int(float(x)), int(float(y))] for x, y in pts]
            else:
                box_py = None

            t_py = str(t) if t is not None else ""
            c_py = float(c) if c is not None else 0.0

            if t_py:
                lines.append({"text": t_py, "conf": c_py, "box": box_py})
                confs.append(c_py)

        # Fallback: 결과가 짧거나 신뢰도 낮으면 원본 전체 프레임 재시도
        need_fallback = False
        avg_conf = float(np.mean(confs)) if confs else 0.0
        if not lines:
            need_fallback = True
        else:
            total_len = len(" ".join([x["text"] for x in lines]))
            if total_len < 6 and avg_conf < 0.55:
                need_fallback = True

        if need_fallback:
            full = bgr.copy()
            try:
                res2 = reader.readtext(
                    full,
                    detail=1,
                    allowlist=allowlist,
                    blocklist="`~|{}[]<>^_=",
                    contrast_ths=0.05, adjust_contrast=0.7,
                    text_threshold=0.50, low_text=0.22, link_threshold=0.30,
                    canvas_size=1920 if not _is_jetson() else 1280,
                    mag_ratio=1.5  if not _is_jetson() else 1.3,
                    slope_ths=0.2, ycenter_ths=0.5, height_ths=0.6, width_ths=0.7,
                    decoder='beamsearch' if not _is_jetson() else 'greedy',
                    paragraph=False,
                    rotation_info=[0,90,180,270],
                )
            except Exception:
                res2 = []

            lines2, confs2 = [], []
            for it in (res2 or []):
                if isinstance(it,(list,tuple)) and len(it)>=3:
                    box, t, c = it[:3]
                elif isinstance(it,dict):
                    box, t, c = it.get('box'), it.get('text',''), it.get('conf',0)
                else:
                    continue
                t_py = str(t) if t is not None else ""
                if t_py:
                    lines2.append({"text": t_py, "conf": float(c or 0.0), "box": None})
                    confs2.append(float(c or 0.0))

            if lines2:
                joined2 = normalize_errors(" ".join([x["text"] for x in lines2]).strip())
                preds.append((joined2, float(np.mean(confs2)) if confs2 else 0.0))
                raw_all.append({"variant": "fallback_full", "lines": lines2})

        if lines:
            joined = " ".join([x["text"] for x in lines]).strip()
            joined = normalize_errors(joined)  # 오인식 보정
            preds.append((joined, float(np.mean(confs)) if confs else 0.0))
            raw_all.append({"variant": vname, "lines": lines})

        # 오버레이 저장
        if debug is not None:
            vis = _draw_detections(im, res or [])
            out_path = str(dbg_dir / f"{vname}_overlay.jpg")
            cv2.imwrite(out_path, vis)
            overlays.append(out_path)
            debug["variants"].append({"name": vname, "overlay": out_path, "lines": lines})

    best = select_best(preds, brand_lex or [], product_lex or [])
    best["raw"] = raw_all
    best["overlays"] = overlays

    # 디버그 JSON 저장 (남은 numpy 타입도 안전 변환)
    if debug is not None:
        with open(dbg_dir / "ocr_debug.json", "w", encoding="utf-8") as f:
            json.dump({"best": best}, f, ensure_ascii=False, indent=2, default=_json_safe)

    return best

# 호환 래퍼
def process_ocr(bgr, brand_lex=None, product_lex=None, allowlist="가-힣A-Za-z0-9()+&- .,[] ", debug=None):
    return read_product_text(bgr, brand_lex=brand_lex, product_lex=product_lex, allowlist=allowlist, debug=debug)
