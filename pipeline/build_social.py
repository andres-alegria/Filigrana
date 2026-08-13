#!/usr/bin/env python3
"""
Filigrana social-asset generator — Instagram profile images and per-article
post cards, built from the same brand tokens the site uses so nothing has to
be re-matched by eye.

Everything visual is defined in the CONFIG block below: colours are copied
from site/src/styles/global.css, and the guilloche layer parameters from
site/src/pages/index.astro, so a change on the site can be mirrored here by
editing one dict rather than redrawing anything.

Article content is read from the same source of truth the site uses —
site/src/data/publish.ts for what's published, and each article's Markdown
front matter for title/author/date — so a post card can never drift out of
step with what's actually online.

Usage:
    python3 pipeline/build_social.py profile          # profile image variants
    python3 pipeline/build_social.py post <slug-or-id>
    python3 pipeline/build_social.py post --all       # every published article

Output lands in social/ (profile/ and posts/), which is git-ignored — these
are regenerable artefacts, not sources.
"""
import os, re, sys, math, glob

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'pipeline', 'assets', 'fonts')
CONTENT = os.path.join(ROOT, 'content')
PUBLIC = os.path.join(ROOT, 'site', 'public')
OUT = os.path.join(ROOT, 'social')

# ─── brand tokens — mirror of site/src/styles/global.css ────────────────────
# Adjust these to retint every generated asset at once.
PAPER     = (233, 223, 199)   # --paper
PAPER_LIT = (244, 238, 218)   # --paper-lit
INK       = (28, 26, 21)      # --ink
INK_SOFT  = (84, 76, 61)      # --ink-soft
GREEN     = (26, 71, 49)      # --green
GREEN_MID = (53, 107, 79)     # --green-mid
BLUE      = (38, 68, 88)      # --blue
GOLD      = (176, 134, 63)    # --gold

# Guilloche layers — copied from the hero in site/src/pages/index.astro.
# (R, r, d, colour, alpha, turns). Tweak alpha/lw for a louder or quieter motif.
GUILLOCHE_LAYERS = [
    (1.0, 0.34,  0.68, GREEN, 0.24, 50),
    (1.0, 0.30,  0.62, BLUE,  0.16, 50),
    (1.0, 0.233, 0.50, GOLD,  0.18, 80),
]

SS = 2            # supersampling factor — raise for smoother lines at more cost
IG_POST = (1080, 1350)   # Instagram 4:5 portrait — the largest feed real estate
IG_PROFILE = 1080


def font(name, size, **axes):
    """Load a brand font, applying variable-font axes where present."""
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if axes:
        try:
            names = [a['name'].decode() if isinstance(a['name'], bytes) else a['name']
                     for a in f.get_variation_axes()]
            cur = {}
            for a in f.get_variation_axes():
                n = a['name'].decode() if isinstance(a['name'], bytes) else a['name']
                cur[n] = a['default']
            for k, v in axes.items():
                for n in names:
                    if n.lower().startswith(k.lower()):
                        cur[n] = v
            f.set_variation_by_axes([cur[n] for n in names])
        except Exception:
            pass
    return f


def _opsz(size, opsz=None):
    """Fraunces' optical-size axis, tracking the rendered size by default.

    Browsers do this automatically (font-optical-sizing: auto), so matching it
    keeps exports identical to the site. It matters here: the 144 end of the
    axis is drawn for headlines and its hairlines thin out to nothing at small
    sizes, while the 9 end is drawn for text and holds its thin strokes —
    which is what survives Instagram's downscaling and JPEG compression.
    """
    return max(9, min(144, size if opsz is None else opsz))


def fraunces(size, weight=400, opsz=None):
    return font('Fraunces-VF.ttf', size, **{'Optical': _opsz(size, opsz),
                                            'Weight': weight,
                                            'Softness': 0, 'Wonky': 0})


def fraunces_italic(size, weight=400, opsz=None):
    return font('Fraunces-Italic-VF.ttf', size, **{'Optical': _opsz(size, opsz),
                                                   'Weight': weight,
                                                   'Softness': 0, 'Wonky': 0})


def archivo(size, weight=400):
    return font('Archivo-VF.ttf', size, **{'Weight': weight, 'Width': 100})


def mono(size):
    return font('PlexMono.ttf', size)


