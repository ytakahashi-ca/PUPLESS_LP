#!/usr/bin/env python3
"""PNG の読み書き（PIL / numpy 不要）。他のツールから import して使う。

この環境には PIL も numpy も入っていないため、zlib と struct だけで
8bit RGB / RGBA / グレースケール / パレットPNG をデコードする。
"""
import zlib, struct


def load(path):
    """PNG を読んで (width, height, channels, bytearray) を返す。
    パレット・グレースケールは RGBA に正規化する。"""
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", f"{path}: PNGではない"
    pos, idat, hdr, plte, trns = 8, [], None, None, None
    while pos < len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        typ = d[pos + 4:pos + 8]
        body = d[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", body)
        elif typ == b"IDAT":
            idat.append(body)
        elif typ == b"PLTE":
            plte = body
        elif typ == b"tRNS":
            trns = body
        elif typ == b"IEND":
            break
        pos += 12 + ln

    w, h, depth, ctype, _, _, interlace = hdr
    assert depth == 8, f"{path}: bitdepth={depth} は未対応"
    assert interlace == 0, f"{path}: インターレースは未対応"
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]

    raw = zlib.decompress(b"".join(idat))
    stride = w * ch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if f == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line

    if ctype == 3:                                   # パレット -> RGBA
        rgba = bytearray(w * h * 4)
        for i in range(w * h):
            idx = out[i]
            rgba[i * 4:i * 4 + 3] = plte[idx * 3:idx * 3 + 3]
            rgba[i * 4 + 3] = trns[idx] if trns and idx < len(trns) else 255
        out, ch = rgba, 4
    elif ctype in (0, 4):                            # グレースケール -> RGBA
        rgba = bytearray(w * h * 4)
        for i in range(w * h):
            g = out[i * ch]
            rgba[i * 4] = rgba[i * 4 + 1] = rgba[i * 4 + 2] = g
            rgba[i * 4 + 3] = out[i * ch + 1] if ctype == 4 else 255
        out, ch = rgba, 4
    return w, h, ch, out


def save(path, w, h, ch, buf):
    """RGB(3ch) / RGBA(4ch) の bytearray を PNG として書き出す。"""
    stride = w * ch
    raw = bytearray()
    for y in range(h):
        raw.append(0)                                # filter type 0 (None)
        raw += buf[y * stride:(y + 1) * stride]

    def chunk(t, b):
        return (struct.pack(">I", len(b)) + t + b +
                struct.pack(">I", zlib.crc32(t + b) & 0xffffffff))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2 if ch == 3 else 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def crop(w, h, ch, buf, x, y, cw, chh):
    cw = min(cw, w - x)
    chh = min(chh, h - y)
    out = bytearray(cw * chh * ch)
    for j in range(chh):
        s = ((y + j) * w + x) * ch
        out[j * cw * ch:(j + 1) * cw * ch] = buf[s:s + cw * ch]
    return cw, chh, out


def pixel_diff(A, B, w, h, ch, tol=2, skip_rows=None):
    """行ごとの差分画素数を返す。skip_rows(y)->bool で除外できる。"""
    rows = {}
    for y in range(h):
        if skip_rows and skip_rows(y):
            continue
        base = y * w * ch
        bad = 0
        for x in range(w):
            o = base + x * ch
            if max(abs(A[o + k] - B[o + k]) for k in range(3)) > tol:
                bad += 1
        if bad:
            rows[y] = bad
    return rows
