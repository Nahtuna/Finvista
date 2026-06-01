# -*- coding: utf-8 -*-
"""
🎥 YouTube-to-Markdown (yt_to_md.py)
=====================================
Trích xuất thông tin chi tiết và transcript từ link YouTube, chuyển đổi thành 
file tài liệu Markdown (.md) chuẩn để lưu trữ vào Finvista hoặc nạp trực tiếp vào NotebookLM.
"""

import os
import sys
import json
import re
import argparse

# Đảm bảo in tiếng Việt không lỗi trên Console Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import yt_dlp
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("⚠️ Thiếu thư viện cần thiết! Đang cài đặt tự động...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp", "youtube_transcript_api"], check=True)
    import yt_dlp
    from youtube_transcript_api import YouTubeTranscriptApi

def get_youtube_video_id(url: str) -> str:
    """Trích xuất Video ID từ YouTube URL."""
    patterns = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\s]+)",
        r"(?:https?://)?(?:www\.)?youtu\.be/([^\?\s]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([^&\s]+)",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([^&\s]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def fetch_metadata(url: str) -> dict:
    """Tải metadata của video bằng yt-dlp."""
    print("📡 Đang tải thông tin video từ YouTube...")
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'description': info.get('description', ''),
            'channel': info.get('uploader', 'Unknown Channel'),
            'channel_url': info.get('uploader_url', ''),
            'view_count': info.get('view_count', 0),
            'duration': info.get('duration', 0),
            'upload_date': info.get('upload_date', ''),
        }

def fetch_transcript(video_id: str) -> str:
    """Tải transcript của video (ưu tiên tiếng Việt -> tiếng Anh)."""
    # Bước 0: Quét cục bộ xem video đã được OMNI-LEARN crawl trước đó chưa
    local_dirs = [
        "data/raw_youtube",
        "../Omni_Learn/data/raw_youtube",
        "c:/Users/samvo/Downloads/Omni_Learn/data/raw_youtube"
    ]
    for ldir in local_dirs:
        if os.path.exists(ldir):
            for file_name in os.listdir(ldir):
                if file_name.startswith(video_id) and file_name.endswith(".json"):
                    file_path = os.path.join(ldir, file_name)
                    print(f"📦 Tìm thấy bản dịch cục bộ tại: {file_name}")
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            t_text = data.get("transcript", "").strip()
                            if t_text and t_text != "[Transcript unavailable]" and t_text != "[Transcript unavailable].":
                                # Tách thành các đoạn văn ngắn dễ đọc
                                sentences = re.split(r'(?<=[.!?])\s+', t_text)
                                paragraphs = []
                                current = []
                                count = 0
                                for s in sentences:
                                    current.append(s)
                                    count += len(s)
                                    if count > 400:
                                        paragraphs.append(" ".join(current))
                                        current = []
                                        count = 0
                                if current:
                                    paragraphs.append(" ".join(current))
                                return "\n\n".join(paragraphs), "cục bộ (cached)"
                    except Exception as e:
                        print(f"⚠️ Không thể đọc file cache: {e}")

    print("📝 Đang tải bản dịch/transcript trực tuyến từ YouTube...")
    api = YouTubeTranscriptApi()
    
    # Danh sách thứ tự ưu tiên ngôn ngữ
    lang_priorities = [['vi'], ['en'], ['en-US']]
    
    for lang in lang_priorities:
        try:
            transcript_list = api.fetch(video_id, languages=lang)
            # Gom các đoạn thoại lại thành các đoạn văn có tính đọc hiểu cao
            paragraphs = []
            current_paragraph = []
            char_count = 0
            
            for t in transcript_list:
                text = t['text'].strip()
                current_paragraph.append(text)
                char_count += len(text)
                
                # Cứ khoảng 300 ký tự hoặc gặp dấu ngắt câu thì tạo đoạn văn mới để dễ đọc
                if char_count > 300 or text.endswith(('.', '!', '?')):
                    paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = []
                    char_count = 0
                    
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                
            return "\n\n".join(paragraphs), lang[0]
        except Exception:
            continue
            
    # Thử lấy transcript tự động nếu không có transcript thủ công
    try:
        transcript_list = api.get_transcript(video_id)
        text = " ".join([t['text'] for t in transcript_list])
        return text, 'auto'
    except Exception:
        return "[Bản dịch/Transcript chưa được bật hoặc không thể tải tự động cho video này]", 'none'

def clean_filename(title: str) -> str:
    """Tạo tên file an toàn từ tiêu đề video."""
    # Bỏ dấu tiếng Việt đơn giản và ký tự đặc biệt
    title = title.lower()
    title = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', title)
    title = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', title)
    title = re.sub(r'[ìíịỉĩ]', 'i', title)
    title = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', title)
    title = re.sub(r'[ùúụủũưừứựửữ]', 'u', title)
    title = re.sub(r'[ỳýỵỷỹ]', 'y', title)
    title = re.sub(r'[đ]', 'd', title)
    # Loại bỏ ký tự đặc biệt
    title = re.sub(r'[^a-z0-9\s_-]', '', title)
    # Thay khoảng trắng thành dấu gạch dưới
    title = re.sub(r'[\s_-]+', '_', title)
    return title.strip('_')[:60]

