#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布依赖预检：Python 包、ffprobe、可选 CDP 环境。

用法: python3 check_dependencies.py
退出码 0 = 必需项齐全；非 0 = 缺必需项。
"""
from __future__ import annotations

import importlib.util
import shutil
import sys

REQUIRED = {"requests": "requests"}
OPTIONAL = {
    "websockets": "websockets（仅 macOS CDP 提取登录态需要）",
    "PIL": "Pillow（仅封面尺寸校验需要）",
}


def has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def main() -> int:
    failures: list[str] = []
    print("== bilibili-publish 依赖预检 ==\n")

    for module, display in REQUIRED.items():
        ok = has(module)
        print(f"[{'ok' if ok else '缺'}] {display}")
        if not ok:
            failures.append(display)

    for module, display in OPTIONAL.items():
        ok = has(module)
        print(f"[{'ok' if ok else '可选缺失'}] {display}")

    for exe in ("ffprobe", "ffmpeg"):
        path = shutil.which(exe)
        print(f"[{'ok' if path else '缺'}] {exe}" + (f" -> {path}" if path else ""))
        if exe == "ffprobe" and not path:
            failures.append("ffprobe")

    import os

    if sys.platform == "darwin":
        app = "/Applications/哔哩哔哩.app"
        ok = os.path.isdir(app)
        print(f"[{'ok' if ok else '缺'}] 哔哩哔哩客户端（CDP 取登录态用）")
        print("[info] 取登录态: ./scripts/extract_bili_login_macos.sh")
    elif sys.platform == "win32":
        # The Windows launcher auto-detects the client; we cannot verify it
        # from here without launching it, so just report that support exists.
        print("[info] Windows: 自动检测；若失败请用 -ExePath 指定 bilibili.exe")
        print("[info] 取登录态: powershell -ExecutionPolicy Bypass "
              "-File .\\scripts\\extract_bili_login_windows.ps1")
        print("[warn] Windows 脚本未经实机测试，仅供参考；详见 references/windows-cookies.md")
    else:
        print(f"[info] 当前平台 {sys.platform}：没有一键取登录态脚本，请提供 cookies.json")

    print()
    if failures:
        print("缺少必需项: " + ", ".join(failures))
        print("安装示例: python3 -m pip install requests websockets Pillow")
        return 1
    print("必需依赖齐全。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
