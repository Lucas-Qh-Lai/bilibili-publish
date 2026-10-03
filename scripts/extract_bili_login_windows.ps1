<#
.SYNOPSIS
    Extract Bilibili login cookies on Windows via the Chrome DevTools Protocol.

.DESCRIPTION
    The Bilibili desktop client is Chromium-based. Launching it with a remote
    debugging port lets us read the current session's cookies over CDP, which
    avoids the client's App-Bound encrypted cookie database (DPAPI cannot
    decrypt it).

    This script closes the running client, relaunches it with a debugging port,
    waits for the port, extracts the cookies, then verifies the session against
    the `nav` endpoint.

    !! WINDOWS SUPPORT IS UNTESTED !!
    This script was written from the upstream workflow notes but has not been
    run on a Windows machine. Treat it as a starting point and verify each step
    yourself before relying on it. See references/windows-cookies.md.

.PARAMETER Port
    CDP debugging port. Default 9222.

.PARAMETER Out
    Output cookie JSON path. Default cookies.json in the current directory.

.PARAMETER ExePath
    Explicit path to bilibili.exe. Use this if auto-detection fails.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\extract_bili_login_windows.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\extract_bili_login_windows.ps1 `
        -ExePath "C:\Program Files\bilibili\bilibili.exe" -Port 9222 -Out .\cookies.json
#>

[CmdletBinding()]
param(
    [int]$Port = 9222,
    [string]$Out = "cookies.json",
    [string]$ExePath
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$Message) {
    Write-Host $Message
}

function Find-BilibiliExe {
    param([string]$Explicit)

    if ($Explicit) {
        if (Test-Path -LiteralPath $Explicit) { return (Resolve-Path -LiteralPath $Explicit).Path }
        throw "指定的 bilibili.exe 不存在: $Explicit"
    }

    # 1. Registry App Paths (most reliable when the client registered itself)
    $appPathKeys = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\bilibili.exe",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\bilibili.exe"
    )
    foreach ($key in $appPathKeys) {
        try {
            $value = (Get-ItemProperty -Path $key -ErrorAction Stop)."(default)"
            if ($value -and (Test-Path -LiteralPath $value)) { return (Resolve-Path -LiteralPath $value).Path }
        } catch { }
    }

    # 2. Uninstall entries
    $uninstallRoots = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )
    foreach ($root in $uninstallRoots) {
        try {
            $entries = Get-ItemProperty -Path $root -ErrorAction Stop |
                Where-Object { $_.DisplayName -match "哔哩哔哩|bilibili" -and $_.InstallLocation }
            foreach ($entry in $entries) {
                $candidate = Join-Path $entry.InstallLocation "bilibili.exe"
                if (Test-Path -LiteralPath $candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
            }
        } catch { }
    }

    # 3. Common install locations
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\bilibili\bilibili.exe"),
        (Join-Path $env:LOCALAPPDATA "bilibili\bilibili.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\哔哩哔哩\bilibili.exe"),
        (Join-Path $env:ProgramFiles "bilibili\bilibili.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "bilibili\bilibili.exe")
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $onPath = Get-Command "bilibili.exe" -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }

    throw @"
找不到 bilibili.exe。请用 -ExePath 显式指定，例如：
  -ExePath "C:\Program Files\bilibili\bilibili.exe"
"@
}

function Stop-Bilibili {
    param([string]$Name)
    $procs = Get-Process -Name $Name -ErrorAction SilentlyContinue
    if (-not $procs) { return }
    Write-Step "  关闭正在运行的客户端..."
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Step "1/5 定位 B 站客户端"
$exe = Find-BilibiliExe -Explicit $ExePath
$procName = [System.IO.Path]::GetFileNameWithoutExtension($exe)
Write-Step "  $exe"

Write-Step "2/5 关闭已运行实例"
Stop-Bilibili -Name $procName

Write-Step "3/5 以调试端口 $Port 启动"
Start-Process -FilePath $exe -ArgumentList "--remote-debugging-port=$Port" | Out-Null

$base = "http://127.0.0.1:$Port"
$ready = $false
for ($i = 1; $i -le 40; $i++) {
    try {
        Invoke-RestMethod -Uri "$base/json/version" -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $ready) {
    throw "调试端口 $Port 未就绪。请确认客户端已启动并完成登录后重试。"
}
Write-Step "  CDP 已就绪 ($base)"

Write-Step "4/5 提取 Cookie 到 $Out"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$extractor = Join-Path $scriptDir "extract_bili_cookies.py"
if (-not (Test-Path -LiteralPath $extractor)) {
    throw "找不到 extract_bili_cookies.py: $extractor"
}

# The extractor prints Chinese; make sure the console can encode it.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
& $python $extractor --cdp $base --out $Out
if ($LASTEXITCODE -ne 0) {
    Write-Warning "提取脚本返回非零退出码 ($LASTEXITCODE)，可能未登录或缺少 websockets。"
}

Write-Step "5/5 用 nav 接口核对登录态"
if (-not (Test-Path -LiteralPath $Out)) {
    throw "未生成 $Out，无法核对登录态。"
}

$cookieJson = Get-Content -LiteralPath $Out -Raw -Encoding UTF8 | ConvertFrom-Json
$pairs = @()
foreach ($prop in $cookieJson.PSObject.Properties) {
    $pairs += ("{0}={1}" -f $prop.Name, $prop.Value)
}
$cookieHeader = $pairs -join "; "

try {
    $nav = Invoke-RestMethod -Uri "https://api.bilibili.com/x/web-interface/nav" `
        -Headers @{
            "Cookie"     = $cookieHeader
            "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        } -TimeoutSec 15
    Write-Step ("  code={0} isLogin={1} uname={2}" -f $nav.code, $nav.data.isLogin, $nav.data.uname)
    if ($nav.data.isLogin) {
        Write-Step "  登录有效"
    } else {
        Write-Warning "  未登录，请先在客户端内登录后重试"
    }
} catch {
    Write-Warning "  核对失败: $($_.Exception.Message)"
}

Write-Step "完成。"
