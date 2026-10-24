#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MedTourChina i18n builder -- agent-driven, two phases.

Drop this file into a static site's ROOT, then:
  python i18n_build.py extract   # build i18n_tm.json (dedup strings, freq-sorted)
  python i18n_build.py build     # generate /fr /es /ru /ar /vi pages from i18n_translations.json

Phase 1 (extract): walk all English source pages, collect every translatable
  string (visible text + title/meta content/alt/aria/placeholder) into a single
  de-duplicated Translation Memory (i18n_tm.json). Ordered by page-coverage desc.

Phase 2 (build): read i18n_tm.json + i18n_translations.json (filled by the
  agent). For every source page and every target language, clone the HTML,
  replace strings via the TM, inject <html lang/dir>, the machine-translation
  disclaimer, full hreflang alternates, and rewrite internal links to the
  /<lang>/ path. Untranslated strings gracefully fall back to English.
  Finally regenerate sitemap.xml from actually-generated pages.

Requires: beautifulsoup4, lxml   (pip install beautifulsoup4 lxml)
"""
import os, json, shutil, sys
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString, Tag, Comment, CData, ProcessingInstruction, Doctype

# Non-visible string node types that must NEVER be extracted/translated.
# CRITICAL: Comment subclasses NavigableString, so find_all(string=True) yields
# comment nodes too. If not skipped, apply_lang() will replace_with() the comment
# and CONVERT IT INTO A VISIBLE TEXT NODE -- e.g. a section label like
# "<!-- Dhaka Medical Exhibition -->" renders as stray translated text above the
# card in every language. Always guard both collect_strings() and apply_lang().
SKIP_NODE_TYPES = (Comment, CData, ProcessingInstruction, Doctype)

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---- per-site config -------------------------------------------------------
TARGETS = ["fr", "es", "ru", "ar", "vi"]          # target languages
RTL = {"ar"}                                       # languages that need dir=rtl
SITE_DOMAIN = "https://cart.medtourchina.net"      # <-- CHANGE per site (sitemap + hreflang)
# Brand / proper-noun strings that must NEVER be translated:
KEEP_ENGLISH = {
    # Brand / program
    "MedTourChina", "CAR-T", "cart.medtourchina.net",
    # Medical abbreviations used universally (keep English)
    "CD19", "BCMA", "CD20", "CD22", "CD30", "GPRC5D", "CD7", "CD123",
    "CRS", "ICANS", "ALL", "DLBCL", "FL", "MCL", "CLL", "NHL", "MM",
    "HLA", "CAR", "TCR", "scFv", "FDA", "NMPA", "EMA", "JCI",
    "MDT", "CT", "MRI", "PET", "PET-CT", "ICU",
    "IL-6", "GM-CSF", "Ig", "IgG",
    # Approved CAR-T drug brand names (keep English / proprietary)
    "Kymriah", "Yescarta", "Tecartus", "Breyanzi", "Abecma", "Carvykti",
    "奕凯达", "倍诺达", "福可苏", "源瑞达", "赛凯泽",
    "Fosun Kite", "JW Therapeutics", "Innovent", "IASO Bio",
    "Juven Sc", "Carsgen", "Novartis", "Gilead", "BMS",
    # Common media / channels
    "WhatsApp",
    # JSON-LD / meta technical strings (must remain in English)
    "FAQ", "WebSite", "MedicalOrganization", "MedicalClinic", "MedicalWebPage",
    "WebPage", "ContactPage", "AboutPage", "BreadcrumbList", "ListItem",
    "Person", "PostalAddress", "GeoCoordinates", "Article", "FAQPage",
    "ItemList", "SearchAction", "Organization", "ContactPoint",
    # Open Graph protocol values (must remain in English)
    "website", "summary_large_image",
    # Geo / viewport (must remain in English / numeric)
    "width=device-width, initial-scale=1.0",
    # Currency / numeric tokens (keep as-is)
    "CNY", "USD",
    # Back-to-parent backlink (brand label)
    "← MedTourChina",
}
# ---------------------------------------------------------------------------

TM_FILE = os.path.join(ROOT, "i18n_tm.json")
TR_FILE = os.path.join(ROOT, "i18n_translations.json")

DISCLAIMER = {
    "fr": "Cette page a été traduite automatiquement par une intelligence artificielle. Pour des informations médicales faisant autorité, veuillez vous référer à la version anglaise.",
    "es": "Esta página fue traducida automáticamente por una inteligencia artificial. Para información médica fiable, consulte la versión en inglés.",
    "ru": "Эта страница переведена автоматически с помощью искусственного интеллекта. Достоверную медицинскую информацию см. в английской версии.",
    "ar": "تمت ترجمة هذه الصفحة آلياً بواسطة الذكاء الاصطناعي. للحصول على معلومات طبية موثوقة، يرجى الرجوع إلى النسخة الإنجليزية.",
    "vi": "Trang này được dịch tự động bằng trí tuệ nhân tạo. Để biết thông tin y tế chính xác, vui lòng tham khảo bản tiếng Anh.",
}

# ---- language switcher ------------------------------------------------------
# (en + 5 targets). EN is the canonical source at site root; each target lives
# under /<lang>/. The switcher lets users jump between locales for the SAME page.
LANGS_UI = [
    ("en", "English"),
    ("fr", "Français"),
    ("es", "Español"),
    ("ru", "Русский"),
    ("ar", "العربية"),
    ("vi", "Tiếng Việt"),
]

# Full locale list for hreflang sets: EN (source) + all targets.
ALL_LOCALES = ["en"] + TARGETS

# Open Graph locale code per language (og:locale must be in xx_XX form).
LOCALE = {
    "en": "en_US",
    "fr": "fr_FR",
    "es": "es_ES",
    "ru": "ru_RU",
    "ar": "ar_AR",
    "vi": "vi_VN",
}

def page_url(locale, src_rel):
    if locale == "en":
        return "/" + src_rel
    return f"/{locale}/{src_rel}"

def page_path(lang, rel):
    """Canonical *path* (no domain) for a (lang, rel).

    index.html collapses to a directory root (trailing slash):
      rel="index.html"        -> "/"            (en)  or "/fr/"       (fr)
      rel="about/index.html"  -> "/about/"      (en)  or "/fr/about/" (fr)
    Any OTHER page KEEPS its filename so each article/page gets its own
    canonical URL. (Earlier versions wrongly collapsed every leaf page onto its
    parent folder, e.g. /equipment/ankpower.html -> /equipment/, so multiple
    pages shared one canonical.) Example:
      rel="equipment/ankpower.html" -> "/equipment/ankpower.html"       (en)
                                    -> "/fr/equipment/ankpower.html"   (fr)
      rel="news/<slug>.html"        -> "/news/<slug>.html"             (en)
                                    -> "/fr/news/<slug>.html"          (fr)
    """
    d = os.path.dirname(rel)
    if os.path.basename(rel) == "index.html":
        path = ("/" + d + "/") if d else "/"
    else:
        path = "/" + rel
    return path if lang == "en" else f"/{lang}{path}"

def canonical_url(lang, rel):
    return SITE_DOMAIN + page_path(lang, rel)

def render_switcher_html(src_rel, active):
    items = []
    for code, label in LANGS_UI:
        href = page_url(code, src_rel)
        extra = ' class="active" aria-current="true"' if code == active else ""
        items.append(f'    <a href="{href}" hreflang="{code}"{extra}>{label}</a>')
    return '<nav class="lang-switch" aria-label="Language">\n' + "\n".join(items) + "\n  </nav>"

def inject_switcher(soup, src_rel, active):
    """Tag-based injection for generated (non-canonical) language pages."""
    if soup.find("nav", class_="lang-switch"):
        return
    nav = BeautifulSoup(render_switcher_html(src_rel, active), "lxml").find("nav")
    body = soup.find("body")
    if body and nav:
        body.insert(0, nav)

def inject_switcher_into_file(path, src_rel):
    """Safe string insertion for canonical EN source pages (no re-serialization
    of the whole document, to avoid altering the authoritative markup)."""
    with open(path, encoding="utf-8") as f:
        html = f.read()
    if 'class="lang-switch"' in html:
        return
    nav_html = render_switcher_html(src_rel, "en")
    idx = html.find("<body")
    if idx == -1:
        return
    end = html.find(">", idx)
    if end == -1:
        return
    html = html[:end + 1] + "\n" + nav_html + "\n" + html[end + 1:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

SKIP_TAGS = {"script", "style", "template", "noscript"}

# technical tokens that must never be sent for translation
SKIP_STRINGS = {
    "viewport", "Open Graph", "description", "twitter:card", "Twitter Card",
    "summary_large_image", "twitter:title", "twitter:description", "en_US",
    "html", "×", "article", "Footer", "Breadcrumb",
    "Article Body", "Article Header", "og:image", "og:title", "og:description",
    "og:type", "og:url", "og:site_name", "theme-color", "charset",
}

# ---- source discovery -------------------------------------------------------
def find_sources():
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Exclude build target dirs, dot dirs, AND dev/scratch dirs (e.g. _probe,
        # feeds, temp _*.py helpers) so they are never treated as HTML sources.
        # Without this, stray .html files under a scratch dir balloon the language
        # output and can trip sandbox batch-deletion protection.
        dirnames[:] = [d for d in dirnames if d not in TARGETS and not d.startswith(".")
                        and not d.startswith("_") and d not in ("__pycache__", "feeds")]
        for fn in filenames:
            # Skip draft / scratch / preview HTML (e.g. _draft-<slug>.html) so an
            # unpublished article is never localized or emitted by build.
            if fn.endswith(".html") and not fn.startswith("_"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
                out.append(rel)
    out.sort()
    return out

SOURCES = find_sources()

ATTR_KEYS = ["alt", "title", "aria-label", "aria-placeholder", "placeholder"]

# ---- extraction -------------------------------------------------------------
def _translatable(s):
    s = s.strip()
    if not s:
        return False
    if s in SKIP_STRINGS or s in KEEP_ENGLISH:
        return False
    # pure symbols / single char / html fragments
    if len(s) < 2:
        return False
    if any(c in s for c in "<>{}[]"):
        return False
    if s.startswith(("http://", "https://", "mailto:", "tel:")):
        return False
    return True

def collect_strings(soup):
    """Return ordered list of unique translatable strings from one page."""
    found = []
    seen = set()

    def add(s):
        s = s.strip()
        if not _translatable(s):
            return
        if s not in seen:
            seen.add(s)
            found.append(s)

    t = soup.title
    if t and t.string:
        add(str(t.string))

    for m in soup.find_all("meta"):
        # <meta name="keywords"> is a comma-separated SEO token list, not
        # user-visible copy -- translating it produces odd localized keyword
        # spam and it is ignored by search engines. Keep it in English.
        if (m.get("name") or "").strip().lower() == "keywords":
            continue
        v = m.get("content")
        if isinstance(v, str):
            add(v)

    for el in soup.find_all(string=True):
        if isinstance(el, SKIP_NODE_TYPES):
            continue
        if isinstance(el, NavigableString):
            parent = el.parent
            if parent is None or parent.name in SKIP_TAGS:
                continue
            add(str(el))

    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        for k in ATTR_KEYS:
            v = el.get(k)
            if isinstance(v, str):
                add(v)

    return found

def extract():
    per_page = {}
    freq = {}  # string -> set of source pages containing it
    for rel in SOURCES:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "lxml")
        strings = collect_strings(soup)
        per_page[rel] = len(strings)
        for s in strings:
            freq.setdefault(s, set()).add(rel)
    tm = sorted(freq.keys(), key=lambda s: (-len(freq[s]), len(s)))
    with open(TM_FILE, "w", encoding="utf-8") as f:
        json.dump({"sources": tm, "freq": {k: len(v) for k, v in freq.items()}},
                  f, ensure_ascii=False, indent=1)
    print(f"Extracted {len(tm)} unique strings across {len(SOURCES)} pages.")
    print("Per-page unique counts:")
    for rel, n in per_page.items():
        print(f"  {n:4d}  {rel}")
    top = [s for s in tm if len(freq[s]) >= 10]
    print(f"\nHigh-frequency strings (appear on >=10 pages): {len(top)} "
          f"-> translating these lifts ALL pages at once.")
    if not os.path.exists(TR_FILE):
        with open(TR_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=1)
        print("Created empty i18n_translations.json -- agent fills this.")

# ---- build helpers ----------------------------------------------------------
def load_translations():
    if os.path.exists(TR_FILE):
        with open(TR_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def rewrite_link(href, lang, src_rel):
    if not href:
        return href
    if href.startswith(("http://", "https://", "//", "#", "mailto:", "tel:", "javascript:")):
        return href
    if href.startswith(("/assets", "/css", "/js", "/images", "/fonts")):
        return href
    if href.startswith("/"):
        if href == "/":
            return f"/{lang}/"
        # already a locale-prefixed link (e.g. language-switcher links like
        # /ar/index.html, /fr/services/) — do NOT double-prefix it.
        if href[1:].split("/", 1)[0] in TARGETS:
            return href
        return f"/{lang}{href}"
    base = os.path.dirname(src_rel)
    resolved = urljoin((base + "/") if base else "", href)
    resolved = resolved.lstrip("/")
    return f"/{lang}/{resolved}"

# Shared root assets (css/js/assets/images/fonts) must stay absolute so they
# resolve correctly from /<lang>/ subdirectories.
ASSET_PREFIXES = ("/assets", "/css", "/js", "/images", "/fonts")
REL_ASSET_DIRS = ("assets/", "css/", "js/", "images/", "fonts/")

def fix_asset_ref(value, src_rel):
    """Promote relative shared-asset references (css/js/images/fonts) to
    root-absolute paths so they work from any /<lang>/ subdirectory. Absolute
    (http, //, /...) and non-asset values are returned unchanged."""
    if not value:
        return value
    if value.startswith(("http://", "https://", "//", "#", "data:", "mailto:", "tel:")):
        return value
    if value.startswith(ASSET_PREFIXES):  # already absolute at root
        return value
    if value.startswith("/"):  # some other absolute internal path
        return value
    # relative -> resolve against source dir, then promote to root absolute
    # only when it points into a shared asset directory.
    base = os.path.dirname(src_rel)
    resolved = urljoin((base + "/") if base else "", value)
    resolved = resolved.lstrip("/")
    if resolved.startswith(REL_ASSET_DIRS):
        return "/" + resolved
    return value

def apply_lang(soup, lang, tr):
    if soup.title and soup.title.string:
        key = str(soup.title.string).strip()
        if key in tr and lang in tr[key] and tr[key][lang]:
            soup.title.string.replace_with(tr[key][lang])
    for m in soup.find_all("meta"):
        for a in ("content", "name"):
            v = m.get(a)
            if isinstance(v, str) and v.strip() and v.strip() in tr and lang in tr[v.strip()] and tr[v.strip()][lang]:
                m[a] = tr[v.strip()][lang]
    for el in soup.find_all(string=True):
        if isinstance(el, SKIP_NODE_TYPES):
            continue
        if isinstance(el, NavigableString):
            parent = el.parent
            if parent is None or parent.name in SKIP_TAGS:
                continue
            key = str(el).strip()
            if key in tr and lang in tr[key] and tr[key][lang]:
                el.replace_with(tr[key][lang])
    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        for k in ATTR_KEYS:
            v = el.get(k)
            if isinstance(v, str) and v.strip() and v.strip() in tr and lang in tr[v.strip()] and tr[v.strip()][lang]:
                el[k] = tr[v.strip()][lang]

def inject_head(soup, lang, src_rel):
    html = soup.find("html")
    if html:
        html["lang"] = lang
        html["dir"] = "rtl" if lang in RTL else "ltr"
    head = soup.find("head")
    if not head:
        return
    body = soup.find("body")
    if body:
        banner = soup.new_tag("div")
        banner["class"] = "mt-disclaimer"
        banner.append(DISCLAIMER.get(lang, ""))
        body.insert(0, banner)
    # --- per-language SEO tags (the original bug: every locale pointed at EN) ---
    self_url = canonical_url(lang, src_rel)
    canon = head.find("link", attrs={"rel": "canonical"})
    if canon is not None:
        canon["href"] = self_url
    else:
        canon = soup.new_tag("link")
        canon["rel"] = "canonical"
        canon["href"] = self_url
        head.append(canon)
    og_url = head.find("meta", attrs={"property": "og:url"})
    if og_url is not None:
        og_url["content"] = self_url
    og_loc = head.find("meta", attrs={"property": "og:locale"})
    if og_loc is not None:
        og_loc["content"] = LOCALE.get(lang, "en_US")
    # --- full hreflang set: en + each target + x-default, all absolute URLs ---
    for old in head.find_all("link", attrs={"rel": "alternate"}):
        old.decompose()
    for loc in ALL_LOCALES:
        l = soup.new_tag("link")
        l["rel"] = "alternate"
        l["hreflang"] = loc
        l["href"] = canonical_url(loc, src_rel)
        head.append(l)
    xd = soup.new_tag("link")
    xd["rel"] = "alternate"
    xd["hreflang"] = "x-default"
    xd["href"] = canonical_url("en", src_rel)
    head.append(xd)

def inject_en_hreflang(path, rel):
    """Safe string insertion of a full hreflang set into the canonical EN source
    page (string insert, NOT soup re-serialization, to protect authoritative
    markup). EN source already has correct canonical/og:url pointing at itself;
    it only lacks the cross-locale hreflang alternates."""
    with open(path, encoding="utf-8") as f:
        html = f.read()
    if 'hreflang="x-default"' in html:
        return  # already injected
    links = []
    for loc in ALL_LOCALES:
        links.append(f'<link rel="alternate" hreflang="{loc}" href="{canonical_url(loc, rel)}"/>')
    links.append(f'<link rel="alternate" hreflang="x-default" href="{canonical_url("en", rel)}"/>')
    block = "\n  ".join(links)
    idx = html.rfind("</head>")
    if idx == -1:
        return
    html = html[:idx] + "  " + block + "\n" + html[idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

def build():
    tr = load_translations()
    for lang in TARGETS:
        d = os.path.join(ROOT, lang)
        if os.path.isdir(d):
            # Delete only .html files, never the whole directory tree.
            # shutil.rmtree on the lang dir can exceed sandbox batch-deletion
            # thresholds (e.g. when scratch dirs ballooned the file count) and
            # abort the build mid-way, leaving language dirs empty. Removing
            # .html only is safe and avoids the protection tripwire.
            for fn in os.listdir(d):
                if fn.endswith(".html"):
                    try:
                        os.remove(os.path.join(d, fn))
                    except OSError:
                        pass
        os.makedirs(d, exist_ok=True)
        os.makedirs(d, exist_ok=True)

    generated = []
    for rel in SOURCES:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            base_soup = BeautifulSoup(f.read(), "lxml")
        for lang in TARGETS:
            soup = BeautifulSoup(str(base_soup), "lxml")
            apply_lang(soup, lang, tr)
            for a in soup.find_all("a"):
                h = a.get("href")
                if not h:
                    continue
                hl = a.get("hreflang")
                if hl:  # language-switcher entry
                    # The English entry must return to the EN site (same page in
                    # English), never get a locale prefix like /fr/index.html.
                    if hl == "en":
                        a["href"] = "/" + rel
                    # Source <nav> hardcodes EN as active -- clear it and mark
                    # the real active locale for this generated page.
                    cls = a.get("class") or []
                    if "active" in cls:
                        cls.remove("active")
                        a["class"] = cls
                    if a.get("aria-current"):
                        del a["aria-current"]
                    if hl == lang:
                        cur = a.get("class") or []
                        a["class"] = cur + ["active"]
                        a["aria-current"] = "true"
                    continue
                # Brand/logo always returns to the EN site home.
                if "nav-brand" in (a.get("class") or []):
                    a["href"] = "/"
                    continue
                a["href"] = rewrite_link(h, lang, rel)
            # rewrite shared-asset references (css/js/images) to root-absolute
            for tag, attr in (("link", "href"), ("script", "src"), ("img", "src")):
                for el in soup.find_all(tag):
                    v = el.get(attr)
                    if v:
                        el[attr] = fix_asset_ref(v, rel)
            inject_head(soup, lang, rel)
            inject_switcher(soup, rel, lang)
            out_rel = os.path.join(lang, rel)
            out_path = os.path.join(ROOT, out_rel)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            generated.append((lang, rel))
    # inject switcher into canonical EN source pages (safe string insert)
    for rel in SOURCES:
        inject_switcher_into_file(os.path.join(ROOT, rel), rel)
        inject_en_hreflang(os.path.join(ROOT, rel), rel)
    build_sitemap(generated)
    covered = len(tr)
    total = len(json.load(open(TM_FILE, encoding="utf-8"))["sources"])
    print(f"Built {len(generated)} language pages across {len(TARGETS)} languages.")
    print(f"Translation Memory entries filled: {covered}/{total}")
    missing = max(0, total - covered)
    if missing:
        print(f"({missing} strings still fall back to English -- fill i18n_translations.json and re-run build.)")

def build_sitemap(generated):
    out = ['<?xml version="1.0" encoding="UTF-8"?>']
    out.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
               'xmlns:xhtml="http://www.w3.org/1999/xhtml">')
    by_rel = {}
    for lang, rel in generated:
        by_rel.setdefault(rel, []).append(lang)
    for rel, langs in by_rel.items():
        # <lastmod>: prefer the source file's mtime (real change signal for
        # Google); fall back to today if the file can't be resolved.
        src = os.path.join(ROOT, rel)
        if os.path.isfile(src):
            lastmod = date.fromtimestamp(os.path.getmtime(src)).isoformat()
        else:
            lastmod = date.today().isoformat()
        out.append("  <url>")
        out.append(f"    <loc>{canonical_url('en', rel)}</loc>")
        out.append(f"    <lastmod>{lastmod}</lastmod>")
        out.append("    <changefreq>weekly</changefreq>")
        for l in langs:
            out.append(f'    <xhtml:link rel="alternate" hreflang="{l}" href="{canonical_url(l, rel)}"/>')
        out.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{canonical_url("en", rel)}"/>')
        out.append("  </url>")
    out.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "extract"
    if mode == "extract":
        extract()
    elif mode == "build":
        build()
    else:
        print("usage: i18n_build.py [extract|build]")
