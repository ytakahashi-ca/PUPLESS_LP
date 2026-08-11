#!/usr/bin/env python3
"""見た目の回帰ゲート。baseline と比較して「意図しない変化」を検出する。

  python3 tools/gate.py               # 比較する
  python3 tools/gate.py --save        # 今の状態を新しい baseline にする

## 何を見ているか

1. **画像帯の外側** … テキスト・余白・色・レイアウト。baseline と 1px でも
   違えば NG。画像の位置はブラウザから実測するのでハードコードしない。
2. **画像帯の中身** … 平均色と分散を baseline と比較する。
   画像を除外して比較するだけだと「画像が丸ごと表示されていない」のを
   見逃すため（実際に AVIF が壊れていたのを見落とした経緯がある）。

## 注意

画像を差し替えた／再エンコードしたときは 1 は 0 のままだが 2 に差が出る。
その場合は目視で確認したうえで --save で baseline を更新すること。
"""
import sys, pathlib, json, re, html

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _png, _chrome                                     # noqa: E402

PROJ = _chrome.PROJ
TOOLS = pathlib.Path(__file__).resolve().parent
BASE = TOOLS / "baseline" / "index-393.png"
SHOT = TOOLS / "baseline" / "_current.png"
PAGE = "index.html"
TOL = 2

PROBE = """
window.addEventListener('load', function(){ setTimeout(function(){
  var R = [];
  document.querySelectorAll('img').forEach(function(im){
    var r = im.getBoundingClientRect();
    R.push(Math.floor(r.top + scrollY) + ',' + Math.ceil(r.bottom + scrollY) + ',' +
           (im.currentSrc || '').split('/').pop());
  });
  document.title = 'R|' + R.join(' ## ');
}, 6000); });
"""


def image_bands():
    rows = _chrome.dump_with_script(PAGE, PROBE)
    if not rows:
        print("画像位置の取得に失敗しました"); sys.exit(2)
    out = []
    for r in rows:
        t, b, name = r.split(",", 2)
        out.append((max(0, int(t) - 2), int(b) + 2, name))
    return out


def main():
    save = "--save" in sys.argv
    _chrome.screenshot(f"file://{PROJ}/{PAGE}", str(SHOT))

    if save or not BASE.exists():
        SHOT.replace(BASE)
        print(f"baseline を更新しました: {BASE.relative_to(PROJ)}")
        return 0

    bands = image_bands()
    print(f"画像の y 範囲（{len(bands)}枚, ブラウザから実測）")

    w, h, ch, A = _png.load(str(BASE))
    w2, h2, _, B = _png.load(str(SHOT))
    if (w, h) != (w2, h2):
        print(f"NG: サイズ不一致 {w}x{h} vs {w2}x{h2}")
        return 2

    in_band = lambda y: any(t <= y < b for t, b, _ in bands)

    # 1) 画像帯の外側 ------------------------------------------------
    rows = _png.pixel_diff(A, B, w, h, ch, TOL, skip_rows=in_band)
    out_px = sum(rows.values())
    print(f"\n[1] 画像帯の外側の差分: {out_px} px  (0 なら レイアウト/テキストは不変)")
    if rows:
        ks = sorted(rows); runs = []; s0 = e0 = ks[0]
        for y in ks[1:]:
            if y <= e0 + 3: e0 = y
            else: runs.append((s0, e0)); s0 = e0 = y
        runs.append((s0, e0))
        print("    差分の行:", [f"{a}..{b}" for a, b in runs][:20])

    # 2) 画像帯の中身 ------------------------------------------------
    print("\n[2] 画像帯の中身（平均色と分散）")
    bad = []
    for t, b, name in bands:
        t2, b2 = max(0, t), min(h, b)
        if b2 <= t2: continue

        def stats(buf):
            tot = [0, 0, 0]; vals = []
            for y in range(t2, b2, 3):
                for x in range(0, w, 3):
                    o = (y * w + x) * ch
                    for k in range(3): tot[k] += buf[o + k]
                    vals.append(buf[o])
            n = len(vals)
            mu = sum(vals) / n
            return [v / n for v in tot], (sum((v - mu) ** 2 for v in vals) / n) ** 0.5

        ma, _ = stats(A)
        mb, sb = stats(B)
        dmean = max(abs(x - y) for x, y in zip(ma, mb))
        ng = dmean > 25 or sb < 3          # 単色に近い = 画像が出ていない
        if ng: bad.append(name)
        print(f"    {name:34} 平均色差={dmean:5.1f} 分散={sb:6.1f}  "
              f"{'★画像が出ていない可能性' if ng else 'OK'}")

    print()
    if out_px == 0 and not bad:
        print("PASS: 意図しない変化はありません")
        return 0
    if bad:
        print(f"FAIL: 画像が表示されていない可能性 -> {bad}")
    if out_px:
        print(f"FAIL: 画像帯の外側に {out_px} px の差分（文言変更なら想定内。"
              f"確認のうえ --save で baseline 更新）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
