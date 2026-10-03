# B 站网页投稿接口参考

本文按「把一个视频投出去」的实际调用顺序整理，只覆盖发布链路需要的接口。
字段值为实测结果；平台可能调整，以线上行为为准。

通用约定：

- 域名：投稿与封面走 `member.bilibili.com`，查询走 `api.bilibili.com`
- 认证：Cookie 中的 `SESSDATA`
- CSRF：Cookie 中的 `bili_jct`，写操作需要在 URL 参数与请求体里同时携带 `csrf`
- 请求头建议带浏览器 `User-Agent`，并设 `Referer: https://member.bilibili.com/`
  与 `Origin: https://member.bilibili.com`

---

## 1. 上传封面

```
POST https://member.bilibili.com/x/vu/web/cover/up?ts=<毫秒时间戳>
Content-Type: application/x-www-form-urlencoded
```

| 参数 | 说明 |
|---|---|
| `csrf` | `bili_jct` |
| `cover` | `data:image/png;base64,<内容>` |

成功返回 `{"code":0,"data":{"url":"..."}}`，`url` 即后面投稿要用的封面地址。
16:9 与 4:3 各上传一次，分别用于 `cover` 和 `cover43`。

---

## 2. 申请上传凭据（预上传）

```
GET https://member.bilibili.com/preupload
```

| 参数 | 值 |
|---|---|
| `name` | 文件名，**带扩展名** |
| `size` | 字节数 |
| `r` | `upos` |
| `profile` | `ugcfx/bup` |
| `ssl` | `0` |
| `version` | `2.10.4.0` |
| `build` | `2140000` |

成功返回 `OK=1`，关键字段：

| 字段 | 用途 |
|---|---|
| `auth` | 后续 UPOS 请求的 `X-Upos-Auth` 头 |
| `endpoint` | UPOS 主机 |
| `upos_uri` | 形如 `upos://bucket/path/name.ext` |
| `biz_id` | 稿件侧的 `cid` |
| `chunk_size` | 官方建议的分片大小 |

UPOS 实际请求地址 = `https:` + `endpoint` + `/` + `upos_uri` 去掉 `upos://` 前缀。

---

## 3. 开启分片会话

```
POST <UPOS 地址>?uploads=&output=json&profile=ugcfx/bup&filesize=<总字节>&partsize=<分片大小>&biz_id=<biz_id>
Header: X-Upos-Auth: <auth>
```

成功返回 `OK=1` 与 `upload_id`。

---

## 4. 上传单个分片

```
PUT <UPOS 地址>?uploadId=<upload_id>&chunks=<总分片数>&total=<总字节>&chunk=<下标从0>&size=<本片字节>&partNumber=<下标+1>&start=<起始偏移>&end=<结束偏移>
Header: X-Upos-Auth: <auth>
Content-Type: application/octet-stream
Body: 分片二进制
```

返回 HTTP 200 即成功，响应头 `ETag` 需要记录，封口时回传。
失败可重试；本 skill 默认重试 4 次、间隔 3 秒。

---

## 5. 封口（完成通知）

```
POST <UPOS 地址>?name=<文件名，带扩展名>&uploadId=<upload_id>&biz_id=<biz_id>&output=json&profile=ugcfx/bup
Header: X-Upos-Auth: <auth>
Content-Type: application/json; charset=UTF-8

{"parts":[{"partNumber":1,"eTag":"<etag1>"}, ...]}
```

成功返回 `OK=1`。到此视频文件已进入 B 站侧存储。

---

## 6. 投稿

```
POST https://member.bilibili.com/x/vu/web/add/v3?ts=<毫秒时间戳>&csrf=<bili_jct>
Content-Type: application/json
```

```json
{
  "videos": [{"filename": "<upos 文件名，不带扩展名>", "title": "...", "desc": "", "cid": "<biz_id>"}],
  "cover": "<16:9 封面 URL>",
  "cover43": "<4:3 封面 URL，可空>",
  "title": "...",
  "copyright": 1,
  "tid": 231,
  "tag": "a,b,c",
  "desc_format_id": 9999,
  "desc": "...",
  "recreate": -1,
  "dynamic": "...",
  "interactive": 0,
  "act_reserve_create": 0,
  "no_disturbance": 0,
  "no_reprint": 0,
  "subtitle": {"open": 0, "lan": ""},
  "dolby": 0,
  "lossless_music": 0,
  "up_selection_reply": false,
  "up_close_reply": false,
  "up_close_danmu": false,
  "web_os": 3,
  "csrf": "<bili_jct>"
}
```

三个最容易写错的点：

1. `videos[0].filename` **不带扩展名**，而封口通知里的 `name` **带扩展名**。
2. `videos[0].cid` 等于预上传返回的 `biz_id`。
3. `copyright=1` 表示自制；`tid` 是分区 ID。

成功返回 `data.bvid` 与 `data.aid`。

提交前可以先 `GET https://member.bilibili.com/x/geetest/pre/add` 预热风控，非必需。

---

## 7. 修改已发布稿件

```
POST https://member.bilibili.com/x/vu/web/edit?ts=<毫秒时间戳>&csrf=<bili_jct>
```

请求体与 `add/v3` 基本一致，另外必须带 `aid`。用于修正标题、简介、标签等
元数据。

> **不要用换源接口替换已发布视频。** 需要换视频源时重新投稿，或由账号所有者
> 在创作中心手动操作。本 skill 不提供换源能力。

`x/tag/archive/add` / `x/tag/archive/del` 在 web Cookie 下会返回 `-403`，
补标签请走 `edit/v3` 全量重传 `tag`。

---

## 8. 分区 ID

```
GET https://member.bilibili.com/x/vupre/web/archive/human/type2/list
```

返回 `data.type_list`，每项含 `id` 与 `name`。也可以查
`https://member.bilibili.com/x/vupre/web/archive/pre` 的 `typelist`。

常用值见 `publish-config.md`，但分区会调整，**以接口实时返回为准**。

---

## 9. 发布后查询

| 用途 | 接口 |
|---|---|
| 稿件详情 | `GET https://api.bilibili.com/x/web-interface/view?bvid=` |
| 播放地址 | `GET https://api.bilibili.com/x/player/playurl?bvid=&cid=&qn=16` |
| 标签 | `GET https://api.bilibili.com/x/tag/archive/tags?bvid=` |
| 稿件列表与审核 | `GET https://member.bilibili.com/x/web/archives?status=all&pn=1&ps=10` |
| 登录态 | `GET https://api.bilibili.com/x/web-interface/nav` |

判读要点：

- `view` 的 `code=0` 且 `state=0` 表示已公开。
- 刚投稿后返回 `-404` 通常是审核排队（`is_pubing`），等约 2 分钟再查。
- `playurl` 出现 `durl` 或 `dash` 说明可播放。
- 创作中心条目里 `reject_reason` 非空表示被驳回。
