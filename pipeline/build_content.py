#!/usr/bin/env python3
"""
Filigrana content pipeline — docx -> clean per-article Markdown.

TOC-driven segmentation + mechanical/light copy-edit. Reads the magazine
.docx files (stdlib only, no external deps), splits each issue into its
articles using the table of contents as the source of truth, cleans the
extracted text, and writes one Markdown file per article plus an issue file.

Usage:
    python3 pipeline/build_content.py "Filatelia/(27) Vol. 1 - Serie 8.docx"

Images are extracted to content/_assets/<issue>/ (git-ignored, regenerable)
and only *flagged* per article for a later precise-matching pass. Anything
the pipeline is unsure about is marked with a `review:` flag in the file's
front-matter and a `⚠` note, so the human pass is a scan, not a re-read.
"""
import sys, os, re, zipfile, unicodedata
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MONTHS = ('enero febrero marzo abril mayo junio julio agosto septiembre '
          'octubre noviembre diciembre').split()

# Words kept lowercase inside a Spanish title (unless first word).
LOWER = set("de del la las el los y e o u en con a al por para un una unos unas "
            "que se su sus lo como sin sobre entre tras ante bajo".split())

# ---------------------------------------------------------------- text utils
def collapse_spacing(s):
    """'A R T ÍC U L O' -> 'ARTÍCULO'. Collapses runs of >=3 single chars."""
    s = re.sub(r'(?:\b\w\b ){2,}\b\w\b', lambda m: m.group(0).replace(' ', ''), s)
    return re.sub(r'[ \t]{2,}', ' ', s).strip()

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

def norm_key(s):
    return re.sub(r'[^a-z0-9]', '', strip_accents(collapse_spacing(s)).lower())

def title_case_es(s):
    s = collapse_spacing(s).strip().rstrip('.').strip()
    words, out, first = re.split(r'(\s+)', s.lower()), [], True
    for w in words:
        if not w.strip():
            out.append(w); continue
        if re.fullmatch(r'[ivxlcdm]+', w) or re.fullmatch(r'\d+[ivxlcdm]*', w):
            out.append(w.upper())
        elif not first and w in LOWER:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
        first = False
    return ''.join(out)

