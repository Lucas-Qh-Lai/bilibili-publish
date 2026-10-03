#!/bin/zsh
# 在 macOS 上从「哔哩哔哩」客户端提取投稿所需的登录 Cookie。
#
# 原理：客户端本身是 Chromium 内核，用调试端口重启后即可通过 CDP 读取
# 当前会话的 Cookie，无需（也无法）解密其本地数据库。
#
# 用法: ./extract_bili_login_macos.sh [调试端口] [输出文件]
#   默认: 9222 / cookies.json
set -euo pipefail

APP="/Applications/哔哩哔哩.app"
BIN="$APP/Contents/MacOS/哔哩哔哩"
PORT="${1:-9222}"
OUT="${2:-cookies.json}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

if [ ! -d "$APP" ]; then
  echo "错误：找不到 $APP" >&2
  exit 1
fi

echo "1/4 关闭正在运行的哔哩哔哩客户端"
osascript -e 'quit app "哔哩哔哩"' >/dev/null 2>&1 || true
sleep 1
pkill -f "$BIN" >/dev/null 2>&1 || true
sleep 1

echo "2/4 以调试端口 $PORT 重新启动"
open -a "$APP" --args --remote-debugging-port="$PORT"

echo "3/4 等待调试端口就绪"
ready=0
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "错误：调试端口 $PORT 未就绪。请确认客户端已登录后重试。" >&2
  exit 1
fi

echo "4/4 提取 Cookie 到 $OUT"
"$PYTHON" "$HERE/extract_bili_cookies.py" --cdp "http://127.0.0.1:$PORT" --out "$OUT"

echo "核对登录态"
"$PYTHON" - "$OUT" <<'PY'
import json
import sys
import urllib.request

with open(sys.argv[1], encoding="utf-8") as handle:
    cookies = json.load(handle)
header = "; ".join(f"{k}={v}" for k, v in cookies.items())
request = urllib.request.Request(
    "https://api.bilibili.com/x/web-interface/nav",
    headers={"Cookie": header, "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
)
try:
    body = json.loads(urllib.request.urlopen(request, timeout=10).read())
    data = body.get("data") or {}
    print(f"  code={body.get('code')} isLogin={data.get('isLogin')} uname={data.get('uname', '')}")
    print("  登录有效" if data.get("isLogin") else "  未登录，请先在客户端内登录")
except Exception as error:  # noqa: BLE001
    print(f"  核对失败: {error}")
PY
