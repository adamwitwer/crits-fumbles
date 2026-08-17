#!/usr/bin/env python3
"""Normalize the house crit/fumble tables into the shape the Foundry module reads.

The web app keeps crits and fumbles in two different shapes: crits are a flat
{"1-15": "Title: Effect"} map, fumbles are [{roll, description, effect}]. Doing the
band parsing and the "Title: Effect" split here means the module ships pre-parsed
data and its resolver is a single find().

Run from the repo root:

    python3 tools/build-foundry-tables.py

Source of truth stays app/*.json; this only ever writes the module's data file.
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_NAME = "Fury & Folly"  # the house tables; the module presents them unnamed
CRIT_SRC = os.path.join(REPO_ROOT, "app", "critical_hits_master.json")
FUMBLE_SRC = os.path.join(REPO_ROOT, "app", "fumbles_master.json")
OUT_PATH = os.path.join(REPO_ROOT, "foundry", "crits-fumbles", "data", "tables.json")

DIE = 100
problems = []


def parse_band(key, where):
    """Turn "1-15" or "7" into (min, max)."""
    try:
        if "-" in key:
            low, high = (int(part) for part in key.split("-", 1))
        else:
            low = high = int(key)
    except ValueError:
        problems.append(f"{where}: unparseable band {key!r}")
        return None

    if low > high:
        problems.append(f"{where}: inverted band {key!r}")
        return None
    return low, high


def check_coverage(entries, where):
    """Every value on the die must resolve to exactly one entry."""
    seen = {}
    for entry in entries:
        for value in range(entry["min"], entry["max"] + 1):
            if value in seen:
                problems.append(f"{where}: roll {value} matches two bands")
            seen[value] = True

    missing = [v for v in range(1, DIE + 1) if v not in seen]
    if missing:
        problems.append(f"{where}: no result for {compress(missing)}")

    stray = sorted(v for v in seen if not 1 <= v <= DIE)
    if stray:
        problems.append(f"{where}: bands cover off-die values {compress(stray)}")


def compress(values):
    """[1,2,3,7] -> '1-3, 7' so coverage errors stay readable."""
    runs, start, prev = [], values[0], values[0]
    for value in values[1:]:
        if value != prev + 1:
            runs.append((start, prev))
            start = value
        prev = value
    runs.append((start, prev))
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)


def split_title(text, where):
    """Crit results encode the title in a "Title: Effect" prefix."""
    title, sep, effect = text.partition(": ")
    if not sep:
        problems.append(f"{where}: no 'Title: Effect' separator")
        return text.strip(), ""
    # A long title means the split landed on a colon inside the prose instead.
    if len(title) > 60:
        problems.append(f"{where}: suspicious title {title[:40]!r}...")
    return title.strip(), effect.strip()


def build_crits(raw):
    out = {}
    for damage_type, bands in raw.items():
        entries = []
        for band_key, text in bands.items():
            where = f"crit/{damage_type}/{band_key}"
            band = parse_band(band_key, where)
            if band is None:
                continue
            title, effect = split_title(text, where)
            entries.append({"min": band[0], "max": band[1], "title": title, "effect": effect})
        entries.sort(key=lambda e: e["min"])
        check_coverage(entries, f"crit/{damage_type}")
        out[damage_type] = entries
    return out


def build_fumbles(raw):
    out = {}
    for category, rows in raw.items():
        entries = []
        for row in rows:
            band_key = row.get("roll", "")
            where = f"fumble/{category}/{band_key}"
            band = parse_band(band_key, where)
            if band is None:
                continue
            entries.append({
                "min": band[0],
                "max": band[1],
                "title": (row.get("description") or "").strip(),
                "effect": (row.get("effect") or "").strip(),
            })
        entries.sort(key=lambda e: e["min"])
        check_coverage(entries, f"fumble/{category}")
        out[category] = entries
    return out


def main():
    with open(CRIT_SRC) as handle:
        crit_raw = json.load(handle)[SOURCE_NAME]
    with open(FUMBLE_SRC) as handle:
        fumble_raw = json.load(handle)[SOURCE_NAME]

    tables = {"die": DIE, "crits": build_crits(crit_raw), "fumbles": build_fumbles(fumble_raw)}

    if problems:
        print(f"Refusing to write: {len(problems)} problem(s) in the source tables.", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(tables, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    crit_count = sum(len(v) for v in tables["crits"].values())
    fumble_count = sum(len(v) for v in tables["fumbles"].values())
    size_kb = os.path.getsize(OUT_PATH) / 1024
    print(f"Wrote {os.path.relpath(OUT_PATH, REPO_ROOT)} ({size_kb:.1f} KB)")
    print(f"  crits:   {len(tables['crits'])} damage types, {crit_count} entries")
    print(f"  fumbles: {len(tables['fumbles'])} categories, {fumble_count} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
