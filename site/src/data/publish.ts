// The site's publishing schedule — deliberately separate from the content
// pipeline's output (content/**/*.md), so re-running the pipeline never
// touches what's live, when it went live, or what's still in review.
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
// `draft: true` keeps an article off the public site entirely. It is then
// reachable only from /revision/, the proof-reading index, which exists
// solely in `npm run dev` and is never emitted by `npm run build`.
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
//
// `cover` overrides the card image. By default a card shows the article's
// FIRST body image, which is usually right — but not when the best cover
// sits halfway down the piece, or is a picture made for the card that has
// no place in the text. Point it at a path under site/public/
// (e.g. "/img/covers/morazan.webp") and the body is left alone.

export interface PublishEntry {
  id: string;
  publishDate: string; // YYYY-MM-DD
  /** Keeps the article off the public site — no card, no page, no route.
   *  Drafts show up only in the dev-only /revision/ proof-reading index. */
  draft?: boolean;
  teaser?: string;
  type?: 'articulo' | 'coleccion';
  coverAlign?: 'center' | 'top';
  /** Card image, overriding the article's first body image. A path under
   *  site/public/ — see the note above. */
  cover?: string;
  /** Pins an article to the front of the home feed: 1 shows first, 2 second,
   *  and so on. Everything without a rank follows, newest first. Kept separate
   *  from `publishDate` so featuring something never rewrites when it went
   *  online — the date on the card stays true. */
  featured?: number;
}

