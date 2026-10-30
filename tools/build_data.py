#!/usr/bin/env python3
"""
Builds build/data.json for the historical units atlas from the per-civilisation files in data/.

File format (one file per civilisation):
  @ id | name | region | source url | period
  # free-text note about the system (optional, may repeat)
  quantity | name | native name | definition | value | notes
where definition is "N unit" / "a⁄b unit" / "N square unit" / "N cubic unit" (unit of the same file)
and value is a metric value or range ("52.3 cm", "0.296–0.333 m", "2.75 L"). A notes field that
starts with "@" makes the line an earlier/regional value of the unit with the same name above it.
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "data"

REGIONS = ["Africa", "Middle East", "Europe", "South Asia", "East Asia", "Southeast Asia", "Americas"]
QUANT = ["length", "area", "volume", "mass"]

# period → (start, end) years for ordering and the timeline (negative = BC)
YEARS = {
    "egypt": (-3000, -30), "mesopotamia": (-3000, -500), "hebrew": (-1000, 500), "persia": (-550, -330),
    "greece": (-800, -146), "rome": (-500, 500), "byzantium": (330, 1453), "islamic": (622, 1500),
    "vedic": (-1500, 1200), "india": (1526, 1956), "china": (-1600, 1929), "japan": (701, 1958),
    "korea": (300, 1961), "thailand": (1350, 1923), "vietnam": (1000, 1945), "malaya": (1400, 1971),
    "myanmar": (1000, 2011), "philippines": (1500, 1975), "khmer": (800, 1914), "ottoman": (1299, 1931),
    "egypt_modern": (641, 1951), "ethiopia": (1270, 1963), "aztec": (1300, 1521), "inca": (1400, 1533),
    "maya": (250, 900), "newspain": (1521, 1896), "spain": (1100, 1849), "portugal": (1100, 1852),
    "england": (600, 1824), "scotland": (1100, 1824), "ireland": (600, 1200), "wales": (940, 1536),
    "france": (800, 1799), "netherlands": (1300, 1820), "germany": (1300, 1872), "austria": (1500, 1876),
    "hungary": (1500, 1876), "bohemia": (1300, 1876), "switzerland": (1838, 1877), "italy": (1100, 1861),
    "denmark": (1683, 1907), "sweden": (1605, 1889), "finland": (1600, 1887), "norse": (800, 1300),
    "russia": (1100, 1924), "poland": (1400, 1849), "romania": (1600, 1864),
}

UNIT = {  # symbol → (quantity, factor to SI: m, m², m³, kg)
    "μm": ("length", 1e-6), "mm": ("length", 1e-3), "cm": ("length", 1e-2), "m": ("length", 1), "km": ("length", 1e3),
    "cm²": ("area", 1e-4), "m²": ("area", 1), "a": ("area", 100), "ha": ("area", 1e4),
    "mL": ("volume", 1e-6), "ml": ("volume", 1e-6), "L": ("volume", 1e-3), "l": ("volume", 1e-3), "m³": ("volume", 1),
    "μg": ("mass", 1e-9), "mg": ("mass", 1e-6), "g": ("mass", 1e-3), "kg": ("mass", 1), "t": ("mass", 1e3),
}
STRIP = re.compile(r" \((?:mass|area|volume)\)")
NUM = r"\d[\d ,]*(?:\.\d+)?"


def num(s):
    """'1⁄12' '2+1⁄2' '12,960' '0.5' → float"""
    s = s.strip().replace(" ", "").replace(" ", "")
    if "+" in s:
        a, b = s.split("+", 1)
        return num(a) + num(b)
    if "⁄" in s or "/" in s:
        a, b = re.split("[⁄/]", s)
        return num(a) / num(b)
    return float(s.replace(",", ""))


def parse_value(v, quantity):
    if v.strip() in ("-", ""):
        return None
    m = re.fullmatch(rf"\s*({NUM})\s*(?:[–-]\s*({NUM}))?\s*(\S+)\s*", v)
    if not m:
        raise ValueError(f"cannot read value {v!r}")
    lo, hi, unit = num(m.group(1)), num(m.group(2)) if m.group(2) else None, m.group(3)
    if unit not in UNIT:
        raise ValueError(f"unknown unit {unit!r} in {v!r}")
    q, f = UNIT[unit]
    if q != quantity:
        raise ValueError(f"{v!r} is {q}, expected {quantity}")
    return [lo * f, (hi if hi is not None else lo) * f]


def parse_def(d):
    """→ (factor, power, unit name) or None. power 2/3 for 'square'/'cubic' of a length."""
    d = d.strip()
    if d in ("-", ""):
        return None
    m = re.fullmatch(r"([\d.,+⁄/]+)\s+(square |cubic )?(.+)", d)
    if not m:
        return ("text", d)
    power = {"square ": 2, "cubic ": 3}.get(m.group(2) or "", 1)
    return (num(m.group(1)), power, m.group(3).strip())


def read(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    head = [x.strip() for x in lines[0].lstrip("@").split("|")]
    civ = {"id": head[0], "name": head[1], "region": head[2], "src": head[3], "period": head[4], "note": ""}
    notes, units, problems = [], [], []
    for no, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        if line.startswith("#"):
            notes.append(line.lstrip("# ").strip())
            continue
        f = [x.strip() for x in line.split("|")]
        if len(f) != 6:
            problems.append(f"{path.name}:{no}: {len(f)} fields")
            continue
        q, name, native, d, v, note = f
        if q not in QUANT:
            problems.append(f"{path.name}:{no}: quantity {q!r}")
            continue
        try:
            val = parse_value(v, q)
        except ValueError as e:
            problems.append(f"{path.name}:{no}: {e}")
            val = None
        u = {"q": q, "n": name, "nat": "" if native == "-" else native, "def": parse_def(d), "dtext": "" if d == "-" else d,
             "v": val, "stated": val is not None, "note": "" if note == "-" else note, "line": no}
        if note.startswith("@"):
            base = next((x for x in reversed(units) if x["n"] == name and x["q"] == q), None)
            if not base:
                problems.append(f"{path.name}:{no}: variant of unknown {name!r}")
                continue
            base.setdefault("var", []).append({"label": note[1:].strip(), "v": val, "dtext": u["dtext"]})
            continue
        units.append(u)
    civ["note"] = " ".join(notes)
    return civ, units, problems


def resolve(units, problems, cid):
    byq = {(u["q"], u["n"]): u for u in units}
    names = {u["n"] for u in units}

    def find(ref, power, q):
        return byq.get((q if power == 1 else "length", ref))

    for _ in range(12):
        changed = False
        for u in units:
            d = u["def"]
            if not d or d[0] == "text" or (u["v"] and not u["stated"]):
                continue
            k, power, ref = d
            r = find(ref, power, u["q"])
            if r is None or r["v"] is None:
                continue
            calc = [k * r["v"][0] ** power, k * r["v"][1] ** power]
            if u["v"] is None:
                u["v"] = calc
                changed = True
        if not changed:
            break
    # consistency of stated values with their definitions
    for u in units:
        d = u["def"]
        if not (d and d[0] != "text" and u["stated"]):
            continue
        k, power, ref = d
        r = find(ref, power, u["q"])
        if r and r["v"]:
            calc = k * math.sqrt(r["v"][0] * r["v"][1]) ** power
            mid = math.sqrt(u["v"][0] * u["v"][1])
            if abs(math.log(calc / mid)) > 0.06:
                u["dv"] = calc
                problems.append(f"{cid}: {u['n']} stated {mid:.6g} but {k:g} {ref} = {calc:.6g} ({calc / mid:.3f}×)")
    for u in units:
        d = u["def"]
        if d and d[0] != "text" and not find(d[2], d[1], u["q"]):
            problems.append(f"{cid}: {u['n']}: definition refers to unknown {d[2]!r}")


def main():
    civs, out, problems = [], [], []
    for p in sorted(RAW.glob("*.txt")):
        civ, units, prob = read(p)
        problems += prob
        resolve(units, problems, civ["id"])
        if civ["id"] not in YEARS:
            problems.append(f"{civ['id']}: no years")
        civ["y"] = YEARS.get(civ["id"], (0, 0))
        if civ["region"] not in REGIONS:
            problems.append(f"{civ['id']}: region {civ['region']!r}")
        ci = len(civs)
        civs.append(civ)
        idx = {(u["q"], u["n"]): len(out) + i for i, u in enumerate(units)}
        for u in units:
            d = u["def"]
            ref = idx.get((u["q"] if d[1] == 1 else "length", d[2])) if d and d[0] != "text" else None
            out.append({
                "c": ci, "q": QUANT.index(u["q"]), "n": STRIP.sub("", u["n"]), "nat": u["nat"], "d": STRIP.sub("", u["dtext"]),
                "r": ref, "v": u["v"], "s": 1 if u["stated"] else 0, "note": u["note"],
                **({"dv": u["dv"]} if u.get("dv") else {}),
                **({"var": u["var"]} if u.get("var") else {}),
            })
    # order civilisations by region, then start year
    order = sorted(range(len(civs)), key=lambda i: (REGIONS.index(civs[i]["region"]) if civs[i]["region"] in REGIONS else 99, civs[i]["y"][0]))
    remap = {old: new for new, old in enumerate(order)}
    civs = [civs[i] for i in order]
    for u in out:
        u["c"] = remap[u["c"]]
    data = {"civs": [{k: c[k] for k in ("id", "name", "region", "src", "period", "note", "y")} for c in civs],
            "units": out, "regions": REGIONS, "quantities": QUANT}
    (HERE / "build").mkdir(exist_ok=True)
    (HERE / "build" / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    nv = sum(1 for u in out if u["v"])
    print(f"{len(civs)} civilisations, {len(out)} units, {nv} with a value, {sum(len(u.get('var', [])) for u in out)} variants")
    for c in civs:
        us = [u for u in out if civs[u["c"]] is c]
    print(f"{len(problems)} problems:")
    for p in problems:
        print("  ", p)


if __name__ == "__main__":
    main()
