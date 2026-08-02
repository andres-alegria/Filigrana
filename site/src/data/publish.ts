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

export interface PublishEntry {
  id: string;
  publishDate: string; // YYYY-MM-DD
  locked?: boolean;
}

export const publishQueue: PublishEntry[] = [
  { id: 'serie-8/vol-01/02-gemas-de-la-mosquitia', publishDate: '2026-08-02', locked: true },
  { id: 'serie-8/vol-03/05-el-musico-que-si-merecia-un-sello-postal', publishDate: '2026-08-02' },
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
