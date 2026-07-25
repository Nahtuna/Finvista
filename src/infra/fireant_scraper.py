# -*- coding: utf-8 -*-
"""
🔥 FINVISTA: FIREANT ARTICLE SCRAPER
=====================================
Cào bài viết phân tích từ FireAnt (https://fireant.vn/analysis)
và lưu vào DB để dùng cho RAG / AI Chat.

Cách hoạt động:
  1. Dùng Bearer token từ session trình duyệt của bạn (lấy 1 lần từ DevTools)
  2. Gọi API restv2.fireant.vn để lấy danh sách bài viết (pagination)
  3. Parse nội dung từng bài → lưu vào bảng `fireant_articles`
  4. (Tùy chọn) Tạo embeddings vector → FAISS index cho RAG

Cách lấy Bearer token:
  1. Mở https://fireant.vn, đăng nhập vào tài khoản
  2. Nhấn F12 → Tab Network → Filter "XHR"
  3. Click vào bất kỳ request nào tới restv2.fireant.vn
  4. Xem header "Authorization: Bearer <TOKEN>"
  5. Copy token và đặt vào biến môi trường FIREANT_TOKEN
     hoặc truyền trực tiếp khi gọi hàm.

Endpoint chính:
  GET https://restv2.fireant.vn/posts?type=1&offset={offset}&limit={limit}
  → type=0: social posts, type=1: bài viết phân tích (analysis articles)

Author: samvo
"""

from __future__ import annotations

import os
import json
import time
import logging
import hashlib
import requests
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.utils import logger

# ─── Config ───────────────────────────────────────────────────────────────────
FIREANT_BASE_URL = "https://restv2.fireant.vn"
FIREANT_TOKEN_ENV = "FIREANT_TOKEN"

DEFAULT_LIMIT = 20      # Số bài mỗi request
MAX_PAGES = 50          # Tối đa bao nhiêu trang (50 * 20 = 1000 bài)
REQUEST_DELAY = 0.8     # Delay giữa các request (giây) — tránh bị rate-limit
CACHE_DIR = os.path.join("data", "processed", "fireant")

# ─── SQLAlchemy model ─────────────────────────────────────────────────────────

def _get_db_session():
    from src.core.database import SessionLocal
    return SessionLocal()


def _ensure_table():
    """Tạo bảng fireant_articles nếu chưa có — hoạt động trên cả SQLite và PostgreSQL."""
    from src.core.database import engine
    from sqlalchemy import (
        Column, Integer, String, Text, DateTime,
        inspect, Table, MetaData
    )

    inspector = inspect(engine)
    if "fireant_articles" not in inspector.get_table_names():
        meta = MetaData()
        Table(
            "fireant_articles", meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("post_id", String(64), unique=True, index=True, nullable=False),
            Column("post_type", Integer, default=1),
            Column("title", String(512)),
            Column("content", Text),
            Column("author_name", String(256)),
            Column("author_id", String(64)),
            Column("symbols", Text),                  # JSON list: '["VNM","HPG"]'
            Column("published_at", String(64)),        # ISO datetime string
            Column("url", String(512)),
            Column("source", String(64), default="FireAnt"),
            Column("sentiment", String(16)),           # POSITIVE/NEGATIVE/NEUTRAL
            Column("embedding_done", Integer, default=0),
            Column("raw_json", Text),
            Column("scraped_at", DateTime),
        )
        meta.create_all(engine)
        logger.info("✅ [FireAnt] Bảng 'fireant_articles' đã được tạo.")
    else:
        logger.info("ℹ️ [FireAnt] Bảng 'fireant_articles' đã tồn tại.")


# ─── Core scraper ─────────────────────────────────────────────────────────────

