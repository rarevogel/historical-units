#!/usr/bin/env python3
"""
Builds the historical units atlas:

  build/data.json              the units, worked out from the files in data/ (tools/build_data.py)
  index.html                   the web page: one self-contained file, fonts from Google Fonts
  android/assets/index.html    the same page for the Android app, with the fonts bundled (works offline)
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOOGLE = re.compile(r'<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="stylesheet" href="https://fonts.googleapis.com/[^"]+">')


def main():
    subprocess.run([sys.executable, str(HERE / "tools" / "build_data.py")], check=True)
    t = (HERE / "src" / "template.html").read_text(encoding="utf-8")
    scenes = (HERE / "src" / "scenes.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    data = (HERE / "build" / "data.json").read_text(encoding="utf-8").replace("<", "\\u003c")
    html = t.replace("__SCENES__", scenes).replace("__DATA__", data)
    assert GOOGLE.search(html), "font link not found in template"
    (HERE / "index.html").write_text(html, encoding="utf-8")
    app = GOOGLE.sub('<link rel="stylesheet" href="fonts/fonts.css">', html).replace('<html lang="en">', '<html lang="en" data-app="android">')
    (HERE / "android" / "assets" / "index.html").write_text(app, encoding="utf-8")
    print(f"index.html {len(html) // 1024} KB, android/assets/index.html {len(app) // 1024} KB")


if __name__ == "__main__":
    main()
