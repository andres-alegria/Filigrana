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
    const isImage = /^<img\b/.test(raw);
    if (looksLikeNewHeading || isImage) break;
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

// Images now live directly in the article's Markdown as plain
// ![caption](path) syntax — placed inline where they belong, or as a bare
// ![](path) block at the end for ones nobody's positioned yet (see
// pipeline/build_images.py). Astro's own Markdown rendering already turns
// those into <p><img alt="..." src="..."></p>; this just gives each one its
// final on-page shape:
//   - an image WITH alt text becomes a <figure> with that text as its
//     caption, exactly where it sits in the prose.
//   - a run of consecutive alt-less images (the "loose" block) is grouped
//     into a single gallery grid.
const IMG_P_RE = /<p><img src="([^"]*)" alt="([^"]*)"[^>]*>\s*<\/p>/g;

export function wrapImages(html: string): string {
  let out = '';
  let lastEnd = 0;
  let galleryBuf: string[] = [];

  const flushGallery = () => {
    if (galleryBuf.length) {
      out += `<div class="article-gallery">${galleryBuf.join('')}</div>`;
      galleryBuf = [];
    }
  };

  let m: RegExpExecArray | null;
  while ((m = IMG_P_RE.exec(html)) !== null) {
    const between = html.slice(lastEnd, m.index);
    // Prose between two loose images ends the run. Without this, a second
    // group further down the article merges into the first one's grid and the
    // text in between gets hoisted above it, silently reordering the article.
    if (between.trim()) flushGallery();
    out += between;
    const [, src, alt] = m;
    if (alt) {
      flushGallery();
      out += `<figure class="article-figure"><img src="${src}" alt="" loading="lazy" />`
        + `<figcaption>${alt}</figcaption></figure>`;
    } else {
      galleryBuf.push(`<img src="${src}" alt="" loading="lazy" />`);
    }
    lastEnd = IMG_P_RE.lastIndex;
  }
  flushGallery();
  out += html.slice(lastEnd);
  return out;
}

// First image in the (already-rendered) article body — used as the card
// listing's thumbnail. Works whether that image ended up captioned inline
// or in the loose end-of-article block; no separate manifest needed.
export function firstImageSrc(html: string): string | null {
  const m = /<img src="([^"]*)"/.exec(html);
  return m ? m[1] : null;
}
