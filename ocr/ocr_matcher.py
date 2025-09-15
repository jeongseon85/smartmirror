# -*- coding: utf-8 -*-
"""
ocr_matcher.py
- Webcam frame → EasyOCR → final.csv product matching
- Robust fuzzy matching with numeric/token boosts
- If confidence is low, still returns top-1 candidate ("확신 부족이어도 1등 강제표시")
Python 3.6+ compatible
"""
from __future__ import annotations

import os
import re
import csv
import unicodedata

import cv2  # only for type hints / potential pre-processing
import easyocr

# Prefer rapidfuzz; fallback to difflib
try:
    from rapidfuzz import fuzz
    def _sim_wr(a, b): return fuzz.WRatio(a, b)
    def _sim_token(a, b): return fuzz.token_set_ratio(a, b)
    def _sim_partial(a, b): return fuzz.partial_ratio(a, b)
except Exception:
    import difflib
    def _sim_wr(a, b): return int(difflib.SequenceMatcher(None, a, b).ratio() * 100)
    def _sim_token(a, b): return _sim_wr(a, b)
    def _sim_partial(a, b): return _sim_wr(a, b)

# ===== Settings =====
# Default CSV path: ../final.csv from this file (i.e., smartmirror/final.csv)
DEFAULT_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "final.csv"))
NAME_COL = "name"
USE_GPU = False  # set True if your env supports it

# Normalization helpers
_keep = re.compile(r"[^가-힣A-Za-z0-9 ]+")
_num_pat = re.compile(r"\\d{3,}")       # 3+ consecutive digits (e.g., 998)
_tok_pat = re.compile(r"[A-Za-z]{3,}")  # 3+ alphabetic token (e.g., ALDER)

def normalize_text(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = _keep.sub(" ", s)
    s = " ".join(s.split())
    return s

def extract_signals(s):
    """Extract numeric and alphabetic tokens from the *raw* string."""
    if not s:
        return set(), set()
    s_norm = unicodedata.normalize("NFKC", s)
    nums = set(_num_pat.findall(s_norm))
    toks = set(t.lower() for t in _tok_pat.findall(s_norm))
    return nums, toks

def score_pair(q, p):
    """Base similarity (WRatio vs token_set), plus a small partial bonus."""
    base = max(_sim_wr(q, p), _sim_token(q, p))
    partial = _sim_partial(q, p)
    bonus = 5 if partial >= 70 else 0
    return base, bonus

def decide_match(base_score, num_matches, token_hits):
    """
    Final decision rule:
    - base_score >= 75 → accept
    - base_score >= 55 and num_matches >= 1 → accept
    - base_score >= 50 and num_matches >= 1 and token_hits >= 1 → accept
    """
    if base_score >= 75:
        return True
    if base_score >= 55 and num_matches >= 1:
        return True
    if base_score >= 50 and num_matches >= 1 and token_hits >= 1:
        return True
    return False

def _read_csv_any(path):
    """Try common encodings: utf-8, utf-8-sig, cp949, euc-kr"""
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr"):
        try:
            with open(path, "r", encoding=enc) as f:
                rdr = csv.DictReader(f)
                data = [row for row in rdr]
                return data
        except Exception:
            continue
    raise RuntimeError("CSV를 읽지 못했습니다: {}".format(path))

def load_products(csv_path, name_col=NAME_COL):
    rows = _read_csv_any(csv_path)
    products = []
    for row in rows:
        nm = row.get(name_col, "") or ""
        products.append({
            "name": nm,
            "name_norm": normalize_text(nm),
            "row": row
        })
    return products

def best_match_robust(texts, products, top_k=3):
    """
    texts: list[str] from OCR (raw)
    products: [{'name':..., 'name_norm':..., 'row':...}]
    returns: (best_product_dict, total_score, top_candidates, ok_flag, detail_dict)
    """
    joined = " ".join(t for t in texts if t)
    ocr_nums, ocr_toks = extract_signals(joined)
    candidates = [joined] + texts

    best, best_score, best_detail = None, -1, {}
    for cand in candidates:
        q_raw = cand or ""
        q = normalize_text(q_raw)
        if not q:
            continue

        for p in products:
            p_name = p["name_norm"]
            base, bns = score_pair(q, p_name)

            # numeric/token bonuses
            nums = sum(1 for n in ocr_nums if n in p_name)
            num_bonus = min(40, nums * 20)

            token_hits = sum(1 for t in ocr_toks if len(t) >= 3 and t in p_name)
            tok_bonus = min(15, token_hits * 5)

            total = base + bns + num_bonus + tok_bonus
            if total > best_score:
                best_score = total
                best = p
                best_detail = {
                    "base": base, "partial_bonus": bns,
                    "num_matches": nums, "num_bonus": num_bonus,
                    "token_hits": token_hits, "tok_bonus": tok_bonus,
                    "q_raw": q_raw
                }

    # top list (scored using joined query only)
    scored = []
    q_join = normalize_text(joined)
    for p in products:
        base, bns = score_pair(q_join, p["name_norm"])
        nums = sum(1 for n in ocr_nums if n in p["name_norm"])
        num_bonus = min(40, nums * 20)
        token_hits = sum(1 for t in ocr_toks if len(t) >= 3 and t in p["name_norm"])
        tok_bonus = min(15, token_hits * 5)
        total = base + bns + num_bonus + tok_bonus
        scored.append((total, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    ok = decide_match(
        base_score=best_detail.get("base", 0),
        num_matches=best_detail.get("num_matches", 0),
        token_hits=best_detail.get("token_hits", 0)
    )
    return (best, best_score, top, ok, best_detail)

def run_ocr(frame, csv_path=None, name_col=NAME_COL):
    """
    Public entrypoint:
    - frame: BGR numpy array (OpenCV frame)
    - csv_path: optional path to final.csv (defaults to smartmirror/final.csv)
    Returns a dict:
      {
        "ok": bool,            # decision rule passed
        "texts": list[str],    # OCR raw texts
        "score": int,          # total score of best candidate
        "detail": dict,        # debug detail
        "best": dict or None,  # row dict of top-1 product (always returned if exists)
        "top": list[dict]      # row dicts for top-K candidates (joined-query scored)
      }
    """
    if csv_path is None:
        csv_path = DEFAULT_CSV

    products = load_products(csv_path, name_col)
    if not products:
        return {"ok": False, "reason": "no_products", "texts": [], "best": None, "top": []}

    reader = easyocr.Reader(['ko', 'en'], gpu=USE_GPU)

    # Use the raw frame (no heavy pre-processing; EasyOCR does its own)
    results = reader.readtext(frame)
    if not results:
        return {"ok": False, "reason": "no_text", "texts": [], "best": None, "top": []}

    ocr_texts = [t for _, t, _ in results]

    best, score, top, ok, detail = best_match_robust(ocr_texts, products, top_k=3)

    if best:
        row = best["row"]
        return {
            "ok": ok,
            "texts": ocr_texts,
            "score": score,
            "detail": detail,
            "best": row,
            "top": [p["row"] for (sc, p) in top]
        }
    else:
        return {"ok": False, "reason": "no_candidate", "texts": ocr_texts, "best": None, "top": []}
