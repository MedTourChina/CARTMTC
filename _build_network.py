# -*- coding: utf-8 -*-
"""Generate /network-news/ from _network_data.json.

The cart hub aggregates CAR-T and haematology coverage published by the other
MedTourChina hospital sites. Per the cross-site content convention we CITE and
LINK to those articles (external, target=_blank) and never copy their body
text here — the origin site keeps the canonical copy and the SEO weight.

The generated page is a normal static page, so it flows through the same
i18n_build extract/build pipeline as every other page.

usage: python _build_network.py
"""
import json
import os
import re
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "network-news")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

NAV = """<nav class="nav" role="navigation" aria-label="Main navigation">
  <div class="nav-inner">
    <a href="../" class="nav-brand" aria-label="CAR-T Therapy China x MedTourChina">
      <span class="logo-icon">T</span>
      <span class="brand-site">CAR-T&nbsp;Therapy&nbsp;China</span>
    </a>
    <button class="nav-toggle" aria-label="Toggle menu" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
    <div class="nav-links">
      <a href="https://www.medtourchina.net/" class="nav-back" target="_blank" rel="noopener" title="Back to MedTourChina">&larr;&nbsp;MedTourChina</a>
      <a href="../what-is-car-t/">What is CAR-T</a>
      <a href="../approved-drugs/">Drugs</a>
      <a href="../indications/">Indications</a>
      <a href="../hospitals/">Hospitals</a>
      <a href="../international-patients/">International Patients</a>
      <a href="../news/">News</a>
      <a href="../contact/" class="btn-nav">Book Consultation</a>
    </div>
  </div>
</nav>"""

LANG_SWITCH = """<nav class="lang-switch" aria-label="Language">
    <a href="/network-news/index.html" hreflang="en" class="active" aria-current="true">English</a>
    <a href="/fr/network-news/index.html" hreflang="fr">Français</a>
    <a href="/es/network-news/index.html" hreflang="es">Español</a>
    <a href="/ru/network-news/index.html" hreflang="ru">Русский</a>
    <a href="/ar/network-news/index.html" hreflang="ar">العربية</a>
    <a href="/vi/network-news/index.html" hreflang="vi">Tiếng Việt</a>
  </nav>"""

FOOTER = """<footer class="footer">
  <div class="container">
    <div class="footer-grid">
      <div>
        <h4>CAR-T Therapy China</h4>
        <p style="margin-bottom:12px;">MedTourChina's dedicated hub for CAR-T cell therapy in China.</p>
        <p>&#128222; +86 17742026990</p>
        <p>&#9993; info@healthtourchina.net</p>
      </div>
      <div>
        <h4>Learn</h4>
        <div class="footer-links">
          <a href="../what-is-car-t/">What is CAR-T</a>
          <a href="../how-it-works/">How It Works</a>
          <a href="../approved-drugs/">Approved Drugs</a>
          <a href="../indications/">Indications</a>
        </div>
      </div>
      <div>
        <h4>Patients</h4>
        <div class="footer-links">
          <a href="../hospitals/">Partner Hospitals</a>
          <a href="../international-patients/">International Patients</a>
          <a href="../resources/faq.html">FAQ</a>
          <a href="../news/">News</a>
        </div>
      </div>
      <div>
        <h4>Quick Links</h4>
        <div class="footer-links">
          <a href="https://www.medtourchina.net/" target="_blank" rel="noopener">MedTourChina</a>
          <a href="../network-news/">Network News</a>
          <a href="../contact/">Contact</a>
          <a href="https://wa.me/8617742026990" target="_blank" rel="noopener">WhatsApp</a>
        </div>
      </div>
    </div>
    <div class="footer-bottom"><p>&copy; 2026 MedTourChina &mdash; CAR-T Therapy China Partner Site. Educational content; not a substitute for professional medical advice.</p></div>
  </div>
</footer>"""

