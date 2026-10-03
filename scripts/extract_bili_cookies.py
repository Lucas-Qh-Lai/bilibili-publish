#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本地 CDP 调试端口读取 B 站客户端的登录 Cookie。

只做一件事：连上 Chrome DevTools Protocol，把当前会话里我们需要的
Cookie 取出来写成 JSON。不解密、不读 SQLite。

前置：哔哩哔哩客户端已用调试端口启动并处于登录状态。
用法：
    python3 extract_bili_cookies.py --cdp http://127.0.0.1:9222 --out cookies.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Windows consoles often default to a legacy code page (cp936/cp1252) which
# cannot encode the Chinese status lines printed below. Force UTF-8 when the
# stream supports reconfiguration; ignore failure on exotic stdout objects.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

# 投稿与验证真正需要的字段，其余一律不落盘。
WANTED = (
    "SESSDATA",
    "bili_jct",
    "DedeUserID",
    "DedeUserID__ckMd5",
    "buvid3",
    "b_nut",
    "bili_ticket",
)

REQUIRED = ("SESSDATA", "bili_jct")


def list_targets(cdp_base: str) -> list[dict]:
    url = cdp_base.rstrip("/") + "/json/list"
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"{url} 返回的不是目标列表")
    return payload


async def dump_cookies(websocket_url: str) -> list[dict]:
    try:
        from websockets.asyncio.client import connect  # websockets >= 12
    except ImportError:  # pragma: no cover - 兼容旧版
        from websockets import connect  # type: ignore

    async with connect(websocket_url, max_size=64 * 1024 * 1024) as socket:
        await socket.send(json.dumps({"id": 1, "method": "Network.enable"}))
        await socket.recv()
        await socket.send(json.dumps({"id": 2, "method": "Network.getAllCookies"}))
        while True:
            frame = json.loads(await socket.recv())
            if frame.get("id") == 2:
                if "error" in frame:
                    raise RuntimeError(f"CDP 返回错误: {frame['error']}")
                return frame["result"]["cookies"]


def pick(cookies: list[dict]) -> dict[str, str]:
    found: dict[str, str] = {}
    for item in cookies:
        name = item.get("name", "")
        if name in WANTED and name not in found:
            found[name] = item.get("value", "")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="通过 CDP 读取 B 站客户端 Cookie")
    parser.add_argument("--cdp", default="http://127.0.0.1:9222")
    parser.add_argument("--out", default="cookies.json")
    args = parser.parse_args(argv)

    targets = list_targets(args.cdp)
    pages = [t for t in targets if t.get("type") == "page"]
    if not pages:
        raise SystemExit(f"CDP 上没有可用页面目标（共 {len(targets)} 个目标）")

    cookies = asyncio.run(dump_cookies(pages[0]["webSocketDebuggerUrl"]))
    print(f"CDP 共返回 {len(cookies)} 条 Cookie")

    keep = pick(cookies)
    for name in WANTED:
        state = "有" if keep.get(name) else "无"
        print(f"  {name}: {state}")

    out_path = Path(args.out)
    out_path.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
    # Tighten permissions where the platform supports POSIX modes. On Windows
    # this only clears the read-only flag, so rely on NTFS ACLs there instead.
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    print(f"已写入 {out_path}（{len(keep)} 条）")

    missing = [name for name in REQUIRED if not keep.get(name)]
    if missing:
        print(f"警告：缺少 {'、'.join(missing)}，客户端可能尚未登录", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
