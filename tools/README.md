# tools/ — LP の見た目とパフォーマンスを壊さないための検証ツール

`index.html` はインラインスタイルが 300 箇所以上あるベタ書き HTML なので、
文言や CSS を触ったときに**意図しない場所が動いていないか**を目で追うのは現実的ではない。
ここのスクリプトは、それを機械的に判定するためのもの。

PIL / numpy / Node.js は不要。**Python 3 と Google Chrome だけ**で動く。

## 使い方

```bash
# 1. 見た目の回帰チェック（いちばん使う）
python3 tools/gate.py

# 2. 狭い画面で横スクロールが出ていないか
python3 tools/viewport.py

# 3. 画像を作り直したあと、中身がちゃんと入っているか
python3 tools/verify_images.py
```

## 常用はしない（2026-08-11 以降の運用）

**`baseline/index-393.png` は古い。素で `gate.py` を叩くと必ず FAIL するが、それは
壊れているのではなく baseline を維持していないだけ。** 混乱しないこと。

以前は「編集したら基本この3つを流す」としていたが、毎回流すのは割に合わないので
やめた。文言修正や単一要素のインラインstyle変更は、影響がその場に閉じる
（カスケードが無いのがインラインstyleの数少ない利点）ので**何も流さなくてよい**。

流す価値があるのは、影響範囲が自分で追えない変更のときだけ:

- `<style>` ブロックを触った（全体に効くルールの追加・変更）
- 要素の追加・削除
- 画像の差し替え → `verify_images.py`
- 幅や折り返しに関わる変更 → `viewport.py`

### 使うときは baseline を「その場で」撮る

baseline を常に最新に保つ必要はない。**使う直前に変更前の状態を撮って、変更後と
比べる使い捨てスナップショット**として使えばいい。この使い方なら維持コストはゼロ。

```bash
python3 tools/gate.py --save    # 1. 変更前の状態を撮る
#   …HTML を変更する…
python3 tools/gate.py           # 2. 変更前と比較。差分の行が想定通りか見る
git checkout -- tools/baseline/index-393.png   # 3. 終わったら戻す（任意）
```

実例: `body{font-family}` と `button{font-family:inherit}` を足したときは、この手順で
差分が 138px / 3か所だけ（カルーセル矢印 `‹ ›` ×3）と確定でき、他は動いていないと
言い切れた。全体に効く CSS を足すときに一番効く。

## 各ツール

| ファイル | 役割 |
|---|---|
| `gate.py` | baseline とのピクセル比較。**画像の位置はブラウザから実測**して除外し、画像の中身は平均色と分散で別途チェックする |
| `viewport.py` | 320〜1440px での横スクロール計測 |
| `verify_images.py` | `img/` の画像を Chrome の canvas で実際にデコードし、中身が空でないか確認 |
| `pngtool.py` | スクショの切り出し・左右比較・差分マスク（目視で当たりを付ける用） |
| `_png.py` | PNG の読み書き（PIL 不要） |
| `_chrome.py` | headless Chrome のラッパ |
| `baseline/index-393.png` | 比較の基準スクショ |
| `ogp.html` | OGP画像（`img/pupless-ogp.jpg`）の版下。検証ツールではなく生成用 |
| `mark.html` | ファビコン／ブランドマークの版下。生成用 |
| `trust1.html` | `img/pupless-trust-1.jpg` の版下。生成用 |
| `cutout.swift` | 写真から被写体だけを切り抜く（背景透過PNG化）。生成用 |

## OGP画像の作り直し

`img/pupless-ogp.jpg`（1200x630、SNSシェア時のカード画像）は `tools/ogp.html` を
headless Chrome で撮って作っている。**価格改定・キャッチコピー変更・パウチ写真の
差し替えをしたら、作り直すこと。**

```bash
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CH" --headless=new --disable-gpu --hide-scrollbars \
      --force-device-scale-factor=2 --window-size=1200,630 \
      --virtual-time-budget=6000 \
      --screenshot=/tmp/ogp@2x.png "file://$PWD/tools/ogp.html"
sips -s format jpeg -s formatOptions 88 -z 630 1200 /tmp/ogp@2x.png \
     --out img/pupless-ogp.jpg
```

- 2倍(2400x1260)で撮ってから 1200x630 に縮小している。文字のジャギーを消すため。
- `--virtual-time-budget` は Google Fonts (Noto Sans JP) の読み込み待ち。短いと
  フォントが当たる前に撮れてしまい、字面が変わる。
