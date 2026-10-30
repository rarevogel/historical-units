#!/usr/bin/env python3
"""Copies the fonts the page uses from Fontsource packages into android/assets/fonts with a fonts.css.
Usage: tools/fonts.py <folder with unpacked @fontsource packages>"""
import glob, re, shutil, sys
from pathlib import Path
SRC = Path(sys.argv[1]); OUT = Path(__file__).resolve().parent.parent / "android" / "assets" / "fonts"
WANT = {  # package: [(weight css file), ...]
    "fraunces": ["600", "800"], "ibm-plex-sans": ["400", "500", "600"], "ibm-plex-mono": ["400", "500"],
    "ibm-plex-serif": ["500", "600", "400-italic"], "noto-sans-cuneiform": ["400"], "noto-sans-old-persian": ["400"], "noto-sans-coptic": ["400"],
}
SUBSETS = r"-(latin|latin-ext|greek|greek-ext|cuneiform|old-persian|coptic)-\d+-(normal|italic)$"
OUT.mkdir(parents=True, exist_ok=True)
faces = []
for pkg, files in WANT.items():
    d = Path(glob.glob(str(SRC / f"fontsource-{pkg}-[0-9]*" / "package"))[-1])
    for w in files:
        css = (d / f"{w}.css").read_text()
        for name, body in re.findall(r"/\* ([^*]+) \*/\s*(@font-face \{.*?\})", css, re.S):
            if not re.search(SUBSETS, name.strip()):
                continue
            fn = name.strip() + ".woff2"
            shutil.copy(d / "files" / fn, OUT / fn)
            faces.append(re.sub(r"src:[^;]+;", f"src: url(./{fn}) format('woff2');", body))
    shutil.copy(d / "LICENSE", OUT / f"OFL-{pkg}.txt")
(OUT / "fonts.css").write_text("/* Fraunces, IBM Plex and Noto Sans; SIL Open Font License 1.1 (see OFL-*.txt), via Fontsource */\n" + "\n".join(faces) + "\n")
print(len(faces), "font faces")
