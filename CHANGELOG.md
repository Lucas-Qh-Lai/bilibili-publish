# Changelog

All notable changes to this project are documented here.

## [0.3.0] - 2026-11-14

### Fixed

- **`add/v3` returned `21001 参数错误`.** The submit payload passed
  `videos[0].cid` as a string. `biz_id` is numeric, and the endpoint rejects the
  string form. `cid` is now cast to `int`.
- **`add/v3` now sends a WBI signature.** The endpoint expects
  `web_location`, `t`, `csrf`, `wts` and `w_rid` on the query string; the old
  `ts` + `csrf` form is rejected with `21001`. `wbi_sign()` is implemented
  in-tree with no third-party dependency.
- **`tid` and `human_type2` are now resolved from the API.** The Web upload
  form ignores a hand-written `tid`; the effective value is the first entry
  returned by `POST /x/vupre/web/archive/types/predict`. The script calls that
  endpoint and uses its `data[0].id` plus `data[0].human_type.id`, overriding
  whatever the config file says.
- **Stale cookies after a client restart.** `extract_bili_login_macos.sh`
  could report a valid login while the captured `SESSDATA` was the previous
  session's value, which then failed with `-101 账号未登录` at publish time.
  `extract_bili_cookies.py` can now be re-run against an already-open debug
  port to capture the live session; the troubleshooting table documents the
  symptom.

### Added

- **`--submit-only` for re-submitting without re-uploading.** After the
  multipart upload is sealed, the file already lives in Bilibili's storage —
  a failed submit does not need the gigabytes uploaded again. The script now
  writes `upload_receipt.json` (upos filename, `cid`, cover URLs) and accepts
  `--submit-only upload_receipt.json` to create the archive from it.
- **`references/video-specs.md`** documents the container/codec/bitrate rules
  that were verified against the live API in November 2026, including why
  re-encoding a master before upload only costs quality.
- `validate_assets.py` accepts H.264, HEVC and AV1 video, MP4/MOV/MKV/FLV
  containers, and both 44.1 kHz and 48 kHz AAC. It still fails on a missing
  video or audio stream, and still warns about non-30 fps sources.

### Compatibility

- macOS and Windows flows are unchanged.
- The publish, validate and verify scripts remain platform-agnostic.

## [0.2.0] - 2026-10-03

### Added

- **Windows cookie extraction** (`scripts/extract_bili_login_windows.ps1`).
  Auto-detects `bilibili.exe` (registry `App Paths`, Uninstall entries, common
  install locations, `PATH`, or an explicit `-ExePath`), closes the running
  client, relaunches it with `--remote-debugging-port`, waits for CDP, extracts
  the cookies, and verifies the session against the `nav` endpoint.
- `references/windows-cookies.md` documents the Windows flow, the manual
  fallback, requirements, a troubleshooting table, and the security notes.

### Changed

- `extract_bili_cookies.py` now forces UTF-8 on stdout/stderr so the Chinese
  status output does not fail on legacy Windows code pages, and only applies
  POSIX file modes where the platform supports them.
- `check_dependencies.py` reports the platform-appropriate credential command.
- README (both languages) and `SKILL.md` document the Windows path.

### Windows support status

> **Windows support is UNTESTED.** The script was written from the upstream
> workflow notes; it has not been run on a Windows machine, and it could not
> even be syntax-checked here because no PowerShell is installed. Treat it as a
> starting point and verify each step yourself. Only the macOS path is
> exercised.

The CDP approach itself is sound — the client is Chromium-based, and its
App-Bound encrypted cookie database cannot be decrypted with DPAPI — but the
launcher details (install paths, process names, argument handling) may need
adjustment on a real machine.

## [0.1.0] - 2026-10-03

### Added

- Publishing-only Codex skill extracted from a combined produce-and-publish
  workflow.
- `scripts/publish_bilibili.py`: cover upload, UPOS pre-upload, multipart
  session, chunked upload with retry, finalize, and `add/v3` submission,
  supporting both a 16:9 and an optional 4:3 cover.
- `scripts/validate_assets.py`: pre-flight validation of video codec,
  resolution, fps, audio sample rate, cover dimensions, metadata length and
  UTF-8 integrity.
- `scripts/check_dependencies.py`: dependency pre-flight.
- `scripts/extract_bili_login_macos.sh` / `extract_bili_cookies.py`: macOS CDP
  credential extraction from the native Bilibili client.
- `scripts/verify_published.py`: post-publish verification of visibility,
  playback, tags and review state.
- Chinese-first `README.md` with an English companion (`README.en.md`), both
  carrying upstream attribution.
- `THIRD_PARTY_NOTICES.md` documenting the upstream project's license status.
- MIT license, security policy, contribution guide, CI validation and issue
  templates.

### Notes

- The publishing flow was refactored from
  [sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills).
  That repository has no LICENSE file and states that its skills and scripts
  are for personal learning and automation-workflow reference only. The scripts
  and documentation here were rewritten as an independent implementation rather
  than copied; attribution is retained in the README and third-party notices.
- This skill intentionally does **not** implement the replace-source endpoint.

### Release Policy

- Future updates use strictly increasing semantic versions.
- Previous releases and tags are retained for traceability.