class FireAntScraper:
    """
    Scraper bài viết phân tích từ FireAnt.

    Sử dụng:
        scraper = FireAntScraper(token="Bearer <TOKEN>")
        results = scraper.scrape(symbol="VNM", max_pages=5)
        # Hoặc lấy tất cả bài analysis không lọc symbol:
        results = scraper.scrape(max_pages=10)
    """

    def __init__(self, token: Optional[str] = None):
        """
        Args:
            token: Bearer token từ FireAnt session.
                   Có thể truyền trực tiếp hoặc để None để đọc từ env
                   FIREANT_TOKEN.
        """
        raw_token = token or os.environ.get(FIREANT_TOKEN_ENV, "")
        if raw_token and not raw_token.startswith("Bearer "):
            raw_token = f"Bearer {raw_token}"
        self.token = raw_token

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            "Origin": "https://fireant.vn",
            "Referer": "https://fireant.vn/",
        })
        if self.token:
            self.session.headers["Authorization"] = self.token

        os.makedirs(CACHE_DIR, exist_ok=True)
        _ensure_table()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict) -> Optional[Any]:
        """HTTP GET với retry + logging."""
        url = f"{FIREANT_BASE_URL}{path}"
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code == 401:
                    logger.error(
                        "❌ [FireAnt] 401 Unauthorized — Token thiếu hoặc hết hạn. "
                        "Vui lòng lấy token mới từ DevTools và đặt FIREANT_TOKEN."
                    )
                    return None
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    logger.warning(f"⚠️ [FireAnt] Rate limited, chờ {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                logger.warning(f"⚠️ [FireAnt] Attempt {attempt+1}/3 lỗi: {e}")
                time.sleep(2 ** attempt)
        return None

    def _upsert_article(self, db, post: dict) -> bool:
        """Lưu một bài viết vào DB, bỏ qua nếu đã tồn tại. Trả về True nếu mới."""
        from sqlalchemy import text

        post_id = str(post.get("id", ""))
        if not post_id:
            return False

        # Check tồn tại
        exists = db.execute(
            text("SELECT 1 FROM fireant_articles WHERE post_id = :pid"),
            {"pid": post_id}
        ).fetchone()
        if exists:
            return False

        # Extract fields
        author = post.get("tagUser") or post.get("user") or {}
        symbols_raw = post.get("taggedSymbols") or post.get("symbols") or []
        symbols_list = [s.get("symbol", s) if isinstance(s, dict) else s
                        for s in symbols_raw]

        title = post.get("title") or _extract_title(post.get("content", ""))
        content = post.get("content", "")
        published_at = (
            post.get("date")
            or post.get("publishedAt")
            or post.get("createdAt")
            or ""
        )
        url = (
            post.get("url")
            or f"https://fireant.vn/post/{post_id}"
        )

        db.execute(
            text("""
                INSERT INTO fireant_articles
                    (post_id, post_type, title, content, author_name, author_id,
                     symbols, published_at, url, source, embedding_done, raw_json, scraped_at)
                VALUES
                    (:post_id, :post_type, :title, :content, :author_name, :author_id,
                     :symbols, :published_at, :url, :source, 0, :raw_json, :scraped_at)
            """),
            {
                "post_id": post_id,
                "post_type": post.get("type", 1),
                "title": title,
                "content": content,
                "author_name": (author.get("displayName") or author.get("name") or ""),
                "author_id": str(author.get("id", "")),
                "symbols": json.dumps(symbols_list, ensure_ascii=False),
                "published_at": str(published_at),
                "url": url,
                "source": "FireAnt",
                "raw_json": json.dumps(post, ensure_ascii=False),
                "scraped_at": datetime.now(timezone.utc),
            }
        )
        return True

    # ── Public API ─────────────────────────────────────────────────────────────

    def scrape(
        self,
        symbol: Optional[str] = None,
        post_type: int = 1,
        max_pages: int = 10,
        offset_start: int = 0,
    ) -> Dict[str, Any]:
        """
        Cào bài viết từ FireAnt và lưu vào DB.

        Args:
            symbol:     Lọc theo mã CK (ví dụ "VNM"). None = lấy tất cả.
            post_type:  1 = analysis articles, 0 = social posts.
            max_pages:  Số trang tối đa (mỗi trang 20 bài).
            offset_start: Offset bắt đầu (dùng để tiếp tục từ chỗ dừng).

        Returns:
            {"status": "ok", "new": X, "total_fetched": Y, "skipped": Z}
        """
        if not self.token:
            return {
                "status": "error",
                "error": (
                    "Chưa có FireAnt token. "
                    "Đặt biến môi trường FIREANT_TOKEN hoặc truyền token khi khởi tạo. "
                    "Xem hướng dẫn lấy token trong docstring của module này."
                )
            }

        db = _get_db_session()
        total_new = 0
        total_fetched = 0
        total_skipped = 0

        try:
            for page in range(max_pages):
                offset = offset_start + page * DEFAULT_LIMIT

                # Chọn endpoint: có symbol hay không
                if symbol:
                    path = f"/symbols/{symbol.upper()}/posts"
                    params = {
                        "type": post_type,
                        "offset": offset,
                        "limit": DEFAULT_LIMIT,
                    }
                else:
                    path = "/posts"
                    params = {
                        "type": post_type,
                        "offset": offset,
                        "limit": DEFAULT_LIMIT,
                    }

                logger.info(
                    f"📥 [FireAnt] Page {page+1}/{max_pages} | "
                    f"offset={offset} | symbol={symbol or 'ALL'}"
                )
                data = self._get(path, params)

                if data is None:
                    logger.warning(f"⚠️ [FireAnt] Không có data tại page {page+1}, dừng.")
                    break

                # API có thể trả về list hoặc dict với key "data"
                posts = data if isinstance(data, list) else data.get("data", data.get("posts", []))

                if not posts:
                    logger.info(f"✅ [FireAnt] Hết bài viết tại page {page+1}.")
                    break

                for post in posts:
                    total_fetched += 1
                    is_new = self._upsert_article(db, post)
                    if is_new:
                        total_new += 1
                    else:
                        total_skipped += 1

                db.commit()
                logger.info(
                    f"   ✅ Page {page+1}: +{sum(1 for p in posts if True)} bài | "
                    f"Mới: {total_new} | Trùng: {total_skipped}"
                )

                if len(posts) < DEFAULT_LIMIT:
                    logger.info("✅ [FireAnt] Đã cào hết tất cả bài viết.")
                    break

                time.sleep(REQUEST_DELAY)

        except Exception as e:
            db.rollback()
            logger.error(f"❌ [FireAnt] Lỗi khi scrape: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
        finally:
            db.close()

        logger.info(
            f"🏁 [FireAnt] Hoàn thành. "
            f"Mới: {total_new} | Trùng/đã có: {total_skipped} | "
            f"Tổng fetch: {total_fetched}"
        )
        return {
            "status": "ok",
            "new": total_new,
            "total_fetched": total_fetched,
            "skipped": total_skipped,
        }

    def get_articles_for_rag(
        self,
        symbol: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Trả về danh sách bài viết từ DB để dùng cho RAG / AI Chat.

        Args:
            symbol: Lọc theo mã CK. None = tất cả.
            limit:  Số bài tối đa.

        Returns:
            List of dicts with keys: post_id, title, content, symbols,
                                     author_name, published_at, url
        """
        from sqlalchemy import text
        db = _get_db_session()
        try:
            if symbol:
                rows = db.execute(
                    text("""
                        SELECT post_id, title, content, symbols, author_name,
                               published_at, url
                        FROM fireant_articles
                        WHERE symbols LIKE :sym
                        ORDER BY published_at DESC
                        LIMIT :lim
                    """),
                    {"sym": f'%"{symbol.upper()}"%', "lim": limit}
                ).fetchall()
            else:
                rows = db.execute(
                    text("""
                        SELECT post_id, title, content, symbols, author_name,
                               published_at, url
                        FROM fireant_articles
                        ORDER BY published_at DESC
                        LIMIT :lim
                    """),
                    {"lim": limit}
                ).fetchall()

            return [
                {
                    "post_id": r[0],
                    "title": r[1] or "",
                    "content": r[2] or "",
                    "symbols": json.loads(r[3] or "[]"),
                    "author_name": r[4] or "",
                    "published_at": r[5] or "",
                    "url": r[6] or "",
                }
                for r in rows
            ]
        finally:
            db.close()

    def build_rag_context(
        self,
        query: str,
        symbol: Optional[str] = None,
        top_k: int = 5,
    ) -> str:
        """
        Xây dựng context RAG từ bài viết FireAnt cho AI Chat.
        Dùng simple keyword matching (không cần vector DB).

        Args:
            query:   Câu hỏi của user.
            symbol:  Lọc theo mã CK.
            top_k:   Số bài liên quan trả về.

        Returns:
            String context để đưa vào system prompt của AI.
        """
        articles = self.get_articles_for_rag(symbol=symbol, limit=100)
        if not articles:
            return ""

        # Keyword matching đơn giản
        query_words = set(query.lower().split())
        scored = []
        for art in articles:
            text_blob = f"{art['title']} {art['content']}".lower()
            score = sum(1 for w in query_words if w in text_blob)
            scored.append((score, art))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_articles = [a for _, a in scored[:top_k] if _ > 0]

        if not top_articles:
            # Nếu không khớp keyword, lấy bài mới nhất
            top_articles = [a for _, a in scored[:top_k]]

        context_parts = []
        for art in top_articles:
            syms = ", ".join(art["symbols"]) if art["symbols"] else "Không rõ"
            snippet = (art["content"] or "")[:800]
            context_parts.append(
                f"**[{art['published_at'][:10] if art['published_at'] else '?'}] "
                f"{art['title'] or 'Không có tiêu đề'}**\n"
                f"Cổ phiếu: {syms} | Tác giả: {art['author_name'] or 'Ẩn danh'}\n"
                f"{snippet}\n"
                f"Nguồn: {art['url']}"
            )

        return "\n\n---\n\n".join(context_parts)

    def stats(self) -> Dict[str, Any]:
        """Thống kê số bài viết đã cào."""
        from sqlalchemy import text
        db = _get_db_session()
        try:
            total = db.execute(text("SELECT COUNT(*) FROM fireant_articles")).scalar() or 0
            latest = db.execute(
                text("SELECT published_at FROM fireant_articles ORDER BY published_at DESC LIMIT 1")
            ).scalar()
            oldest = db.execute(
                text("SELECT published_at FROM fireant_articles ORDER BY published_at ASC LIMIT 1")
            ).scalar()
            top_symbols_raw = db.execute(
                text("""
                    SELECT symbols, COUNT(*) as cnt
                    FROM fireant_articles
                    GROUP BY symbols
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
            ).fetchall()
            return {
                "total_articles": total,
                "latest": latest,
                "oldest": oldest,
                "top_symbols_sample": [r[0] for r in top_symbols_raw[:5]],
            }
        finally:
            db.close()


# ─── Utility ──────────────────────────────────────────────────────────────────

def _extract_title(content: str, max_len: int = 120) -> str:
    """Trích tiêu đề từ nội dung nếu không có title riêng."""
    if not content:
        return ""
    first_line = content.strip().split("\n")[0]
    return first_line[:max_len] if len(first_line) > 5 else content[:max_len]


# ─── CLI runner ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("🔥 FireAnt Article Scraper")
    print("=" * 50)

    token = os.environ.get(FIREANT_TOKEN_ENV, "")
    if not token:
        print(
            "⚠️  FIREANT_TOKEN chưa được đặt!\n"
            "Cách lấy token:\n"
            "  1. Mở https://fireant.vn, đăng nhập\n"
            "  2. Nhấn F12 → Tab Network → Filter XHR\n"
            "  3. Click request tới restv2.fireant.vn\n"
            "  4. Copy giá trị 'Authorization' header\n"
            "  5. Chạy: set FIREANT_TOKEN=<token_của_bạn>\n"
        )
        sys.exit(1)

    scraper = FireAntScraper(token=token)

    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    print(f"Symbol: {symbol or 'ALL'} | Max pages: {pages}")
    result = scraper.scrape(symbol=symbol, max_pages=pages)
    print(f"\n📊 Kết quả: {json.dumps(result, ensure_ascii=False, indent=2)}")

    stats = scraper.stats()
    print(f"\n📈 Thống kê DB: {json.dumps(stats, ensure_ascii=False, indent=2)}")
