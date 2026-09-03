#!/usr/bin/env python3
"""
One-off: give the extracted images back the captions Word had for them.

build_content.py pulls every image out of an issue but only *counts* them per
article — matching each picture to its caption was deferred (see
content/_REVIEW.md, "Not done in this phase"). So the archive carries hundreds
of images written as ![](path) with empty alt text, and lib/content.ts renders
an alt-less image with no <figcaption> at all, dropped into a gallery grid.

The captions exist in the .docx. Word sets them as a wholly-italic paragraph
either holding the image itself or sitting directly beneath it. This pairs each
image with that paragraph and writes it into the Markdown as the image's alt
text, which is what the renderer turns into a <figcaption>.

Images keep their source filename through extraction (media/image37.png ->
image37.webp), so the pairing is by filename stem, not by position — it does
not care that the articles have been reordered and edited since.

Only empty alt text is filled; a caption already written by hand always wins.

    python3 pipeline/apply_captions.py            # dry run, prints a report
    python3 pipeline/apply_captions.py --apply    # write the changes
"""
import sys, os, re, glob, zipfile, importlib.util
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location('bc', os.path.join(HERE, 'build_content.py'))
bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
W, R = bc.W, bc.R
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'

MIN_CAP, MAX_CAP = 12, 300


def image_captions(docx):
    """{image filename: caption} for every captioned image in an issue."""
    z = zipfile.ZipFile(docx)
    styles = bc.character_styles(z)
    rels = {r.get('Id'): 'word/' + r.get('Target').replace('../', '')
            for r in ET.fromstring(z.read('word/_rels/document.xml.rels'))
            if 'image' in r.get('Type', '')}
    root = ET.fromstring(z.read('word/document.xml'))

    paras = []
    for p in root.iter(W + 'p'):
        imgs = [rels[b.get(R + 'embed')] for b in p.iter(A + 'blip')
                if b.get(R + 'embed') in rels]
        segs = bc.para_segments(p, styles)
        text = bc.collapse_spacing(''.join(s[0] for s in segs))
        ital = sum(len(s[0].strip()) for s in segs if s[2])
        plain = sum(len(s[0].strip()) for s in segs if not s[2])
        # a caption is set wholly in italic; body prose is not
        paras.append((imgs, text, bool(ital) and plain < 12))

    out = {}
    for i, (imgs, text, is_cap) in enumerate(paras):
        if not imgs:
            continue
        cap = text if (text and is_cap) else ''
        if not cap and i + 1 < len(paras):
            nxt_imgs, nxt_text, nxt_cap = paras[i + 1]
            if not nxt_imgs and nxt_cap:
                cap = nxt_text
        cap = cap.strip()
        if not (MIN_CAP <= len(cap) <= MAX_CAP):
            continue
        for im in imgs:
            out.setdefault(os.path.basename(im), cap)
    return out


def clean(cap):
    """Alt text is written inside ![...](...), so brackets must not survive."""
    cap = re.sub(r'\s+', ' ', cap).strip()
    cap = cap.replace('[', '(').replace(']', ')')
    return cap.strip(' ;,')


def main(apply_changes):
    total = 0
    report = []
    for docx in sorted(glob.glob(os.path.join(ROOT, 'Filatelia', '*.docx'))):
        base = os.path.basename(docx)
        if base.startswith('~$') or 'incompleta' in base.lower():
            continue
        m = re.search(r'Vol\.\s*(\d+)\s*-\s*Serie\s*(\d+)', base)
        if not m:
            continue
        vol, ser = int(m.group(1)), int(m.group(2))
        caps = {os.path.splitext(k)[0]: v for k, v in image_captions(docx).items()}
        if not caps:
            continue
        for md in sorted(glob.glob(os.path.join(
                ROOT, 'content', f'serie-{ser}', f'vol-{vol:02d}', '*.md'))):
            raw = open(md, encoding='utf-8').read()
            n = 0

            def fill(mm):
                nonlocal n
                stem = os.path.splitext(os.path.basename(mm.group(1)))[0]
                cap = caps.get(stem)
                if not cap:
                    return mm.group(0)
                n += 1
                return f'![{clean(cap)}]({mm.group(1)})'

            new = re.sub(r'!\[\]\(([^)]+)\)', fill, raw)
            if n:
                total += n
                report.append((n, os.path.relpath(md, os.path.join(ROOT, 'content'))))
                if apply_changes:
                    open(md, 'w', encoding='utf-8').write(new)

    for n, rel in sorted(report, reverse=True):
        print(f'  {n:3}  {rel}')
    verb = 'captioned' if apply_changes else 'would caption'
    print(f'\n{verb} {total} images across {len(report)} articles')
    if not apply_changes:
        print('re-run with --apply to write them')


if __name__ == '__main__':
    main('--apply' in sys.argv)
