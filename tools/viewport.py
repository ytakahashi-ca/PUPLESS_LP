#!/usr/bin/env python3
"""実機幅での横スクロール（はみ出し）を計測する。

  python3 tools/viewport.py                     # 既定の幅セットをまとめて確認
  python3 tools/viewport.py 320                 # 単一の幅
  python3 tools/viewport.py 320 --shot out.png  # その幅でスクショ

## 重要

Chrome headless は **最小ウィンドウ幅が 500px** で、`--window-size=320` を
指定しても実際には 500px で描画される。そのため 393px 未満の検証は
`--window-size` ではできない。ここでは目的の幅を持つ **iframe** に対象ページを
載せることで、本物の狭いビューポートを作っている。
"""
import sys, subprocess, pathlib, re, html, json

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _chrome                                            # noqa: E402

PROJ = _chrome.PROJ
DEFAULT_WIDTHS = [320, 360, 375, 393, 414, 430, 768, 1440]

PROBE = """
<script>
window.addEventListener('load', function(){ setTimeout(function(){
  var f = document.getElementById('F'), d = f.contentDocument;
  var de = d.documentElement, lim = de.clientWidth, off = [];
  d.querySelectorAll('*').forEach(function(el){
    var r = el.getBoundingClientRect();
    if (r.right > lim + 1 || r.left < -1) {
      var p = el.parentElement, inScroller = false;
      while (p) {                       // 横スクローラの中身は溢れて当然なので除外
        var ox = getComputedStyle(p).overflowX;
        if (ox === 'auto' || ox === 'scroll') { inScroller = true; break; }
        p = p.parentElement;
      }
      if (!inScroller && off.length < 10) {
        off.push('<' + el.tagName + '> w=' + Math.round(r.width) +
                 ' x[' + Math.round(r.left) + '..' + Math.round(r.right) + '] ' +
                 (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 24));
      }
    }
  });
  document.title = 'R|' + de.clientWidth + '|' +
                   Math.max(0, de.scrollWidth - de.clientWidth) + '|' + off.join(' // ');
}, 5000); });
</script>"""


def probe(page, width, height=2500, shot=None):
    tmp = _chrome.iframe_page(page, width, height, "" if shot else PROBE)
    try:
        args = [_chrome.CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--allow-file-access-from-files",
                f"--window-size={max(width, 500)},{height}",
                f"--virtual-time-budget={_chrome.BUDGET}"]
        if shot:
            subprocess.run(args + [f"--screenshot={shot}", f"file://{tmp}"],
                           capture_output=True)
            return None
        out = subprocess.run(args + ["--dump-dom", f"file://{tmp}"],
                             capture_output=True, text=True).stdout
        m = re.search(r"<title>R\|(\d+)\|(\d+)\|(.*?)</title>", out, re.S)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2)), html.unescape(m.group(3))
    finally:
        tmp.unlink(missing_ok=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    page = "index.html"
    widths = DEFAULT_WIDTHS
    if args and args[0].isdigit():
        widths = [int(args[0])]
    elif args:
        page = args[0]
        if len(args) > 1 and args[1].isdigit():
            widths = [int(args[1])]

    if "--shot" in sys.argv:
        out = sys.argv[sys.argv.index("--shot") + 1]
        probe(page, widths[0], 1400, shot=out)
        print(f"スクショ -> {out} (iframe幅 {widths[0]}px)")
        return 0

    ng = 0
    print(f"対象: {page}")
    for w in widths:
        r = probe(page, w)
        if not r:
            print(f"  {w:>5}px: 計測失敗"); ng += 1; continue
        actual, over, off = r
        mark = "OK" if over == 0 else "★はみ出し"
        print(f"  {w:>5}px (実測{actual}): はみ出し {over}px  {mark}")
        if off.strip():
            for o in off.split(" // ")[:5]:
                print(f"         {o}")
        if over: ng += 1
    print()
    print("PASS: どの幅でも横スクロールなし" if ng == 0 else f"FAIL: {ng}件で横スクロール発生")
    return 0 if ng == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