export const publishQueue: PublishEntry[] = [
  {
    id: 'serie-8/vol-01/02-gemas-de-la-mosquitia',
    draft: true,
    publishDate: '2026-09-03',
    teaser: 'Durante 207 años, una dinastía de reyes zambo-misquitos gobernó un reino olvidado en el litoral hondureño, entre piratas, contrabando y guerra fronteriza con España. Cinco piezas filatélicas, únicas en el mundo, son el rastro que sobrevive de aquel reino perdido.',
  },
  {
    id: 'serie-8/vol-03/05-el-musico-que-si-merecia-un-sello-postal',
    featured: 3,
    publishDate: '2026-09-02',
    coverAlign: 'top',
    teaser: 'Tocó bajo la batuta de Toscanini, heredó acceso a un Stradivarius y deslumbró a la crítica en Milán, París y Berlín. Carlos Humberto Cano fue, sin discusión, el mejor violinista de Centroamérica — y aun así nunca recibió el sello postal que su historia merecía.',
  },
  {
    id: 'serie-6/vol-05/02-el-escandalo-de-los-sellos-de-oro',
    featured: 1,
    publishDate: '2026-09-03',
    teaser: 'En algún momento de su historia, Honduras emitió sellos de oro de 23 quilates para conmemorar sus tesoros arqueológicos — y lo que debía ser un orgullo filatélico terminó en el mayor escándalo del gremio en el país. Su autor fue testigo y participante directo de los hechos, y aquí los cuenta por primera vez en detalle.',
  },
  {
    id: 'serie-6/vol-09/04-dos-buques-nombrados-en-honor-a-francisco-morazan',
    cover: '/img/covers/morazan.webp',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'El SS Morazán zarpó por primera vez en 1908, con casi 3,000 toneladas de acero — y en 1922 pasó a manos de la naviera que un año después se convertiría en compañía hondureña. Dos buques, un mismo nombre, y la historia marítima que conectó a Honduras con el mundo.',
  },
  {
    id: 'serie-6/vol-10/02-las-islas-del-cisne-recuperan-su-soberania',
    cover: '/img/covers/swan.webp',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'Aisladas en el Caribe occidental, a 17°24\' de latitud norte, las Islas del Cisne vivieron una historia territorial que terminó por resolverse en sellos y matasellos. El relato filatélico de cómo Honduras recuperó su soberanía sobre este archipiélago remoto.',
  },
  {
    id: 'serie-6/vol-12/02-marcas-de-agua-en-la-prefilatelia-de-honduras',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'Antes de que existiera el primer sello postal hondureño, en 1865, el papel mismo llevaba su propia firma secreta: la marca de agua. Un recorrido por las filigranas ocultas en la correspondencia colonial y republicana de Honduras — el mismo lenguaje visual que le da nombre a este sitio.',
  },
  {
    id: 'serie-7/vol-01/02-paso-albert-einstein-por-amapala',
    featured: 2,
    publishDate: '2026-09-03',
    teaser: 'Durante años circuló el rumor de que Albert Einstein, el físico más famoso del siglo XX, había pisado suelo hondureño en el puerto de Amapala. ¿Mito urbano o hecho real? El expediente filatélico detrás de la leyenda.',
  },
  {
    id: 'serie-7/vol-04/02-el-sueno-del-ferrocarril-interoceanico-trasciende-a-la-filat',
    draft: true,
    publishDate: '2026-09-04',
    coverAlign: 'top',
    teaser: 'En 1979, un lote de cinco cartas paquebote enviadas entre 1857 y 1858 se subastó por 1,100 dólares, calificado como una rareza jamás vista. Detrás de esas cartas, el sueño — nunca cumplido del todo — de un ferrocarril que uniera los dos océanos a través de Honduras.',
  },
  {
    id: 'serie-7/vol-06/03-el-puente-ulua-en-una-estampilla',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'En 1915, el gobierno de Francisco Bertrand inauguró un puente entonces majestuoso sobre el río Ulúa, pieza clave del ferrocarril transoceánico que buscaba unir dos costas. ¿Llegó esa hazaña de ingeniería a inmortalizarse en una estampilla?',
  },
  {
    id: 'serie-7/vol-07/02-la-presencia-de-william-walker-en-centro-america',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'Desde la escuela escuchamos la historia de William Walker y su intento de anexar Centroamérica a Estados Unidos — pero pocas veces de cerca, a través del rastro que dejó en el correo de la región. Un repaso a la presencia filatélica de uno de los personajes más controvertidos del istmo.',
  },
  {
    id: 'serie-7/vol-08/02-el-sistema-postal-en-nicaragua-durante-el-gobierno-espurio-d',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'Segunda entrega de la serie sobre William Walker: esta vez, el enfoque es el sistema postal que operó en Nicaragua bajo su gobierno espurio — cartas, matasellos y marcas que sobrevivieron a uno de los capítulos más turbulentos de la historia centroamericana.',
  },
  {
    id: 'serie-7/vol-11/03-marcas-de-control-sobre-los-timbres-de-honduras',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'Cuando el robo o la pérdida de especies postales se volvía un problema, las autoridades hondureñas respondían con marcas de control — un sistema que también alcanzó a los timbres fiscales. Un catálogo visual de esas marcas, poco documentadas hasta ahora.',
  },
  {
    id: 'serie-8/vol-01/03-raoul-charles-de-thuin-una-verdadera-pesadilla-filatelica',
    draft: true,
    publishDate: '2026-09-04',
    coverAlign: 'top',
    teaser: 'Nacido en Bruselas en 1890, Raoul Charles de Thuin se convirtió en uno de los falsificadores de sellos postales más prolíficos de su época, operando desde Mérida, Yucatán. Su legado sigue siendo, hasta hoy, una pesadilla para los filatelistas serios.',
  },
  {
    id: 'serie-8/vol-01/04-italo-ghizzoni-en-la-genesis-de-la-filatelia-hondurena',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'Todo parte de un sobre precioso, fechado el 30 de mayo de 1896 y enviado a Madrid, que documenta los primerísimos días de vida de la Litografía Nacional de Honduras. Detrás de esa pieza, la huella de Italo Ghizzoni en el nacimiento mismo de la filatelia hondureña.',
  },
  {
    id: 'serie-8/vol-02/02-filatelia-de-la-republica-mayor-de-centro-america',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'A finales de 1894, el Dr. Policarpo Bonilla fue electo presidente de Honduras con un sueño mayor: la unión de Centroamérica en una sola república. Este es el rastro filatélico de ese proyecto político — breve, ambicioso, y hoy casi olvidado.',
  },
  {
    id: 'serie-8/vol-02/03-tres-conceptos-ship-steamship-y-steamboat',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'SHIP, STEAMSHIP, STEAMBOAT: tres palabras que aparecen una y otra vez en la filatelia marítima clásica, y que confunden incluso a coleccionistas experimentados. Una guía clara para distinguir un concepto postal de otro.',
  },
  {
    id: 'serie-8/vol-04/02-censura-postal-civil-al-correo-de-honduras-durante-la-segund',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'Durante la Segunda Guerra Mundial, tanto los Aliados como el Eje censuraron el correo civil a gran escala — el Reino Unido llegó a emplear a unos 10,000 censores. Honduras no fue la excepción: este es el rastro que dejó esa vigilancia en su correo.',
  },
  {
    id: 'serie-8/vol-04/03-la-locomotora-su-reimpresion-de-1902',
    draft: true,
    publishDate: '2026-09-04',
    teaser: 'A inicios del último año de vigencia de la célebre emisión de La Locomotora, los valores más bajos —y más demandados— empezaron a escasear. La historia de la reimpresión de 1902 que evitó el colapso del sistema postal.',
  },
  // TODO(Andrés): add the rest of your launch slate here.
  // Pick `id` values (the `file` column, .md optional) from content/_index.csv.
  // { id: 'serie-8/vol-01/06-un-sello-con-historia', publishDate: '2026-09-11' },
];

function normalizeId(id: string): string {
  return id.replace(/\.md$/, '');
}

/** Public visibility: a draft is never public, whatever its date says.
 *  Every public listing and route funnels through this one predicate, so
 *  flipping `draft` is all it takes to pull an article off the site. */
export function isPublished(entry: PublishEntry, today = new Date()): boolean {
  return !entry.draft && entry.publishDate <= today.toISOString().slice(0, 10);
}

/** The proof-reading set — everything held back from the public site. */
export function isDraft(entry: PublishEntry): boolean {
  return !!entry.draft;
}

export function findEntry(articles: { id: string }[], p: PublishEntry) {
  const wanted = normalizeId(p.id);
  return articles.find((a) => a.id === wanted);
}
