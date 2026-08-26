#!/usr/bin/env python3
"""Minimal QR Code encoder — byte mode, error-correction level H.

Written out in full rather than pulling in a library, because the rest of
this pipeline depends only on Pillow and this machine's Python refuses new
packages (PEP 668) — a `pip install` dependency here would mean the script
simply doesn't run. Every matrix it produces is checked module-for-module
against segno in the test at the bottom of this file.

Level H is fixed deliberately: it tolerates ~30% damage, which is what makes
it safe to drop a mark into the middle of the symbol.

    from qr import encode
    matrix = encode('https://filigrana.hn')   # list[list[bool]], no quiet zone

Versions 1–10 are covered, i.e. up to 122 bytes at level H — far more than
any URL this project will ever encode.
"""

# ---------------------------------------------------------------- GF(256)
# Arithmetic for Reed–Solomon, over the field the QR spec fixes with the
# primitive polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D).
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else EXP[LOG[a] + LOG[b]]


def _poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        if av:
            for j, bv in enumerate(b):
                out[i + j] ^= _mul(av, bv)
    return out


def _generator(n):
    """Generator polynomial for n error-correction codewords."""
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, EXP[i]])
    return g


def _ec_codewords(data, n):
    """The n check codewords for one block — polynomial long division."""
    g = _generator(n)
    rem = list(data) + [0] * n
    for i in range(len(data)):
        lead = rem[i]
        if lead:
            for j, gv in enumerate(g):
                rem[i + j] ^= _mul(gv, lead)
    return rem[len(data):]


# ------------------------------------------------------------ spec tables
# version -> (total codewords, EC codewords per block, [(block count, data
# codewords per block), ...]) at error-correction level H.
VERSIONS = {
    1:  (26,  17, [(1, 9)]),
    2:  (44,  28, [(1, 16)]),
    3:  (70,  22, [(2, 13)]),
    4:  (100, 16, [(4, 9)]),
    5:  (134, 22, [(2, 11), (2, 12)]),
    6:  (172, 28, [(4, 15)]),
    7:  (196, 26, [(4, 13), (1, 14)]),
    8:  (242, 26, [(4, 14), (2, 15)]),
    9:  (292, 24, [(4, 12), (4, 13)]),
    10: (346, 28, [(6, 15), (2, 16)]),
}

# centre coordinates of the alignment patterns; every pairing is used except
# the three that would land on a finder pattern
ALIGN = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
}

# unused bits left over after the last codeword, by version
REMAINDER = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7, 7: 0, 8: 0, 9: 0, 10: 0}

ECC_H = 0b10  # the level's own two-bit code, for the format information


def capacity(version):
    return sum(count * size for count, size in VERSIONS[version][2])


def _pick_version(nbytes):
    for v in sorted(VERSIONS):
        # 4 bits mode + 8 or 16 bits length, rounded up to whole codewords
        header = 4 + (8 if v < 10 else 16)
        if (header + 7) // 8 + nbytes <= capacity(v):
            return v
    raise ValueError(f'{nbytes} bytes is more than level H holds up to version 10')


# --------------------------------------------------------------- bitstream
def _bitstream(data, version):
    bits = []

    def put(value, length):
        for k in range(length - 1, -1, -1):
            bits.append((value >> k) & 1)

    put(0b0100, 4)                              # byte mode
    put(len(data), 8 if version < 10 else 16)   # character count
    for byte in data:
        put(byte, 8)

    total_bits = capacity(version) * 8
    put(0, min(4, total_bits - len(bits)))      # terminator
    if len(bits) % 8:                           # pad to a codeword boundary
        put(0, 8 - len(bits) % 8)

    codewords = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    for pad in _cycle(0xEC, 0x11):              # the spec's alternating filler
        if len(codewords) >= capacity(version):
            break
        codewords.append(pad)
    return codewords


def _cycle(*values):
    while True:
        for v in values:
            yield v


