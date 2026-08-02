// Article bodies from the content pipeline open with "# {title}" — the same
// title the page already renders in its own <h1>. Strip that leading
// heading so it isn't shown twice.
export function stripLeadingTitle(html: string): string {
  return html.replace(/^\s*<h1[^>]*>.*?<\/h1>\s*/i, '');
}

// Turn a trailing "Bibliografía" / "Bibliografía:" / "Bibliografía consultada:"
// paragraph into a proper subheading, and the reference paragraphs that follow
// into a bulleted list. Stops early at an ALL-CAPS short paragraph (reads as a
// new section header, e.g. a stray recurring-feature title glued on by the
// content pipeline), so unrelated trailing content isn't swept into the list.
export function formatBibliography(html: string): string {
  const labelRe = /<p>\s*Bibliograf[íi]a(?:\s+consultada)?\s*:?\s*(.*?)<\/p>/i;
  const m = labelRe.exec(html);
  if (!m) return html;

  const before = html.slice(0, m.index);
  const inlineFirst = m[1]?.trim();
  const afterHtml = html.slice(m.index + m[0].length);

  const pRe = /<p>([\s\S]*?)<\/p>/g;
  const items: string[] = inlineFirst ? [inlineFirst] : [];
  let consumedEnd = 0;
  let match: RegExpExecArray | null;
  while ((match = pRe.exec(afterHtml)) !== null) {
    const raw = match[1].trim();
    if (!raw) { consumedEnd = pRe.lastIndex; continue; }
    const plain = raw.replace(/<[^>]+>/g, '');
    const letters = plain.replace(/[^A-Za-zÀ-ÿ]/g, '');
    const looksLikeNewHeading = letters.length > 3 && letters === letters.toUpperCase()
      && plain.trim().split(/\s+/).length <= 6;
    if (looksLikeNewHeading) break;
    items.push(raw);
    consumedEnd = pRe.lastIndex;
  }
  const rest = afterHtml.slice(consumedEnd);

  const heading = '<h2 class="bib-heading">Bibliografía</h2>';
  const list = items.length
    ? `<ul class="bibliography">${items.map((i) => `<li>${i}</li>`).join('')}</ul>`
    : '';
  return before + heading + list + rest;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export interface ArticleImages {
  captions: { text: string; file: string | null }[];
  gallery: string[];
  cover: string | null;
}

// Turns each "(N) ..." caption paragraph the image pipeline recognized into
// an inline <figure> with its matched photo (see pipeline/build_images.py
// for how the match is made — document proximity, not list order). Walks
// the SAME paragraphs in the SAME order the pipeline found them in, so the
// zip with `images.captions` never misaligns. A caption the pipeline
// couldn't match to a free image is left as plain text, untouched. Any
// image the pipeline couldn't attach to a caption is appended as an
// unlabeled gallery at the end.
export function injectFigures(html: string, cid: string, images?: ArticleImages | null): string {
  if (!images || (!images.captions.length && !images.gallery.length)) return html;

  let i = 0;
  let out = html.replace(/<p>\(\d+\)\.?\s[\s\S]*?<\/p>/g, (match) => {
    const c = images.captions[i++];
    if (!c || !c.file) return match;
    const src = `/img/${cid}/${c.file}`;
    return `<figure class="article-figure"><img src="${src}" alt="" loading="lazy" />`
      + `<figcaption>${escapeHtml(c.text)}</figcaption></figure>`;
  });

  if (images.gallery.length) {
    const items = images.gallery
      .map((f) => `<img src="/img/${cid}/${f}" alt="" loading="lazy" />`)
      .join('');
    out += `<div class="article-gallery">${items}</div>`;
  }
  return out;
}
