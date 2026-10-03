#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把已经渲染好的视频投稿到 B 站（bilibili-publish）。

职责边界：只做发布。不做文案、配音、封面设计、剪辑或渲染。

投稿链路（B 站网页投稿接口的固有顺序）：
    封面上传 -> 申请上传凭据 -> 开启分片会话 -> 逐片上传 -> 封口
    -> 调用 add/v3 建立稿件

用法：
    publish_bilibili.py --video 成片.mp4 --cover 封面16x9.png \
        --cookies cookies.json --config publish.json
    publish_bilibili.py --video 成片.mp4 --cover 封面16x9.png \
        --cover43 封面4x3.png --cookies cookies.json --config publish.json

凭据：cookies.json 必须含有 SESSDATA 与 bili_jct。它是一次性凭据，
用完即删，不要提交到版本库，也不要写进任何报告。
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

COVER_API = "https://member.bilibili.com/x/vu/web/cover/up"
TICKET_API = "https://member.bilibili.com/preupload"
SUBMIT_API = "https://member.bilibili.com/x/vu/web/add/v3"
GEETEST_WARMUP = "https://member.bilibili.com/x/geetest/pre/add"

PART_RETRIES = 4
RETRY_BACKOFF_SECONDS = 3
MAX_TITLE = 80
MAX_DESC = 2000
MAX_TAGS = 10

TITLE_LIMIT, DESC_LIMIT, TAG_LIMIT = MAX_TITLE, MAX_DESC, MAX_TAGS


class PublishError(RuntimeError):
    """投稿过程中任何不可继续的失败。"""


