import pypdf
import os
import sys

# Force UTF-8 encoding for stdout on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

pdf_path = os.path.join("docs", "finvista-nhom-1-bao-cao.pdf")
out_path = os.path.join("data", "pdf_content.txt")

reader = pypdf.PdfReader(pdf_path)

with open(out_path, "w", encoding="utf-8") as f:
    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        f.write(f"\n--- PAGE {idx+1} ---\n")
        f.write(text)

print(f"Extraction completed successfully! Pages: {len(reader.pages)}")
