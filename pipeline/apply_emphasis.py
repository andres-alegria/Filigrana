#!/usr/bin/env python3
"""
One-off: put Word's italics back into the already-reviewed articles.

build_content.py used to flatten every run in a paragraph into one string,
which dropped every italic the authors set — ship names, publication titles,
Latin terms. That is fixed in the converter now, but re-running the converter
is not an option: content/ holds hand-reviewed files (blockquotes, rejoined
page breaks, reordered sections, promoted headings) that a rebuild would
overwrite.

So this works the other way round. Instead of regenerating an article and
trying to re-apply the edits, it reads the *phrases* Word set in italic and
re-marks those phrases wherever they still appear in the committed Markdown.
Nothing else about the file is touched, so the review work survives.

Phrase-level rather than paragraph-level on purpose: paragraphs have been
merged, split, moved and quoted since generation, so they no longer align with
the source. Individual phrases still do.

    python3 pipeline/apply_emphasis.py            # dry run, prints a report
    python3 pipeline/apply_emphasis.py --apply    # write the changes
"""
import sys, os, re, glob, zipfile, importlib.util
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# reuse the converter's run-merging, so both agree on what a phrase even is
spec = importlib.util.spec_from_file_location('bc', os.path.join(HERE, 'build_content.py'))
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)
W = bc.W

# ---------------------------------------------------------------- tuning
MIN_LEN = 3       # "SS" alone is noise; a real title or name is longer
MAX_LEN = 45
MAX_WORDS = 6

# The important filter is not length, it is position. Word uses italic for two
# quite different jobs in these magazines:
#
#   whole paragraph  — an image caption, a letter's dateline, a transcribed
#                      document. These already have a home in the Markdown as
#                      figure captions or blockquotes, both of which render
#                      italic on their own. Re-marking them inline would be
#                      redundant at best and wrong at worst.
#   part of a line   — a ship name, a newspaper, a Latin term. This is the
#                      inline emphasis that was lost, and the only thing we
#                      want back.
#
# So a run only counts when its own paragraph also holds real un-italic text.

# A phrase is only re-marked when it still reads as a discrete thing: it must
# not be glued to surrounding word characters, and must hold a letter.
LETTER = re.compile(r'[^\W\d_]', re.UNICODE)


def docx_for(series, volume):
    """The source .docx for an issue, by its '(NN) Vol. X - Serie Y' name."""
    for p in glob.glob(os.path.join(ROOT, 'Filatelia', '*.docx')):
        if os.path.basename(p).startswith('~$') or 'incompleta' in p.lower():
            continue
        m = re.search(r'Vol\.\s*(\d+)\s*-\s*Serie\s*(\d+)', os.path.basename(p))
        if m and int(m.group(1)) == volume and int(m.group(2)) == series:
            return p
    return None


def italic_phrases(docx):
    """Every distinct phrase Word set in italic in this issue."""
    root = ET.fromstring(zipfile.ZipFile(docx).read('word/document.xml'))
    found = {}
    for p in root.iter(W + 'p'):
        segs = bc.para_segments(p)
        # does this paragraph carry substantive text that is NOT italic?
        plain_here = sum(len(t.strip()) for t, _b, i in segs if not i)
        if plain_here < 12:
            continue                      # wholly-italic: caption or document
        for text, _bold, ital in segs:
            if not ital:
                continue
            t = re.sub(r'\s+', ' ', text).strip().strip('“”"\'()[[]].,;:')
            if not (MIN_LEN <= len(t) <= MAX_LEN):
                continue
            if len(t.split()) > MAX_WORDS or not LETTER.search(t):
                continue
            # Trimming punctuation can leave a bracket without its partner
            # ("Postal Commemorative Society (PCS"), which would italicize an
            # unbalanced span. Skip rather than guess where it should close.
            if t.count('(') != t.count(')'):
                continue
            found[t] = found.get(t, 0) + 1
    # longest first, so "SS Capitán Polonio" is marked before "Capitán Polonio"
    return dict(sorted(found.items(), key=lambda kv: len(kv[0]), reverse=True))


