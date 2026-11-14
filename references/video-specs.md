# 成片规格与画质取舍（2026-11 实测）

本文记录 B 站 Web 投稿对成片规格的实际处理，以及本地实操得到的结论。
文中「实测」指用真实账号在 2026-11 通过 `x/vu/web/add/v3` 投稿并核验的结果。

## 1. 容器与编码：B 站会自己转码

| 项目 | 状态 |
|---|---|
| H.264 / AVC | 兼容性最好。平台可能直接沿用你的码率或轻度再压 |
| HEVC / H.265 | **可以投稿**。平台会转成 AVC 再对外分发 |
| AV1 | 可以投稿，同样会被转码 |
| 容器 | MP4 / MOV / MKV / FLV 都可以，MOV 里的 H.264/HEVC 不会被拒 |
| 音轨 | AAC，44.1 kHz 与 48 kHz 都可 |

**关键结论：上传 HEVC 不会「发布失败」，只会被平台再压一次。**
所以「转码成 H.264 再传」和「直接传 HEVC」在平台侧的结果是一致的：
都是平台拿你的源再压一遍。前者多了一次你自己的有损编码，**画质只会更差**。

因此本 skill 的默认策略是：

> **不要为迁就平台而重新编码。直接上传原始成片。**

只有在你明确知道 B 站的压制策略会对你这类型内容更友好时，才主动准备 H.264 副本。

### 参考：社区实测结论

- B 站 Web 投稿会把 HEVC 稿件转码为 AVC；同样码率下 VMAF 对比中
  AVC 约 95.6、HEVC 约 94.1，HEVC 压制后略逊。
- 1080P 档位的平均码率上限约 6000 kbps；源文件远高于这个值时平台必然再压。
- 码率卡在 5900 kbps、yuv420p / 8bit / BT.709 是 1080P 的稳妥区间。

### 参考：不同来源的码率建议

| 来源 | 建议 |
|---|---|
| 平台压制研究 | 1080P 平均码率控制在 5900 kbps 最稳 |
| 4K 投稿攻略 | 4K 码率控制在 16000–18500 kbps，Level 4.1，CRF 16–18 |
| 真实创作者分享 | 高码率上传后再压，不如自己预压到 5000 kbps 防止二压不可控 |

> 这些是社区经验值，**不是平台硬性规则**。以你账号后台实际显示的码率为准。

## 2. 本 skill 实操踩过的坑

### 坑 1：Cookie 提取到的是「重启前的旧值」

`extract_bili_login_macos.sh` 会先关闭客户端再用调试端口重启。第一次执行时
CDP 里读到的可能仍是旧会话的 Cookie，表现为：

- 提取脚本打印 `SESSDATA: 有`、`登录有效`
- 但真正投稿时返回 `code: -101 账号未登录`

**处理：** 客户端已处于调试端口模式时，直接再跑一次
`scripts/extract_bili_cookies.py --cdp http://127.0.0.1:9222 --out cookies.json`
取当前会话的真实 Cookie，并核对 `x/web-interface/nav` 返回 `isLogin=true`。

### 坑 2：`add/v3` 返回 `21001 参数错误`

这是 2026-11 实际遇到的失败。根因是 **`videos[0].cid` 传了字符串**。
`biz_id` 从预上传接口回来是数字，但脚本里 `str(ticket["biz_id"])` 把它变成了字符串，
`add/v3` 直接判为参数错误。

```python
cid = int(ticket["biz_id"])   # 必须是数字
```

### 坑 3：`tid` 不能手填

Web 端的 `tid` 语义已经变了：**真正生效的是「预测稿件类型」接口返回的第一项**。

```
POST https://member.bilibili.com/x/vupre/web/archive/types/predict
```

请求体（multipart/form-data）：`filename`（可空）、`title`。

返回 `data[0]` 含 `id`（子分区 id，即 `tid`）与 `human_type`（新分区 id，即 `human_type2`）。
本 skill 现在会自动调用它，不再手填 `tid`。

### 坑 4：`add/v3` 需要 WBI 签名

只带 `ts` + `csrf` 在当前接口上会返回 `21001`。查询参数需要 WBI 签名：

```
web_location=333.1024 & t=<ms> & csrf=<bili_jct> & wts=<秒> & w_rid=<md5>
```

`w_rid` 的算法：从 `x/web-interface/nav` 的 `wbi_img.img_url` / `sub_url` 取
两个 32 位 key，拼成 64 位后按固定的置换表重排取前 32 位作为 mixin key；
把除 `w_rid` 外的参数按 key 排序、过滤 `!'()*` 字符后拼成查询串，
`md5(查询串 + mixin key)` 即 `w_rid`。

本 skill 已内置 `wbi_sign()`，无需外部依赖。

### 坑 5：投稿失败时文件已经在 B 站存储里了

上传（预上传 → 分片 → 封口）成功后，文件已经在 upos 存储中，即使 `add/v3`
投稿失败也不会消失。重新投稿时**不需要重传 GB 级文件**。

本 skill 现在会在封口后写 `upload_receipt.json`（含 `stem`、`cid`、封面 URL），
投稿失败可用它免重传重投：

```bash
python3 scripts/publish_bilibili.py \
  --video final.mp4 --cover cover16x9.png --cover43 cover4x3.png \
  --cookies cookies.json --config publish.json \
  --submit-only upload_receipt.json
```

## 3. 投稿前自检清单

| 项 | 要求 |
|---|---|
| 分辨率 | 1920×1080（4K 需短边 ≥1600 才进 4K 通道） |
| 帧率 | 30 或 60 整数帧率，不要 59.94 |
| 像素格式 | yuv420p / 8bit |
| 色彩空间 | BT.709 |
| GOP | ≤ 2 秒（60fps → ≤120 帧） |
| 音轨 | AAC，44.1 或 48 kHz |
| 码率 | 1080P 约 5900–6000 kbps；4K 16000–18500 kbps |
| 字幕 | 单独字幕流会被剥离，音轨必须内嵌 |
| 标题 | ≤80 字（超长报 `21103`） |
| 简介 | ≤2000 字 |
| 标签 | ≤10 个 |

## 4. 上传后怎么确认画质

B 站不显示你上传时的原始参数，看播放时的实际值：

- PC 网页端：右键播放画面 →「统计信息」→「Video Bitrate」
- 长期低于 5000 kbps（1080P 档）说明被压制了
- 这个数值是**平台压制后**的结果，不是你的源码率
