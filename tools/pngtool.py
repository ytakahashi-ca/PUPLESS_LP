#!/usr/bin/env python3
"""スクショを目視確認するための切り出しツール。

  python3 tools/pngtool.py crop A.png OUT.png X Y W H       # 切り出し
  python3 tools/pngtool.py sbs  A.png B.png OUT.png X Y W H # 同じ領域を左右に並べる
  python3 tools/pngtool.py mask A.png B.png OUT.png [--tol N] # 差分を赤で塗る

縮小表示された画像を目で比べると位置ズレやスケール差を誤読しやすい。
判断は必ず gate.py の数値で行い、これは「どこが変わったか当たりを付ける」用途に留めること。
"""
import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _png                                               # noqa: E402

cmd = sys.argv[1]

if cmd == "crop":
    w, h, ch, b = _png.load(sys.argv[2])
    x, y, cw, chh = map(int, sys.argv[4:8])
    cw, chh, o = _png.crop(w, h, ch, b, x, y, cw, chh)
    _png.save(sys.argv[3], cw, chh, ch, o)
    print(f"crop -> {sys.argv[3]} ({cw}x{chh})")

elif cmd == "sbs":
    x, y, cw, chh = map(int, sys.argv[5:9])
    w, h, ch, A = _png.load(sys.argv[2])
    _, _, _, B = _png.load(sys.argv[3])
    aw, ah, a = _png.crop(w, h, ch, A, x, y, cw, chh)
    bw, bh, b = _png.crop(w, h, ch, B, x, y, cw, chh)
    gap, ow = 8, aw + 8 + cw
    out = bytearray(b"\x20" * (ow * ah * ch))
    for j in range(ah):
        out[(j * ow) * ch:(j * ow + aw) * ch] = a[j * aw * ch:(j + 1) * aw * ch]
        s = (j * ow + aw + gap) * ch
        out[s:s + bw * ch] = b[j * bw * ch:(j + 1) * bw * ch]
    _png.save(sys.argv[4], ow, ah, ch, out)
    print(f"sbs -> {sys.argv[4]} ({ow}x{ah}) 左=A 右=B")

elif cmd == "mask":
    tol = int(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 2
    w, h, ch, A = _png.load(sys.argv[2])
    _, _, _, B = _png.load(sys.argv[3])
    out = bytearray(w * h * 3)
    for i in range(w * h):
        o = i * ch
        d = max(abs(A[o + k] - B[o + k]) for k in range(3))
        if d > tol:
            out[i * 3] = 255
        else:
            g = A[o] * 30 // 100 + A[o + 1] * 59 // 100 + A[o + 2] * 11 // 100
            out[i * 3] = out[i * 3 + 1] = out[i * 3 + 2] = 128 + g // 2
    _png.save(sys.argv[4], w, h, 3, out)
    print(f"mask -> {sys.argv[4]}（差分が赤）")

else:
    print(__doc__)
    sys.exit(1)
