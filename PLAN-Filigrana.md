# Filigrana — Site Plan

*Digital home for* **Honduras Filatélica** *— the magazine of the Federación Filatélica de la República de Honduras, edited by Edgardo Alegría Reichmann. Honduran and world history, told through stamps and the postal record.*

---

## 1. Concept

**Name:** Filigrana — the watermark hidden inside a stamp's paper: the secret mark that proves what's authentic, revealed only when held to the light. A fitting metaphor for a site that surfaces the hidden histories inside Honduras's postal record.

**Mission:** Turn 60 years of philatelic scholarship into a living, bilingual, visually striking archive that reaches young Hondurans — not a dusty catalog, but stamps as doorways into history.

**Three things at once:**
1. **The Archive** — the 24 magazine editions, readable and searchable.
2. **The Exhibitions** — curated, experimental digital showcases of collections (the "wow").
3. **The Blog / Journal** — ongoing articles, in the magazine's voice, for a modern audience.

**Decisions locked in (from our conversation):**
- Static site (fast, secure, ~free hosting, ideal for an image-heavy archive)
- Spanish-first, with English for key/featured content
- You (technical-ish) maintain it
- Lead with the experimental exhibitions as the centerpiece
- Domain: **filigrana.hn** (register later; build first)

---

## 2. What's in the source material

24 editions across **Series 6, 7, and 8** (Vol. 1–12 each, some gaps). Mixed `.doc` (older) and `.docx` (newer). Each issue is image-rich (60–110+ embedded images: stamps, covers, postmarks, maps, photos).

Typical issue structure (observed):
- **Editorial** (e.g. "Un Desafío Monumental")
- **Research articles** — technical philately *and* history:
  - "Cancelaciones falsas en la emisión provisional de 1877"
  - "Matasellos y sellos fechadores usados en las emisiones Seebeck"
  - "Gemas de la Mosquitia"
  - "La presencia de William Walker en Centroamérica"
- **Recurring features** — "Credo del Filatelista," practical guides ("Retirando charnelas de manera segura")
- **Guest authors** (e.g. Bill Welch) alongside Edgardo Alegría Reichmann

This gives a natural content taxonomy: **by series/volume**, **by theme** (postal history, forgeries, Seebeck issues, biography, Honduran history), and **by author**.

---

## 3. Information architecture (sitemap)

```
Home  (the "light through paper" landing — featured exhibition + latest articles)
│
├── Exhibiciones / Exhibitions        ← the centerpiece
│     ├── [Featured experimental exhibition]
│     └── Gallery of collections (maps, photos, stamp sets)
│
├── Revista / Archive
│     ├── By series (6, 7, 8) → volumes → issue reader
│     └── Search & filter (theme, author, year)
│
├── Artículos / Journal (blog)
│     └── Individual articles (re-formatted from issues + new posts)
│
├── Sobre / About
│     ├── The Federación, the editor, the magazine's history
│     └── Contact
│
└── [EN / ES] language switch (global)
```

---

## 4. Tech stack (proposed)

Static-site generator optimized for content + bilingual + images:

- **Astro** (recommended) — excellent for content-heavy, image-heavy sites; ships almost no JavaScript by default (fast on mobile, important for young HN audience on phones); built-in i18n for ES/EN; supports "islands" of interactivity for the experimental exhibition pieces. *Alternative: Eleventy (simpler) or Hugo (fastest builds).*
- **Markdown/MDX** for articles — clean, version-controllable, you can edit in any text editor.
- **Hosting:** Netlify or Cloudflare Pages — free tier, global CDN, automatic HTTPS, deploy-on-push. Point filigrana.hn at it via DNS when ready.
- **Images:** processed/optimized at build (WebP, responsive sizes) so 100+ images per issue stay fast.

Why static fits: no server to hack or patch, near-zero cost, blazing fast, and an archive doesn't need a database.

---

## 5. Bilingual approach (Spanish-first)

- Spanish is the canonical content; English added for the homepage, exhibition intros, About, and selected flagship articles.
- URL structure: `/es/...` (default) and `/en/...`.
- A clear language toggle in the header. Pages without an English version gracefully fall back to Spanish with a small note.
- I can draft English translations of featured pieces as we go.

---

## 6. Content pipeline (the real work)

The 24 `.doc/.docx` files need to become clean web content. Proposed automated pipeline:

1. **Convert** each issue to clean HTML/Markdown + extract all images (I can script this with LibreOffice + python-docx).
2. **Split** each issue into individual articles (using the ALL-CAPS title pattern + bylines we identified).
3. **Tag** each article: series, volume, year, theme, author.
4. **Optimize** images and link them to the right articles.
5. **Review** — you check a sample for fidelity; we fix the conversion rules; then batch the rest.

This is the heaviest lift but highly automatable. We'd do one issue end-to-end as a template, get it right, then run the rest.

---

## 7. The "wow" — experimental digital exhibitions

This is the centerpiece and where the modern, young-adult feel lives. Ideas:

- **Interactive stamp viewer** — zoom into a stamp to reveal its watermark, perforations, forged vs. genuine cancellations (ties directly to the "Filigrana" concept and the 1877-forgeries article).
- **Map-based storytelling** — e.g. "Walker in Central America" or "Gemas de la Mosquitia" plotted on a map, with stamps/covers appearing along the route.
- **Timeline scrollytelling** — scroll through Honduran postal history; stamps animate in at key dates.
- **Collection showcases** — full-screen, gallery-grade presentation of his collections.

Start with **one** flagship exhibition built end-to-end as the signature piece.

---

## 8. Ambitious: NotebookLM podcasts over visuals

The vision: short AI-generated audio (NotebookLM) overlaid on graphic material — maps, stamps, photos from the issues.

Realistic path:
- NotebookLM has no public API, so audio is **generated manually** in NotebookLM (feed it an article → get an audio overview) and **downloaded**.
- On the site, pair that audio with a **synchronized visual** — e.g. an audio player alongside a slideshow/Ken-Burns pan over the relevant maps and stamps, or captioned chapters.
- This is very doable as a static feature once we have the audio files. We'd template it so each exhibition can optionally carry a "Listen" companion.

Flagged as Phase 3 — it depends on the core + first exhibition existing.

---

## 9. Roadmap

**Phase 0 — Foundation (no domain needed)**
- Scaffold Astro project, design system (typography, the "light/watermark" visual identity), bilingual plumbing, deploy a placeholder to Netlify.

**Phase 1 — Core archive**
- Build the content pipeline; convert 1 issue as the template; get the issue-reader + archive browse/search working; convert remaining issues.

**Phase 2 — The flagship exhibition**
- Design + build one signature experimental exhibition (e.g. the interactive 1877 forgeries viewer or a map-story).

**Phase 3 — Journal + polish + podcasts**
- Blog/journal section, English translations of featured content, NotebookLM audio companions, accessibility + performance pass.

**Phase 4 — Launch**
- Register filigrana.hn (or do earlier), point DNS, go live.

---

## 10. Open questions for you

1. **Visual identity** — do you have any colors, logo, or look in mind (or from the magazine), or should I propose a fresh modern identity built around the "filigrana / light through paper" idea?
2. **Which flagship exhibition** excites you most as the first centerpiece?
3. **Rights** — are all 24 issues and the collection images cleared to publish openly online? (Worth confirming before public launch.)
4. **Scope of English** — which specific things must be bilingual at launch vs. later?
