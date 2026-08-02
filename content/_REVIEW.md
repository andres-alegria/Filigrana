# Content — review guide

This folder holds the **auto-generated first draft** of the 24 issues, split
into one Markdown file per article, produced by `pipeline/build_content.py`
from the source `.docx` files. Copy-editing was **mechanical + light**:
extraction artifacts fixed, titles normalized, boilerplate stripped — the
authors' wording and historical spellings preserved.

Nothing here is final. Everything the pipeline was unsure about is marked with
a `review:` flag in each file's front-matter, so your pass is a **scan of the
flagged items**, not a re-read of everything.

## Layout

```
content/
  serie-<6|7|8>/vol-NN/
    _issue.md                 # the issue: date + table of contents
    NN-<slug>.md              # one article, ordered by the TOC
  _index.csv                  # master index — every article, all metadata
  _assets/sXvNN/              # extracted images (git-ignored, regenerable)
```

`_index.csv` is the fastest way to review: open it, filter the `review`
column, and work through the flags. It is regenerated from the files by
`pipeline/build_index.py` — so **edit the `.md` files, then re-run the index**,
don't edit the CSV by hand.

## The review flags

| Flag | Meaning | What to do |
| --- | --- | --- |
| `theme-guessed` | Theme is a keyword-based **guess** from the 5-theme vocab | Confirm or correct `themes:` (this is your editorial call) |
| `date-missing` | No issue date in the text/header — newer covers carry the date only as an image | Fill `issue_date:` (YYYY-MM); you know the schedule |
| `author-unconfirmed` | No byline found; defaulted to the editor | Confirm/replace `author:` |
| `heading-image-only` | The section heading is an image, so no text was extracted (recurring features like *El Sobresaliente de Hoy*) | Usually fine as a stub; add content if wanted |
| `empty-body` | No body text extracted | Expected for the *incompleta* issue (S6V7) and image-only stubs; elsewhere check the source |

## Known things to check

- **S6V7 (Vol. 7 Serie 6)** was **excluded** — its source `.docx` is
  incomplete (only a table of contents + one section). The pipeline skips any
  file marked *incompleta*; the source stays in `Filatelia/`. Re-run on a
  complete version to add it back.
- **Recurring admin sections removed:** *Buzón de novedades* and *Nuestro(s)
  nuevo(s) socio(s)* are dropped everywhere (pipeline `SKIP_TITLES`). Real
  articles that merely mention the words are kept (*Los buzones de 1954*,
  *Un buzón de 1877…*, *Nos visitó nuestro socio Christian B*). **Still to
  decide:** three wrapped-title merges keep a "Buzón de novedades" tail fused
  to a real feature — split or trim as you like:
  `serie-7/vol-10/09-un-sello-con-historia-buzon-de-novedades.md`,
  `serie-8/vol-02/09-primera-muestra-filatelica-buzon-de-novedades.md`,
  `serie-8/vol-03/10-un-sello-con-historia-buzon-de-novedades.md`.
- **Issue dates** whose cover carries the date only as an image are set from
  `DATE_OVERRIDES` in `build_content.py` (Andrés-confirmed), so a rebuild
  keeps them. A full rebuild does re-add the `theme-guessed` /
  `author-unconfirmed` flags (they're generation-time guesses); the committed
  files are the reviewed version with those cleared.
- **Wrapped TOC titles** occasionally split one article in two (e.g. S8V3
  *"Emerge tarjeta postal…"* + *"…hijo del general Morazán"*). Flagged
  `empty-body` — merge the two files if so.
- **Titles keep the TOC spelling** (per decision), so a few carry the original
  typos (e.g. *"titulo de distincio"*); the in-body heading is often the
  correct spelling if you want to fix them.

## Not done in this phase (by design)

English titles/translations, precise image→article matching and captions, and
the final theme tagging — all deferred to later passes.