CHATWOOT = """<script src="/js/main.js"></script>

<script>
  (function (d, t) {
    var BASE_URL = "https://chat.healthtourchina.net";
    var g = d.createElement(t), s = d.getElementsByTagName(t)[0];
    g.src = BASE_URL + "/packs/js/sdk.js";
    g.defer = true; g.async = true;
    s.parentNode.insertBefore(g, s);
    g.onload = function () {
      window.chatwootSDK.run({
        websiteToken: "KR1QcN4h2Y6ogm8QbzLYyGRt",
        baseUrl: BASE_URL
      });
    };
  })(document, "script");
</script>"""


def fmt_date(iso):
    try:
        y, m, d = iso.split("-")
        return "%d %s %s" % (int(d), MONTHS[int(m) - 1], y)
    except Exception:
        return iso


def card(it):
    return """      <a class="net-card" href="%s" target="_blank" rel="noopener">
        <span class="net-tag">%s</span>
        <h3>%s</h3>
        <p>%s</p>
        <span class="net-meta">%s <span class="net-out" aria-hidden="true">&#8599;</span></span>
      </a>""" % (it["url"], it["tag"], it["title"], it["summary"], fmt_date(it["date"]))


# Four cards promoted on the news index. Chosen to cover the range of the
# network in one glance: a paediatric research result, a solid-tumour first,
# a long-term solid-tumour control, and a rescue strategy after CAR-T failure.
FEATURED = [
    "https://gobroad.medtourchina.net/resources/news/apbmt-2026-cd7-car-t-bridged-hsct-pediatric-t-all-2026.html",
    "https://jiahui.medtourchina.net/news/newzealand-josh-solid-tumor-car-t-discharge-jiahui.html",
    "https://gobroad.medtourchina.net/resources/news/cldn18.2-car-t-gastric-cancer-peritoneal-metastasis-48-month-survival-2026.html",
    "https://arion.medtourchina.net/resources/news/refractory-dlbcl-car-t-bispecific-antibody-mdt.html",
]

NEWS_INDEX = os.path.join(HERE, "news", "index.html")
T_START = "<!-- NETWORK:START -->"
T_END = "<!-- NETWORK:END -->"


def patch_news_index(all_items, total, groups):
    """Rewrite the teaser block inside news/index.html between the markers."""
    if not os.path.isfile(NEWS_INDEX):
        print("!! news/index.html not found, skipping teaser")
        return
    src = open(NEWS_INDEX, encoding="utf-8").read()
    if T_START not in src or T_END not in src:
        print("!! teaser markers missing in news/index.html, skipping")
        return
    picked = [i for u in FEATURED for i in all_items if i["url"] == u]
    block = """%s
<section class="section bg-alt">
  <div class="container">
    <div class="net-head">
      <h2>From Our Hospital Network</h2>
      <p class="net-blurb">The hospitals we work with publish their own CAR-T case reports, trial notices and research updates. Here are four of the latest, in their own words &mdash; %d articles in all, from %d centres.</p>
    </div>
    <div class="net-grid net-grid-2">
%s
    </div>
    <p style="margin-top:30px;"><a href="../network-news/" class="btn btn-primary btn-lg">Read all %d articles &#8594;</a></p>
  </div>
</section>
%s""" % (
        T_START,
        total,
        len(groups),
        "\n".join(card(i) for i in picked),
        total,
        T_END,
    )
    pre, rest = src.split(T_START, 1)
    _, post = rest.split(T_END, 1)
    open(NEWS_INDEX, "w", encoding="utf-8", newline="\n").write(pre + block + post)
    print("patched news/index.html teaser with %d cards" % len(picked))