def safe_phrases(body, phrases):
    """Drop phrases we cannot place with confidence.

    A word Word italicized once as a ship's name may also be an ordinary place
    name the article uses throughout — "Granada" is both a vessel and the city
    Walker burned, and appears 27 times in that piece. Since the source tells
    us only *how often* a phrase was italicized, not *where*, a phrase that
    turns up in the prose more often than Word italicized it is ambiguous, and
    marking every occurrence would be wrong. Those are left alone.
    """
    keep, skipped = {}, []
    for ph, times in phrases.items():
        hits = len(re.findall(r'(?<![\w*])' + re.escape(ph) + r'(?![\w*])', body))
        if hits and hits <= times:
            keep[ph] = times
        elif hits:
            skipped.append((ph, hits, times))
    return keep, skipped


def protected_spans(line):
    """Ranges that must not be touched: links, images, inline code, and any
    emphasis already present."""
    spans = []
    for rx in (r'!\[[^\]]*\]\([^)]*\)', r'\[[^\]]*\]\([^)]*\)', r'`[^`]*`',
               r'\*{1,3}[^*]+\*{1,3}', r'https?://\S+'):
        spans += [m.span() for m in re.finditer(rx, line)]
    return spans


def mark_line(line, phrases):
    """Italicize each phrase where it appears as a standalone run of words."""
    # Headings, image lines and tables are not prose. Blockquotes are skipped
    # too: verbatim quotations and pull quotes are already set in italic by
    # the stylesheet, so marking inside them adds asterisks that show up as
    # upright text against the surrounding italic.
    if not line.strip() or line.lstrip().startswith(('#', '!', '|', '>')):
        return line, 0
    # Some articles already use a bare asterisk in the prose — a footnote
    # marker after a word, or a run of them standing in for redacted text in a
    # transcribed letter. Markdown pairs asterisks greedily, so adding a mark
    # to such a line can pair with the existing one and italicize the span
    # between them instead. Those lines are left alone; there are 91 in the
    # corpus and they are better handled by eye.
    if '*' in line:
        return line, 0
    n = 0
    for ph in phrases:
        pat = re.compile(r'(?<![\w*])' + re.escape(ph) + r'(?![\w*])')
        out, pos, guard = [], 0, 0
        while True:
            m = pat.search(line, pos)
            if not m or guard > 40:
                break
            guard += 1
            if any(s <= m.start() < e for s, e in protected_spans(line)):
                pos = m.end()
                continue
            line = line[:m.start()] + '*' + m.group(0) + '*' + line[m.end():]
            pos = m.end() + 2
            n += 1
    return line, n


def body_lines(text):
    """(frontmatter, body) — front matter is metadata and stays untouched."""
    m = re.match(r'^---\n.*?\n---\n', text, re.S)
    return (text[:m.end()], text[m.end():]) if m else ('', text)


def main(apply_changes):
    total_files = total_marks = 0
    report, ambiguous = [], []
    for md in sorted(glob.glob(os.path.join(ROOT, 'content', 'serie-*', 'vol-*', '*.md'))):
        raw = open(md, encoding='utf-8').read()
        head, body = body_lines(raw)
        m_s = re.search(r'^series:\s*(\d+)', head, re.M)
        m_v = re.search(r'^volume:\s*(\d+)', head, re.M)
        if not (m_s and m_v):
            continue
        docx = docx_for(int(m_s.group(1)), int(m_v.group(1)))
        if not docx:
            continue
        phrases = italic_phrases(docx)
        if not phrases:
            continue
        phrases, skipped = safe_phrases(body, phrases)
        ambiguous.extend((os.path.basename(md), p, h, t) for p, h, t in skipped)
        if not phrases:
            continue

        out, marks = [], 0
        for line in body.split('\n'):
            line, n = mark_line(line, phrases)
            out.append(line)
            marks += n
        if not marks:
            continue
        total_files += 1
        total_marks += marks
        rel = os.path.relpath(md, os.path.join(ROOT, 'content'))
        report.append((marks, rel))
        if apply_changes:
            open(md, 'w', encoding='utf-8').write(head + '\n'.join(out))

    for marks, rel in sorted(report, reverse=True):
        print(f'  {marks:4}  {rel}')
    if ambiguous:
        print(f'\n{len(ambiguous)} phrase(s) left alone as ambiguous '
              f'(more occurrences in the prose than italics in the source):')
        for f, p, h, t in sorted(ambiguous, key=lambda a: -a[2])[:12]:
            print(f'  {p!r} — {h}x in {f}, italic {t}x in source')

    verb = 'applied' if apply_changes else 'would apply'
    print(f'\n{verb} {total_marks} italic marks across {total_files} files')
    if not apply_changes:
        print('re-run with --apply to write them')


if __name__ == '__main__':
    main('--apply' in sys.argv)
