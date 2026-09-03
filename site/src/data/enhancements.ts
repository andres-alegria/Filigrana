// Per-article presentation choices that don't belong in the Markdown.
//
// The article bodies stay plain Markdown so they remain readable as text and
// survive a pipeline rebuild. Anything that is a *display* decision for one
// specific article is declared here instead, keyed by its route slug
// (see lib/routing.ts — `s<series>v<volume>-<slug>`).

/** A run of consecutive uncaptioned images normally renders as a grid
 *  (see lib/content.ts `wrapImages`). Listing a gallery here renders it as a
 *  coverflow slider instead: one card in focus, its neighbours receding to
 *  either side, looping endlessly.
 *
 *  `gallery` is the zero-based index of the image run within the article, so
 *  0 is the first group of loose images, 1 the second, and so on.
 *
 *  The caption is not repeated here: the slider adopts the paragraph
 *  immediately above it, which is where the print edition put it. */
export const SLIDER_GALLERIES: Record<string, number[]> = {
  // The seven gold replicas Italcambio struck — the centrepiece of the piece,
  // and a set that reads far better one stamp at a time than as a 7-up grid.
  's6v5-el-escandalo-de-los-sellos-de-oro': [0],
};

/** Long verbatim documents (a contract, a decree) that would otherwise push
 *  the article's argument several screens down. The blockquote is collapsed
 *  to an opening extract with a control to unfold the rest.
 *
 *  `blockquote` is the zero-based index of the *single-level* blockquote in
 *  the article; pull quotes (nested `> >`) are not counted. `label` is the
 *  wording on the control, so it can name the document being unfolded. */
export const COLLAPSED_QUOTES: Record<
  string,
  { blockquote: number; label: string; previewChars?: number }[]
> = {
  // The 1980 Italcambio contract: ~4,000 words of legal clauses that the
  // article then spends the rest of its length dismantling.
  's6v5-el-escandalo-de-los-sellos-de-oro': [
    { blockquote: 0, label: 'el contrato completo', previewChars: 300 },
  ],
};