- パウチ写真は白背景のJPGを `mix-blend-mode:multiply` で背景に馴染ませている。
  `filter` を足すと合成コンテキストが分離してこれが効かなくなるので注意。
- **`tools/ogp.html` の価格は index.html と二重管理**。連動していないので、
  改定時は両方直す。詳細はファイル冒頭のコメントに書いた。
- ブランドマーク（`img/pupless-mark.png`）を作り直したら、OGPも撮り直すこと。
  OGPの左上にこのマークを置いている。

## ファビコン／ブランドマークの作り直し

元データは `uploads/pupless-mark-src.png`（背景透過・1536x1024、円は中央やや上）。
`tools/mark.html` が、この円の部分だけを 512x512 に切り出す枠になっている。

```bash
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 1. 透過版（ファビコン用のマスター）
"$CH" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
      --default-background-color=00000000 --force-device-scale-factor=1 \
      --window-size=512,512 --virtual-time-budget=6000 \
      --screenshot=img/pupless-mark.png "file://$PWD/tools/mark.html"

# 2. 白背景版（apple-touch-icon 用）
"$CH" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
      --default-background-color=ffffffff --force-device-scale-factor=1 \
      --window-size=512,512 --virtual-time-budget=6000 \
      --screenshot=/tmp/mark-white.png "file://$PWD/tools/mark.html"

# 3. 各サイズへ縮小
sips -Z 192 img/pupless-mark.png --out img/favicon-192.png
sips -Z 32  img/pupless-mark.png --out img/favicon-32.png
sips -Z 180 /tmp/mark-white.png  --out img/apple-touch-icon.png
```

**共通フラグを変数にまとめて `$COMMON` と展開する書き方はしないこと。**
このマシンのシェルは zsh で、zsh はクォートしない変数展開を単語分割しない。
フラグ全体が1個の引数として渡り、`--window-size` が無視されて 512x512 にならない
（実際に踏んだ。出力が 756x469 になり、気づかないと壊れたファビコンが commit される）。

- **`apple-touch-icon.png` だけ白背景**にしている。iOS はホーム画面アイコンの透過部分を
  黒で塗りつぶすため、透過のまま渡すと黒い角が出る。
- `--allow-file-access-from-files` が無いと `file://` のページから画像を読めない。
- 元画像内の円の位置（left=343 top=80 w=849 h=846）は Chrome の canvas で画素を
  走査して実測した値。**元データを差し替えたら、この座標も測り直すこと**。
  `mark.html` の CSS にべた書きしてある。

## 返金保証タイルの画像（pupless-trust-1）

置き場所の枠が `aspect-ratio: 1/1` の正方形で、`object-fit: cover` が掛かっている。
**縦長の画像をそのまま入れると上下が切れてパッケージが見切れる**（実際にそうなった）。
`tools/trust1.html` は、元データの被写体を余白付きで 800x800 の正方形に収める枠。
生成方法は `mark.html` と同じ。

現在の元データは `uploads/pupless-trust-1-square.png`（1254x1254）。
`uploads/pupless-trust-1.png`（1122x1402の縦長）は一つ前の版で、戻せるように残してある。
切り替え方は `trust1.html` の冒頭コメントに書いた。

```bash
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CH" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
      --force-device-scale-factor=1 --window-size=800,800 --virtual-time-budget=6000 \
      --screenshot=/tmp/trust1.png "file://$PWD/tools/trust1.html"
sips -s format jpeg -s formatOptions 88 /tmp/trust1.png --out img/pupless-trust-1.jpg
sips -s format avif -s formatOptions 62 /tmp/trust1.png --out img/pupless-trust-1.avif
```

被写体の位置（現データは bbox 300,219-1034,1063）も canvas で実測した値で、
`trust1.html` の CSS にべた書きしてある。**元データを差し替えたら測り直すこと。**
元データが正方形でも被写体が中央に写っているとは限らない（現データは右下寄り）。

背景が白でよければ、切り抜きは要らない。元写真の地色を `brightness()` で 255 に
上げるだけでカードの白と地続きになり、離れた粒も元の影もそのまま残る。
切り抜きが要るのは、白以外の背景に載せたいときだけ。

生成AIに作らせたパッケージ画像は、**毎回どこかの文字が崩れていないか確認すること。**
現データも右下バッジの「理想の」が崩れている（表示サイズでは読めないので許容した）。
拡大して確認する例:

```bash
sips -r 180 uploads/pupless-trust-1-square.png --out /tmp/rot.png  # 写真が上下逆なので
open /tmp/rot.png
```