def slugify(s):
    s = strip_accents(collapse_spacing(s)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return re.sub(r'-{2,}', '-', s)[:60].strip('-')

# ---------------------------------------------------------------- docx load
def load_blocks(path):
    z = zipfile.ZipFile(path)
    rels = ET.fromstring(z.read('word/_rels/document.xml.rels'))
    rid2media = {r.get('Id'): 'word/' + r.get('Target').replace('../', '')
                 for r in rels if 'image' in r.get('Type', '')}
    root = ET.fromstring(z.read('word/document.xml'))
    body = root.find(W + 'body')
    blocks = []
    for p in body.iter(W + 'p'):
        text = ''.join(t.text or '' for t in p.iter(W + 't'))
        imgs = [rid2media[b.get(R + 'embed')] for b in p.iter(A + 'blip')
                if b.get(R + 'embed') in rid2media]
        s = text.strip()
        pagenum = int(s) if re.fullmatch(r'\d{1,3}', s) else None
        blocks.append({'text': text, 'images': imgs, 'pagenum': pagenum})
    fulltext = ' '.join(t.text or '' for t in root.iter(W + 't'))
    return z, blocks, fulltext

def parse_meta(path):
    b = os.path.basename(path)
    m = re.search(r'Vol\.\s*(\d+)\s*-\s*Serie\s*(\d+)', b)
    vol, serie = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    return {'serie': serie, 'volume': vol,
            'incompleta': 'incompleta' in b.lower(), 'source_file': b}

MONTH_NUM = {m: i for i, m in enumerate(MONTHS, 1)}
MONTH_NUM['setiembre'] = 9
DATE_RE = re.compile(r'(' + '|'.join(strip_accents(m) for m in MONTH_NUM)
                     + r')\D{0,10}(20\d{2})')

def _first_date(text):
    m = DATE_RE.search(strip_accents(text).lower())
    if m:
        return f"{m.group(2)}-{MONTH_NUM[m.group(1)]:02d}", m.group(0)
    return None, None

def find_issue_date(z, fulltext):
    """The printed masthead date lives in the page header/footer (most
    reliable); fall back to the cover textbox / body text."""
    hdr = []
    for n in z.namelist():
        if re.search(r'word/(header|footer)\d*\.xml', n):
            hdr.append(' '.join(t.text or ''
                       for t in ET.fromstring(z.read(n)).iter(W + 't')))
    d, raw = _first_date(' '.join(hdr))
    return (d, raw) if d else _first_date(fulltext)

# ---------------------------------------------------------------- TOC parse
SKIP_TOC = {'CONTENIDO', 'PAGINA', 'ARTICULO'}

def parse_toc(blocks):
    """Return ordered [(title, page|None)] including DIRECTORIO/EDITORIAL."""
    titles, pages, started = [], [], False
    for blk in blocks[:60]:
        s = collapse_spacing(blk['text']).strip()
        if not s:
            continue
        up = strip_accents(s).upper().rstrip('.')
        if up == 'CONTENIDO':
            started = True; continue
        if blk['pagenum'] is not None:
            pages.append(blk['pagenum']); continue
        if up.startswith('FEDERACION FILATELICA'):
            break
        if pages:
            break
        if up in SKIP_TOC or up == 'PÁGINA':
            continue
        letters = [c for c in s if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
            titles.append(s); started = True
        elif started and titles:
            titles[-1] += ' ' + s               # wrapped title continuation
    # Align: drop leading page belonging to DIRECTORIO if counts differ by 1
    entries = []
    if len(pages) == len(titles) + 1:
        # first title is usually EDITORIAL; first page belongs to DIRECTORIO
        entries.append(('DIRECTORIO', pages[0]))
        for t, p in zip(titles, pages[1:]):
            entries.append((t, p))
    else:
        for i, t in enumerate(titles):
            entries.append((t, pages[i] if i < len(pages) else None))
    return entries

# ---------------------------------------------------------------- segment
def find_body_start(blocks, entries):
    """Index where article body begins (first real heading after masthead)."""
    # locate the second occurrence of EDITORIAL (first is the TOC line)
    occ = [i for i, b in enumerate(blocks)
           if norm_key(b['text']) == 'editorial']
    return occ[1] if len(occ) > 1 else (occ[0] if occ else 0)

def locate_headings(blocks, entries, start):
    """For each entry title, find its heading index in body >= running cursor."""
    locs, cursor = [], start
    for title, page in entries:
        key = norm_key(title)[:22]
        found = None
        for i in range(cursor, len(blocks)):
            bk = norm_key(blocks[i]['text'])
            if bk and (bk.startswith(key) or key.startswith(bk[:22]) and len(bk) > 6):
                # avoid matching a tiny fragment
                if len(bk) >= min(6, len(key)):
                    found = i; break
        locs.append(found)
        if found is not None:
            cursor = found + 1
    return locs

# ---------------------------------------------------------------- copy-edit
RUNNING = re.compile(r'^(honduras filatelica|volumen\s+\d+|serie\s+\d+)', re.I)

def clean_body(blocks, lo, hi, issue_title_keys):
    """Turn a block range into cleaned Markdown paragraphs + image list."""
    paras, images, flags = [], [], []
    for b in blocks[lo:hi]:
        images.extend(b['images'])
        if b['pagenum'] is not None:
            continue                                   # drop page markers
        s = collapse_spacing(b['text'])
        if not s:
            continue
        low = strip_accents(s).lower()
        if RUNNING.match(low) and len(s) < 40:
            continue                                   # running header/footer
        if norm_key(s) in issue_title_keys and len(s) < 60:
            continue                                   # repeated article title
        # join hard-wrapped line into previous paragraph
        if paras and paras[-1] and not re.search(r'[.!?:»”"\)]\s*$', paras[-1]) \
           and s[:1].islower():
            paras[-1] += ' ' + s
        else:
            paras.append(s)
    return paras, images, flags

BYLINE = re.compile(r'^\s*(?:por|texto de|escrito por)\s*[:\-]?\s*(.+)$', re.I)

def detect_author(paras):
    """Return (author, flag, byline_index). byline_index is the paragraph to
    drop from the body once its name is lifted into the author field."""
    for i, p in enumerate(paras[:6]):
        m = BYLINE.match(p)
        if m and len(m.group(1)) < 60:
            return collapse_spacing(m.group(1)).rstrip('.'), False, i
    return "Edgardo Alegría Reichmann", True, None   # default -> flag

def feature_type(title):
    k = norm_key(title)
    if k.startswith('editorial'): return 'editorial'
    if k.startswith('unselloconhistoria'): return 'sello-con-historia'
    if 'novedades' in k or 'nuevasemisiones' in k: return 'novedades'
    if k.startswith('elsobresaliente'): return 'sobresaliente'
    if 'credo' in k: return 'credo'
    if k.startswith('directorio'): return 'directorio'
    return 'investigacion'

# ---------------------------------------------------------------- emit
def yaml_str(s):
    return '"' + s.replace('"', '\\"') + '"'

def emit_article(meta, title, page_start, page_end, author, author_flag,
                 ftype, paras, images, extra_flags):
    slug = slugify(title)
    summary = ' '.join(' '.join(paras).split()[:40]) if paras else ''
    review = []
    if author_flag: review.append('author-unconfirmed')
    if not paras: review.append('empty-body')
    review += extra_flags
    fm = [
        '---',
        f'title_es: {yaml_str(title)}',
        'title_en: ""',
        f'slug: {slug}',
        f'series: {meta["serie"]}',
        f'volume: {meta["volume"]}',
        f'issue_date: {meta.get("issue_date") or "\"\""}',
        f'author: {yaml_str(author)}',
        'themes: []            # EDITORIAL DECISION — assign from the 5-theme vocab',
        f'feature_type: {ftype}',
        f'page_start: {page_start if page_start else "null"}',
        f'page_end: {page_end if page_end else "null"}',
        f'image_count: {len(images)}   # flagged; precise article-image match is a later pass',
        f'summary_es: {yaml_str(summary)}',
        'is_featured: false     # EDITORIAL DECISION',
        'has_exhibition: false  # EDITORIAL DECISION',
        'has_audio: false       # EDITORIAL DECISION',
        'lang_available: [es]',
        f'review: [{", ".join(review)}]' if review else 'review: []',
        '---',
        '',
        f'# {title}',
        '',
    ]
    body = '\n\n'.join(paras) if paras else '_(sin cuerpo extraído — revisar)_'
    imgblock = ''
    if images:
        imgblock = ('\n\n---\n\n'
                    '<!-- IMÁGENES (extraídas, sin emparejar aún) '
                    f'{len(images)} en este artículo:\n'
                    + '\n'.join('  - ' + os.path.basename(i) for i in images)
                    + '\n-->\n')
    return slug, '\n'.join(fm) + body + imgblock + '\n'

# ---------------------------------------------------------------- driver
def main(path):
    meta = parse_meta(path)
    z, blocks, fulltext = load_blocks(path)
    meta['issue_date'], date_raw = find_issue_date(z, fulltext)
    entries = parse_toc(blocks)
    start = find_body_start(blocks, entries)
    locs = locate_headings(blocks, entries, start)

    out_dir = os.path.join(ROOT, 'content',
                           f'serie-{meta["serie"]}',
                           f'vol-{meta["volume"]:02d}')
    os.makedirs(out_dir, exist_ok=True)
    assets_dir = os.path.join(ROOT, 'content', '_assets',
                              f's{meta["serie"]}v{meta["volume"]:02d}')
    os.makedirs(assets_dir, exist_ok=True)

    issue_title_keys = {norm_key(t) for t, _ in entries}

    # boundaries: next found heading (or end)
    n = len(blocks)
    written = []
    for i, (title, page) in enumerate(entries):
        if feature_type(title) == 'directorio':
            continue
        clean_title = title_case_es(title)
        ftype = feature_type(title)
        page_start = page
        page_end = entries[i + 1][1] - 1 if i + 1 < len(entries) \
            and entries[i + 1][1] else None
        extra = []
        if locs[i] is None:
            # heading absent from the text (usually an image-only section
            # divider). Emit a flagged stub rather than stealing the previous
            # article's range; the body stays with its true owner.
            extra.append('heading-image-only')
            slug, md = emit_article(meta, clean_title, page_start, page_end,
                                    "Edgardo Alegría Reichmann", False, ftype,
                                    [], [], extra)
            fname = f'{i:02d}-{slug}.md'
            with open(os.path.join(out_dir, fname), 'w') as f:
                f.write(md)
            written.append((fname, clean_title, 0, 0, extra))
            continue
        lo = locs[i]
        hi = next((locs[j] for j in range(i + 1, len(locs))
                   if locs[j] is not None), n)
        paras, images, _ = clean_body(blocks, lo + 1, hi, issue_title_keys)
        author, aflag, byidx = detect_author(paras)
        if byidx is not None:
            paras.pop(byidx)                    # lift byline into front-matter
        if ftype in ('editorial', 'sello-con-historia', 'sobresaliente',
                     'credo', 'novedades'):
            author, aflag = "Edgardo Alegría Reichmann", False
        slug, md = emit_article(meta, clean_title, page_start, page_end,
                                author, aflag, ftype, paras, images, extra)
        fname = f'{i:02d}-{slug}.md'
        with open(os.path.join(out_dir, fname), 'w') as f:
            f.write(md)
        written.append((fname, clean_title, len(paras), len(images), extra))

    media = [nm for nm in z.namelist() if nm.startswith('word/media/')]

    # issue-level file: the magazine as an object (cover, date, contents)
    toc_lines = []
    for i, (title, page) in enumerate(entries):
        if feature_type(title) == 'directorio':
            toc_lines.append(f'| Directorio | {page} | — |')
            continue
        toc_lines.append(
            f'| {title_case_es(title)} | {page or "?"} | '
            f'[{i:02d}]({i:02d}-{slugify(title_case_es(title))}.md) |')
    issue_md = '\n'.join([
        '---',
        f'series: {meta["serie"]}',
        f'volume: {meta["volume"]}',
        f'issue_date: {meta.get("issue_date") or chr(34)*2}',
        f'source_file: {yaml_str(meta["source_file"])}',
        f'incompleta: {str(meta["incompleta"]).lower()}',
        f'article_count: {len(written)}',
        f'image_count: {len(media)}',
        '---', '',
        f'# Honduras Filatélica — Serie {meta["serie"]}, Volumen {meta["volume"]}',
        '', f'*{date_raw or "fecha por confirmar"}*', '',
        '## Contenido', '',
        '| Artículo | Pág. | Archivo |', '| --- | ---: | --- |',
        *toc_lines, '',
    ])
    with open(os.path.join(out_dir, '_issue.md'), 'w') as f:
        f.write(issue_md)

    # extract all media (flagged, regenerable)
    for m in media:
        with open(os.path.join(assets_dir, os.path.basename(m)), 'wb') as f:
            f.write(z.read(m))

    # report
    print(f"Issue: Serie {meta['serie']} Vol {meta['volume']}"
          f"  date={meta['issue_date']}  (raw: {date_raw})")
    print(f"Output: {os.path.relpath(out_dir, ROOT)}/  "
          f"({len(media)} images -> {os.path.relpath(assets_dir, ROOT)}/)\n")
    print(f"{'file':<46}{'paras':>6}{'imgs':>5}  flags")
    print('-' * 78)
    for fn, t, np_, ni, fl in written:
        print(f"{fn:<46}{np_:>6}{ni:>5}  {','.join(fl)}")

if __name__ == '__main__':
    main(sys.argv[1])
