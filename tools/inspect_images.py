import os
import sys
from PIL import Image

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

img_dir = os.path.join("docs", "img")
if not os.path.exists(img_dir):
    print("img directory does not exist")
    sys.exit(1)

files = sorted(os.listdir(img_dir))
print(f"Total images found: {len(files)}")
for f in files:
    path = os.path.join(img_dir, f)
    if os.path.isfile(path) and f.endswith(".png"):
        try:
            with Image.open(path) as img:
                print(f"📷 {f:<20} | size: {img.size[0]}x{img.size[1]} | format: {img.format} | mode: {img.mode} | bytes: {os.path.getsize(path)}")
        except Exception as e:
            print(f"Failed to open {f}: {e}")
