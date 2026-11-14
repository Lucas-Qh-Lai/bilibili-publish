# v0.3.0 — Working Web submit, and honest video-spec guidance

Fixes the Web publish path against the live API (verified November 2026 with a
real upload of a 1080p60 HEVC master) and documents what actually happens to
your file once it reaches Bilibili.

## What broke, and why

`x/vu/web/add/v3` answered `{"code":21001,"message":"参数错误"}` after a
successful gigabyte-scale upload. Three separate things were wrong, and all
three had to be fixed for the submit to succeed:

1. **`videos[0].cid` was a string.** `biz_id` comes back from the preupload
   endpoint as a number; the submit endpoint rejects the string form. It is
   now cast to `int`.
2. **The query string had no WBI signature.** The endpoint expects
   `web_location=333.1024`, `t`, `csrf`, `wts` and `w_rid`. The old request
   only sent `ts` and `csrf`. `wbi_sign()` is implemented in-tree — the
   mixin-key permutation table, the parameter sort, the `!'()*` filter and the
   `md5` are all standard, and it needs no third-party package.
3. **`tid` was hand-written.** The Web upload form no longer accepts a manual
   `tid`; the effective value is the first entry returned by
   `POST /x/vupre/web/archive/types/predict`, and the new-partition id
   (`human_type2`) comes from that same entry's `human_type.id`. The script
   now calls the endpoint and overrides the config file.

## New: re-submit without re-uploading

A sealed multipart upload already lives in Bilibili's storage. If the submit
then fails, the gigabytes do not need to go up again. The script writes
`upload_receipt.json` after sealing, and accepts:

```bash
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png --cover43 cover4x3.png \
  --cookies cookies.json --config publish.json \
  --submit-only upload_receipt.json
```

## New: `references/video-specs.md`

The rule this release makes explicit: **do not re-encode your master to
satisfy the platform.** H.264, HEVC and AV1 all upload; the platform transcodes
whatever it receives. Pre-encoding to H.264 adds a second lossy pass on top of
the platform's own transcode, so it can only cost quality. The document
records the container and codec rules, the bitrate ceilings that were read out
of community tests (1080p ≈ 5900 kbps, 4K 16000–18500 kbps), the GOP and
colour requirements, how to read the *post-transcode* bitrate back out of the
player, and the five failure modes that were hit during this release —
including the stale-cookie trap where the extraction script reports a valid
login but publish returns `-101`.

## Compatibility

- macOS and Windows credential flows are unchanged.
- The publish, validate and verify scripts stay platform-agnostic.
- `validate_assets.py` now accepts H.264/HEVC/AV1, MP4/MOV/MKV/FLV, and
  44.1 kHz or 48 kHz AAC. It still fails on a missing video or audio stream.

## Install

```bash
git clone https://github.com/Lucas-Qh-Lai/bilibili-publish.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish"
```

## Attribution

The CDP approach and the App-Bound encryption note come from
[sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills)
(`skills/bilibili-ai-video`). That repository has no LICENSE file and states
that its skills and scripts are for personal learning and automation-workflow
reference only. This repository rewrote the flow as an independent
implementation; see `THIRD_PARTY_NOTICES.md`.

## Release Policy

Future updates use strictly increasing semantic versions. Previous releases and
tags are retained.
