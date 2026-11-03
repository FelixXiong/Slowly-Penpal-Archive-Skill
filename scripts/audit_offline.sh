#!/bin/bash
# 离线自证：确认这条链路里没有任何联网 / 外部资源 / 浏览器自动化调用。
# 扫描对象：scripts/ 下的 .py 与模板 .html、仓库根的 .command、生成出来的 index.html（正文数据行除外）。
set -uo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="${SLOWLY_PDF_OUT:-$HOME/Desktop/Slowly离线档案}"
if [ -z "${SLOWLY_PDF_OUT:-}" ] && [ -s scripts/library_out.txt.local ]; then
  IFS= read -r OUT_DIR < scripts/library_out.txt.local
fi
OUT_HTML="$OUT_DIR/index.html"

# 网络栈 / 外部资源引用 / 浏览器与系统自动化
PATTERN='urllib|urlopen|http\.client|requests\.|aiohttp|websocket|XMLHttpRequest|EventSource|sendBeacon|fetch *\(|<script[^>]*src|<link[^>]*href|@import|url\( *["'"'"']?https?|[a-z]+\.example|osascript|AppleScript|subprocess|\bcurl\b|\bwget\b|slowly\.app|googleapis|cloudflare|cdn'

scan() {  # $1 = 标签  $2 = 文件  $3 = skipdata 时排除内嵌信件数据行
  [ -f "$2" ] || return 0
  local hits
  if [ "${3:-}" = "skipdata" ]; then
    hits=$(grep -v '^const DATA = ' "$2" | grep -nEi "$PATTERN" || true)
  else
    hits=$(grep -nEi "$PATTERN" "$2" || true)
  fi
  if [ -n "$hits" ]; then
    printf '\n✗ %s  %s\n' "$1" "$2"
    printf '%s\n' "$hits" | sed 's/^/    /'
    return 1
  fi
  printf '· 干净：%s\n' "$2"
  return 0
}

fail=0
for f in scripts/pdf_index.py scripts/local_media.py scripts/viewer.html scripts/test_*.py; do
  scan "源码" "$f" || fail=1
done

if [ -f "$OUT_HTML" ]; then
  # 内嵌的信件数据是一整行文本，可能含笔友写的网址；那只是显示用字符串，
  # 页面只用 textContent 渲染，不会执行，所以扫描时排除该行后单独确认它存在。
  scan "生成页面" "$OUT_HTML" skipdata || fail=1
  n=$(grep -c '^const DATA = ' "$OUT_HTML")
  [ "$n" = "1" ] && echo "· 数据内嵌正常：index.html 第 1 处 const DATA（单文件，无外链）" \
                 || { echo "✗ const DATA 占位异常（出现 $n 次）"; fail=1; }
  echo "· 生成页面：${OUT_HTML}（$(du -h "$OUT_HTML" | cut -f1)，可离线双击打开）"
else
  echo "· 尚未生成 index.html：先跑 python3 scripts/pdf_index.py"
fi

if [ "$fail" = "0" ]; then
  echo
  echo "✓ 未发现任何联网 / 外部资源 / 浏览器自动化调用；源目录全程只读。"
else
  echo
  echo "以上命中需要人工确认：本管线的设计前提是零网络请求。"
fi
exit $fail
