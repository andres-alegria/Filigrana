// The title-derived `slug` front-matter field is NOT unique site-wide —
// recurring sections (editorial, un-sello-con-historia, el-sobresaliente-de-hoy)
// repeat across nearly every issue. Prefix with series+volume to guarantee a
// collision-free public URL while staying readable.
export function routeSlug(entry: { data: { series: number; volume: number; slug: string } }): string {
  return `s${entry.data.series}v${entry.data.volume}-${entry.data.slug}`;
}
