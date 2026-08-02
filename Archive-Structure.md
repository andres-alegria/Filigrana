# Filigrana — Archive Structure

*How the 24 editions (1,740 images, ~130 feature articles) are organized so both specialists and general readers can find their way.*

---

## Principle: two paths, one destination

Readers have two mental models. Serve both; force neither.

- **Path A — by publication** (the philatelist): Serie → Volumen → Issue → Article.
- **Path B — by subject** (the general reader): Theme / Author / Year / Search → filtered list → Article.

Both converge on the **article page**, which links *up* to its parent issue and *sideways* to related articles through shared theme tags.

---

## The two axes

### Axis 1 — Publication hierarchy
```
Serie (6, 7, 8)
  └── Volumen (1–12)
        └── Issue   (cover, masthead, table of contents)
              └── Article
```
The issue page is a real destination: it shows the cover, the original contents, and links to every article in that issue. It preserves the magazine as an object, which matters to collectors and honors the publication.

### Axis 2 — Subject access
- **Themes (5)** — the recurring veins found in the survey:
  1. Historia postal y falsificaciones (postal history & forgeries)
  2. Historia a través del correo (history through the mail)
  3. Transporte y modernidad (transport & modernity)
  4. Intriga y escándalo (intrigue & scandal)
  5. Curiosidades (curiosities)
- **Author** — Edgardo Alegría Reichmann (primary), Humberto Prats, guest authors (Bill Welch, etc.)
- **Year / timeline** — issues carry dates; articles can be plotted chronologically.
- **Search** — full-text across all articles (Spanish; English where translated).
- **Feature type** — see metadata below; lets you collect all "Un Sello con Historia," all editorials, etc.

---

## Recurring feature types

Found in nearly every issue — each becomes a filterable collection:

- **Editorial** — the editor's opening (often topical: postal policy, the state of Honducor).
- **Investigación** — the deep research articles (the core scholarship).
- **Un Sello con Historia** — recurring short feature; bite-sized, ideal for young readers & social.
- **Buzón de Novedades** — new issues / philatelic news.
- **Apéndice / Catálogo** — the structured catalog sections in Series 6 (Colecciones, Acumulaciones, Tarjetas Postales, Aerogramas, Historia Postal).

---

## Metadata schema (every article)

This is the engine. Each article (a Markdown/MDX file) carries front-matter:

```yaml
title_es: "Cancelaciones falsas en la emisión provisional de 1877"
title_en: "False cancellations on Honduras' 1877 provisional issue"
slug: cancelaciones-falsas-1877
series: 8
volume: 5
issue_date: 2026-01
year_topic: 1877          # the historical year the article is about
author: "Edgardo Alegría Reichmann"
themes: [postal-history-forgeries]
feature_type: investigacion   # editorial | investigacion | sello-con-historia | novedades | apendice
image_count: 24
summary_es: "..."
summary_en: "..."
is_featured: true         # surfaces on homepage
has_exhibition: true      # an immersive version exists
has_audio: false          # NotebookLM companion exists
lang_available: [es, en]  # which languages this article exists in
```

Two date fields matter: `issue_date` (when published) vs `year_topic` (the history it covers) — they let you build *both* a "browse by issue" timeline and a "Honduran postal history" timeline.

---

## URL structure (Spanish-first, bilingual)

```
/es/                                  home
/es/archivo/                          archive landing (both paths)
/es/archivo/serie-8/                  series index
/es/archivo/serie-8/vol-5/            issue page
/es/archivo/serie-8/vol-5/cancelaciones-falsas-1877/   article
/es/temas/historia-postal/            theme listing
/es/autores/edgardo-alegria/          author listing
/es/buscar/                           search
/en/... (mirror for translated content)
```

---

## Page templates needed

1. **Archive landing** — the fork: choose Path A or Path B, plus search.
2. **Series index** — the volumes in a series, as cover thumbnails.
3. **Issue page** — cover, metadata, table of contents, article list.
4. **Article page** — the reading experience (serif headline, sans body, image gallery, perforated-edge framing), with up-links and related tags.
5. **Theme / Author / Search results** — filtered article lists (shared component).

---

## Why this serves the project goals

- **Young audience:** Path B (themes, curiosities, "Sello con Historia," search) is the friendly door — no philatelic knowledge required.
- **Scholars & collectors:** Path A preserves the publication structure they know.
- **Exhibitions:** `has_exhibition` / `has_audio` flags let any article point to its immersive version — the archive and the "wow" stay woven together.
- **Bilingual:** every record knows which languages it exists in, so the UI degrades gracefully when English isn't available yet.
- **Scales cleanly:** one consistent schema across 130+ articles; new issues drop in without rework.

---

## Decisions made

- **Granularity: one page per article.** Each issue splits into separate article pages, each with its own URL — better for search, social sharing, and featuring single stories. The issue page acts as the table of contents linking to them. *(Decided by Andrés.)*

## Open questions

1. **Theme names in English** — keep Spanish theme labels, or fully localize? (e.g. "Curiosidades" vs "Curiosities")
2. **Catalog sections (Apéndice)** — reproduce as content, or treat as reference/downloadable? They're more tabular than narrative.
3. **"Un Sello con Historia"** — promote to its own marquee section given how reader-friendly it is?