# ─── guilloche ─────────────────────────────────────────────────────────────
def guilloche(size, layers=GUILLOCHE_LAYERS, scale=1.15, lw=0.5, bg=None, alpha=1.0):
    """Port of site/src/lib/guilloche.js — hypotrochoid interference rosette.

    Each layer is drawn opaque on its own canvas and composited once at its
    intended alpha, exactly as the browser version does, because
    self-overlapping strokes otherwise accumulate opacity unevenly.

    `alpha` scales every layer's opacity at once — 1.0 matches the site,
    lower values make the motif more transparent without touching the shared
    GUILLOCHE_LAYERS definition.
    """
    w = h = size * SS
    base = Image.new('RGBA', (w, h), (bg or PAPER) + (255,) if bg is not False else (0, 0, 0, 0))
    cx, cy = w / 2, h / 2
    rad = (min(w, h) / 2) * scale
    for R, r, d, colour, layer_alpha, turns in layers:
        layer = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(layer)
        k = (R - r) / r
        pts, t, end, step = [], 0.0, math.pi * 2 * turns, 0.02
        while t <= end:
            x = (R - r) * math.cos(t) + d * math.cos(k * t)
            y = (R - r) * math.sin(t) - d * math.sin(k * t)
            pts.append((cx + x * rad, cy + y * rad))
            t += step
        dr.line(pts, fill=colour + (255,), width=max(1, int(lw * SS)), joint='curve')
        base = Image.alpha_composite(base, Image.blend(
            Image.new('RGBA', (w, h), (0, 0, 0, 0)), layer,
            max(0.0, min(1.0, layer_alpha * alpha))))
    return base.resize((size, size), Image.LANCZOS)


def scrim(card, strength=0.82, falloff=2.1, colour=None):
    """Wash the centre of the canvas back toward paper so the guilloche stays
    visible at the edges without cutting through centred type. Raise
    `strength` for a cleaner field, lower it to let more motif through."""
    from PIL import ImageOps
    W, H = card.size
    g = ImageOps.invert(Image.radial_gradient('L'))       # bright at centre
    g = g.point(lambda v: int(255 * ((v / 255) ** falloff) * strength))
    card.paste(Image.new('RGB', (W, H), colour or PAPER), (0, 0),
               g.resize((W, H), Image.LANCZOS))
    return card


def mark(size, fg=GREEN, dot=GOLD):
    """The 'F.' mark, rasterised from the site's favicon.svg."""
    import cairosvg, io
    svg = open(os.path.join(PUBLIC, 'favicon.svg'), encoding='utf8').read()
    svg = svg.replace('#1a4731', '#%02x%02x%02x' % fg).replace('#b0863f', '#%02x%02x%02x' % dot)
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert('RGBA')


# ─── content ───────────────────────────────────────────────────────────────
def published():
    """Parse site/src/data/publish.ts for published article ids, in order."""
    src = open(os.path.join(ROOT, 'site/src/data/publish.ts'), encoding='utf8').read()
    return re.findall(r"id:\s*'([^']+)'", src)


def article(cid):
    """Read an article's front matter + first image from its Markdown."""
    path = os.path.join(CONTENT, cid + '.md')
    txt = open(path, encoding='utf8').read()
    def fm(key):
        m = re.search(rf'^{key}:\s*"?([^"\n]+)"?\s*$', txt, re.M)
        return m.group(1).strip().strip('"') if m else ''
    img = re.search(r'!\[[^\]]*\]\((/img/[^)]+)\)', txt)
    return {
        'id': cid,
        'title': fm('title_es'),
        'author': fm('author'),
        'date': fm('issue_date'),
        'cover': os.path.join(PUBLIC, img.group(1).lstrip('/')) if img else None,
    }


MONTHS = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
          'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def pretty_date(d):
    m = re.match(r'(\d{4})-(\d{2})', d or '')
    return f'{MONTHS[int(m.group(2)) - 1]} de {m.group(1)}' if m else ''


def tracked(d, xy, text, fnt, fill, tracking=0, anchor_centre=None):
    """Draw letterspaced text — PIL has no tracking, so step per glyph.
    Pass anchor_centre=<width> to centre the run in that width."""
    widths = [d.textlength(c, font=fnt) for c in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x, y = xy
    if anchor_centre is not None:
        x = (anchor_centre - total) / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=fnt, fill=fill)
        x += w + tracking
    return total


def centre(d, y, text, fnt, fill, W):
    x = (W - d.textlength(text, font=fnt)) / 2
    d.text((x, y), text, font=fnt, fill=fill)