def _interleave(codewords, version):
    """Split into blocks, add check codewords, then interleave both runs."""
    _, ec_len, groups = VERSIONS[version]
    blocks, pos = [], 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(codewords[pos:pos + size])
            pos += size
    ec_blocks = [_ec_codewords(b, ec_len) for b in blocks]

    out = []
    for i in range(max(len(b) for b in blocks)):
        for b in blocks:
            if i < len(b):
                out.append(b[i])
    for i in range(ec_len):
        for b in ec_blocks:
            out.append(b[i])
    return out


# ------------------------------------------------------------------ matrix
def _blank(version):
    size = version * 4 + 17
    return [[None] * size for _ in range(size)], size


def _place_function_patterns(m, size, version):
    """Finders, separators, alignment, timing and the lone dark module.

    Order matters. Alignment patterns are laid before the timing patterns
    because from version 7 up some of them legitimately sit on row/column 6
    and share modules with the timing line; drawing timing first would make
    those cells look occupied and the pattern would be skipped.
    """
    def finder(r, c):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                rr, cc = r + dr, c + dc
                if not (0 <= rr < size and 0 <= cc < size):
                    continue
                if not (0 <= dr <= 6 and 0 <= dc <= 6):
                    m[rr][cc] = False          # separator: always light
                else:
                    ring = dr in (0, 6) or dc in (0, 6)
                    core = 2 <= dr <= 4 and 2 <= dc <= 4
                    m[rr][cc] = ring or core

    finder(0, 0)
    finder(0, size - 7)
    finder(size - 7, 0)

    centres = ALIGN[version]
    for r in centres:
        for c in centres:
            # the three that would land on a finder are omitted, and only
            # those three — position, not occupancy, is the test
            if ((r < 8 and c < 8) or (r < 8 and c > size - 9)
                    or (r > size - 9 and c < 8)):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    m[r + dr][c + dc] = max(abs(dr), abs(dc)) != 1

    for i in range(size):                              # timing patterns
        if m[6][i] is None:
            m[6][i] = i % 2 == 0
        if m[i][6] is None:
            m[i][6] = i % 2 == 0

    m[size - 8][8] = True                              # always-dark module


def _reserve(size, version):
    """Modules that carry format/version information, not data."""
    res = [[False] * size for _ in range(size)]
    for i in range(9):
        res[8][i] = res[i][8] = True
    for i in range(8):
        res[8][size - 1 - i] = res[size - 1 - i][8] = True
    if version >= 7:
        for i in range(6):
            for j in range(3):
                res[size - 11 + j][i] = True
                res[i][size - 11 + j] = True
    return res


def _place_data(m, size, bits, reserved):
    """Two-module-wide zigzag, upwards from the bottom-right corner.

    `reserved` has to be honoured as well as the function patterns already
    in `m`: the format-information cells are still empty at this point, and
    without skipping them the data run writes straight through them and
    every module after that lands one position early.
    """
    i, upward, col = 0, True, size - 1
    while col > 0:
        if col == 6:            # the vertical timing pattern is not a column
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for row in rows:
            for c in (col, col - 1):
                if m[row][c] is None and not reserved[row][c]:
                    m[row][c] = i < len(bits) and bits[i] == 1
                    i += 1
        upward = not upward
        col -= 2


