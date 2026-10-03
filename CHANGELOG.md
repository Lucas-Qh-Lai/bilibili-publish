# Changelog

All notable changes to this project are documented here.

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
