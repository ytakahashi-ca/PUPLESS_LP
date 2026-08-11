#!/usr/bin/env python3
"""img/ の画像が「中身の入った画像として実際にデコードできるか」を検証する。

  python3 tools/verify_images.py

## なぜ必要か

macOS の sips は **無音で壊れた AVIF を出力することがある**。
ファイルサイズも妥当、`<img>` の complete も true、naturalWidth も正しい値なのに、
デコードすると全画素が rgba(0,0,0,0) になる、という壊れ方をする。
実際に FV のヒーロー画像がこれで表示されなくなった。

そのため画像を作り直したら必ずこれを通すこと。Chrome の canvas で
各画像を 9 点サンプリングし、中身があるかを確認する。
"""
import sys, subprocess, pathlib, re, html, json

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _chrome                                            # noqa: E402

PROJ = _chrome.PROJ

PAGE = """<body><script>
var files = %s, out = [], n = 0;
function done(){ if (++n === files.length) document.title = 'R|' + out.join(' ## '); }
files.forEach(function(f){
  var im = new Image();
  im.onload = function(){
    var c = document.createElement('canvas');
    c.width = im.naturalWidth; c.height = im.naturalHeight;
    var x = c.getContext('2d'); x.drawImage(im, 0, 0);
    var opaque = 0, nonblack = 0, tot = 0;
    [0.25, 0.5, 0.75].forEach(function(fx){
      [0.25, 0.5, 0.75].forEach(function(fy){
        var d = x.getImageData(Math.floor(im.naturalWidth * fx),
                               Math.floor(im.naturalHeight * fy), 1, 1).data;
        tot++; if (d[3] > 10) opaque++; if (d[0] + d[1] + d[2] > 24) nonblack++;
      });
    });
    out.push(f + '|' + im.naturalWidth + 'x' + im.naturalHeight +
             '|' + opaque + '|' + nonblack + '|' + tot);
    done();
  };
  im.onerror = function(){ out.push(f + '|ERROR|0|0|0'); done(); };
  im.src = './img/' + f;
});
</script></body>"""


def main():
    files = sorted(p.name for p in (PROJ / "img").iterdir()
                   if p.suffix.lower() in (".avif", ".jpg", ".jpeg", ".png", ".webp"))
    if not files:
        print("img/ に画像がありません"); return 2

    tmp = PROJ / "_verify_images.html"
    tmp.write_text(PAGE % json.dumps(files), encoding="utf-8")
    try:
        out = subprocess.run(
            [_chrome.CHROME, "--headless=new", "--disable-gpu",
             "--allow-file-access-from-files", "--window-size=500,500",
             "--virtual-time-budget=30000", "--dump-dom", f"file://{tmp}"],
            capture_output=True, text=True).stdout
        m = re.search(r"<title>(.*?)</title>", out, re.S)
        if not m or "R|" not in m.group(1):
            print("検証ページの読み込みに失敗しました"); return 2
        rows = html.unescape(m.group(1)).replace("R|", "").split(" ## ")
    finally:
        tmp.unlink(missing_ok=True)

    bad = []
    print(f"{'ファイル':34}{'寸法':>12}{'不透明':>8}{'非黒':>7}  判定")
    for r in sorted(rows):
        f, dim, op, nb, tot = r.split("|")
        ok = dim != "ERROR" and int(op) >= 5 and int(nb) >= 3
        if not ok: bad.append(f)
        print(f"{f:34}{dim:>12}{op + '/' + tot:>8}{nb + '/' + tot:>7}  "
              f"{'OK' if ok else '★中身が空'}")

    print()
    if bad:
        print(f"FAIL: {len(bad)}件が壊れています -> {bad}")
        print("      sips で別サイズに作り直して再検証してください")
        print("      （786x1703 と 800x1733 で壊れ、852x1846 と 768x1664 では正常だった実績あり）")
        return 1
    print(f"PASS: {len(rows)}件すべて正常にデコードできました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
