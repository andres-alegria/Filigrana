#!/usr/bin/env python3
"""
Filigrana image pipeline — links each article's extracted images to its
content, matching them to numbered captions in the prose by *document
proximity*, not list order.

Why proximity, not just pairing caption N with image N in order: articles
routinely mix a few specifically-cited artifacts (each with its own
"(1) ..." caption paragraph) among many uncaptioned illustrative images, so
the two counts almost never match — an exact-count-match strategy found
zero positional pairs across the whole corpus. Instead, for each caption
paragraph found in an article's ORIGINAL block stream (re-derived from the
source .docx, same slice the content pipeline used to emit that article),
this looks at a small window of nearby blocks and takes the closest image,
preferring: same block > nearest preceding block > nearest following block
(verified against real examples: a caption's image is consistently placed
just before it in the document flow, occasionally in the same paragraph).

For every article (content/serie-*/vol-*/NN-*.md):
  1. Re-derive its raw block range from the source .docx (same slice the
     content pipeline used to emit it) and collect its images in document
     order.
  2. Proximity-match each numbered caption paragraph to the nearest image.
     Matched pairs become inline <figure>s on the article page; every
     other image becomes an uncaptioned end-of-article gallery item.
  3. Resize (max 1400px) and re-encode each image as WebP, writing it to
     site/public/img/<content-id>/<name>.webp — a small, git-tracked,
     deployable copy. The raw originals in content/_assets/ stay put,
     local-only and regenerable, same as Filatelia/ is to content/.

Writes content/_images.json (the manifest the site reads) and prints a
summary. Nothing here is asserted as certain — proximity matches are a
strong heuristic, not a guarantee; spot-check a sample before trusting it
blindly across all 157 articles.
"""
import os, re, sys, glob, json
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')
ASSETS = os.path.join(CONTENT, '_assets')
FILATELIA = os.path.join(ROOT, 'Filatelia')
OUT_IMG = os.path.join(ROOT, 'site', 'public', 'img')
MANIFEST = os.path.join(CONTENT, '_images.json')

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
    """Return (caption_entries, gallery_files).

    caption_entries is EVERY "(N) ..." paragraph found, in document order,
    as (caption_text, image_filename_or_None) — None means no free image was
    found nearby, so the site leaves that paragraph as plain text rather
    than guessing. This 1:1, order-preserving list is what makes site-side
    rendering safe: it can walk the same paragraphs in the same order with
    no ambiguity about which caption is which, even for a future article
    where some captions match and others don't.

    gallery_files is every image not claimed by a caption, in document order.
    """
    all_images = []          # (block_index, filename) in document order
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
        # search priority: same block, then nearest preceding, then nearest following
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
        results[cid] = {'series': meta['serie'], 'volume': meta['volume'],
                        'captions': caption_entries, 'gallery': gallery}
    return results


def main():
    issue_dirs = sorted(glob.glob(f'{CONTENT}/serie-*/vol-*'))
    manifest = {}
    n_figures = n_gallery = n_articles_with_figures = 0

    for d in issue_dirs:
        res = process_issue(d)
        for cid, data in res.items():
            src_dir = os.path.join(ASSETS, f"s{data['series']}v{int(data['volume']):02d}")

            def optimize(fname):
                src = os.path.join(src_dir, fname)
                if not os.path.exists(src):
                    return None
                stem = os.path.splitext(fname)[0]
                dst = os.path.join(OUT_IMG, cid, f'{stem}.webp')
                optimize_image(src, dst)
                return f'{stem}.webp'

            captions_out = []
            n_matched = 0
            for caption_text, fname in data['captions']:
                webp = optimize(fname) if fname else None
                captions_out.append({'text': caption_text, 'file': webp})
                if webp:
                    n_matched += 1

            gallery_out = [f for f in (optimize(fn) for fn in data['gallery']) if f]

            if not captions_out and not gallery_out:
                continue
            first_fig = next((c['file'] for c in captions_out if c['file']), None)
            cover = first_fig or (gallery_out[0] if gallery_out else None)
            manifest[cid] = {'captions': captions_out, 'gallery': gallery_out, 'cover': cover}
            n_figures += n_matched
            n_gallery += len(gallery_out)
            if n_matched:
                n_articles_with_figures += 1

    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"\nWrote {MANIFEST}")
    print(f"Articles with images: {len(manifest)}  |  articles with matched figures: {n_articles_with_figures}")
    print(f"Total: {n_figures} captioned figures, {n_gallery} gallery images")


if __name__ == '__main__':
    main()
