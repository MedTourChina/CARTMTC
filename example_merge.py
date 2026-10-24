# -*- coding: utf-8 -*-
"""
Example / template: how the AGENT fills translations for ONE page.

Usage pattern (run from the site root, alongside i18n_build.py):
  1) Dump this page's not-yet-translated strings to a readable file:
         python example_merge.py dump index.html
  2) The agent reads that file, translates each line into fr/es/ru/ar/vi,
     and edits the PAIRS list below (triple-quoted to avoid escaping).
  3) Merge + persist:
         python example_merge.py merge
  4) Rebuild:
         python i18n_build.py build

The triple-quoted string literals below are intentional: English source text
often contains apostrophes ("patient's") and double quotes, which would break
normal Python string quoting. Triple quotes keep everything safe.
"""
import json
import sys
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = "."
TR_FILE = "i18n_translations.json"

ATTR_KEYS = ["alt", "title", "aria-label", "aria-placeholder", "placeholder"]
SKIP_TAGS = {"script", "style", "template", "noscript"}


def collect(soup):
    out, seen = [], set()
    def add(s):
        s = s.strip()
        if s and s not in seen:
            seen.add(s); out.append(s)
    if soup.title and soup.title.string:
        add(str(soup.title.string))
    for m in soup.find_all("meta"):
        v = m.get("content")
        if isinstance(v, str):
            add(v)
    for el in soup.find_all(string=True):
        if isinstance(el, NavigableString):
            p = el.parent
            if p and p.name not in SKIP_TAGS:
                add(str(el))
    for el in soup.find_all(True):
        if isinstance(el, Tag):
            for k in ATTR_KEYS:
                v = el.get(k)
                if isinstance(v, str):
                    add(v)
    return out


def dump(page):
    html = open(page, encoding="utf-8").read()
    soup = BeautifulSoup(html, "lxml")
    strings = collect(soup)
    tr = json.load(open(TR_FILE, encoding="utf-8")) if os.path.exists(TR_FILE) else {}
    missing = [s for s in strings if s not in tr]
    with open(f"_missing_{page.replace('/', '_')}.txt", "w", encoding="utf-8") as f:
        for i, s in enumerate(missing):
            f.write(f"[{i}] {s}\n")
    print(f"wrote {len(missing)} missing strings for {page} -> _missing_{page.replace('/','_')}.txt")


# ---------------------------------------------------------------------------
# AGENT FILLS THIS: [English source, fr, es, ru, ar, vi]  (triple-quoted!)
# Copy exact lines from the _missing_*.txt dump as the first element.
# ---------------------------------------------------------------------------
PAIRS = [
    # ["""English source string here""",
    #  """French translation""",
    #  """Spanish translation""",
    #  """Russian translation""",
    #  """Arabic translation (real Unicode)""",
    #  """Vietnamese translation"""],
]


def merge():
    if not PAIRS:
        print("PAIRS is empty -- fill it with translations first.")
        return
    tr = json.load(open(TR_FILE, encoding="utf-8")) if os.path.exists(TR_FILE) else {}
    n = 0
    for k, fr, es, ru, ar, vi in PAIRS:
        tr[k] = {"fr": fr, "es": es, "ru": ru, "ar": ar, "vi": vi}
        n += 1
    json.dump(tr, open(TR_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"merged {n} entries into {TR_FILE}")


if __name__ == "__main__":
    import os
    mode = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if mode == "dump":
        dump(sys.argv[2] if len(sys.argv) > 2 else "index.html")
    elif mode == "merge":
        merge()
    else:
        print("usage: example_merge.py [dump <page> | merge]")
