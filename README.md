# CAR-T Therapy China — MedTourChina

> Vertical hub for **CAR-T cell therapy**: treatment methods, approved drugs, indications,
> and international patient routing to partner hospitals in China.
> Domain: `https://cart.medtourchina.net`

This is a **Phase 1 English source site** built with the `medtourchina-i18n-site` skill scaffold.
It is pure static HTML/CSS/JS, deployable to Cloudflare Pages with zero build step, and is
structured to be i18n-ready (Phase 2: fr/es/ru/ar/vi) and CMTA-aggregatable (Phase 3).

## Page Map

| Path | Purpose |
|------|---------|
| `/` | Homepage — what CAR-T is, how it works, drugs, indications, journey, hospitals |
| `/what-is-car-t/` | In-depth explainer: what CAR-T therapy is |
| `/how-it-works/` | How CAR-T works — the manufacturing & infusion process |
| `/approved-drugs/` | Approved CAR-T drugs (global + China / NMPA) comparison table |
| `/indications/` | Approved & emerging indications (leukemia, lymphoma, myeloma, solid tumors) |
| `/treatment-journey/` | Patient journey: apheresis → manufacturing → lymphodepletion → infusion → monitoring |
| `/hospitals/` | Partner hospitals in China offering CAR-T (routing) |
| `/international-patients/` | Services for international patients (remote consult, visa, insurance, accommodation) |
| `/news/` | CAR-T news, case studies & education articles |
| `/resources/faq.html` | FAQ (FAQPage JSON-LD) |
| `/contact/` | Chatwoot live chat + central contact line (Call/Email/WhatsApp/Visit) |

## Brand & Visual

- **Palette**: indigo `#4338CA` (primary) + magenta `#DB2777` (accent) — biotech / cell-therapy feel.
- **Central contact line** (group standard): phone `+86 17742026990`, email `info@healthtourchina.net`, WhatsApp `wa.me/8617742026990`.
- **Chatwoot**: the contact channel is the Chatwoot website widget, embedded site-wide (every page). Set each site's `website_token` in the SDK snippet (placeholder `REPLACE_WITH_CARTMTC_CHATWOOT_TOKEN`) before go-live. No backend or API key required; inquiries land in the Chatwoot inbox.

## Deploy (Cloudflare Pages)

1. Create repo `MedTourChina/CARTMTC`, push this folder.
2. Cloudflare Pages → Connect to Git → select repo.
3. Build settings: Framework `None`, Build command empty, Build output `/`.
4. (Optional) Custom domain `cart.medtourchina.net`.

## Phase 2 — i18n (fr/es/ru/ar/vi)

1. `python i18n_build.py extract` → `i18n_tm.json` + `i18n_translations.json`.
2. Append `css_base.css` into `css/style.css`.
3. Translate page-by-page, `python i18n_build.py build`.
4. Verify `/fr/`, `/ar/` (RTL) etc. `SITE_DOMAIN` is already set to `cart.medtourchina.net`.

## Notes

- All medical content is educational. High-sensitivity pages (drugs, dosing) should be
  reviewed by a clinician before publication. A machine-translation disclaimer is injected
  by `i18n_build.py` on every translated page.
- News articles were adapted from oncology / hematology / cell-therapy themes across other
  MedTourChina hospital repos (CONCORD, HYGEIA, JINGDU) and reframed for the CAR-T topic.
