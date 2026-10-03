# v0.1.0 — Publishing-only skill

First release of **bilibili-publish**, a Codex skill that does exactly one
thing: publish an already-rendered video to Bilibili.

## Highlights

- **Publishing only.** No copywriting, TTS, slides, editing, or rendering.
  It starts from a finished MP4.
- **Dual covers.** Uploads the 16:9 cover (`cover`) and an optional 4:3 cover
  (`cover43`) as independent images.
- **Resilient upload.** UPOS pre-upload, multipart session, chunked upload with
  four retries per chunk, then finalize.
- **Pre-flight validation.** Checks H.264 / AAC / 44.1 kHz / resolution / fps,
  cover dimensions, metadata length, and UTF-8 integrity before anything is
  submitted.
- **macOS credential extraction.** Reads the session over CDP from the native
  Bilibili client and verifies it against the `nav` endpoint. No database
  decryption.
- **Post-publish verification.** Confirms the archive is public, playable,
  fully tagged, and not rejected.
- **No replace-source support.** Replacing a published archive's video is
  deliberately unimplemented.

## Origin

The publishing flow was refactored from
[sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills)
(`skills/bilibili-ai-video`). That repository has no LICENSE file and its
README states that the skills and scripts are for personal learning and
automation-workflow reference only — a restrictive notice, not an open-source
license.

To respect the upstream author, the scripts and documentation in this release
were rewritten as an independent implementation rather than copied, and the
attribution is retained in `README.md`, `README.en.md`, and
`THIRD_PARTY_NOTICES.md`.

## Requirements

- Python 3.10+, `requests`, `ffprobe`
- macOS + Bilibili desktop client for automatic credential extraction
- `websockets` (extraction) and `Pillow` (cover size checks) optional
- A Bilibili account with phone binding / real-name verification

## Install

```bash
git clone https://github.com/Lucas-Qh-Lai/bilibili-publish.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish"
python3 "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/check_dependencies.py"
```

## Release Policy

Future updates use strictly increasing semantic versions. Previous releases and
tags are retained.