## 背景の切り抜き（cutout.swift）

**現在このLPでは使っていない**（trust-1 は白背景なので切り抜き不要になった）。
白以外の背景に商品を載せたくなったときのために残してある。

macOS の Vision framework（`VNGenerateForegroundInstanceMaskRequest`）で、写真から
被写体だけを抜いて背景透過PNGにする。Python も外部ライブラリも要らない。

```bash
swiftc -O tools/cutout.swift -o /tmp/cutout
/tmp/cutout uploads/pupless-trust-1.png uploads/pupless-trust-1-cutout.png
```

- **生成AIに「背景透過で」と頼んで出てくる画像は、透過ではないことがある。**
  市松模様を「絵として」描いただけで、アルファチャンネルを持たない。実際に踏んだ。
  受け取ったら必ず `sips -g hasAlpha <file>` で確認する（`no` なら透過していない）。
  カラータイプまで見るなら PNG ヘッダの IHDR 14バイト目（2=RGB, 6=RGBA）。
- **被写体として認識された1塊だけが残る。** trust-1 では、パウチから離れて転がっている
  粒が背景と判定されて消えた。切り抜き後は必ず何が消えたか確認すること。
- 切り抜くと元の影も消えるので、接地感は CSS の `drop-shadow` で足す。

## ハマりどころ（実際に踏んだもの）

### 1. Chrome headless の最小ウィンドウ幅は 500px

`--window-size=320` を指定しても実際には 500px で描画される。
**393px 未満の検証は `--window-size` ではできない。**
`viewport.py` は目的の幅を持つ iframe に対象ページを載せることでこれを回避している。

### 2. PNG のバイト比較は使えない

同じページを 2 回撮っただけで PNG のバイト列が変わる（エンコーダが非決定的）。
一方で**画素レベルでは決定的**なので、`gate.py` は画素を tol=2 で比較している。
この条件なら同一ページの撮り直しで差分 0 になることを確認済み。

### 3. 画像帯を除外するだけだと「画像が消えている」のを見逃す

画像を再エンコードすると画像領域に差分が出るため除外比較が必要だが、
除外しただけだと**画像が丸ごと表示されていない事故を検出できない**。
実際にヒーロー画像が真っ白になっているのを見逃した。
`gate.py` は除外に加えて、各画像領域の**平均色と分散**を baseline と比較している。

### 4. sips は無音で壊れた AVIF を出すことがある

ファイルサイズは妥当、`complete` は true、`naturalWidth` も正しいのに、
デコードすると全画素が `rgba(0,0,0,0)` になる。エラーも出ない。
**出力サイズ依存**で、`786x1703` と `800x1733` では壊れ、`852x1846` と
`768x1664` では正常だった。画像を作り直したら必ず `verify_images.py` を通すこと。

### 5. `width`/`height` 属性は CSS の `height` とセットで

CSS 側に `height` の指定がない `<img>` に `height` 属性を付けると、
属性値が presentational hint として**実際の高さ**になり画像が伸びる。
`height: auto` を必ず併記する。

### 6. リサイズで縦横比が変わると下の要素が全部ずれる

元画像 823x1115 を幅 642 にリサイズすると 642x869 になり、比が僅かに変わって
表示高さが 0.4px ずれ、**以降の全要素に伝播**した。
`aspect-ratio` を元画像の比で固定して吸収している。

## 画像を差し替えるとき

```bash
# 例: 表示実寸の2倍を目安にリサイズし、AVIF と JPEG を作る
sips --resampleWidth 600 assets/foo.png --out img/foo.avif \
     --setProperty format avif --setProperty formatOptions 80
sips --resampleWidth 600 assets/foo.png --out img/foo.jpg \
     --setProperty format jpeg --setProperty formatOptions 82

python3 tools/verify_images.py     # ← 必ず通す
python3 tools/gate.py
```

元画像（マスター）は `assets/` と `uploads/` に置いてある。
公開に必要なのは `index.html` / `privacy-policy.html` / `tokushoho.html` / `img/` のみ。

## 公開時の注意

- `.avif` は `image/avif` で配信すること。`<picture>` は `<source>` を選んだあとに
  読み込みが失敗しても `<img>` にフォールバックしないため、MIME を厳格に扱う
  ブラウザだと画像が出なくなる（Live Server は `application/octet-stream` を返す）
- HTML は CSS/JS をインライン化しているため、gzip / brotli を有効にすること
