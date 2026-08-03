#!/usr/bin/env python3
"""
Filigrana image pipeline — links each article's extracted images to its
content and writes the result directly into the article's Markdown, as
plain image syntax, so it's visible and editable in the same file as the
text: ![caption](path). No separate manifest to keep in sync.

Matching strategy: numbered "(N) ..." caption paragraphs are matched to the
nearest image by *document proximity* — re-deriving the article's raw block
range from its source .docx (the same slice the content pipeline used to
emit it) and preferring same block > nearest preceding block > nearest
following block. An exact-count-match strategy (pair caption N with image N
in list order) was tried first and found zero matches across the whole
corpus — articles mix a few specifically-cited artifacts with many
uncaptioned illustrative images, so the counts almost never agree.
Proximity matching is a strong heuristic, not a guarantee — this is a
first-pass suggestion, not a final answer; open the .md file and move,
fix, or delete an image line wherever the match looks wrong.

For every article (content/serie-*/vol-*/NN-*.md) with at least one image:
  1. Re-derive its block range and proximity-match numbered captions.
  2. Resize (max 1400px) and re-encode each image as WebP, writing it to
     site/public/img/<content-id>/<name>.webp — a small, git-tracked,
     deployable copy. The raw originals in content/_assets/ stay put,
     local-only and regenerable, same as Filatelia/ is to content/.
  3. Edit the article's .md IN PLACE:
       - a matched "(N) ..." paragraph is replaced with
         "![caption text](/img/<content-id>/<name>.webp)" at that exact
         spot in the prose.
       - the old "<!-- IMÁGENES ... -->" listing is removed.
       - every image NOT matched to a caption is appended as a block of
         bare "![](/img/.../name.webp)" lines at the end — cut one of
         those lines and paste it wherever it actually belongs, adding
         alt text in the [] if you want it captioned.

This is a first-pass conversion: running it again on an article you've
since hand-edited will re-derive the same suggestions and may not respect
your edits. Safe to re-run on articles you haven't touched yet.
"""
import os, re, sys, glob
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')
ASSETS = os.path.join(CONTENT, '_assets')
FILATELIA = os.path.join(ROOT, 'Filatelia')
OUT_IMG = os.path.join(ROOT, 'site', 'public', 'img')

sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
import build_content as bc

CAPTION_RE = re.compile(r'^\(\d+\)\.?\s')
MAX_DIM = 1400
WEBP_QUALITY = 82
WINDOW = 3  # blocks to search on either side of a caption
# A handful of articles use "(N) ..." for a numbered list of PEOPLE (a family
# genealogy), not image captions — same surface pattern, different meaning.
# More than this many "(N)" paragraphs in one article means "enumerated
# list", not "sparse figure captions"; skip matching for that whole article
# so a genealogy entry doesn't get glued onto an unrelated nearby image.
MAX_CAPTIONS_PER_ARTICLE = 8

IMG_COMMENT_RE = re.compile(r'\n*<!-- IMÁGENES.*?-->\n*', re.S)


def optimize_image(src_path, dst_path):
    im = Image.open(src_path)
    if im.mode not in ('RGB', 'RGBA'):
        im = im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
    w, h = im.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    im.save(dst_path, 'WEBP', quality=WEBP_QUALITY, method=6)


def media_filename(media_path):
    return os.path.basename(media_path)  # 'word/media/image3.png' -> 'image3.png'


def match_captions(article_blocks):
    """Return (caption_entries, gallery_files): caption_entries is every
    "(N) ..." paragraph found, in document order, as
    (caption_text, image_filename_or_None); gallery_files is every image
    not claimed by a caption, in document order. See module docstring for
    the proximity-matching rationale."""
    all_images = []
    for i, b in enumerate(article_blocks):
        for m in b['images']:
            all_images.append((i, media_filename(m)))

    captions = [(i, bc.collapse_spacing(b['text']).strip())
               for i, b in enumerate(article_blocks)
               if CAPTION_RE.match(bc.collapse_spacing(b['text']).strip())]
    if len(captions) > MAX_CAPTIONS_PER_ARTICLE:
        captions = []  # looks like an enumerated list (e.g. a genealogy), not captions

    claimed = set()
    caption_entries = []
    for ci, ctext in captions:
        caption_text = re.sub(r'^\(\d+\)\.?\s*', '', ctext).strip()
        order = [ci] + [ci - d for d in range(1, WINDOW + 1)] + [ci + d for d in range(1, WINDOW + 1)]
        found = None
        for bi in order:
            cands = [f for (bidx, f) in all_images if bidx == bi and f not in claimed]
            if cands:
                found = cands[0]
                break
        if found:
            claimed.add(found)
        caption_entries.append((caption_text, found))

    seen = set()
    gallery = []
    for _, f in all_images:
        if f not in claimed and f not in seen:
            gallery.append(f)
            seen.add(f)
    return caption_entries, gallery


