---
name: bilibili-publish
description: Publish a finished video to Bilibili (B站) on macOS through the web upload API. Use when the user wants to upload / 投稿 / 发布 an already-rendered video — extract the logged-in cookies from the native Bilibili client via CDP, upload the cover (16:9 and optional 4:3), preupload, chunked UPOS upload, finalize, submit through add/v3, and verify the public result. Publishing only: it does not write scripts, synthesize TTS, generate slides, or edit video. Never uses the replace-source (换源) endpoint.
---

# Bilibili Publish（仅发布）

把一个**已经渲染好的视频文件**发布到 B 站。本 skill 的职责边界只有发布：

- 取登录态（CDP）
- 上传封面（16:9 必填，4:3 可选）
- 预上传 → UPOS 分块上传 → 完成通知
- `add/v3` 提交稿件
- 发布后验证

**不做**：文案、配音、幻灯片、封面设计、剪辑、渲染。这些属于制作流程，交给别的 skill。

## 硬规则

1. **不要对已发布稿件使用换源接口。** 需要改视频源就重新投稿，或把新文件交给用户手动换源。本 skill 不包含换源脚本。
2. **Cookie 只走 CDP 提取**，不要尝试解密客户端 SQLite。`cookies.json` 是临时凭据：不要提交、不要贴图、不要写进报告，验证完删除。
3. **提交前先校验 UTF-8。** 中文标题/简介/标签一旦变成 `?` 或 U+FFFD，B 站会静默丢标签或显示乱码。
4. **发布前必须过素材校验**（`validate_assets.py`）。跳过校验需要用户明确同意。
5. **标题 ≤80 字、简介 ≤2000 字、标签 ≤10 个。** 封面 16:9 用 1920×1080，4:3 用 1440×1080。

## 前置依赖

- Python 3.10+，`requests`（必须）、`websockets`（仅 CDP 提取需要）、`Pillow`（仅封面尺寸校验需要）
- `ffprobe`（`validate_assets.py` 校验视频用）
- macOS 且安装了哔哩哔哩桌面客户端（用于 CDP 提取登录态）
- 账号已完成手机绑定/实名，否则无法投稿

```bash
python3 scripts/check_dependencies.py
```

## 工作流

### 1. 准备素材

| 素材 | 要求 |
|---|---|
| 视频 | `final.mp4`，H.264 + AAC 44.1kHz，建议 1920×1080 / 30fps |
| 封面 16:9 | 1920×1080 PNG，必填 |
| 封面 4:3 | 1440×1080 PNG，可选但推荐 |
| 元数据 | `publish.json`，见下 |

`publish.json` 示例：

```json
{
  "title": "【标题】不超过 80 字",
  "desc": "简介正文，≤2000 字，可含分段时间轴与来源",
  "tag": "标签1,标签2,标签3",
  "dynamic": "粉丝动态文案",
  "tid": 231,
  "human_type2": 1012,
  "no_reprint": 0
}
```

字段与分区 ID 见 `references/publish-config.md`。

### 2. 校验（必做）

```bash
python3 scripts/validate_assets.py \
  --video final.mp4 \
  --cover cover16x9.png \
  --publish-json publish.json \
  [--cover43 cover4x3.png]
```

校验视频编码/分辨率/帧率/音轨采样率、封面尺寸、元数据长度与 UTF-8 完整性、分区 ID 类型。

### 3. 取登录态（macOS）

```bash
./scripts/extract_bili_login_macos.sh 9222 /tmp/cookies.json
```

脚本会关闭并用调试端口重启「哔哩哔哩」客户端，通过 CDP 读取 Cookie，并用 `nav` 接口核对登录态。**它不读浏览器 Cookie，也不解密客户端数据库。**

非 macOS 或已有 Cookie 时，直接提供 `cookies.json`（需含 `SESSDATA` 与 `bili_jct`）。

### 4. 发布

```bash
# 单封面
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png \
  --cookies /tmp/cookies.json --config publish.json

# 双封面（16:9 + 4:3）
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png --cover43 cover4x3.png \
  --cookies /tmp/cookies.json --config publish.json
```

内部顺序：

1. 封面 `POST /x/vu/web/cover/up` → 得到封面 URL
2. 预上传 `GET /preupload` → `auth / chunk_size / endpoint / upos_uri / biz_id`
3. UPOS 元数据 `POST`（头 `X-Upos-Auth`）→ `upload_id`
4. 分块 `PUT`（每块失败重试 4 次）
5. 完成通知 `POST` → `OK=1`
6. 提交 `POST /x/vu/web/add/v3` → `data.bvid`

成功后写入 `publish_result.json`（含 `aid`/`bvid`/封面 URL）。

### 5. 验证

```bash
python3 scripts/verify_published.py --bvid BVxxxx --cookies /tmp/cookies.json
```

通过标准：

- `x/web-interface/view` 返回 `code=0`、`state=0`（公开）
- `playurl` 有 `durl` 或 `dash`
- 标签接口返回数量与提交一致
- 创作中心 `arc_audits` 无 `reject_reason`

**刚发布后立刻查可能返回 `-404`**，这是稿件在审核队列（`is_pubing`），等约 2 分钟再查，不要重复投稿。

### 6. 清理

验证完成后删除临时 Cookie：

```bash
rm -f /tmp/cookies.json
```

## 关键坑速查

| 现象 | 原因 | 处理 |
|---|---|---|
| 标签只挂上几个 / 出现 `AI??` | 元数据写入时编码损坏 | 用 UTF-8 无 BOM 重写 `publish.json`，重发 `edit/v3` 重传完整 `tag` |
| `json.load` 报 `Unexpected UTF-8 BOM` | 文件带 BOM | 读取用 `encoding="utf-8-sig"`，写回不带 BOM |
| 发布后 `view` 返回 `-404` | 审核中 | 等 2 分钟后重试，不要重复提交 |
| 音轨变成 96kHz | 归一化时没指定 `-ar` | 渲染阶段显式 `-ar 44100` |
| `x/tag/archive/add` 返回 `-403` | web Cookie 无权限 | 改用 `edit/v3` 全量重传 `tag` |
| 分块上传偶发失败 | 网络抖动 | 脚本已内置 4 次重试、间隔 3 秒 |
| 标题/简介超限 | 平台限制 | 标题 ≤80 字、简介 ≤2000 字、标签 ≤10 个 |

更多见 `references/publishing-errors.md`。

## 资源

- `scripts/check_dependencies.py` — 依赖预检
- `scripts/extract_bili_login_macos.sh` — macOS CDP 一键取登录态
- `scripts/extract_bili_cookies.py` — CDP 提取实现
- `scripts/validate_assets.py` — 发布前素材校验
- `scripts/publish_bilibili.py` — 投稿主脚本（单/双封面）
- `scripts/verify_published.py` — 发布后验证
- `scripts/publish.example.json` — 配置模板
- `references/bilibili-upload-api.md` — 投稿接口文档
- `references/publish-config.md` — 配置字段与分区 ID
- `references/publishing-errors.md` — 发布向错误档案

## 致谢

本 skill 的发布流程重构自
[sukai213/bilibili-ai-skills](https://github.com/sukai213/bilibili-ai-skills)
中的 `bilibili-ai-video`（作者 sukai213）。原仓库在撰写时未声明开源许可证，
详见 `THIRD_PARTY_NOTICES.md`。
