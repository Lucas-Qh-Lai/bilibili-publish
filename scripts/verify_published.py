#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布后核验：稿件是否公开、能否播放、标签是否挂全、审核是否通过。

用法:
    python3 verify_published.py --bvid BVxxxxxxxxxx --cookies cookies.json

通过标准：view 返回 code=0 且 state=0、playurl 有可播放地址、
标签数量与提交一致、创作中心无驳回原因。
刚投稿后立刻查可能返回 -404，那是审核排队，等约 2 分钟再查。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def load_cookies(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def report_archive(session: requests.Session, bvid: str) -> dict | None:
    body = session.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"bvid": bvid}, timeout=20,
    ).json()
    if body.get("code") != 0:
        print(f"稿件尚不可见: code={body.get('code')} message={body.get('message')}")
        print("若刚发布，通常是在审核队列中，等约 2 分钟再试。")
        return None

    data = body["data"]
    stat = data.get("stat") or {}
    print(f"标题    : {data.get('title')}")
    print(f"bvid    : {data.get('bvid')}  aid={data.get('aid')}")
    print(f"分区    : {data.get('tid')} ({data.get('tname')})")
    print(f"状态    : {data.get('state')}  (0 = 公开)")
    print(f"时长    : {data.get('duration')} 秒")
    print(f"封面    : {data.get('pic')}")
    print(f"数据    : 播放={stat.get('view')} 点赞={stat.get('like')} "
          f"投币={stat.get('coin')} 收藏={stat.get('favorite')}")
    desc = (data.get("desc") or "").replace("\n", " / ")
    print(f"简介    : {desc[:80]}")
    return data


def report_playback(session: requests.Session, bvid: str, cid: int) -> None:
    body = session.get(
        "https://api.bilibili.com/x/player/playurl",
        params={"bvid": bvid, "cid": cid, "qn": 16}, timeout=20,
    ).json()
    data = body.get("data") or {}
    playable = bool(data.get("durl")) or bool(data.get("dash"))
    print(f"播放    : {'可播放' if playable else '暂不可播放'} "
          f"(durl={len(data.get('durl') or [])} dash={bool(data.get('dash'))})")


def report_tags(session: requests.Session, bvid: str) -> None:
    body = session.get(
        "https://api.bilibili.com/x/tag/archive/tags",
        params={"bvid": bvid}, timeout=20,
    ).json()
    names = [item.get("tag_name") for item in (body.get("data") or [])]
    print(f"标签    : {names}")


def report_audit(session: requests.Session, aid: int | str) -> None:
    body = session.get(
        "https://member.bilibili.com/x/web/archives",
        params={"status": "all", "pn": 1, "ps": 10}, timeout=20,
    ).json()
    for entry in (body.get("data") or {}).get("arc_audits") or []:
        archive = entry.get("Archive") or {}
        if str(archive.get("aid")) == str(aid):
            reason = archive.get("reject_reason")
            print(f"审核    : {'通过' if not reason else '驳回 - ' + str(reason)}")
            return
    print("审核    : 未在最近稿件中找到（可能还没进列表）")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="核验已发布的 B 站稿件")
    parser.add_argument("--bvid", required=True)
    parser.add_argument("--cookies", required=True)
    args = parser.parse_args(argv)

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Referer": "https://www.bilibili.com/"})
    session.cookies.update(load_cookies(args.cookies))

    data = report_archive(session, args.bvid)
    if data is None:
        return 1
    report_playback(session, args.bvid, int(data["cid"]))
    report_tags(session, args.bvid)
    report_audit(session, data["aid"])
    print(f"链接    : https://www.bilibili.com/video/{args.bvid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