def apply_to_markdown(md_path, cid, caption_entries, gallery_files, optimize_fn):
    text = open(md_path, encoding='utf-8').read()
    text = IMG_COMMENT_RE.sub('\n', text)

    n_placed = 0
    for caption_text, fname in caption_entries:
        if not fname:
            continue
        webp = optimize_fn(fname)
        if not webp:
            continue
        key = caption_text[:80]
        pattern = re.compile(r'\(\d+\)\.?\s*' + re.escape(key) + r'[^\n]*')
        img_line = f'![{caption_text}](/img/{cid}/{webp})'
        new_text, n = pattern.subn(lambda m: img_line, text, count=1)
        if n:
            text = new_text
            n_placed += 1

    gallery_webps = [w for w in (optimize_fn(fn) for fn in gallery_files) if w]
    if gallery_webps:
        block = ('\n\n<!-- Imágenes sin posición asignada — mueve cada línea al '
                 'lugar del texto que le corresponda, o bórrala si no aplica. -->\n\n')
        # blank line between each — Markdown merges same-line images without
        # one into a single paragraph, which breaks the per-image gallery
        # rendering (and is harder to edit as separate lines anyway)
        block += '\n\n'.join(f'![](/img/{cid}/{w})' for w in gallery_webps)
        text = text.rstrip('\n') + '\n' + block + '\n'

    total = n_placed + len(gallery_webps)
    if total:
        text = re.sub(
            r'image_count:\s*\d+\s*(#.*)?',
            f'image_count: {total}   # {n_placed} colocadas en el texto, '
            f'{len(gallery_webps)} sueltas al final',
            text, count=1,
        )

    open(md_path, 'w', encoding='utf-8').write(text)
    return n_placed, len(gallery_webps)


def process_issue(issue_dir):
    issue_md = os.path.join(issue_dir, '_issue.md')
    if not os.path.exists(issue_md):
        return {}
    text = open(issue_md, encoding='utf-8').read()
    m = re.search(r'source_file:\s*"(.*?)"', text)
    if not m:
        return {}
    docx_path = os.path.join(FILATELIA, m.group(1))
    if not os.path.exists(docx_path):
        print(f"  WARN source docx not found: {docx_path}")
        return {}

    z, blocks, fulltext = bc.load_blocks(docx_path)
    meta = bc.parse_meta(docx_path)
    entries = bc.parse_toc(blocks, meta)
    start = bc.find_body_start(blocks, entries)
    locs = bc.locate_headings(blocks, entries, start, meta)

    results = {}
    for md_path in sorted(glob.glob(os.path.join(issue_dir, '*.md'))):
        base = os.path.basename(md_path)
        if base == '_issue.md':
            continue
        oi_match = re.match(r'(\d+)-', base)
        if not oi_match:
            continue
        oi = int(oi_match.group(1))
        if oi >= len(locs) or locs[oi] is None:
            continue
        lo = locs[oi]
        hi = next((locs[j] for j in range(oi + 1, len(locs)) if locs[j] is not None), len(blocks))
        article_blocks = blocks[lo + 1:hi]
        caption_entries, gallery = match_captions(article_blocks)
        cid = os.path.relpath(md_path, CONTENT)[:-3]
        results[cid] = {'series': meta['serie'], 'volume': meta['volume'], 'md_path': md_path,
                        'captions': caption_entries, 'gallery': gallery}
    return results


def main():
    issue_dirs = sorted(glob.glob(f'{CONTENT}/serie-*/vol-*'))
    n_placed_total = n_gallery_total = n_articles_with_figures = n_articles = 0

    for d in issue_dirs:
        res = process_issue(d)
        for cid, data in res.items():
            if not data['captions'] and not data['gallery']:
                continue
            src_dir = os.path.join(ASSETS, f"s{data['series']}v{int(data['volume']):02d}")

            def optimize(fname):
                src = os.path.join(src_dir, fname)
                if not os.path.exists(src):
                    return None
                stem = os.path.splitext(fname)[0]
                dst = os.path.join(OUT_IMG, cid, f'{stem}.webp')
                optimize_image(src, dst)
                return f'{stem}.webp'

            n_placed, n_gallery = apply_to_markdown(
                data['md_path'], cid, data['captions'], data['gallery'], optimize)
            n_articles += 1
            n_placed_total += n_placed
            n_gallery_total += n_gallery
            if n_placed:
                n_articles_with_figures += 1

    print(f"Articles with images: {n_articles}  |  articles with placed captions: {n_articles_with_figures}")
    print(f"Total: {n_placed_total} images placed inline, {n_gallery_total} in loose end-of-article blocks")


if __name__ == '__main__':
    main()
