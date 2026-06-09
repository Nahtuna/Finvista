import sys, io, requests, re, os, time, threading
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36")
}

# ═══════════════════════════════════════════════════════════
#  NORMALIZE DATE
# ═══════════════════════════════════════════════════════════
def normalize_date(raw: str) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    now = datetime.now()

    try:
        clean_raw = raw.replace("Z", "+00:00").replace(" (GMT+7)", "").replace(" GMT+7", "")
        dt = datetime.fromisoformat(clean_raw)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        pass

    raw_lower = raw.lower()
    rel = re.search(r"(\d+)\s*(phút|giờ|ngày|tuần|tháng|năm)", raw_lower)
    if rel:
        n, u = int(rel.group(1)), rel.group(2)
        delta = {
            "phút": timedelta(minutes=n), 
            "giờ": timedelta(hours=n),
            "ngày": timedelta(days=n), 
            "tuần": timedelta(weeks=n),
            "tháng": timedelta(days=n*30),
            "năm": timedelta(days=n*365)
        }.get(u, timedelta())
        return (now - delta).strftime("%Y-%m-%d %H:%M")

    if "hôm qua" in raw_lower or "hm qua" in raw_lower:
        t = re.search(r"(\d{1,2}:\d{2})", raw)
        return (now - timedelta(days=1)).strftime("%Y-%m-%d") + " " + (t.group(1) if t else "12:00")

    if "hôm nay" in raw_lower or "hm nay" in raw_lower:
        t = re.search(r"(\d{1,2}:\d{2})", raw)
        return now.strftime("%Y-%m-%d") + " " + (t.group(1) if t else now.strftime("%H:%M"))

    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    if m:
        d, mo, y = m.groups()
        t = re.search(r"(\d{1,2}:\d{2})", raw)
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)} {(t.group(1) if t else '00:00')}"

    return None

# ═══════════════════════════════════════════════════════════
#  THREAD-SAFE UTILITIES
# ═══════════════════════════════════════════════════════════
file_lock = threading.Lock()
seen_lock = threading.Lock()

def _save(news_list, path):
    if not news_list:
        return
    re_clean = re.compile(r'[\u200b-\u200f\ufeff\u202a-\u202e]')
    for item in news_list:
        for key in ["Title", "Summary"]:
            if key in item and item[key]:
                text = str(item[key])
                text = re_clean.sub('', text)
                item[key] = text.replace("\n", " ").replace("\r", " ").strip()
                
    with file_lock:
        write_header = not os.path.exists(path) or os.path.getsize(path) == 0
        import csv
        pd.DataFrame(news_list).to_csv(
            path, mode='a', index=False, header=write_header, 
            encoding="utf-8-sig", quoting=csv.QUOTE_NONNUMERIC)

def _add_seen(seen: set, link: str) -> bool:
    with seen_lock:
        if link in seen:
            return False
        seen.add(link)
        return True

class BaseScraper:
    def _get_details(self, url, date_selectors, summary_selectors, site_name):
        for attempt in range(3):
            try:
                r = requests.get(url, headers=HEADERS, timeout=30)
                if r.status_code == 403:
                    time.sleep(10 * (attempt + 1))
                    continue
                soup = BeautifulSoup(r.content, "html.parser")
                norm_date = None
                meta = soup.select_one('meta[property="article:published_time"]')
                if meta and meta.get("content"):
                    norm_date = normalize_date(meta["content"])
                if not norm_date:
                    for sel in date_selectors:
                        el = soup.select_one(sel)
                        if el:
                            norm_date = normalize_date(el.get_text(strip=True))
                            if norm_date: break
                summary = ""
                for sel in summary_selectors:
                    s_el = soup.select_one(sel)
                    if s_el:
                        summary = s_el.get_text(strip=True)
                        if summary: break
                return norm_date, summary
            except Exception:
                if attempt < 2: time.sleep(3 * (attempt + 1))
        return None, ""

class CafeFScraper(BaseScraper):
    def __init__(self):
        self.base_url = "https://cafef.vn"
        self.categories = {
            "Chứng khoán": "18831",
            "Doanh nghiệp": "18836",
            "Vĩ mô": "18833",
            "Tài chính ngân hàng": "18834",
        }

    def scrape_category(self, cat_name, cat_id, from_date, to_date, seen, output):
        page = 1
        while page <= 10:
            url = f"{self.base_url}/timelinelist/{cat_id}/{page}.chn"
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code != 200: break
                soup = BeautifulSoup(r.content, "html.parser")
                items = soup.select(".tlitem")
                if not items: break
                news = []
                for item in items:
                    a_title = item.select_one("h3 a, .tlitem-title, a[title]")
                    if not a_title: continue
                    href = a_title["href"]
                    if not href.endswith(".chn"): continue
                    link = self.base_url + href if href.startswith("/") else href
                    if not _add_seen(seen, link): continue
                    time_el = item.select_one(".time-ago")
                    raw_date = time_el.get("title") if time_el else ""
                    norm = normalize_date(raw_date)
                    sapo_el = item.select_one(".sapo")
                    summary = sapo_el.get_text(strip=True) if sapo_el else ""
                    if not norm: continue
                    if to_date and norm > to_date: continue
                    if from_date and norm < from_date:
                        news = []; page = 99999; break
                    news.append({"Date": norm, "Title": a_title.get_text(strip=True), "Source": "CafeF", "Link": link, "Summary": summary, "Category": cat_name})
                if news: _save(news, output)
                page += 1
                time.sleep(0.1)
            except Exception: break

def run_news_scraping(days_lookback: int = 3, output_path: str = "data/raw/news_data.csv"):
    """Entry point for news scraping within Finvista."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    from_date = (datetime.now() - timedelta(days=days_lookback)).strftime("%Y-%m-%d 00:00")
    to_date = datetime.now().strftime("%Y-%m-%d 23:59")
    
    print(f"📡 Scraping financial news from {from_date}...")
    scraper = CafeFScraper()
    seen = set()
    if os.path.exists(output_path):
        try:
            df = pd.read_csv(output_path)
            seen = set(df["Link"].dropna().unique())
        except: pass

    for cat_name, cat_id in scraper.categories.items():
        scraper.scrape_category(cat_name, cat_id, from_date, to_date, seen, output_path)
    
    print(f"✅ News scraping complete. Results saved to {output_path}")

if __name__ == "__main__":
    run_news_scraping()
