#!/usr/bin/env python3
"""headless Chrome の共通ラッパ。

注意: Chrome headless は最小ウィンドウ幅が 500px で、--window-size=320 などを
指定しても実際には 500px で描画される。狭い幅を再現したいときは iframe に
目的の幅を与える（shot_width / probe_in_iframe）。
"""
import subprocess, pathlib, tempfile, re, html, json

PROJ = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# アニメーションが完全に収束するまで仮想時間を進める
BUDGET = "25000"


def _run(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def screenshot(url, out, w=393, h=9000):
    """ページ全体のスクショ。w は 500 未満だと Chrome 側で 500 に切り上がる点に注意
    （baseline との比較用途では両者同条件なので問題ない）。"""
    _run([CHROME, "--headless=new", "--hide-scrollbars", "--disable-gpu",
          f"--window-size={w},{h}", f"--virtual-time-budget={BUDGET}",
          f"--screenshot={out}", url])
    return out


def dump_with_script(page_rel, script, w=393, h=9000):
    """対象ページに計測スクリプトを差し込んで document.title 経由で結果を取り出す。
    結果は 'R|a ## b ## c' 形式で返す想定。"""
    src = (PROJ / page_rel).read_text(encoding="utf-8")
    tmp = PROJ / "_tool_probe.html"
    tmp.write_text(src.replace("</body>", f"<script>{script}</script></body>", 1),
                   encoding="utf-8")
    try:
        out = _run([CHROME, "--headless=new", "--disable-gpu",
                    f"--window-size={w},{h}", f"--virtual-time-budget={BUDGET}",
                    "--dump-dom", f"file://{tmp}"])
        m = re.search(r"<title>(.*?)</title>", out, re.S)
        if not m or "R|" not in m.group(1):
            return None
        return html.unescape(m.group(1)).replace("R|", "").split(" ## ")
    finally:
        tmp.unlink(missing_ok=True)


def iframe_page(page_rel, width, height, script=""):
    """指定幅の iframe に対象ページを載せた一時ページを作り、そのパスを返す。
    Chrome の最小幅 500px を回避して“本物の”狭いビューポートを作るための仕掛け。"""
    tmp = PROJ / "_tool_vp.html"
    tmp.write_text(
        f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;background:#fff}}
iframe{{width:{width}px;height:{height}px;border:0;display:block}}</style></head>
<body><iframe id="F" src="./{page_rel}"></iframe>{script}</body></html>""",
        encoding="utf-8")
    return tmp
