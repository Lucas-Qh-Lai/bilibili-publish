# Changelog

All notable changes to this project are documented here.

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
