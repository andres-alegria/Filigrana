// The site's publishing schedule — deliberately separate from the content
// pipeline's output (content/**/*.md), so re-running the pipeline never
// touches what's live, when it went live, or what's locked.
//
// `id` is the article's unique content path — copy the `file` column from
// content/_index.csv, with or without the trailing ".md"
// (e.g. "serie-8/vol-01/02-gemas-de-la-mosquitia"). The title-based `slug`
// front-matter field is NOT unique site-wide (recurring sections like
// "editorial" repeat in every issue), so it can't be used as the key here.
//
// `publishDate` controls both ordering and visibility — an entry with a
// future date stays hidden until that date, so you can schedule several
// weeks of the "one every week or two" cadence in advance.
// `locked: true` gates the article behind the shared password.
//
// `teaser` is an optional hand-written, punchy card summary — write one
// whenever you add an article; if omitted, the card falls back to the
// pipeline's auto-extracted `summary_es` (the article's first ~40 words,
// which reads more mechanically). This is the "systematic" hook for future
// articles: the mechanism already exists, filling it in per-article is the
// only remaining manual step.
//
// `type` labels the card's green overlay tag ("ARTÍCULO" / "COLECCIÓN").
// Everything published so far is a plain article; omit it and it defaults
// to 'articulo'. Set it to 'coleccion' once the first collection is ready.
//
// `coverAlign` controls how the card thumbnail crops its cover image
// (object-position) — 'center' (default) or 'top', for a cover portrait
// whose subject sits near the top of the frame.

export interface PublishEntry {
  id: string;
  publishDate: string; // YYYY-MM-DD
  locked?: boolean;
  teaser?: string;
  type?: 'articulo' | 'coleccion';
  coverAlign?: 'center' | 'top';
}

export const publishQueue: PublishEntry[] = [
  {
    id: 'serie-8/vol-01/02-gemas-de-la-mosquitia',
    publishDate: '2026-08-02',
    locked: true,
    teaser: 'Durante 207 años, una dinastía de reyes zambo-misquitos gobernó un reino olvidado en el litoral hondureño, entre piratas, contrabando y guerra fronteriza con España. Cinco piezas filatélicas, únicas en el mundo, son el rastro que sobrevive de aquel reino perdido.',
  },
  {
    id: 'serie-8/vol-03/05-el-musico-que-si-merecia-un-sello-postal',
    publishDate: '2026-08-02',
    coverAlign: 'top',
    teaser: 'Tocó bajo la batuta de Toscanini, heredó un Stradivarius y deslumbró a la crítica en Milán, París y Berlín. Carlos Humberto Cano fue, sin discusión, el mejor violinista de Centroamérica — y aun así nunca recibió el sello postal que su historia merecía.',
  },
  // TODO(Andrés): add the rest of your launch slate here.
  // Pick `id` values (the `file` column, .md optional) from content/_index.csv.
  // { id: 'serie-8/vol-01/06-un-sello-con-historia', publishDate: '2026-08-11', locked: true },
];

function normalizeId(id: string): string {
  return id.replace(/\.md$/, '');
}

export function isPublished(entry: PublishEntry, today = new Date()): boolean {
  return entry.publishDate <= today.toISOString().slice(0, 10);
}

export function findEntry(articles: { id: string }[], p: PublishEntry) {
  const wanted = normalizeId(p.id);
  return articles.find((a) => a.id === wanted);
}