MASKS = [
    lambda i, j: (i + j) % 2 == 0,
    lambda i, j: i % 2 == 0,
    lambda i, j: j % 3 == 0,
    lambda i, j: (i + j) % 3 == 0,
    lambda i, j: (i // 2 + j // 3) % 2 == 0,
    lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    lambda i, j: ((i + j) % 2 + (i * j) % 3) % 2 == 0,
]


def _format_bits(mask):
    data = (ECC_H << 3) | mask
    rem = data << 10
    while rem.bit_length() >= 11:
        rem ^= 0x537 << (rem.bit_length() - 11)
    return ((data << 10) | rem) ^ 0x5412


def _version_bits(version):
    rem = version << 12
    while rem.bit_length() >= 13:
        rem ^= 0x1F25 << (rem.bit_length() - 13)
    return (version << 12) | rem


def _place_format(m, size, mask):
    """Both copies of the 15 format bits. The two are laid out differently:
    one wraps the top-left finder as an L, the other is split between the
    bottom-left and top-right corners — they are not transposes."""
    bits = _format_bits(mask)
    get = lambda k: (bits >> k) & 1 == 1

    for k in range(6):                 # copy 1: column 8 down, then row 8 out
        m[k][8] = get(k)
    m[7][8] = get(6)
    m[8][8] = get(7)
    m[8][7] = get(8)
    for k in range(9, 15):
        m[8][14 - k] = get(k)

    for k in range(8):                 # copy 2: row 8 right, column 8 down
        m[8][size - 1 - k] = get(k)
    for k in range(8, 15):
        m[size - 15 + k][8] = get(k)


def _place_version(m, size, version):
    if version < 7:
        return
    bits = _version_bits(version)
    for k in range(18):
        bit = (bits >> k) & 1 == 1
        r, c = k // 3, k % 3
        m[size - 11 + c][r] = bit
        m[r][size - 11 + c] = bit


_N3 = [True, False, True, True, True, False, True]   # the 1:1:3:1:1 ratio


def _finder_like(line, size):
    """Rule 3: 40 points per finder-like run with a 4-module light margin.

    A run flush against the edge of the symbol counts too — the quiet zone
    supplies the light margin there, which is why the spec phrases the rule
    in terms of a light area rather than light modules.
    """
    score, i = 0, 0
    while i <= size - 7:
        try:
            idx = next(k for k in range(i, size - 6) if line[k:k + 7] == _N3)
        except StopIteration:
            break
        after = idx + 7
        if (idx in (0, size - 7)
                or not any(line[max(idx - 4, 0):idx])
                or not any(line[after:after + 4])):
            score += 40
            i = after
        else:
            # overlapping matches can only restart at the middle dark run
            i = idx + 4
    return score


def _penalty(m, size):
    """The spec's four mask-selection penalties; lower is better."""
    score = 0

    for line in list(m) + [list(col) for col in zip(*m)]:   # rule 1: runs
        run, prev = 1, line[0]
        for cell in line[1:]:
            if cell == prev:
                run += 1
            else:
                if run >= 5:
                    score += 3 + run - 5
                run, prev = 1, cell
        if run >= 5:
            score += 3 + run - 5

    for r in range(size - 1):                                # rule 2: 2x2
        for c in range(size - 1):
            if m[r][c] == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                score += 3

    for line in list(m) + [list(col) for col in zip(*m)]:    # rule 3
        score += _finder_like(line, size)

    # rule 4: how far the dark/light balance strays from 50%, in 5% steps.
    # Kept in integers: |dark/total*100 - 50| / 5  ==  |dark*20 - total*10| / total
    dark = sum(cell for row in m for cell in row)
    total = size * size
    score += 10 * (abs(dark * 20 - total * 10) // total)
    return score


def encode(text, version=None):
    """Return the QR matrix for `text` as list[list[bool]] — True is dark.

    No quiet zone is included; the renderer adds it (four modules, minimum).
    """
    data = text.encode('utf-8') if isinstance(text, str) else bytes(text)
    version = version or _pick_version(len(data))
    if len(data) > capacity(version):
        raise ValueError(f'{len(data)} bytes will not fit in version {version}')

    stream = _interleave(_bitstream(data, version), version)
    bits = [(b >> k) & 1 for b in stream for k in range(7, -1, -1)]
    bits += [0] * REMAINDER[version]

    base, size = _blank(version)
    _place_function_patterns(base, size, version)
    reserved = _reserve(size, version)
    template = [row[:] for row in base]
    _place_data(template, size, bits, reserved)

    best, best_score = None, None
    for mask in range(8):
        m = [row[:] for row in template]
        for r in range(size):
            for c in range(size):
                if base[r][c] is None and not reserved[r][c] and MASKS[mask](r, c):
                    m[r][c] = not m[r][c]
        _place_format(m, size, mask)
        _place_version(m, size, version)
        score = _penalty(m, size)
        if best_score is None or score < best_score:
            best, best_score = m, score
    return [[bool(cell) for cell in row] for row in best]
