# Bilibili Publish

[English](README.en.md) | [简体中文](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-000000)](https://openai.com/codex)
[![Bilibili](https://img.shields.io/badge/Publish-Bilibili-00A1D6)](https://www.bilibili.com/)

Publish an **already-rendered video** to Bilibili. This is a **publishing-only**
Codex skill.

> **It does not make videos.** No copywriting, no TTS, no slides, no editing,
> no rendering. It starts from "you already have an MP4".

## What it does

| Step | Detail |
|---|---|
| Credentials | Reads cookies from the logged-in Bilibili client over CDP; no database decryption. macOS is tested; the Windows script is provided **untested** |
| Covers | Uploads the 16:9 cover (required) and 4:3 cover (optional) separately |
| Video | UPOS pre-upload → open multipart session → chunked upload (4 retries) → finalize |
| Submit | Calls `add/v3`, supporting dual covers |
| Pre-flight | Validates codec, resolution, fps, audio sample rate, cover size, metadata length and UTF-8 integrity |
| Verify | Checks that the archive is public, playable, fully tagged, and not rejected |
| Cleanup | Cookies are one-shot; delete them after verification |

## What it does not do

- Generate or edit video
- Generate cover images
- Replace the video source of an already-published archive (never uses the
  replace-source endpoint)
- Store credentials in the repository or in reports

## Origin and credit

The publishing flow was refactored from
**[sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills)**,
specifically `skills/bilibili-ai-video` by
[sukai213](https://github.com/sukai213).

That project turned the Bilibili publishing chain (CDP credentials, cover and
UPOS chunked upload, `add/v3`, post-publish verification) into a runnable Codex
skill; the sequence and the hard-won field notes come from that work.
**The upstream repository has no LICENSE file.** Its README "许可" section states:

> 技能与脚本仅用于个人学习与自动化工作流参考.
> ("Skills and scripts are for personal learning and automation-workflow
> reference only.")

That is a restrictive notice, not an open-source license: it grants no right to
copy, modify, redistribute, or use commercially. To respect the author, this
repository's scripts and docs were **rewritten as an independent
implementation** — no verbatim copying — while keeping full attribution in this
README and in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

If you intend to redistribute or use this commercially, verify the upstream
licensing position first. The original author is welcome to request changes to
attribution or usage.

## Requirements

- **Required**: Python 3.10+, `requests`, `ffprobe`
- **Credential extraction**: Bilibili desktop client, `websockets` (macOS tested; Windows untested)
- **Cover size checks**: `Pillow`
- The account must have completed phone binding / real-name verification

```bash
python3 -m pip install requests websockets Pillow
python3 scripts/check_dependencies.py
```

## Install

### Agent install

Send this to a skill-aware Codex / Claude Code:

```
Install this skill for me: https://github.com/Lucas-Qh-Lai/bilibili-publish
Put it in ~/.codex/skills/bilibili-publish, then run scripts/check_dependencies.py.
```

### Manual install

```bash
git clone https://github.com/Lucas-Qh-Lai/bilibili-publish.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish"
chmod +x "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/"*.sh \
         "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/"*.py
python3 "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/check_dependencies.py"
```

## Usage

### 1. Prepare assets

```text
final.mp4          H.264 + AAC 44.1kHz, 1920x1080 / 30fps recommended
cover16x9.png      1920x1080, required
cover4x3.png       1440x1080, optional
publish.json       title / description / tags / category
```

```json
{
  "title": "Title, max 80 characters",
  "desc": "Description, max 2000 characters",
  "tag": "tag1,tag2,tag3",
  "dynamic": "Text for the follower feed",
  "tid": 231,
  "human_type2": 1012,
  "no_reprint": 0
}
```

See [`references/publish-config.md`](references/publish-config.md) for fields and
category IDs.

### 2. Pre-flight validation

```bash
python3 scripts/validate_assets.py \
  --video final.mp4 --cover cover16x9.png --publish-json publish.json \
  [--cover43 cover4x3.png]
```

### 3. Get credentials

**macOS (tested)**

```bash
./scripts/extract_bili_login_macos.sh 9222 /tmp/cookies.json
```

The script briefly restarts the client, reads cookies over CDP, and verifies the
session against the `nav` endpoint.

**Windows (⚠️ UNTESTED, for reference only)**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\extract_bili_login_windows.ps1
```

Auto-detects `bilibili.exe` (or pass `-ExePath`), restarts it with a debugging
port, then runs the same CDP extraction. See
[`references/windows-cookies.md`](references/windows-cookies.md).

**Other platforms**: supply a `cookies.json` containing `SESSDATA` and
`bili_jct`. How you obtained it does not affect the upload logic.

### 4. Publish

```bash
# single cover
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png \
  --cookies /tmp/cookies.json --config publish.json

# dual cover
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png --cover43 cover4x3.png \
  --cookies /tmp/cookies.json --config publish.json
```

Writes `publish_result.json` with `aid` / `bvid` / cover URLs on success.

### 5. Verify

```bash
python3 scripts/verify_published.py --bvid BVxxxxxxxxxx --cookies /tmp/cookies.json
```

A `-404` right after submission usually means the archive is still in the review
queue. Wait about two minutes instead of submitting again.

### 6. Clean up

```bash
rm -f /tmp/cookies.json
```

## Hard rules

- **Never use the replace-source endpoint on a published archive.** Re-upload,
  or let the account owner do it manually from the creator console.
- Extract cookies over CDP only; do not attempt database decryption.
- Temporary cookies must never be committed, screenshotted, or written into
  reports. Delete them after verification.

## License

This repository's own code is [MIT](LICENSE).

Upstream licensing and the attribution for
[sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills) are
documented in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). The MIT license
covers only this repository's original work; it does not alter upstream rights.
