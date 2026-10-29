# -*- coding: utf-8 -*-
"""Scan every local MedTourChina site repo for news articles related to
CAR-T / haematology / oncology, resolve each site's live domain, and emit a
compact inventory JSON so the cart hub can build a 'From our hospital
network' citation block.

Per project convention: we NEVER copy these articles into the cart site.
We only cite them (headline + one-line summary + external link).
"""
import glob
import json
import os
import re
import html

WB = r"C:/Users/KILLT/WorkBuddy"

# Only the English source news dirs (skip the i18n mirrors)
SKIP_LANG = {"fr", "es", "ru", "ar", "vi", "ja", "ko", "de"}

CART_DIR = os.path.join(WB, "2026-10-24-22-05-24", "cart.medtourchina.net")

# CAR-T core = strongly on-topic for a CAR-T hub.
# NOTE: \b boundaries are essential — without them "CAR-T" matches "cartilage",
# which pulled knee/shoulder orthopaedic articles into the first scan.
CORE = re.compile(
    r"\bCAR[-\u2011 ]?T\b|\bCT041\b|Satri-?cel|Axi-?cel|axi-?cel|\bLM101\b|"
    r"\bCD19\b|\bBCMA\b|\bCLDN18\.2\b|\bCD7\b|\bscFv\b|chimeric antigen",
    re.I,
)
# Adjacent haematology / stem-cell transplant (secondary but genuinely close)
ADJ = re.compile(
    r"lymphoma|leuk[ae]mi|myeloma|haematolog|hematolog|stem[-\u2011 ]cell transplant|"
    r"淋巴|白血病|骨髓瘤|血液",
    re.I,
)


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def page_title(t):
    m = re.search(r"<title>(.*?)</title>", t, re.S)
    if not m:
        return ""
    return html.unescape(strip_tags(m.group(1)))


def meta(t, name):
    m = re.search(
        r'<meta[^>]+name=["\']%s["\'][^>]+content=["\'](.*?)["\']' % name, t, re.S | re.I
    )
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']%s["\']' % name,
            t,
            re.S | re.I,
        )
    return html.unescape(m.group(1)).strip() if m else ""


def page_date(t):
    for pat in (
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)',
        r'"datePublished"\s*:\s*"([^"]+)"',
        r'<time[^>]+datetime=["\']([^"\']+)',
    ):
        m = re.search(pat, t)
        if m:
            return m.group(1)[:10]
    return ""


def site_domain(site_dir):
    """Resolve the live domain for a site dir."""
    for fn in ("CNAME", "sitemap.xml", "robots.txt", "index.html"):
        p = os.path.join(site_dir, fn)
        if not os.path.isfile(p):
            continue
        t = open(p, encoding="utf-8", errors="ignore").read()
        if fn == "CNAME":
            v = t.strip().splitlines()[0].strip()
            if v:
                return v
        m = re.search(r"https?://([a-z0-9.-]*medtourchina\.net)", t, re.I)
        if m:
            return m.group(1)
    return ""


def find_repo_root(path):
    """Walk up from a news dir until we hit the real site root.

    Several sites keep news under resources/news, so basename() of the parent
    is not a reliable site identity. A site root is the nearest ancestor that
    looks like an independent repo/deploy (has a CNAME, sitemap, or .git).
    """
    p = os.path.abspath(path)
    fallback = None
    for _ in range(6):
        p = os.path.dirname(p)
        if os.path.basename(p) in SKIP_LANG:
            continue
        has_marks = any(
            os.path.exists(os.path.join(p, x))
            for x in ("CNAME", "sitemap.xml", ".git")
        )
        if has_marks:
            return p.replace("\\", "/")
        if fallback is None and os.path.isfile(os.path.join(p, "index.html")):
            fallback = p.replace("\\", "/")
    return fallback


# Collect candidate site roots, dedupe by real repo path; for each root keep
# the actual news directory that lives outside any language mirror.
cand = {}
for pat in ("*/*", "*/*/*"):
    for d in sorted(glob.glob(os.path.join(WB, pat, "news"))):
        d = d.replace("\\", "/")
        if "_tmp_rebuilt" in d:
            continue
        # skip any news dir that sits inside an i18n mirror
        rel = d[len(WB) + 1:].split("/")[:-1]
        if any(seg in SKIP_LANG for seg in rel):
            continue
        site = find_repo_root(d)
        if not site:
            continue
        name = os.path.basename(site)
        prev = cand.get(name)
        # prefer the newest session dir, and prefer the variant with more files
        if prev is None or (site, d) > (prev[0], prev[1]):
            cand[name] = (site, d)

rows = []
for name, (site, ndir) in sorted(cand.items()):
    dom = site_domain(site)
    arts = [
        f
        for f in sorted(glob.glob(os.path.join(ndir, "*.html")))
        if os.path.basename(f) != "index.html"
    ]
    for f in arts:
        t = open(f, encoding="utf-8", errors="ignore").read()
        title = page_title(t)
        body = strip_tags(re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S))
        base = os.path.basename(f)
        head = base + " " + title
        hcore = len(CORE.findall(head))
        bcore = len(CORE.findall(body))
        hadj = len(ADJ.findall(head))
        badj = len(ADJ.findall(body))
        # An article qualifies when the signal sits in the headline, or when the
        # body mentions it repeatedly (a single passing mention is not enough).
        if hcore >= 1 or bcore >= 3:
            tier = "core"
        elif hadj >= 1 or badj >= 3:
            tier = "adj"
        else:
            continue
        rows.append(
            {
                "site": name,
                "site_dir": site,
                "domain": dom,
                "file": base,
                # URL must mirror the site's real layout: some sites keep
                # articles under news/, others under resources/news/.
                "path": os.path.relpath(f, site).replace("\\", "/"),
                "url": (
                    "https://%s/%s"
                    % (dom, os.path.relpath(f, site).replace("\\", "/"))
                    if dom
                    else ""
                ),
                "title": title,
                "desc": meta(t, "description"),
                "date": page_date(t),
                "tier": tier,
                "chars": len(body),
            }
        )

# dedupe identical (file, title) across duplicate repo copies
seen = {}
for r in rows:
    k = (r["file"], r["title"])
    if k not in seen:
        seen[k] = r
rows = list(seen.values())

out = os.path.join(CART_DIR, "_network_inventory.json")
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("site roots scanned:", len(cand))
print("relevant articles:", len(rows))
print("  core CAR-T :", sum(1 for r in rows if r["tier"] == "core"))
print("  adjacent   :", sum(1 for r in rows if r["tier"] == "adj"))
print("no domain    :", sum(1 for r in rows if not r["domain"]))
print()
print("%-16s %-32s %5s %5s" % ("SITE", "DOMAIN", "CORE", "ADJ"))
for name in sorted(cand):
    sub = [r for r in rows if r["site"] == name]
    if not sub:
        continue
    dom = sub[0]["domain"] or "?"
    print(
        "%-16s %-32s %5d %5d"
        % (
            name,
            dom,
            sum(1 for r in sub if r["tier"] == "core"),
            sum(1 for r in sub if r["tier"] == "adj"),
        )
    )
print()
print("written ->", out)
