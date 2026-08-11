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

編集したら基本この3つを流す。全部 PASS なら、レイアウト・横スクロール・画像に
問題は出ていない。

意図的に見た目を変えたとき（文言修正など）は `gate.py` が FAIL になるので、
差分の場所が想定通りかを確認したうえで baseline を更新する。

```bash
python3 tools/gate.py --save    # 今の状態を新しい baseline にする
```

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