def emit(message: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    print(f"{stamp} | {message}", flush=True)


def _json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise PublishError(f"响应不是 JSON (HTTP {response.status_code}): {response.text[:200]}") from exc
    if not isinstance(payload, dict):
        raise PublishError(f"响应结构异常: {payload!r}")
    return payload


def read_utf8_json(path: str | Path, label: str) -> dict[str, Any]:
    """读 JSON。容错 PowerShell 写出的 BOM（utf-8-sig）。"""
    try:
        raw = Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise PublishError(f"读不到{label}: {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PublishError(f"{label} 不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PublishError(f"{label} 顶层必须是对象")
    return data


def inspect_metadata(cfg: dict[str, Any]) -> list[str]:
    """发布前的元数据体检，返回警告列表；硬性问题直接抛错。"""
    title = str(cfg.get("title") or "")
    desc = str(cfg.get("desc") or "")
    raw_tags = cfg.get("tag") or ""
    tags = [t.strip() for t in str(raw_tags).split(",") if t.strip()]

    if not title:
        raise PublishError("title 不能为空")
    if len(title) > TITLE_LIMIT:
        raise PublishError(f"title 超长：{len(title)} > {TITLE_LIMIT}")
    if not desc:
        raise PublishError("desc 不能为空")
    if len(desc) > DESC_LIMIT:
        raise PublishError(f"desc 超长：{len(desc)} > {DESC_LIMIT}")
    if not tags:
        raise PublishError("tag 不能为空")
    if len(tags) > TAG_LIMIT:
        raise PublishError(f"tag 过多：{len(tags)} > {TAG_LIMIT}")
    if not isinstance(cfg.get("tid"), int):
        raise PublishError("tid 必须是整数分区 ID")

    joined = "\n".join([title, desc, *tags])
    if "\ufffd" in joined:
        raise PublishError("元数据含 U+FFFD，说明写入时就损坏了，先修 UTF-8")
    if "??" in joined:
        raise PublishError("元数据出现 '??'，中文疑似被转成问号，先修 UTF-8")

    warnings: list[str] = []
    if "?" in joined:
        warnings.append("元数据含 '?'，请确认是刻意写的而不是编码损坏")
    return warnings


class BilibiliPublisher:
    """一次投稿会话。"""

    def __init__(self, cookies: dict[str, str]) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": BROWSER_UA,
            "Referer": "https://member.bilibili.com/",
            "Origin": "https://member.bilibili.com",
        })
        self.session.cookies.update(cookies)
        self.csrf = str(cookies["bili_jct"])

    # ---------- 封面 ----------

    def upload_cover(self, image_path: str | Path, label: str) -> str:
        path = Path(image_path)
        if not path.is_file():
            raise PublishError(f"{label}不存在: {path}")
        payload = base64.b64encode(path.read_bytes()).decode()
        resp = self.session.post(
            COVER_API,
            params={"ts": int(time.time() * 1000)},
            data={"csrf": self.csrf, "cover": f"data:image/png;base64,{payload}"},
            timeout=60,
        )
        body = _json(resp)
        if body.get("code") != 0:
            raise PublishError(f"{label}上传失败: {body}")
        url = (body.get("data") or {}).get("url")
        if not url:
            raise PublishError(f"{label}上传成功但没拿到 URL: {body}")
        emit(f"{label}已上传")
        return url

    # ---------- 上传凭据 ----------

    def request_ticket(self, filename: str, size: int) -> dict[str, Any]:
        resp = self.session.get(
            TICKET_API,
            params={
                "name": filename,
                "size": size,
                "r": "upos",
                "profile": "ugcfx/bup",
                "ssl": 0,
                "version": "2.10.4.0",
                "build": "2140000",
                "webVersion": "2.13.0",
            },
            timeout=30,
        )
        body = _json(resp)
        if body.get("OK") != 1:
            raise PublishError(f"申请上传凭据失败: {body}")
        emit(f"凭据就绪 biz_id={body['biz_id']} 分片大小={body['chunk_size']}")
        return body

    def _upos_url(self, ticket: dict[str, Any]) -> str:
        endpoint = ticket["endpoint"]
        uri = str(ticket["upos_uri"]).replace("upos://", "")
        return f"https:{endpoint}/{uri}"

    def open_session(self, ticket: dict[str, Any], size: int) -> tuple[str, str]:
        url = self._upos_url(ticket)
        resp = requests.post(
            url,
            params={
                "uploads": "",
                "output": "json",
                "profile": "ugcfx/bup",
                "filesize": size,
                "partsize": ticket["chunk_size"],
                "biz_id": ticket["biz_id"],
            },
            headers={"X-Upos-Auth": ticket["auth"], "User-Agent": BROWSER_UA},
            timeout=30,
        )
        body = _json(resp)
        if body.get("OK") != 1:
            raise PublishError(f"开启分片会话失败: {body}")
        emit("分片会话已开启")
        return body["upload_id"], url

    # ---------- 分片 ----------

    def _send_part(self, url: str, auth: str, upload_id: str, blob: bytes,
                   index: int, total: int, total_bytes: int, offset: int) -> str:
        params = {
            "uploadId": upload_id,
            "chunks": total,
            "total": total_bytes,
            "chunk": index,
            "size": len(blob),
            "partNumber": index + 1,
            "start": offset,
            "end": offset + len(blob),
        }
        last_error = ""
        for attempt in range(1, PART_RETRIES + 1):
            try:
                resp = requests.put(
                    url,
                    params=params,
                    data=blob,
                    headers={
                        "X-Upos-Auth": auth,
                        "Content-Type": "application/octet-stream",
                        "User-Agent": BROWSER_UA,
                    },
                    timeout=240,
                )
                if resp.status_code == 200:
                    tag = resp.headers.get("ETag") or resp.headers.get("Etag") or "etag"
                    return tag.strip('"')
                last_error = f"HTTP {resp.status_code} {resp.text[:120]}"
            except requests.RequestException as exc:
                last_error = str(exc)
            if attempt < PART_RETRIES:
                emit(f"分片 {index + 1}/{total} 第 {attempt} 次未成功，重试")
                time.sleep(RETRY_BACKOFF_SECONDS)
        raise PublishError(f"分片 {index + 1}/{total} 上传失败：{last_error}")

    def send_parts(self, url: str, auth: str, upload_id: str,
                   video_path: str | Path, size: int, chunk_size: int) -> tuple[list[str], int]:
        total = math.ceil(size / chunk_size)
        emit(f"开始上传 {total} 个分片")
        etags: list[str] = []
        with open(video_path, "rb") as handle:
            for index in range(total):
                offset = index * chunk_size
                blob = handle.read(chunk_size)
                etag = self._send_part(url, auth, upload_id, blob, index, total, size, offset)
                etags.append(etag)
                emit(f"分片 {index + 1}/{total} 完成")
        return etags, total

    def seal(self, url: str, auth: str, upload_id: str, biz_id: str,
             filename: str, etags: list[str], total: int) -> None:
        parts = [{"partNumber": i + 1, "eTag": etags[i] if i < len(etags) else "etag"}
                 for i in range(total)]
        resp = requests.post(
            url,
            params={
                "name": filename,
                "uploadId": upload_id,
                "biz_id": biz_id,
                "output": "json",
                "profile": "ugcfx/bup",
            },
            json={"parts": parts},
            headers={
                "X-Upos-Auth": auth,
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": BROWSER_UA,
            },
            timeout=60,
        )
        body = _json(resp)
        if body.get("OK") != 1:
            raise PublishError(f"封口失败: {body}")
        emit("上传已封口")

    # ---------- 投稿 ----------

    def submit(self, cfg: dict[str, Any], cover_url: str, cover43_url: str,
               stem: str, cid: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "videos": [{
                "filename": stem,
                "title": cfg["title"],
                "desc": "",
                "cid": cid,
            }],
            "cover": cover_url,
            "cover43": cover43_url or "",
            "title": cfg["title"],
            "copyright": 1,
            "tid": cfg["tid"],
            "tag": cfg["tag"],
            "desc_format_id": 9999,
            "desc": cfg["desc"],
            "recreate": -1,
            "dynamic": cfg.get("dynamic", ""),
            "interactive": 0,
            "act_reserve_create": 0,
            "no_disturbance": 0,
            "no_reprint": int(cfg.get("no_reprint", 0)),
            "subtitle": {"open": 0, "lan": ""},
            "dolby": 0,
            "lossless_music": 0,
            "up_selection_reply": False,
            "up_close_reply": False,
            "up_close_danmu": False,
            "web_os": 3,
            "csrf": self.csrf,
        }
        if cfg.get("human_type2"):
            payload["human_type2"] = cfg["human_type2"]

        try:
            self.session.get(GEETEST_WARMUP, timeout=10)
        except requests.RequestException:
            pass

        resp = self.session.post(
            SUBMIT_API,
            params={"ts": int(time.time() * 1000), "csrf": self.csrf},
            json=payload,
            timeout=60,
        )
        body = _json(resp)
        if body.get("code") != 0:
            raise PublishError(f"投稿失败: {body}")
        emit("稿件已创建")
        return body["data"] or {}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="publish_bilibili.py",
        description="把已渲染好的视频投稿到 B 站（仅发布）",
    )
    parser.add_argument("--video", required=True, help="成片文件")
    parser.add_argument("--cover", required=True, help="16:9 封面 PNG")
    parser.add_argument("--cover43", help="4:3 封面 PNG（可选）")
    parser.add_argument("--cookies", required=True, help="含 SESSDATA 与 bili_jct 的 cookie JSON")
    parser.add_argument("--config", required=True, help="publish.json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    cookies = read_utf8_json(args.cookies, "cookies")
    missing = [k for k in ("SESSDATA", "bili_jct") if not cookies.get(k)]
    if missing:
        raise PublishError(
            "cookies 缺少 " + "、".join(missing) +
            "；请先用 scripts/extract_bili_login_macos.sh 从已登录的哔哩哔哩客户端提取"
        )

    cfg = read_utf8_json(args.config, "publish.json")
    for warning in inspect_metadata(cfg):
        emit(f"注意：{warning}")

    video = Path(args.video)
    if not video.is_file():
        raise PublishError(f"视频不存在: {video}")
    size = video.stat().st_size
    filename = video.name
    emit(f"开始投稿 {filename}（{size} 字节）")

    publisher = BilibiliPublisher(cookies)
    cover_url = publisher.upload_cover(args.cover, "16:9 封面")
    cover43_url = publisher.upload_cover(args.cover43, "4:3 封面") if args.cover43 else ""

    ticket = publisher.request_ticket(filename, size)
    upload_id, upos_url = publisher.open_session(ticket, size)
    etags, total = publisher.send_parts(
        upos_url, ticket["auth"], upload_id, video, size, ticket["chunk_size"]
    )
    publisher.seal(upos_url, ticket["auth"], upload_id, ticket["biz_id"], filename, etags, total)

    stem = os.path.splitext(str(ticket["upos_uri"]).split("/")[-1])[0]
    cid = str(ticket["biz_id"])
    emit(f"稿件文件名={stem} cid={cid}")

    data = publisher.submit(cfg, cover_url, cover43_url, stem, cid)
    bvid = data.get("bvid", "")
    aid = data.get("aid", "")
    emit(f"投稿成功 aid={aid} bvid={bvid}")
    if bvid:
        emit(f"链接 https://www.bilibili.com/video/{bvid}")

    receipt_path = Path(args.config).resolve().parent / "publish_result.json"
    receipt_path.write_text(
        json.dumps(
            {"code": 0, "data": data, "cover": cover_url, "cover43": cover43_url, **cfg},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    emit(f"回执已写入 {receipt_path}")
    emit("建议约 2 分钟后运行 verify_published.py 确认公开状态")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PublishError as error:
        print(f"失败: {error}", file=sys.stderr)
        sys.exit(1)
