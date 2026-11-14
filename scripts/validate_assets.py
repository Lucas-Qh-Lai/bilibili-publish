#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布前素材校验：视频编码/分辨率/帧率/音轨、封面尺寸、元数据长度与 UTF-8。

用法:
  python3 validate_assets.py --video final.mp4 --cover cover16x9.png \
      --publish-json publish.json [--cover43 cover4x3.png]

退出码 0 = 通过；非 0 = 不通过（原因打印到 stderr）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# B 站 Web 投稿链路能接收的容器与编码。
# H.264 是最省心的选择；HEVC/AV1 也能上传，但平台会自行转码，
# 画质取决于平台压制策略（详见 references/video-specs.md）。
ALLOWED_VIDEO_CODECS = {"h264", "hevc", "av1"}
ALLOWED_VIDEO_CONTAINERS = {".mp4", ".mov", ".mkv", ".flv", ".m4v", ".avi"}
# 平台按 44.1kHz / 48kHz 分别处理音轨，两种都能上传。
ALLOWED_AUDIO_SAMPLE_RATES = {"44100", "48000"}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def probe_video(path: Path) -> dict:
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-show_entries", "stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
                "-of", "json", str(path),
            ],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError:
        fail("找不到 ffprobe，请先安装 ffmpeg")
    except subprocess.CalledProcessError as exc:
        fail(f"ffprobe 读取失败: {exc.stderr.strip()[:200]}")
    return json.loads(proc.stdout)


def check_cover(path: Path, expected: tuple[int, int], label: str) -> None:
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        print(f"WARN: 未安装 Pillow，跳过 {label} 尺寸校验", file=sys.stderr)
        return
    with Image.open(path) as image:
        if image.size != expected:
            fail(f"{label} 必须是 {expected[0]}x{expected[1]}，实际 {image.size}")
        if image.mode not in ("RGB", "RGBA", "P"):
            fail(f"{label} 色彩模式异常: {image.mode}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--cover", required=True, help="16:9 封面")
    ap.add_argument("--cover43", help="4:3 封面（可选）")
    ap.add_argument("--publish-json", required=True)
    ap.add_argument("--allow-size", default="1920x1080",
                    help="允许的视频分辨率，默认 1920x1080")
    args = ap.parse_args()

    video = Path(args.video).expanduser().resolve()
    cover = Path(args.cover).expanduser().resolve()
    cover43 = Path(args.cover43).expanduser().resolve() if args.cover43 else None
    config = Path(args.publish_json).expanduser().resolve()

    targets = [("视频", video), ("16:9 封面", cover), ("publish.json", config)]
    if cover43:
        targets.append(("4:3 封面", cover43))
    for label, path in targets:
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"{label} 不存在或为空: {path}")

    data = probe_video(video)
    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if not video_streams:
        fail("视频缺少视频流")
    if not audio_streams:
        fail("视频缺少音频流")
    v, a = video_streams[0], audio_streams[0]

    container = video.suffix.lower()
    if container not in ALLOWED_VIDEO_CONTAINERS:
        fail(
            f"容器格式必须是 {'/'.join(sorted(ALLOWED_VIDEO_CONTAINERS))}，实际 {container or '无扩展名'}"
        )

    expected_w, expected_h = (int(x) for x in args.allow_size.lower().split("x"))
    if (v.get("width"), v.get("height")) != (expected_w, expected_h):
        fail(f"视频分辨率必须是 {expected_w}x{expected_h}，实际 {v.get('width')}x{v.get('height')}")
    video_codec = str(v.get("codec_name") or "")
    if video_codec not in ALLOWED_VIDEO_CODECS:
        fail(
            f"视频编码必须是 {'/'.join(sorted(ALLOWED_VIDEO_CODECS))}，实际 {video_codec}"
        )
    if a.get("codec_name") != "aac":
        fail(f"音频编码必须是 aac，实际 {a.get('codec_name')}")
    sample_rate = str(a.get("sample_rate"))
    if sample_rate not in ALLOWED_AUDIO_SAMPLE_RATES:
        fail(
            f"音频采样率必须是 {'/'.join(ALLOWED_AUDIO_SAMPLE_RATES)}，实际 {sample_rate}"
        )

    num, den = (v.get("r_frame_rate") or "0/1").split("/", 1)
    fps = float(num) / float(den or 1)
    if abs(fps - 30.0) > 0.01:
        print(f"WARN: 视频帧率为 {fps:g}fps（B 站推荐 30fps，不是硬性失败）", file=sys.stderr)

    check_cover(cover, (1920, 1080), "16:9 封面")
    if cover43:
        check_cover(cover43, (1440, 1080), "4:3 封面")

    try:
        meta = json.loads(config.read_text(encoding="utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f"publish.json 不是合法 UTF-8 JSON: {exc}")

    title = meta.get("title", "")
    desc = meta.get("desc", "")
    tags = [t.strip() for t in (meta.get("tag") or "").split(",") if t.strip()]
    if not title or len(title) > 80:
        fail(f"title 必须 1-80 字，实际 {len(title)}")
    if not desc or len(desc) > 2000:
        fail(f"desc 必须 1-2000 字，实际 {len(desc)}")
    if not 1 <= len(tags) <= 10:
        fail(f"tag 必须 1-10 个，实际 {len(tags)}")
    if not isinstance(meta.get("tid"), int):
        fail("tid 必须是整数")

    text = "\n".join([title, desc, *tags])
    if "\ufffd" in text:
        fail("元数据含 U+FFFD，编码已损坏")
    if "??" in text:
        fail("元数据疑似乱码（'??'），中文已被转成问号")
    if "?" in text:
        print("WARN: 元数据含 '?'，请确认是刻意写的", file=sys.stderr)

    duration = float((data.get("format") or {}).get("duration") or 0)
    print(json.dumps({
        "video": str(video),
        "duration_seconds": round(duration, 3),
        "container": container.lstrip("."),
        "video_spec": f"{v.get('width')}x{v.get('height')} {v.get('codec_name')} {fps:g}fps",
        "audio_spec": f"{a.get('codec_name')} {a.get('sample_rate')}Hz",
        "cover_16x9": str(cover),
        "cover_4x3": str(cover43) if cover43 else None,
        "title_chars": len(title),
        "desc_chars": len(desc),
        "tags": tags,
    }, ensure_ascii=False, indent=2))
    print("OK: 素材校验通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
