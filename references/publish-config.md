# publish.json 配置参考

`publish.json` 必须保存为 **UTF-8 无 BOM**。用 PowerShell 写过文件的话，
Python 读取一律用 `encoding="utf-8-sig"`。

## 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `title` | str | 是 | 稿件标题，1–80 字 |
| `desc` | str | 是 | 简介，1–2000 字；可分段时间轴、来源标注 |
| `tag` | str | 是 | 逗号分隔，最多 10 个；超出会被静默丢弃 |
| `dynamic` | str | 否 | 同步到粉丝动态的文案 |
| `tid` | int | 是 | 分区 ID，见下表 |
| `human_type2` | int | 否 | 新分区二级分类 ID，例如 `1012` |
| `no_reprint` | int | 否 | `1` = 禁止转载，`0` = 允许（默认） |

`publish_bilibili.py` 还接受命令行参数：

| 参数 | 说明 |
|---|---|
| `--video` | 成片路径 |
| `--cover` | 16:9 封面（必填） |
| `--cover43` | 4:3 封面（可选） |
| `--cookies` | Cookie JSON，需含 `SESSDATA` 与 `bili_jct` |
| `--config` | `publish.json` 路径 |
| `--skip-validate` | 跳过内置元数据校验（不推荐） |

## 封面

| 位置 | 尺寸 | 对应字段 |
|---|---|---|
| 16:9 主封面 | 1920×1080 | `cover` |
| 4:3 封面 | 1440×1080 | `cover43` |

两张封面必须是**独立排版**，不是互相裁切。不上传 4:3 时 `cover43` 为空字符串。

## 常用分区 ID（tid）

| tid | 分区 |
|---|---|
| 231 | 科技 → 计算机技术 |
| 95 | 科技 → 数码 |
| 201 | 知识 → 科学科普 |
| 208 | 知识 → 财经商业 |
| 209 | 知识 → 人文历史 |
| 21 | 生活 → 日常 |
| 138 | 生活 → 搞笑 |
| 76 | 生活 → 美食 |
| 26 | 生活 → 综合 |
| 188 | 数码 → 手机平板 |
| 199 | 数码 → 电脑装机 |
| 211 | 科技 → 软件应用 |
| 230 | 科技 → 演讲·公开课 |

分区会调整，**权威来源是接口实时返回**，不要长期硬编码：

```bash
curl -s "https://member.bilibili.com/x/vupre/web/archive/human/type2/list?t=$(date +%s000)" \
  -H "Cookie: SESSDATA=<...>"
```

或直接查 `references/bilibili-upload-api.md` 的「获取新分区ID」「预测稿件类型」两节。

## 长度与格式限制

| 项 | 限制 |
|---|---|
| 标题 | ≤80 字 |
| 简介 | ≤2000 字 |
| 标签 | ≤10 个，逗号分隔 |
| 视频 | H.264 + AAC，建议 1920×1080 / 30fps / 44.1kHz |
| 封面 | 16:9 1920×1080；4:3 1440×1080 |

## add/v3 提交字段

`publish_bilibili.py` 构造的 payload 关键字段：

```json
{
  "videos": [{"filename": "<upos 文件名去扩展名>", "title": "...", "desc": "", "cid": "<biz_id>"}],
  "cover": "<16:9 URL>",
  "cover43": "<4:3 URL 或空>",
  "copyright": 1,
  "tid": 231,
  "tag": "a,b,c",
  "desc_format_id": 9999,
  "recreate": -1,
  "interactive": 0,
  "no_reprint": 0,
  "subtitle": {"open": 0, "lan": ""},
  "web_os": 3,
  "csrf": "<bili_jct>"
}
```

注意：`videos[0].filename` **不带扩展名**；UPOS 完成通知的 `name` **带扩展名**；
`videos[0].cid` 等于预上传返回的 `biz_id`。