def convert_duration(seconds: int) -> str:
    """Đổi giây sang định dạng MM:SS hoặc HH:MM:SS."""
    if not seconds:
        return "N/A"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def extract_links(text: str) -> list:
    """Trích xuất các link hữu ích từ phần mô tả."""
    github_pattern = r"https?://github\.com/[\w\-]+/[\w\-]+"
    colab_pattern = r"https?://colab\.research\.google\.com/[^\s]+"
    web_pattern = r"https?://(?:www\.)?[\w\-]+\.[\w\.\-/]+(?:\?[\w\-=&]+)?"
    
    githubs = list(set(re.findall(github_pattern, text)))
    colabs = list(set(re.findall(colab_pattern, text)))
    
    # Lấy các link khác loại trừ github/colab/youtube
    all_links = re.findall(web_pattern, text)
    others = []
    for l in all_links:
        if 'github.com' not in l and 'colab.research' not in l and 'youtube.com' not in l and 'youtu.be' not in l:
            others.append(l)
    return list(set(others)), githubs, colabs

def parse_chapters(description: str) -> list:
    """Trích xuất danh sách chương dựa trên mốc thời gian."""
    chapters = []
    chapter_matches = re.findall(r"(\d{1,2}:\d{2}(?::\d{2})?)\s*[-:]?\s*(.*)", description)
    for match in chapter_matches:
        chapters.append({"time": match[0], "title": match[1].strip()})
    return chapters

def save_to_markdown(meta: dict, transcript: str, lang: str, output_dir: str) -> str:
    """Tạo và lưu trữ file Markdown định dạng chuẩn Premium."""
    os.makedirs(output_dir, exist_ok=True)
    
    safe_title = clean_filename(meta['title'])
    file_name = f"yt_{meta['id']}_{safe_title}.md"
    file_path = os.path.join(output_dir, file_name)
    
    other_links, githubs, colabs = extract_links(meta['description'])
    chapters = parse_chapters(meta['description'])
    
    # Định dạng ngày
    date_str = meta['upload_date']
    if len(date_str) == 8:
        date_str = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
    md = []
    md.append(f"# 🎥 {meta['title']}")
    md.append(f"\n> **Nguồn tri thức tự động từ YouTube** | Kênh: [{meta['channel']}]({meta['channel_url']})")
    md.append("\n## 📊 1. THÔNG TIN THAM CHIẾU")
    md.append("| Thuộc tính | Giá trị |")
    md.append("|---|---|")
    md.append(f"| **Đường dẫn (URL)** | [Xem trên YouTube](https://www.youtube.com/watch?v={meta['id']}) |")
    md.append(f"| **Video ID** | `{meta['id']}` |")
    md.append(f"| **Thời lượng** | `{convert_duration(meta['duration'])}` |")
    md.append(f"| **Ngày tải lên** | `{date_str}` |")
    md.append(f"| **Ngôn ngữ Transcript** | `{lang.upper()}` |")
    
    # Chương học (Chapters) nếu có
    if chapters:
        md.append("\n## 📖 2. DANH SÁCH CHƯƠNG HỌC")
        for chap in chapters:
            md.append(f"- **`{chap['time']}`** - {chap['title']}")
            
    # Tài nguyên đính kèm
    if githubs or colabs or other_links:
        md.append("\n## 🛠️ 3. TÀI NGUYÊN & MÃ NGUỒN LIÊN KẾT")
        if githubs:
            md.append("\n### 💻 Kho mã nguồn GitHub:")
            for g in githubs:
                md.append(f"- [{g.split('/')[-1]}]({g})")
        if colabs:
            md.append("\n### 🪐 Google Colab Jupyter Notebooks:")
            for c in colabs:
                md.append(f"- [Mở Google Colab Notebook]({c})")
        if other_links:
            md.append("\n### 🔗 Tài liệu và liên kết khác:")
            for o in other_links:
                md.append(f"- [{o}]({o})")
                
    # Bản mô tả gốc
    md.append("\n## 📝 4. BẢN MÔ TẢ GỐC (DESCRIPTION)")
    md.append("```text")
    md.append(meta['description'].strip())
    md.append("```")
    
    # Bản dịch / Transcript
    md.append("\n## 🔊 5. NỘI DUNG NÓI CHI TIẾT (TRANSCRIPT)")
    md.append("> [!TIP]")
    md.append("> Bản dịch này được tải tự động và tối ưu hóa thành các đoạn văn để dễ đọc. Bạn có thể sao chép phần này dán vào Google Translate hoặc nạp thẳng file này vào NotebookLM để học tập tương tác.")
    md.append("\n" + transcript)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))
        
    return file_path

def main():
    parser = argparse.ArgumentParser(description="Chuyển đổi YouTube Video thành tài liệu Markdown (.md)")
    parser.add_argument("url", help="Đường dẫn YouTube cần xử lý")
    parser.add_argument("--output", "-o", default="docs/knowledge_base", help="Thư mục lưu trữ file .md đầu ra")
    
    args = parser.parse_args()
    
    video_id = get_youtube_video_id(args.url)
    if not video_id:
        print("❌ Lỗi: Đường dẫn YouTube không hợp lệ!")
        sys.exit(1)
        
    print(f"🎯 Đang xử lý Video ID: {video_id}")
    
    try:
        # 1. Tải metadata
        meta = fetch_metadata(args.url)
        
        # 2. Tải transcript
        transcript, lang = fetch_transcript(video_id)
        
        # 3. Lưu thành Markdown
        file_path = save_to_markdown(meta, transcript, lang, args.output)
        
        print(f"\n🎉 THÀNH CÔNG! Đã lưu tài liệu tri thức tại:")
        print(f"👉 {os.path.abspath(file_path)}")
        print(f"💡 Bạn có thể copy file .md này hoặc nạp trực tiếp vào NotebookLM!")
    except Exception as e:
        print(f"❌ Lỗi trong quá trình xử lý: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
