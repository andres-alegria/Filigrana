// Article bodies from the content pipeline open with "# {title}" — the same
// title the page already renders in its own <h1>. Strip that leading
// heading so it isn't shown twice.
export function stripLeadingTitle(html: string): string {
  return html.replace(/^\s*<h1[^>]*>.*?<\/h1>\s*/i, '');
}