def build():
    data = json.load(open(os.path.join(HERE, "_network_data.json"), encoding="utf-8"))
    groups = data["groups"]
    total = sum(len(g["items"]) for g in groups)

    blocks = []
    for g in groups:
        # avoid repeating the hospital name when the site name *is* the hospital
        # (ignoring a parenthetical parent-group suffix like "(Fosun Health)")
        norm = lambda s: re.sub(r"\(.*?\)", "", s).strip().lower()
        meta = g["city"]
        if norm(g["site"]) != norm(g["hospital"]):
            meta += " &middot; " + g["site"]
        blocks.append(
            """<section class="section bg-white" id="%s">
  <div class="container">
    <div class="net-head">
      <h2>%s</h2>
      <p class="net-city">%s</p>
      <p class="net-blurb">%s</p>
    </div>
    <div class="net-grid">
%s
    </div>
  </div>
</section>"""
            % (
                g["id"],
                g["hospital"],
                meta,
                g["blurb"],
                "\n".join(card(i) for i in g["items"]),
            )
        )

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CAR-T Across Our Hospital Network: %d Partner Stories &amp; Studies</title>
<meta name="description" content="CAR-T, lymphoma and transplant coverage published by MedTourChina partner hospitals across China — paediatric CD7 CAR-T, solid-tumour CT041, refractory DLBCL rescue and long-term survivor stories, each linked to the original article.">
<meta name="keywords" content="CAR-T China hospital network, CAR-T case reports China, pediatric CAR-T China, CT041 solid tumor, DLBCL CAR-T, lymphoma treatment China">
<link rel="canonical" href="https://cart.medtourchina.net/network-news/">
<link rel="icon" href="/assets/images/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/css/style.css">
<meta property="og:title" content="CAR-T Across Our Hospital Network">
<meta property="og:description" content="What our partner hospitals are publishing about CAR-T, lymphoma and transplant in China.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://cart.medtourchina.net/network-news/">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "CAR-T Across Our Hospital Network",
  "url": "https://cart.medtourchina.net/network-news/",
  "description": "CAR-T, lymphoma and transplant articles published by MedTourChina partner hospitals in China.",
  "isPartOf": { "@type": "WebSite", "name": "CAR-T Therapy China", "url": "https://cart.medtourchina.net/" }
}
</script>
</head>
<body>
%s

%s

<section class="page-hero">
  <div class="container">
    <nav class="breadcrumb" style="color: rgba(255,255,255,0.8);">
      <a href="../" style="color: rgba(255,255,255,0.8);">Home</a> &rsaquo;
      <a href="../news/" style="color: rgba(255,255,255,0.8);">News</a> &rsaquo; Network
    </nav>
    <h1>CAR-T Across Our Hospital Network</h1>
    <p>%d articles on CAR-T, lymphoma and stem-cell transplant, published by the hospitals we work with — and linked to the original.</p>
  </div>
</section>

<section class="section bg-alt">
  <div class="container">
    <div class="note-box">
      <p class="note-lead"><strong>How this page works.</strong></p>
      <p>Each card below links to an article published by that hospital on its own website. We translate the headline and summary into your language and send you to the original for the full text, the imaging and the clinician's own account. Nothing here is rewritten or republished, and no article on this page is a substitute for medical advice about your own case.</p>
    </div>
  </div>
</section>

%s

<section class="section bg-alt">
  <div class="container">
    <div class="cta-banner">
      <h2>Not Sure Which Centre Fits Your Case?</h2>
      <p>Tell us the diagnosis, the treatments already tried and the reports you have. We will match you to the hospitals actually running the relevant programme.</p>
      <div style="display:flex; gap:16px; justify-content:center; flex-wrap:wrap;">
        <a href="../contact/" class="btn btn-white btn-lg">Send Your Reports</a>
        <a href="../hospitals/" class="btn btn-outline btn-lg">See Partner Hospitals</a>
      </div>
    </div>
  </div>
</section>

%s

%s

</body>
</html>
""" % (
        total,
        LANG_SWITCH,
        NAV,
        total,
        "\n\n".join(blocks),
        FOOTER,
        CHATWOOT,
    )

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "index.html")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("wrote %s (%d groups, %d articles)" % (out, len(groups), total))

    all_items = [i for g in groups for i in g["items"]]
    patch_news_index(all_items, total, groups)
    return total, len(groups)


if __name__ == "__main__":
    build()
