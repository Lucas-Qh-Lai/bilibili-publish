# v0.2.0 — Windows credential extraction

Adds a Windows path for pulling Bilibili login cookies, alongside the existing
macOS flow.

> ## ⚠️ Windows support is untested
>
> The Windows script is included **for reference only**. It has not been run on
> a Windows machine, and it could not be syntax-checked in the environment
> where it was written because no PowerShell was installed there.
>
> Verify each step yourself before relying on it. If something fails, the
> manual fallback in `references/windows-cookies.md` is only a few commands.

## What's new

- **`scripts/extract_bili_login_windows.ps1`** — one-command extraction:
  1. locates `bilibili.exe` via `-ExePath`, the registry `App Paths` key,
     Uninstall entries, common install locations, or `PATH`;
  2. closes the running client;
  3. relaunches it with `--remote-debugging-port`;
  4. waits for the CDP endpoint and runs `extract_bili_cookies.py`;
  5. verifies the session against the `nav` endpoint.
- **`references/windows-cookies.md`** — the flow, a manual fallback, a
  troubleshooting table, and the security notes.

## Why CDP on Windows too

The Windows client stores cookies in `Network\Cookies` (SQLite v18) with values
encrypted using **App-Bound Encryption**. That key is bound to the app identity
and cannot be unwrapped with plain DPAPI, so decrypting the database is a dead
end on Windows exactly as it is on macOS.

The client is Chromium-based, so the debugging port gives us the live session's
cookies directly. Same technique, same script underneath — only the launcher
differs per platform.

## Compatibility

- `extract_bili_cookies.py` now forces UTF-8 on stdout/stderr, so the Chinese
  status lines do not crash on legacy Windows code pages, and it applies POSIX
  file modes only where the platform supports them.
- macOS behaviour is unchanged.
- The publish, validate, and verify scripts are platform-agnostic and were not
  modified.

## Install

```bash
git clone https://github.com/Lucas-Qh-Lai/bilibili-publish.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish"
python3 "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/check_dependencies.py"
```

On Windows, `check_dependencies.py` prints the PowerShell command to use and
repeats the untested warning.

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
