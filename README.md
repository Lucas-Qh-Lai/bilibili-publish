# Bilibili Publish

[English](README.en.md) | [简体中文](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-000000)](https://openai.com/codex)
[![Bilibili](https://img.shields.io/badge/Publish-Bilibili-00A1D6)](https://www.bilibili.com/)

把一个**已经渲染好的视频**发布到 B 站。这是一个**只做发布**的 Codex Skill。

> **它不制作视频。** 不写文案、不合成配音、不做幻灯片、不剪辑、不渲染。
> 制作流程请交给别的 skill；本 skill 从「你已经有一个 MP4」开始。

## 它做什么

| 环节 | 说明 |
|---|---|
| 取登录态 | 通过 CDP 从已登录的哔哩哔哩客户端读取 Cookie，不解密本地数据库。macOS 已实测；Windows 脚本提供但**未经测试** |
| 上传封面 | 16:9 必填，4:3 可选，两张独立上传 |
| 上传视频 | UPOS 预上传 → 开启分片会话 → 逐片上传（失败重试 4 次）→ 封口 |
| 投稿 | 调用 `add/v3` 建立稿件，支持双封面 |
| 发布前校验 | 视频编码/分辨率/帧率/音轨、封面尺寸、元数据长度与 UTF-8 完整性 |
| 发布后验证 | 稿件是否公开、能否播放、标签是否挂全、审核是否驳回 |
| 清理 | Cookie 是一次性凭据，用完即删 |

## 它不做什么

- 不生成或编辑视频
- 不生成封面图
- 不修改**已发布**稿件的视频源（不使用换源接口）
- 不保存账号凭据到仓库或报告

## 来源与致谢

本项目的发布流程重构自
**[sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills)**
中的 `skills/bilibili-ai-video`（作者 [sukai213](https://github.com/sukai213)）。

上游把 B 站投稿链路（CDP 取登录态、封面与 UPOS 分片上传、`add/v3`、
发布后验证）整理成了可运行的 Codex skill，本项目的流程顺序与踩坑经验
来自那份工作。**上游仓库没有 LICENSE 文件**，其 README 的「许可」一节声明：

> 技能与脚本仅用于个人学习与自动化工作流参考。

这不是开源许可证 —— 它是限制性声明，没有授予复制、修改、再分发或商业使用的
权利。为了尊重作者，本项目的脚本与文档已**重写为独立实现**，没有逐字复制
上游代码，同时在 README 与本仓库的 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
中保留完整署名与许可状态说明。

如果你要再分发或商用本项目，请先自行确认上游授权情况。也欢迎原作者提出任何
署名或使用方式上的调整要求。

## 环境要求

- **必需**：Python 3.10+、`requests`、`ffprobe`
- **取登录态**：哔哩哔哩桌面客户端、`websockets`（macOS 已实测；Windows 未测试）
- **封面尺寸校验**：`Pillow`
- 账号需完成手机绑定/实名，否则无法投稿

```bash
python3 -m pip install requests websockets Pillow
python3 scripts/check_dependencies.py
```

## 安装

### 方式一：交给 Agent 安装

把下面这句话发给支持 skill 的 Codex / Claude Code：

```
帮我安装这个 skill：https://github.com/Lucas-Qh-Lai/bilibili-publish
装到 ~/.codex/skills/bilibili-publish，然后跑一遍 scripts/check_dependencies.py 确认依赖。
```

### 方式二：手动安装

```bash
git clone https://github.com/Lucas-Qh-Lai/bilibili-publish.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish"
chmod +x "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/"*.sh \
         "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/"*.py
python3 "${CODEX_HOME:-$HOME/.codex}/skills/bilibili-publish/scripts/check_dependencies.py"
```

## 使用

### 1. 准备素材

```text
final.mp4          成片（H.264 + AAC 44.1kHz，建议 1920x1080 / 30fps）
cover16x9.png      16:9 封面（1920x1080，必填）
cover4x3.png       4:3 封面（1440x1080，可选）
publish.json       标题 / 简介 / 标签 / 分区
```

```json
{
  "title": "【标题】不超过 80 字",
  "desc": "简介正文，≤2000 字",
  "tag": "标签1,标签2,标签3",
  "dynamic": "粉丝动态文案",
  "tid": 231,
  "human_type2": 1012,
  "no_reprint": 0
}
```

字段与分区 ID 见 [`references/publish-config.md`](references/publish-config.md)。

### 2. 发布前校验

```bash
python3 scripts/validate_assets.py \
  --video final.mp4 --cover cover16x9.png --publish-json publish.json \
  [--cover43 cover4x3.png]
```

### 3. 取登录态

**macOS（已实测）**

```bash
./scripts/extract_bili_login_macos.sh 9222 /tmp/cookies.json
```

脚本会短暂重启客户端、通过 CDP 读取 Cookie，并用 `nav` 接口核对登录状态。

**Windows（⚠️ 未经实机测试，仅供参考）**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\extract_bili_login_windows.ps1
```

自动定位 `bilibili.exe`（可 `-ExePath` 指定），关闭后以调试端口重启，再走同样的
CDP 提取。步骤与排错见 [`references/windows-cookies.md`](references/windows-cookies.md)。

**其他平台**：直接提供 `cookies.json`（需含 `SESSDATA` 与 `bili_jct`）即可，
取法不影响上传逻辑。

### 4. 投稿

```bash
# 单封面
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png \
  --cookies /tmp/cookies.json --config publish.json

# 双封面
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png --cover43 cover4x3.png \
  --cookies /tmp/cookies.json --config publish.json
```

成功后写入 `publish_result.json`（含 `aid` / `bvid` / 封面 URL）。

### 5. 验证

```bash
python3 scripts/verify_published.py --bvid BVxxxxxxxxxx --cookies /tmp/cookies.json
```

刚投稿后立刻查询可能返回 `-404` —— 那是审核排队，等约 2 分钟再查，
**不要重复投稿**。

### 6. 清理

```bash
rm -f /tmp/cookies.json
```

## 硬规则

- **不对已发布稿件使用换源接口。** 需要换视频源就重新投稿，或由账号所有者
  在创作中心手动操作。本 skill 不提供该能力。
- Cookie 只走 CDP 提取，不尝试解密客户端数据库。
- 临时 Cookie 不提交、不截图、不写进报告，验证后删除。

## 目录结构

```text
bilibili-publish/
├── SKILL.md
├── README.md / README.en.md
├── LICENSE / THIRD_PARTY_NOTICES.md
├── scripts/
│   ├── check_dependencies.py
│   ├── extract_bili_login_macos.sh
│   ├── extract_bili_login_windows.ps1
│   ├── extract_bili_cookies.py
│   ├── validate_assets.py
│   ├── publish_bilibili.py
│   ├── verify_published.py
│   └── publish.example.json
└── references/
    ├── bilibili-upload-api.md
    ├── publish-config.md
    ├── publishing-errors.md
    └── windows-cookies.md
```

## 许可

本仓库自身代码采用 [MIT](LICENSE)。

上游 [sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills)
的许可状态与本仓库的署名说明见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
MIT 许可仅覆盖本仓库作者原创的部分，不改变上游对其自身内容的权利。
