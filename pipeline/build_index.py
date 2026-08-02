#!/usr/bin/env python3
"""
Regenerate the master index from the clean per-article Markdown output.

Walks content/serie-*/vol-*/, reads each article's front-matter, and writes
content/_index.csv (the authoritative index, replacing the old auto-extracted
draft) plus prints a review summary: article counts, flag tallies, and issues
that look anomalous (missing date, few articles, image-only stubs).
"""
import os, re, csv, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'content')

FIELDS = ['series', 'volume', 'issue_date', 'order', 'title_es', 'author',
          'feature_type', 'themes', 'page_start', 'page_end', 'image_count',
          'review', 'file']

def parse_front_matter(path):
    txt = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---', txt, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        km = re.match(r'([a-z_]+):\s*(.*?)\s*(?:#.*)?$', line)
        if not km:
            continue
        k, v = km.group(1), km.group(2).strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith('['):
            v = [x.strip().strip('"') for x in v[1:-1].split(',') if x.strip()]
        fm[k] = v
    return fm

def main():
    rows, issues = [], []
    for issue_md in sorted(glob.glob(f'{CONTENT}/serie-*/vol-*/_issue.md')):
        d = os.path.dirname(issue_md)
        fm = parse_front_matter(issue_md)
        arts = sorted(f for f in glob.glob(f'{d}/*.md')
                      if not f.endswith('_issue.md'))
        issues.append((fm, len(arts), issue_md))
        for a in arts:
            afm = parse_front_matter(a)
            order = re.match(r'(\d+)', os.path.basename(a))
            rows.append({
                'series': afm.get('series', ''),
                'volume': afm.get('volume', ''),
                'issue_date': afm.get('issue_date', ''),
                'order': order.group(1) if order else '',
                'title_es': afm.get('title_es', ''),
                'author': afm.get('author', ''),
                'feature_type': afm.get('feature_type', ''),
                'themes': '; '.join(afm.get('themes', [])
                                    if isinstance(afm.get('themes'), list) else []),
                'page_start': afm.get('page_start', ''),
                'page_end': afm.get('page_end', ''),
                'image_count': afm.get('image_count', ''),
                'review': '; '.join(afm.get('review', [])
                                    if isinstance(afm.get('review'), list) else []),
                'file': os.path.relpath(a, CONTENT),
            })

    out = os.path.join(CONTENT, '_index.csv')
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)

    # ---- summary ----
    flags = {}
    for r in rows:
        for fl in filter(None, r['review'].split('; ')):
            flags[fl] = flags.get(fl, 0) + 1
    by_series = {}
    for r in rows:
        by_series[r['series']] = by_series.get(r['series'], 0) + 1

    print(f"Master index: {os.path.relpath(out, ROOT)}")
    print(f"Issues: {len(issues)}   Articles: {len(rows)}\n")
    print("Articles by series:")
    for s in sorted(by_series):
        print(f"  Serie {s}: {by_series[s]}")
    print("\nReview flags:")
    for fl, c in sorted(flags.items(), key=lambda x: -x[1]):
        print(f"  {c:4}  {fl}")

    print("\nPer-issue (articles / images / date):")
    for fm, na, p in issues:
        rel = os.path.relpath(os.path.dirname(p), CONTENT)
        warn = []
        if not fm.get('issue_date'):
            warn.append('NO-DATE')
        if na <= 3:
            warn.append('FEW-ARTICLES')
        if fm.get('incompleta') == 'true':
            warn.append('INCOMPLETA')
        print(f"  {rel:20} {na:2} art  {str(fm.get('image_count','')):>3} img  "
              f"{str(fm.get('issue_date') or '—'):8} {' '.join(warn)}")

if __name__ == '__main__':
    main()
