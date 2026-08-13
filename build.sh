#!/bin/bash
# 公開用の dist/ を組み立てる。Cloudflare Pages のビルドコマンドから呼ばれる。
#
# 公開するものだけをここに書く方式。ファイルを追加したら、このリストにも足すこと。
# 足し忘れるとリポジトリには在るのに本番に出ない、という状態になる。
#
# 意図的に含めていないもの:
#   tools/    検証用スクリプト（公開不要）
#   uploads/  加工前の元画像・下書き。どのページからも参照していない
set -eu

rm -rf dist
mkdir -p dist

# HTML とルート直下に置く必要があるファイル
cp index.html privacy-policy.html tokushoho.html dist/
cp robots.txt sitemap.xml dist/

# ページから参照している静的ファイル
cp -R assets img dist/

echo "dist/ に配置したもの:"
ls dist