def fading_rule(card, y, W, inset=190, colour=None, thickness=2):
    """The site's centre hairline that fades out toward both ends."""
    colour = colour or INK
    grad = Image.new('L', (W - inset * 2, 1))
    px = grad.load()
    n = grad.width
    for i in range(n):
        t = 1 - abs(i / (n - 1) * 2 - 1)          # 0 at ends, 1 at centre
        px[i, 0] = int(255 * (t ** 0.7) * 0.55)
    grad = grad.resize((W - inset * 2, thickness))
    card.paste(Image.new('RGB', grad.size, colour), (inset, y), grad)


def wrap(draw, text, fnt, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        trial = (cur + ' ' + w).strip()
        if draw.textlength(trial, font=fnt) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ─── profile images ────────────────────────────────────────────────────────
def build_profile():
    os.makedirs(os.path.join(OUT, 'profile'), exist_ok=True)
    S = IG_PROFILE
    variants = {}

    # a — plain paper, green mark. Quietest; matches the site header.
    a = Image.new('RGBA', (S, S), PAPER + (255,))
    m = mark(int(S * .54))
    a.alpha_composite(m, ((S - m.width) // 2, (S - m.height) // 2))
    variants['a-paper'] = a

    # b — paper with the guilloche rosette behind the mark.
    b = guilloche(S, scale=1.05, lw=0.9).convert('RGBA')
    b.alpha_composite(m, ((S - m.width) // 2, (S - m.height) // 2))
    variants['b-guilloche'] = b

    # c — green ground, paper mark. Highest contrast at thumbnail size.
    c = Image.new('RGBA', (S, S), GREEN + (255,))
    mc = mark(int(S * .54), fg=PAPER, dot=GOLD)
    c.alpha_composite(mc, ((S - mc.width) // 2, (S - mc.height) // 2))
    variants['c-green'] = c

    for name, im in variants.items():
        im.convert('RGB').save(os.path.join(OUT, 'profile', f'profile-{name}.png'))
    return variants


# ─── post card ─────────────────────────────────────────────────────────────
def build_post(cid):
    os.makedirs(os.path.join(OUT, 'posts'), exist_ok=True)
    a = article(cid)
    W, H = IG_POST
    card = Image.new('RGB', (W, H), PAPER)
    d = ImageDraw.Draw(card)

    # Measure the text block first, then give the cover whatever is left, so a
    # three-line title pushes the image up instead of colliding with the
    # footer. Titles across the archive run one to three lines.
    TITLE, LEAD = 66, 78
    title_lines = wrap(d, a['title'], fraunces(TITLE, 400), W - 128)[:3]
    panel_h = (56          # padding above the author line
               + 52        # author
               + LEAD * len(title_lines)
               + 34 + 1 + 34   # gap, rule, gap
               + 30        # date
               + 96)       # breathing room above the footer strip
    IMG_H = H - panel_h - 128   # 128 = footer strip (mark + domain)

    # cover, cropped to fill
    if a['cover'] and os.path.exists(a['cover']):
        cov = Image.open(a['cover']).convert('RGB')
        s = max(W / cov.width, IMG_H / cov.height)
        cov = cov.resize((round(cov.width * s), round(cov.height * s)), Image.LANCZOS)
        # Crop to exactly the cover region before pasting — Image.paste does not
        # clip, so a tall source would otherwise bleed over the text panel.
        left, top = (cov.width - W) // 2, (cov.height - IMG_H) // 2
        card.paste(cov.crop((left, top, left + W, top + IMG_H)), (0, 0))
    else:
        card.paste(guilloche(max(W, IMG_H), lw=0.8).convert('RGB'), (0, 0))

    # paper panel
    y = IMG_H + 56
    d.text((64, y), (a['author'] or '').upper(), font=archivo(25, 500), fill=GOLD)
    y += 52

    tf = fraunces(TITLE, 400)
    for line in title_lines:
        d.text((64, y), line, font=tf, fill=INK)
        y += LEAD

    y += 34
    d.line([(64, y), (W - 64, y)], fill=INK_SOFT, width=1)
    y += 34
    d.text((64, y), pretty_date(a['date']).upper(), font=mono(24), fill=INK_SOFT)

    # footer — mark + domain
    mk = mark(74)
    card.paste(mk, (W - 64 - mk.width, H - 64 - mk.height), mk)
    df = mono(26)
    d.text((64, H - 64 - 30), 'filigrana.hn', font=df, fill=GREEN)

    out = os.path.join(OUT, 'posts', cid.replace('/', '_') + '.png')
    card.save(out)
    return out


# ─── launch announcement ───────────────────────────────────────────────────
# Copy lives here, separate from the layout below — edit the words without
# touching the drawing code.
COMING_SOON = {
    'eyebrow': 'HONDURAS FILATÉLICA · DIGITAL',
    'wordmark': 'Filigrana',
    # A newline here forces an explicit break; without one the tagline wraps
    # to fit the canvas on its own.
    'tagline': 'Historia hondureña,\nrevelada por sellos postales.',
    'kicker': 'PRÓXIMAMENTE',
    # Any field left empty is skipped, and the remaining blocks re-centre
    # themselves — so lines can be dropped without touching the layout.
    'date': '',
    'body': '',
    'url': 'filigrana.hn',
}


def build_coming_soon(copy=None):
    """The launch-announcement post — echoes the filigrana.hn holding page."""
    c = dict(COMING_SOON, **(copy or {}))
    W, H = IG_POST
    os.makedirs(os.path.join(OUT, 'posts'), exist_ok=True)

    # alpha=0.5 — the announcement carries a lighter motif than the site hero
    card = guilloche(max(W, H), scale=0.92, lw=0.7, alpha=0.5).convert('RGB')
    card = card.crop(((card.width - W) // 2, (card.height - H) // 2,
                      (card.width - W) // 2 + W, (card.height - H) // 2 + H))
    scrim(card)          # keep the rosette at the edges, clear the type zone
    d = ImageDraw.Draw(card)

    # Blocks are (draw, height, gap-after). Empty copy fields contribute
    # nothing, so the stack collapses and re-centres around what's left.
    wf, tf, bf = fraunces(158, 400), fraunces_italic(46, 400), archivo(29, 400)
    tag_lines = ([l.strip() for l in c['tagline'].split('\n')]
                 if '\n' in c['tagline'] else wrap(d, c['tagline'], tf, W - 240))
    body_lines = wrap(d, c['body'], bf, W - 260) if c['body'] else []

    def draw_wordmark(y):
        word, dot = c['wordmark'], '.'
        ww = d.textlength(word, font=wf)
        x = (W - (ww + d.textlength(dot, font=wf))) / 2
        d.text((x, y), word, font=wf, fill=GREEN)
        d.text((x + ww, y), dot, font=wf, fill=GOLD)

    blocks = []
    if c['eyebrow']:
        blocks.append((lambda y: tracked(d, (0, y), c['eyebrow'], archivo(27, 500),
                                         INK_SOFT, 7, W), 34, 78))
    if c['wordmark']:
        blocks.append((draw_wordmark, 196, 44))
    for i, line in enumerate(tag_lines):
        blocks.append(((lambda ln: lambda y: centre(d, y, ln, tf, INK_SOFT, W))(line),
                       62, 0 if i < len(tag_lines) - 1 else 52))
    blocks.append((lambda y: fading_rule(card, y, W), 2, 62))
    if c['kicker']:
        blocks.append((lambda y: tracked(d, (0, y), c['kicker'], archivo(40, 600),
                                         GREEN, 10, W), 50, 56))
    if c['date']:
        blocks.append((lambda y: tracked(d, (0, y), c['date'], mono(30), GOLD, 3, W),
                       36, 62))
    for i, line in enumerate(body_lines):
        blocks.append(((lambda ln: lambda y: centre(d, y, ln, bf, INK_SOFT, W))(line),
                       44, 0))

    total = sum(h + g for _, h, g in blocks) - (blocks[-1][2] if blocks else 0)
    y = (H - total) / 2 - 40          # nudged above centre — optically truer
    for fn, h, g in blocks:
        fn(int(round(y)))     # paste/mask offsets must be integers
        y += h + g

    centre(d, H - 120, c['url'], mono(28), GREEN, W)

    out = os.path.join(OUT, 'posts', '000-proximamente.png')
    card.save(out)
    return out


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'profile'
    if cmd == 'profile':
        build_profile()
        print('wrote', os.path.join(OUT, 'profile'))
    elif cmd in ('coming-soon', 'proximamente'):
        print('wrote', build_coming_soon())
    elif cmd == 'post':
        arg = sys.argv[2] if len(sys.argv) > 2 else '--all'
        ids = published() if arg == '--all' else [
            i for i in published() if arg in i] or [arg]
        for cid in ids:
            print('wrote', build_post(cid))
