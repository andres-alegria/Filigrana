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
import sys, os, re, zipfile, unicodedata, hashlib
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

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

# ------------------------------------------------- inline emphasis (runs)
# Word marks emphasis per run (<w:r>), not per paragraph. Flattening every
# <w:t> into one string loses it, and with it the distinctions the authors
# actually made: ship names, publication titles, Latin terms, and the
# vendor's own bold in an advert the author then calls charlatanería.

def _rpr_on(el):
    """A toggle property is on unless it carries an explicit off value."""
    if el is None:
        return False
    return el.get(W + 'val') not in ('0', 'false', 'off')

def _emphasize(text, bold, italic):
    """Wrap in Markdown markers, keeping whitespace outside them — ``* x *``
    is not emphasis in Markdown, ``*x*`` is."""
    marker = '***' if bold and italic else '**' if bold else '*' if italic else ''
    if not marker or not text.strip():
        return text
    lead = text[:len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    return f'{lead}{marker}{text.strip()}{marker}{trail}'

def character_styles(z):
    """styleId -> (bold, italic) for character styles, following basedOn.

    Emphasis is not always direct formatting: these documents lean on Word's
    built-in character styles ("Strong", "Emphasis"), where the run carries
    only an rStyle and the boldness lives in styles.xml."""
    try:
        st = ET.fromstring(z.read('word/styles.xml'))
    except KeyError:
        return {}
    raw = {}
    for s in st.iter(W + 'style'):
        if s.get(W + 'type') != 'character':
            continue
        rpr = s.find(W + 'rPr')
        based = s.find(W + 'basedOn')
        get = lambda tag: (_rpr_on(rpr.find(W + tag))
                           if rpr is not None and rpr.find(W + tag) is not None else None)
        raw[s.get(W + 'styleId')] = (get('b'), get('i'),
                                     based.get(W + 'val') if based is not None else None)

    def resolve(sid, seen=()):
        if sid not in raw or sid in seen:
            return False, False
        b, i, base = raw[sid]
        pb, pi = resolve(base, seen + (sid,)) if base else (False, False)
        return (pb if b is None else b), (pi if i is None else i)

    return {sid: resolve(sid) for sid in raw}

def para_segments(p, styles=None):
    """The paragraph as [text, bold, italic] runs, adjacent like-formatted runs
    already merged. Shared with the one-off apply_emphasis.py pass."""
    styles = styles or {}
    segs = []
    for r in p.iter(W + 'r'):
        t = ''.join(x.text or '' for x in r.iter(W + 't'))
        if not t:
            continue
        rpr = r.find(W + 'rPr')
        bold = ital = False
        if rpr is not None:
            rs = rpr.find(W + 'rStyle')
            if rs is not None:
                bold, ital = styles.get(rs.get(W + 'val'), (False, False))
            # b and i are toggle properties: used as *direct* formatting they
            # set the absolute state, so they override the character style.
            # These files are full of Strong runs carrying an explicit
            # b val="0" — 107 of them — which are not bold at all.
            if rpr.find(W + 'b') is not None:
                bold = _rpr_on(rpr.find(W + 'b'))
            if rpr.find(W + 'i') is not None:
                ital = _rpr_on(rpr.find(W + 'i'))
        # Word splits runs mid-word for reasons of its own (spell-check state,
        # rsid tracking); merge neighbours that share formatting so a single
        # phrase emits one pair of markers instead of several.
        if segs and segs[-1][1] == bold and segs[-1][2] == ital:
            segs[-1][0] += t
        else:
            segs.append([t, bold, ital])
    # Word often leaves the space between two emphasized words in its own
    # unformatted run, which would emit ``*Doctor* *Honoris Causa*``. Absorb a
    # whitespace-only run when the runs on either side agree, so the phrase
    # emits as one: ``*Doctor Honoris Causa*``.
    i = 1
    while i < len(segs) - 1:
        if (not segs[i][0].strip()
                and segs[i - 1][1:] == segs[i + 1][1:]
                and (segs[i - 1][1] or segs[i - 1][2])):
            segs[i - 1][0] += segs[i][0] + segs[i + 1][0]
            del segs[i:i + 2]
        else:
            i += 1
    return segs

def para_markdown(p, styles=None):
    """Paragraph text with Word's bold/italic runs carried over as Markdown."""
    return ''.join(_emphasize(*s) for s in para_segments(p, styles))

def strip_md(s):
    """Plain text of a Markdown string — for matching, keys and heuristics."""
    return re.sub(r'\*{1,3}([^*]*?)\*{1,3}', r'\1', s)

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

# Recurring-feature titles with a fixed canonical casing (override sentence
# case). El Sobresaliente de Hoy per Andrés's instruction.
CANONICAL = {'elsobresalientedehoy': 'El Sobresaliente de Hoy'}

# In the newer issues (S7V11, S7V12, S8V1–V5) the "El Sobresaliente de Hoy"
# heading is a title image, not text — so it can't be matched as a heading and
# its content was being absorbed by the previous article. The same banner
# graphic is reused across all 7 (md5 prefix below), so we use it as the
# heading anchor. Found by hashing every image and taking the one that recurs
# in exactly those issues, sitting right before the section's text.
SOBRESALIENTE_BANNER = '6335d5990e'

# Recurring administrative sections to drop entirely (not real articles).
# Matched on the exact normalized title, so real pieces that merely mention
# these words ("Los buzones de 1954", "Un buzón de 1877...") are kept, as are
# wrapped-title merges ("Un sello con historia buzón de novedades").
SKIP_TITLES = {'buzondenovedades', 'nuestronuevosocio', 'nuestrosnuevossocios',
               'nuestronuevossocios', 'bienvenidosnuestrosnuevossocios'}

# Recurring-feature names that get fused onto the end of a real title when the
# TOC wraps ("... UN SELLO CON HISTORIA BUZÓN DE NOVEDADES"). Peeled off as
# their own entries so the real article stays clean and the feature is handled
# on its own (dropped if in SKIP_TITLES, or kept as its own file).
FEATURE_PHRASES = ['buzon de novedades', 'un sello con historia',
                   'el sobresaliente de hoy', 'credo del filatelista',
                   'nuestros nuevos socios', 'nuestro nuevos socios',
                   'nuestro nuevo socio']

# Words a title should never end on: a title ending here is a wrapped line and
# continues into the next TOC entry ("...ENVIADA POR UN" + "HIJO DEL...").
DANGLE = {'de', 'del', 'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas',
          'y', 'e', 'o', 'en', 'a', 'al', 'con', 'para', 'por', 'su', 'sus',
          'que', 'sin'}

def split_features(title):
    """Peel any trailing recurring-feature names off a title.
    Returns (prefix, [feature_entries])."""
    words = title.split()
    norm = [strip_accents(w).lower().strip('.,;:¿?¡!') for w in words]
    suffixes = []
    changed = True
    while changed and words:
        changed = False
        for ph in FEATURE_PHRASES:
            pw = ph.split(); n = len(pw)
            if len(words) > n and norm[-n:] == pw:
                suffixes.insert(0, ' '.join(words[-n:]))
                words, norm = words[:-n], norm[:-n]; changed = True; break
    return ' '.join(words).strip(), suffixes

def merge_danglers(entries):
    """Join a title that ends on a dangling connector/article into the next
    entry (a wrapped TOC title split across two lines)."""
    out = []
    i = 0
    while i < len(entries):
        title, page = entries[i]
        while i + 1 < len(entries) and title.split() and \
                strip_accents(title.split()[-1]).lower().strip('.,;:') in DANGLE:
            title = title + ' ' + entries[i + 1][0]
            i += 1                               # absorb next, keep first page
        out.append((title, page)); i += 1
    return out

def apply_toc_corrections(entries, meta):
    split = []
    for t, p in entries:
        if norm_key(t) in SKIP_TITLES:           # whole title is a dropped
            split.append((t, p)); continue       # section — keep it intact
        pre, sufs = split_features(t)
        if pre:
            split.append((pre, p))
        for s in sufs:
            split.append((s, p))
    entries = merge_danglers(split)

    # per-issue manual corrections
    mc = MANUAL.get((meta['serie'], meta['volume']), {})
    drop = {norm_key(x) for x in mc.get('drop', set())}
    merge_prev = {norm_key(x) for x in mc.get('merge_prev', set())}
    out = []
    for t, p in entries:
        k = norm_key(t)
        if k in drop:
            continue
        if k in merge_prev and out:
            out[-1] = (out[-1][0] + ' ' + t, out[-1][1])   # fold into previous
            continue
        out.append((t, p))
    return out

# Per-issue manual corrections from Andrés's review (the corpus is fixed).
#   merge_prev : this TOC line is really the tail of the previous entry
#                (a wrapped title the auto-rules can't detect grammatically).
#   drop       : not a real article (e.g. a lone image with a TOC line).
#   anchor     : image-only heading — start the article at the block whose
#                text contains this phrase.
MANUAL = {
    (7, 10): {'merge_prev': {'en la capitania general de guatemala'}},
    (7, 12): {'drop': {'fallecio christian bostvironois'}},
    (8, 3):  {'anchor': {'el musico que si merecia un sello postal':
                         'carlos humberto daniel'}},
}

# Confirmed issue dates for issues whose cover date is image-only (not in the
# text). Andrés-confirmed; overrides extraction so a rebuild keeps them.
DATE_OVERRIDES = {
    (7, 7): '2021-06', (7, 11): '2023-06', (7, 12): '2023-12',
    (8, 1): '2024-06', (8, 2): '2024-12', (8, 3): '2025-06',
    (8, 4): '2025-08', (8, 5): '2026-01',
}

def build_propers(fulltext):
    """Corpus-driven proper-noun set: words that appear capitalized
    mid-sentence (not sentence-initial) more often than lowercased. Gives us
    the case signal the ALL-CAPS titles lack."""
    counts = {}
    tokens = re.findall(r"[^\W\d_]+|[.!?:;¡¿]", fulltext, re.UNICODE)
    sent_start = True
    for tok in tokens:
        if tok in '.!?:;¡¿':
            sent_start = tok in '.!?'
            continue
        if tok.isupper() and len(tok) > 1:      # acronym / heading word
            sent_start = False; continue
        low = tok.lower()
        d = counts.setdefault(low, [0, 0])       # [cap_mid, lower]
        if tok[0].isupper():
            if not sent_start:
                d[0] += 1
        else:
            d[1] += 1
        sent_start = False
    # Common adjectives that ride along inside org names ("Honduras
    # Filatélica", "Federación Filatélica") but are lowercase as plain words.
    stop = {'filatelica', 'filatelico', 'filatelia', 'postal', 'postales',
            'nacional', 'internacional', 'republica', 'federacion'}
    return {w for w, (cap, lo) in counts.items()
            if cap >= 2 and cap > lo and len(w) > 2
            and strip_accents(w) not in stop}

def sentence_case_es(s, propers):
    """Spanish sentence case: first word + proper nouns capitalized, the
    rest lowercase. Roman numerals stay upper."""
    key = norm_key(s)
    if key in CANONICAL:
        return CANONICAL[key]
    s = collapse_spacing(s).strip().rstrip('.').strip()
    parts, out, first = re.split(r'(\s+|[–—-])', s.lower()), [], True
    for p in parts:
        if not p.strip() or p in '–—-':
            out.append(p); continue
        if re.fullmatch(r'[ivxlcdm]+', p) and len(p) > 1:
            out.append(p.upper())
        elif first or p in propers:
            out.append(p[:1].upper() + p[1:])
        else:
            out.append(p)
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
    styles = character_styles(z)
    body = root.find(W + 'body')
    mhash = {}
    def img_hash(target):
        if target not in mhash:
            try:
                mhash[target] = hashlib.md5(z.read(target)).hexdigest()[:10]
            except KeyError:
                mhash[target] = None
        return mhash[target]
    blocks = []
    for p in body.iter(W + 'p'):
        text = ''.join(t.text or '' for t in p.iter(W + 't'))
        imgs = [rid2media[b.get(R + 'embed')] for b in p.iter(A + 'blip')
                if b.get(R + 'embed') in rid2media]
        s = text.strip()
        pagenum = int(s) if re.fullmatch(r'\d{1,3}', s) else None
        # 'text' stays plain — every heading match, TOC key and heuristic in
        # this file reads it. 'md' is the same paragraph with emphasis, and is
        # what actually gets written out.
        blocks.append({'text': text, 'md': para_markdown(p, styles), 'images': imgs,
                       'pagenum': pagenum, 'hashes': [img_hash(t) for t in imgs]})
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

def find_issue_date(z, cover_text):
    """The printed masthead date lives in the page header/footer (most
    reliable); else the cover (text above the TOC). We deliberately do NOT
    scan the article body — a date deep in a story is not the issue date."""
    hdr = []
    for n in z.namelist():
        if re.search(r'word/(header|footer)\d*\.xml', n):
            hdr.append(' '.join(t.text or ''
                       for t in ET.fromstring(z.read(n)).iter(W + 't')))
    d, raw = _first_date(' '.join(hdr))
    return (d, raw) if d else _first_date(cover_text)

# ---------------------------------------------------------------- TOC parse
SKIP_TOC = {'CONTENIDO', 'PAGINA', 'ARTICULO'}

def strip_leaders(s):
    """Drop dotted-leader runs ('DIRECTORIO ……… 2' style) and trailing dots."""
    s = re.sub(r'[.…]{2,}', ' ', s)
    return re.sub(r'\s{2,}', ' ', s).strip().rstrip('.').strip()

def is_title_line(s):
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.7

# Wrapped-title continuation signals. A line whose predecessor ends with a
# dangling connector (CONN_END: "...usados en las") continues it; likewise a
# line starting with CONN_START ("de/y..."). CONN_START deliberately excludes
# articles (el/la/un) since real titles routinely start with them.
CONN_END = {'de', 'del', 'la', 'el', 'los', 'las', 'y', 'e', 'o', 'en', 'a',
            'al', 'con', 'para', 'por', 'que', 'usados', 'usadas', 'usado'}
CONN_START = {'de', 'del', 'y', 'e'}

def _nospace(s):
    return re.sub(r'\s', '', strip_accents(collapse_spacing(s))).upper()

def toc_start_index(blocks):
    """First TOC block: anchored on DIRECTORIO, else a CONTENIDO/ARTÍCULO/
    PÁGINA header, else 0. Everything before it is the cover."""
    s = next((i for i, b in enumerate(blocks[:120])
              if norm_key(b['text']).startswith('directorio')), None)
    if s is None:
        s = next((i for i, b in enumerate(blocks[:120])
                  if _nospace(b['text']) in ('CONTENIDO', 'ARTICULO',
                                             'PAGINA')), 0)
    return s

def merge_to_count(titles, target):
    """Block layout: #titles must equal #pages. Merge wrapped continuation
    lines into their predecessor until the counts match — grammatical signal
    first, shortest-line fallback (never touching entries 0/1 = DIR/EDITORIAL)."""
    titles = list(titles)
    while len(titles) > target > 0:
        merged = False
        for i in range(1, len(titles)):
            pw = strip_accents(titles[i - 1].split()[-1]).lower()
            cw = strip_accents(titles[i].split()[0]).lower()
            if pw in CONN_END or cw in CONN_START:
                titles[i - 1] += ' ' + titles[i]; del titles[i]
                merged = True; break
        if not merged:
            i = min(range(2, len(titles)), key=lambda j: len(titles[j])) \
                if len(titles) > 2 else len(titles) - 1
            titles[i - 1] += ' ' + titles[i]; del titles[i]
    return titles

def parse_toc(blocks, meta):
    """Return ordered [(title, page|None)]. Handles both TOC layouts:
    Serie 8 = titles block then pages block; Serie 6/7 = interleaved
    title,page,title,page. Auto-detected."""
    # TOC region: anchor on DIRECTORIO (reliably the first TOC entry in every
    # issue; the DIRECTORIO body section comes much later) and end at the
    # masthead. This is robust to missing/garbled 'CONTENIDO/ARTÍCULO' headers.
    start_i = toc_start_index(blocks)
    end_i = next((i for i in range(start_i + 1, len(blocks))
                  if _nospace(blocks[i]['text']).startswith('FEDERACIONFILAT')),
                 len(blocks))

    seq = []                                     # ordered ('title'|'num', val)
    for b in blocks[start_i:end_i]:
        s = collapse_spacing(b['text']).strip()
        if not s:
            continue
        if _nospace(s) in SKIP_TOC:
            continue
        if b['pagenum'] is not None:
            seq.append(('num', b['pagenum'])); continue
        if is_title_line(s):
            seq.append(('title', strip_leaders(s)))
        elif seq and seq[-1][0] == 'title':      # mixed-case wrapped line
            seq[-1] = ('title', seq[-1][1] + ' ' + strip_leaders(s))

    types = [t for t, _ in seq]
    titles = [v for t, v in seq if t == 'title']
    nums = [v for t, v in seq if t == 'num']
    first_num = types.index('num') if 'num' in types else len(types)
    last_title = max((i for i, t in enumerate(types) if t == 'title'),
                     default=-1)

    entries = []
    if first_num < last_title:                   # interleaved (Serie 6/7)
        pending = []
        for t, v in seq:
            if t == 'title':
                pending.append(v)
            elif pending:                        # num closes the pending title
                entries.append((' '.join(pending), v)); pending = []
        entries += [(v, None) for v in pending]
    else:                                         # block (Serie 8)
        if len(nums) and len(titles) > len(nums):
            titles = merge_to_count(titles, len(nums))
        if len(nums) == len(titles) + 1 and \
           not norm_key(titles[0]).startswith('directorio'):
            entries = [('DIRECTORIO', nums[0])] + list(zip(titles, nums[1:]))
        else:
            entries = [(t, nums[i] if i < len(nums) else None)
                       for i, t in enumerate(titles)]
    return apply_toc_corrections(entries, meta)

# ---------------------------------------------------------------- segment
def find_body_start(blocks, entries):
    """Index where article body begins (first real heading after masthead)."""
    # locate the second occurrence of EDITORIAL (first is the TOC line)
    occ = [i for i, b in enumerate(blocks)
           if norm_key(b['text']) == 'editorial']
    return occ[1] if len(occ) > 1 else (occ[0] if occ else 0)

def _heading_score(title_key, block):
    """Similarity of a body block to a TOC title, if the block looks like a
    heading. 0 = not a heading / no match."""
    s = collapse_spacing(block['text'])
    if not is_title_line(s):
        return 0.0
    bk = norm_key(s)
    if not bk or len(bk) < 4:
        return 0.0
    if bk.startswith(title_key[:15]) or title_key.startswith(bk[:15]):
        return 0.95                              # strong prefix agreement
    return SequenceMatcher(None, title_key, bk).ratio()

def locate_headings(blocks, entries, start, meta):
    """For each TOC title, find its in-body heading, fuzzily (Serie 6/7 titles
    differ from their body headings by OCR/typos). Forward cursor keeps the
    matches in document order; first strong hit wins, else best decent hit."""
    anchors = {norm_key(k): v for k, v
              in MANUAL.get((meta['serie'], meta['volume']), {})
              .get('anchor', {}).items()}
    locs, cursor = [], start
    for title, page in entries:
        if feature_type(title) == 'directorio':
            locs.append(None); continue          # no body article; don't scan
        key = norm_key(title)
        best_i, best_s = None, 0.0
        for i in range(cursor, len(blocks)):
            sc = _heading_score(key, blocks[i])
            if sc >= 0.72:                        # strong -> take first in order
                best_i, best_s = i, sc; break
            if sc > best_s:
                best_i, best_s = i, sc
        # 0.70 cleanly separates real (typo'd) headings (>=0.86 in practice)
        # from spurious matches (<=0.6); image-only headings fall through to
        # a flagged stub.
        if best_i is not None and best_s >= 0.70:
            locs.append(best_i); cursor = best_i + 1
            continue
        # image-only "El Sobresaliente de Hoy": anchor on its banner image
        if norm_key(title) == 'elsobresalientedehoy':
            bj = next((j for j in range(cursor, len(blocks))
                       if SOBRESALIENTE_BANNER in blocks[j]['hashes']), None)
            if bj is not None:
                locs.append(bj); cursor = bj + 1; continue
        # manual anchor: image-only heading located by a body text phrase
        if norm_key(title) in anchors:
            phrase = strip_accents(anchors[norm_key(title)]).lower()
            aj = next((j for j in range(cursor, len(blocks))
                       if phrase in strip_accents(blocks[j]['text']).lower()),
                      None)
            if aj is not None:
                loc = aj - 1                      # include a byline just above
                for k in range(max(cursor, aj - 3), aj):
                    if strip_accents(blocks[k]['text']).lower().strip()\
                            .startswith('por '):
                        loc = k - 1; break
                locs.append(loc); cursor = aj; continue
        locs.append(None)
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
        # Emphasis-carrying version of the same paragraph. Every decision above
        # and below is made on the plain text; only what gets appended differs.
        # If the two ever disagree on wording, the plain text wins — a lost
        # italic is a blemish, dropped words are not.
        s_md = collapse_spacing(b.get('md') or s)
        if strip_md(s_md) != s:
            s_md = s
        # join hard-wrapped line into previous paragraph
        if paras and paras[-1] and not re.search(r'[.!?:»”"\)]\s*$', strip_md(paras[-1])) \
           and s[:1].islower():
            paras[-1] += ' ' + s_md
        else:
            paras.append(s_md)
    return paras, images, flags

BYLINE = re.compile(r'^\s*(?:por|texto de|escrito por)\s*[:\-]?\s*(.+)$', re.I)

def canonical_author(name):
    """Standardize the known recurring author names to one canonical form."""
    n = strip_accents(name).lower()
    if 'edgardo' in n and 'alegr' in n: return 'Edgardo Alegría Reichmann'
    if 'humberto' in n and 'prats' in n: return 'Humberto Prats G.'
    if 'balladares' in n: return 'Manuel Balladares'
    if 'welch' in n: return 'Bill Welch'
    return collapse_spacing(name).rstrip('.')

def detect_author(paras):
    """Return (author, flag, byline_index). byline_index is the paragraph to
    drop from the body once its name is lifted into the author field."""
    for i, p in enumerate(paras[:6]):
        # paragraphs carry Markdown emphasis now; the byline may arrive as
        # *Por Edgardo Alegría R.* and would not match with the markers in
        m = BYLINE.match(strip_md(p))
        if m and len(m.group(1)) < 60:
            return canonical_author(m.group(1)), False, i
    return "Edgardo Alegría Reichmann", True, None   # default -> flag

# Best-guess theme classifier (the 5-theme vocab). Always flagged
# `theme-guessed` so Andrés confirms/corrects — never treated as final.
THEME_KW = {
    'Historia postal y falsificaciones':
        ['falsific', 'falso', 'falsa', 'cancelacion', 'matasellos', 'seebeck',
         'thuin', 'emision', 'perforac', 'charnela', 'provisional',
         'sobrecarga', 'filigrana', 'timbre', 'fechador'],
    'Historia a través del correo':
        ['censo', 'independencia', 'presidente', 'guerra', 'colonial',
         'poblacion', 'republica', 'historia postal', 'genesis', 'biografia'],
    'Transporte y modernidad':
        ['ferrocarril', 'tren', 'avion', 'aereo', 'aeropostal', 'vapor',
         'barco', 'transporte', 'carretera', 'diligencia', 'mula', 'vuelo'],
    'Intriga y escándalo':
        ['escandalo', 'intriga', 'asesin', 'robo', 'fraude', 'conspir',
         'pesadilla', 'crimen', 'contrabando', 'pirata'],
    'Curiosidades':
        ['curiosidad', 'rareza', 'gema', 'insolito', 'singular', 'anecdota',
         'peculiar'],
}

def guess_theme(title, summary):
    hay = strip_accents((title + ' ' + summary).lower())
    best, score = None, 0
    for theme, kws in THEME_KW.items():
        s = sum(hay.count(k) for k in kws)
        if s > score:
            best, score = theme, s
    return best or 'Historia a través del correo'

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
                 ftype, paras, images, extra_flags, themes):
    slug = slugify(title)
    # the summary is plain metadata, not prose — emphasis markers don't belong
    summary = ' '.join(strip_md(' '.join(paras)).split()[:40]) if paras else ''
    review = []
    if author_flag: review.append('author-unconfirmed')
    if not paras: review.append('empty-body')
    if themes: review.append('theme-guessed')
    review += extra_flags
    themes_yaml = ('[' + ', '.join(yaml_str(t) for t in themes) + ']'
                   if themes else '[]')
    fm = [
        '---',
        f'title_es: {yaml_str(title)}',
        'title_en: ""',
        f'slug: {slug}',
        f'series: {meta["serie"]}',
        f'volume: {meta["volume"]}',
        f'issue_date: {meta.get("issue_date") or "\"\""}',
        f'author: {yaml_str(author)}',
        f'themes: {themes_yaml}   # GUESS — confirm/correct (5-theme vocab)',
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
    if meta['incompleta']:
        # The source file is incomplete (only a TOC + stray content); it does
        # not belong in the content set. Skip it — the .docx stays in Filatelia/.
        print(f"SKIPPED (incompleta): {meta['source_file']}")
        return
    z, blocks, fulltext = load_blocks(path)
    override = DATE_OVERRIDES.get((meta['serie'], meta['volume']))
    if override:
        meta['issue_date'], date_raw = override, override + ' (confirmado)'
    else:
        cover = ' '.join(collapse_spacing(b['text'])
                         for b in blocks[:toc_start_index(blocks)])
        meta['issue_date'], date_raw = find_issue_date(z, cover)
    date_flags = [] if meta['issue_date'] else ['date-missing']
    entries = parse_toc(blocks, meta)
    start = find_body_start(blocks, entries)
    locs = locate_headings(blocks, entries, start, meta)
    propers = build_propers(fulltext)

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
        clean_title = sentence_case_es(title, propers)
        if norm_key(clean_title) in SKIP_TITLES:
            continue                             # drop recurring admin section
        ftype = feature_type(title)
        page_start = page
        page_end = entries[i + 1][1] - 1 if i + 1 < len(entries) \
            and entries[i + 1][1] else None
        if page_end is not None and page_start:   # same-page split -> clamp
            page_end = max(page_end, page_start)
        extra = list(date_flags)
        if locs[i] is None:
            # heading absent from the text (usually an image-only section
            # divider). Emit a flagged stub rather than stealing the previous
            # article's range; the body stays with its true owner.
            extra.append('heading-image-only')
            slug, md = emit_article(meta, clean_title, page_start, page_end,
                                    "Edgardo Alegría Reichmann", False, ftype,
                                    [], [], extra, [])
            fname = f'{i:02d}-{slug}.md'
            with open(os.path.join(out_dir, fname), 'w') as f:
                f.write(md)
            written.append((fname, clean_title, 0, 0, extra))
            continue
        lo = locs[i]
        hi = next((locs[j] for j in range(i + 1, len(locs))
                   if locs[j] is not None), n)
        paras, images, _ = clean_body(blocks, lo + 1, hi, issue_title_keys)
        # drop a leading ALL-CAPS subtitle that just repeats part of the title
        if paras and paras[0].isupper() and \
           norm_key(paras[0]) in norm_key(clean_title):
            paras.pop(0)
        author, aflag, byidx = detect_author(paras)
        if byidx is not None:
            paras.pop(byidx)                    # lift byline into front-matter
        if ftype in ('editorial', 'sello-con-historia', 'sobresaliente',
                     'credo', 'novedades'):
            author, aflag = "Edgardo Alegría Reichmann", False
        summary_seed = strip_md(' '.join(paras[:2])) if paras else ''
        themes = [] if ftype in ('editorial', 'directorio') \
            else [guess_theme(clean_title, summary_seed)]
        slug, md = emit_article(meta, clean_title, page_start, page_end,
                                author, aflag, ftype, paras, images, extra,
                                themes)
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
        ct = sentence_case_es(title, propers)
        if norm_key(ct) in SKIP_TITLES:
            continue                             # dropped section: keep out of TOC
        toc_lines.append(
            f'| {ct} | {page or "?"} | [{i:02d}]({i:02d}-{slugify(ct)}.md) |')
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
