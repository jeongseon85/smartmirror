
import sqlite3
import os

# 샘플 데이터 (최소 시드) — 실제 운영은 별도 CSV/JSON 권장
ALL_PRODUCTS = {
    'P001': {'brand': '헤라', 'name': '블랙 쿠션 (17N1)', 'type': '쿠션', 'price': '60000', 'desc': '세미매트 피니쉬 쿠션', 'image': 'product_01.jpg'},
    'P002': {'brand': '에스티로더', 'name': '더블웨어 파운데이션 (포슬린)', 'type': '파운데이션', 'price': '82000', 'desc': '지속력 우수', 'image': 'product_02.jpg'},
    'P003': {'brand': '에스쁘아', 'name': '프로 테일러 비글로우 쿠션', 'type': '쿠션', 'price': '35000', 'desc': '건성 추천 글로우', 'image': 'product_03.jpg'},
    'P004': {'brand': '바비브라운', 'name': '인텐시브 스킨 세럼 파운데이션', 'type': '파운데이션', 'price': '95000', 'desc': '세럼 파데', 'image': 'product_04.jpg'},
    'P009': {'brand': '데이지크', 'name': '섀도우 팔레트', 'type': '아이섀도우', 'price': '34000', 'desc': '봄웜 팔레트', 'image': 'product_09.jpg'},
    'P012': {'brand': '롬앤', 'name': '쥬시 래스팅 틴트', 'type': '립틴트', 'price': '9900', 'desc': '촉촉 틴트', 'image': 'product_12.jpg'},
}

