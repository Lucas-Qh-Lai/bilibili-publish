# Windows cookie extraction

> **Windows support is untested.** The scripts and steps below were written
> from the upstream workflow notes and are **not** verified on a real Windows
> machine. Everything here is a starting point — check each step yourself
> before trusting it. Only the macOS path has been exercised.

## Why CDP and not the cookie database

The Bilibili Windows client stores cookies in a SQLite database under
`Network\Cookies` (schema v18) with values encrypted using **App-Bound
Encryption**. That key is bound to the app identity and cannot be unwrapped
with plain DPAPI, so decrypting the database is a dead end.

The client is Chromium-based, so launching it with a remote debugging port
lets us read the live session's cookies over the Chrome DevTools Protocol
instead. This is exactly how the upstream project does it.

## Steps

```powershell
# From the skill directory
powershell -ExecutionPolicy Bypass -File .\scripts\extract_bili_login_windows.ps1
```

With an explicit client path and output file:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\extract_bili_login_windows.ps1 `
    -ExePath "C:\Program Files\bilibili\bilibili.exe" `
    -Port 9222 `
    -Out .\cookies.json
```

The script does five things:

1. Locates `bilibili.exe` — `-ExePath` override, then the registry `App Paths`
   key, then Uninstall entries, then common install locations, then `PATH`.
2. Closes any running instance.
3. Relaunches it with `--remote-debugging-port=<port>`.
4. Waits for `http://127.0.0.1:<port>/json/version`, then runs
   `extract_bili_cookies.py` against that port.
5. Verifies the session against `https://api.bilibili.com/x/web-interface/nav`.

## Doing it by hand

If the script does not work on your machine, the underlying steps are simple:

```powershell
# 1. Close the client, then start it with the debugging port
& "C:\Program Files\bilibili\bilibili.exe" --remote-debugging-port=9222

# 2. In another terminal, extract the cookies
$env:PYTHONUTF8 = "1"
python .\scripts\extract_bili_cookies.py --cdp http://127.0.0.1:9222 --out cookies.json
```

Then confirm the file contains `SESSDATA` and `bili_jct`, and check the
session:

```powershell
$c = Get-Content .\cookies.json -Raw | ConvertFrom-Json
$h = ($c.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join "; "
Invoke-RestMethod -Uri "https://api.bilibili.com/x/web-interface/nav" -Headers @{ Cookie = $h } |
    Select-Object -ExpandProperty data | Select-Object isLogin, uname
```

## Requirements

- Python 3.10+ on `PATH`
- `websockets` (and `requests` for publishing):

  ```powershell
  python -m pip install requests websockets Pillow
  ```

- The client must be **logged in** before extraction. The script restarts it,
  so log in once and leave the session active.

## Troubleshooting

| Symptom | Likely cause | What to try |
|---|---|---|
| `找不到 bilibili.exe` | Non-standard install location | Pass `-ExePath` explicitly |
| `调试端口未就绪` | Client failed to start, or another instance still holds the port | Close all client processes, pick a different `-Port` |
| `缺少 SESSDATA/bili_jct` | Not logged in | Log in inside the client, rerun |
| `ModuleNotFoundError: websockets` | Dependency missing | `python -m pip install websockets` |
| Chinese output renders as `???` | Console code page | The script sets `PYTHONUTF8=1`; also try `chcp 65001` |
| Cookie JSON is fine but publishing returns `-101` | Session expired | Re-extract; `-101` means not logged in |
| Publishing returns `-111` | CSRF mismatch | `csrf` must equal `bili_jct` |

## Security

`cookies.json` is a live credential. Delete it after verification, never
commit it, and never paste it into an issue or report. On Windows the file
inherits the folder's NTFS permissions — keep it out of shared or synced
directories.

## Attribution

The CDP approach and the App-Bound encryption note come from
[sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills)
(`skills/bilibili-ai-video`). See `THIRD_PARTY_NOTICES.md`.
