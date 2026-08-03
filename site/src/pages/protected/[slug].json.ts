import { getCollection } from 'astro:content';
import { publishQueue, isPublished, findEntry } from '../../data/publish';
import { routeSlug } from '../../lib/routing';
import { stripLeadingTitle, formatBibliography, wrapImages } from '../../lib/content';

export const prerender = true;

export async function getStaticPaths() {
  const articles = await getCollection('articles');
  return publishQueue
    .filter((p) => p.locked && isPublished(p))
    .map((p) => {
      const entry = findEntry(articles, p);
      return entry ? { params: { slug: routeSlug(entry) }, props: { entry } } : null;
    })
    .filter((x) => x !== null);
}

export async function GET({ props }: { props: { entry: any } }) {
  const { entry } = props;
  const html = wrapImages(formatBibliography(stripLeadingTitle(entry.rendered?.html ?? '')));
  return new Response(JSON.stringify({ html }), {
    headers: { 'Content-Type': 'application/json' },
  });
}
