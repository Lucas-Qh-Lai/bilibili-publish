# 发布向错误档案

只收录与**上传/投稿/验证**相关的问题。制作环节（TTS、幻灯片、剪辑）的错误不在这里。

## 1. 标题/标签出现乱码，标签只挂上 3 个

- **现象**：`add/v3` 提交了 10 个标签，实际只挂上 3 个，其中一个还是 `AI??`。
- **根因**：写 `publish.json` 时中文已变成 `?`，非法标签被 B 站静默丢弃。
- **修正**：`x/tag/archive/add|del` 用 web Cookie 返回 `-403`，不要用；正确方式是重发
  `edit/v3` 并完整重传 `tag` 字段。
- **预防**：`validate_assets.py` 会在提交前拦截 `?` / `??` / U+FFFD。发布后复查
  `GET https://api.bilibili.com/x/tag/archive/tags?bvid=` 应等于提交数量。

## 2. PowerShell 写出的 JSON 带 BOM

- **现象**：`json.load(open(p, encoding="utf-8"))` 报 `Unexpected UTF-8 BOM`。
- **根因**：PowerShell `Set-Content -Encoding UTF8` 默认带 BOM。
- **修正**：Python 读取用 `encoding="utf-8-sig"`；写回用
  `json.dump(..., ensure_ascii=False)` 且不带 BOM。
- **预防**：`publish_bilibili.py` / `validate_assets.py` 一律用 `utf-8-sig` 读取。

## 3. 发布后 `view` 接口返回 -404

- **现象**：`verify_published.py` 刚发布就跑，返回 `-404 啥都木有`。
- **根因**：稿件在审核队列（`is_pubing`），`view` 还没公开。
- **修正**：等约 2 分钟重试；通过标准是 `state=0`（公开）、`playurl` 有 durl/dash、
  创作中心 `arc_audits` 无 `reject_reason`。
- **预防**：不要因为 -404 就重复投稿，会变成重复稿件。

## 4. 音轨采样率变成 96kHz

- **现象**：`validate_assets.py` 报 `音频采样率必须是 44100，实际 96000`。
- **根因**：上游 `loudnorm` 没指定 `-ar`，ffmpeg 按容器默认选了高采样率。
- **修正**：配音/成片阶段显式
  `-c:a aac -b:a 192k -ar 44100 -movflags +faststart`。
- **预防**：本 skill 的校验脚本把 44100 作为硬性检查项。

## 5. `x/tag/archive/add` 返回 -403

- **现象**：想单独补标签，接口返回 `-403 访问权限不足`。
- **根因**：web Cookie 对该接口无权限。
- **修正**：改用 `edit/v3`，带上 `aid` 与完整 `tag` 重传。

## 6. 分块上传偶发失败

- **现象**：某个 chunk `PUT` 返回非 200 或超时。
- **处理**：`publish_bilibili.py` 已内置 4 次重试、间隔 3 秒；全部失败才中止。
- **注意**：中止后不要换新的 `biz_id` 重来，除非确认预上传上下文失效。

## 7. UPOS 完成通知 / 提交阶段字段错位

- **要点**：`videos[0].filename` 不带扩展名；完成通知的 `name` 带扩展名；
  `videos[0].cid = biz_id`。三者写错会报参数错误或投稿失败。

## 8. CSRF

- **要点**：`bili_jct` 就是 CSRF。`add/v3` / `edit/v3` 需要在 URL 参数和 body 里
  同时带 `csrf`。

## 9. Cookie 提取失败

- **现象**：CDP 端口连不上，或提取出的 Cookie 缺 `SESSDATA`。
- **修正**：确认「哔哩哔哩」客户端已登录；用
  `./scripts/extract_bili_login_macos.sh 9222 /tmp/cookies.json`，
  它会重启客户端并核对 `nav` 返回的 `isLogin`。
- **不要**：尝试解密客户端 SQLite（新版是 App-Bound 加密，解不开）。