class DatabaseManager:
    def __init__(self, db_name='data/cosmetics.db'):
        self.db_name = db_name
        self._ensure_db()

    # ---------- DB 준비/초기화 ----------
    def _ensure_db(self):
        db_folder = os.path.dirname(self.db_name) or '.'
        if not os.path.exists(db_folder):
            os.makedirs(db_folder, exist_ok=True)
        if not os.path.exists(self.db_name):
            self._create_and_seed()

    def _create_and_seed(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                brand TEXT,
                price TEXT,
                image TEXT,
                description TEXT,
                type TEXT,
                category TEXT,
                skin_types TEXT,
                personal_colors TEXT
            )
        """)
        # 최소 샘플 주입 (빈 화면 방지)
        for _, p in ALL_PRODUCTS.items():
            cur.execute("""
                INSERT INTO products (name, brand, price, image, description, type, category, skin_types, personal_colors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p.get('name',''), p.get('brand',''), p.get('price',''), p.get('image',''),
                p.get('desc',''), p.get('type',''), '색조', '', ''
            ))
        conn.commit()
        conn.close()

    # ---------- 커넥션 ----------
    def _conn(self):
        c = sqlite3.connect(self.db_name)
        c.row_factory = sqlite3.Row
        return c
    
    def get_beauty_data(self, user_tone=None, user_color=None, limit=9):
        """
        메인 로직 호환용 단축 API.
        - user_color(예: 'spring','summer','autumn','winter' 또는 'warm','cool')를 우선 사용
        - DB에 해당 컬럼/데이터가 없어도 안전망으로 상위 N을 반환
        """
        # personal_colors / skin_types 컬럼이 없거나 값이 없어도 안전하게 동작하도록 설계
        try:
            # user_color(시즌/톤)가 있으면 우선 필터
            if user_color:
                rows = self.get_products_by_filter(personal_color=user_color, skin_type=None, limit=limit)
            else:
                rows = self.get_products_by_filter(personal_color=None, skin_type=None, limit=limit)
            # 최소 1개는 반환되도록 마지막 안전망
            if not rows:
                conn = self._conn()
                cur = conn.cursor()
                cur.execute("SELECT * FROM products LIMIT ?", (limit,))
                rows = [dict(r) for r in cur.fetchall()]
                conn.close()
            return rows
        except Exception:
            # 어떤 이유든 실패 시 전체 상위 N
            conn = self._conn()
            cur = conn.cursor()
            cur.execute("SELECT * FROM products LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            return rows


    # ---------- 조회 유틸 ----------
    def get_product_by_name(self, name: str, limit: int = 1):
        """제품 이름(부분일치)으로 1건(기본) 또는 N건 조회"""
        if not name: return None if limit == 1 else []
        like = f"%{name.replace(' ', '')}%"
        q = """
        SELECT * FROM products
        WHERE REPLACE(LOWER(name), ' ', '') LIKE LOWER(?)
           OR REPLACE(LOWER(brand||' '||name), ' ', '') LIKE LOWER(?)
        LIMIT ?
        """
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(q, (like, like, limit))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        if limit == 1:
            return rows[0] if rows else None
        return rows

    def get_products_by_filter(self, personal_color: str = None, skin_type: str = None, limit: int = 9):
        """personal_colors / skin_types 문자열 컬럼 부분일치 필터"""
        conn = self._conn()
        cur = conn.cursor()
        where, args = [], []
        if personal_color:
            where.append("personal_colors LIKE ?"); args.append(f"%{personal_color}%")
        if skin_type:
            where.append("skin_types LIKE ?"); args.append(f"%{skin_type}%")
        q = "SELECT * FROM products"
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " LIMIT ?"; args.append(limit)
        cur.execute(q, args)
        rows = [dict(r) for r in cur.fetchall()]
        if not rows:  # 안전망
            cur.execute("SELECT * FROM products LIMIT ?", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_all_brands(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL AND brand<>''")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows

    def get_all_product_names(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT name FROM products WHERE name IS NOT NULL AND name<>''")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows
    def recommend_by_types(self, personal_color: str, skin_type: str, number: str, k_per_section: int = 6) -> dict:
        """
        얼굴촬영 결과 기반 추천:
        - 쿠션/파운데이션: skin_types + number 근사치(±1)로 필터
        - 립/아이        : personal_color 로 필터
        반환: {"쿠션":[...], "파운데이션":[...], "립":[...], "아이":[...]}
        """
        def _num_range(num_str):
            try:
                x = float(num_str)
                return (x - 1.0, x + 1.0)
            except Exception:
                return (None, None)

        low, high = _num_range(number)
        conn = self._conn(); cur = conn.cursor()

        def _pick(sql_where, args, limit=k_per_section):
            q = "SELECT * FROM products WHERE " + sql_where + " LIMIT ?"
            cur.execute(q, [*args, limit])
            rows = [dict(r) for r in cur.fetchall()]
            return rows

        # 쿠션
        cushion = _pick(
            sql_where="(type LIKE '%쿠션%') AND (skin_types LIKE ? OR skin_types IS NULL OR skin_types='')" + \
                      ("" if low is None else " AND (number IS NULL OR CAST(number AS REAL) BETWEEN ? AND ?)"),
            args=([f"%{skin_type}%"] + ([] if low is None else [low, high]))
        )
        if not cushion:  # 타입만으로 대체
            cushion = _pick("type LIKE '%쿠션%'", args=[])

        # 파운데이션 (파데 포함)
        foundation = _pick(
            sql_where="((type LIKE '%파운데%' OR type LIKE '%파데%')) AND (skin_types LIKE ? OR skin_types IS NULL OR skin_types='')" + \
                      ("" if low is None else " AND (number IS NULL OR CAST(number AS REAL) BETWEEN ? AND ?)"),
            args=([f"%{skin_type}%"] + ([] if low is None else [low, high]))
        )
        if not foundation:
            foundation = _pick("type LIKE '%파운데%' OR type LIKE '%파데%'", args=[])

        # 립 계열 (립, 틴트, 립스틱, 글로스 등)
        lip = _pick(
            sql_where="(type LIKE '%립%' OR type LIKE '%틴트%' OR type LIKE '%립스틱%' OR type LIKE '%글로스%' OR type LIKE '%플럼퍼%') AND (personal_colors LIKE ? OR personal_colors IS NULL OR personal_colors='')",
            args=[f"%{personal_color}%"] if personal_color else [""]
        )
        if not lip:
            lip = _pick("(type LIKE '%립%' OR type LIKE '%틴트%' OR type LIKE '%립스틱%' OR type LIKE '%글로스%' OR type LIKE '%플럼퍼%')", args=[])

        # 아이 계열 (아이섀도우, 마스카라, 아이라이너, 브로우 등)
        eye = _pick(
            sql_where="(type LIKE '%아이%' OR type LIKE '%섀도우%' OR type LIKE '%마스카라%' OR type LIKE '%아이라이너%' OR type LIKE '%브로우%') AND (personal_colors LIKE ? OR personal_colors IS NULL OR personal_colors='')",
            args=[f"%{personal_color}%"] if personal_color else [""]
        )
        if not eye:
            eye = _pick("(type LIKE '%아이%' OR type LIKE '%섀도우%' OR type LIKE '%마스카라%' OR type LIKE '%아이라이너%' OR type LIKE '%브로우%')", args=[])

        conn.close()

        # 표준 카드 포맷 정리
        def _cards(rows):
            out = []
            for p in rows:
                price_raw = p.get("price")
                try:
                    price_val = int(price_raw) if price_raw is not None and str(price_raw).isdigit() else None
                except Exception:
                    price_val = None
                out.append({
                    "name": p.get("name",""),
                    "price": price_val,
                    "image_path": p.get("image") or p.get("image_path") or "",
                    "description": p.get("description",""),
                    "type": p.get("type",""),
                    "category": p.get("category",""),
                    "skin_types": p.get("skin_types",""),
                    "personal_colors": p.get("personal_colors",""),
                    "number": p.get("number"),
                })
            return out

        return {
            "쿠션": _cards(cushion),
            "파운데이션": _cards(foundation),
            "립": _cards(lip),
            "아이": _cards(eye),
        }

