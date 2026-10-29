#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Post-build: translate string values inside JSON-LD blocks of built i18n pages.
Only exact matches against i18n_translations.json are replaced, so @type/url/
dates/latin product names stay untouched."""
import json, re, glob, sys, html

LANGS = ["fr", "es", "ru", "ar", "vi"]
TR = json.load(open("i18n_translations.json", encoding="utf-8"))
SCRIPT_RE = re.compile(
    r'(<script[^>]+type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.S | re.I,
)


def walk(node, lang, hits):
    if isinstance(node, dict):
        return {k: walk(v, lang, hits) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v, lang, hits) for v in node]
    if isinstance(node, str):
        key = node.strip()
        entry = TR.get(key)
        if isinstance(entry, dict):
            tgt = (entry.get(lang) or "").strip()
            if tgt and tgt != key:
                hits[0] += 1
                lead = node[: len(node) - len(node.lstrip())]
                trail = node[len(node.rstrip()):]
                return lead + tgt + trail
    return node


total = 0
changed_files = 0
for lang in LANGS:
    for path in glob.glob(lang + "/**/*.html", recursive=True):
        src = open(path, encoding="utf-8").read()
        new = src
        page_hits = 0

        def repl(m):
            global page_hits
            head, body, tail = m.group(1), m.group(2), m.group(3)
            if not body.strip():
                return m.group(0)
            try:
                obj = json.loads(body)
            except Exception:
                return m.group(0)
            hits = [0]
            obj = walk(obj, lang, hits)
            if hits[0] == 0:
                return m.group(0)
            page_hits += hits[0]
            return head + "\n" + json.dumps(obj, ensure_ascii=False, indent=2) + "\n" + tail

        new = SCRIPT_RE.sub(repl, new)
        if new != src:
            open(path, "w", encoding="utf-8", newline="\n").write(new)
            changed_files += 1
            total += page_hits

print(f"JSON-LD translated: {total} string values across {changed_files} files")
