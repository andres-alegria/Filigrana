# Filigrana

*Digital home for **Honduras Filatélica** — the magazine of the Federación Filatélica de la República de Honduras, edited by Edgardo Alegría Reichmann. Honduran and world history, told through stamps and the postal record.*

**Filigrana** is the watermark hidden inside a stamp's paper — the secret mark that proves what's authentic, revealed only when held to the light. A fitting name for a site that surfaces the hidden histories inside Honduras's postal record.

> **Status:** Planning & design stage. This repo currently holds the project plan, the archive's information architecture, and the visual moodboard produced in Claude Design. The Astro site has not been scaffolded yet.

---

## What's here

| File | What it is |
| --- | --- |
| [`PLAN-Filigrana.md`](PLAN-Filigrana.md) | The full site plan — concept, sitemap, tech stack, bilingual approach, content pipeline, roadmap, open questions. |
| [`Archive-Structure.md`](Archive-Structure.md) | How the 24 editions (~1,740 images, ~130 articles) are organized: the two-axis IA, metadata schema, URL structure, page templates. |
| [`Filigrana-Moodboard.html`](Filigrana-Moodboard.html) | Self-contained visual identity moodboard (typography, palette, textures). Open in a browser. |
| `Filigrana-Indice-Contenido.xlsx` | Working index of the magazine contents (series / volume / articles). |

## Not tracked in git (kept local)

Excluded via [`.gitignore`](.gitignore) — they're the raw source for the content pipeline, too large for git, and publication rights aren't cleared yet:

- `Filatelia/` — the 24 magazine editions (`.doc` / `.docx`, ~840 MB).
- `_moodboard_src/` — original images that fed the moodboard.

## Planned stack

Static site (no backend): **Astro** + Markdown/MDX, bilingual (Spanish-first, `/es` · `/en`), images optimized at build. Hosting on Netlify or Cloudflare Pages; domain `filigrana.hn` at launch. See [`PLAN-Filigrana.md`](PLAN-Filigrana.md) §4 for rationale.

## Roadmap (short form)

1. **Foundation** — scaffold Astro, visual identity, bilingual plumbing, placeholder deploy.
2. **Core archive** — content pipeline (docx → clean MD + images), issue reader, browse & search.
3. **Flagship exhibition** — one signature interactive piece (e.g. the 1877-forgeries stamp viewer or a map-story).
4. **Journal + polish + audio companions**, then launch.

---

*Private repo while in development. Publication rights for the magazine content are being confirmed before anything goes public.*
