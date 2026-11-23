# 记忆库数据格式（schema v1）

故事、信件和人物档案都是 UTF-8 编码的 Markdown，开头是 YAML frontmatter。字段保持简单：只用 `键: 值` 和 `键: [a, b]` 两种写法，不用嵌套。每篇条目都带 `schema: 1`，媒体和原始转写另存为原件。

## 配置文件

位置：`~/.memory-keeper/config.json`（不在记忆库里，这样换文件夹不丢配置）。

```json
{
  "schema": 1,
  "vault_path": "C:/Users/xxx/Documents/我的记忆",
  "auto_save": false,
  "language": "zh",
  "created": "2026-11-14"
}
```

## 目录结构

```
<vault_path>/
├── README.md          ← 给用户看的说明（init 时生成）
├── INDEX.md           ← 总索引，由脚本生成，AI 回顾时先读它
├── TIMELINE.md        ← 时间线，由脚本按事情发生的年份生成
├── profile.md         ← 关于记忆库主人
├── memories/          ← 一段记忆一个文件
├── people/            ← 一个人一个档案
├── capsules/          ← 信件 / 时间胶囊
├── media/             ← 首次添加素材时建立，保存原格式二进制文件
├── interviews/        ← 每次采访的原始转写、行号分段和媒体清单
├── exports/           ← 可打印的书（HTML）和单篇家庭记忆卡（ZIP）
└── .trash/            ← remove 移过来的条目，脚本不读它，用户确认后自己清空
```

## 文件命名

- 记忆：`memories/<记录日期>-<标题>.md`，如 `memories/2026-11-14-外婆的院子.md`
- 人物：`people/<称呼>.md`，如 `people/外婆.md`。用户平时怎么叫这个人就怎么命名。
- 胶囊：`capsules/<记录日期>-<标题>.md`，如 `capsules/2026-11-14-给女儿的十八岁.md`
- 标题里去掉 `/ \ : * ? " < > |` 这些文件名不允许的字符。重名时在末尾加 `-2`、`-3`。
- 文件名（不含 `.md`）就是这个条目的 id，文件之间用 `[[id]]` 互相链接（Obsidian 也能直接识别）。
- 用 `add` 归档时以上规则由脚本处理：草稿里不用写 `schema`，`recorded` 不写就取今天，记忆正文没链接到 `people` 里的人时会自动补一个「相关」小节。
- 列表字段里的项用 `,`、`，` 或 `、` 分隔，所以人名、标签本身不要含这几个符号。

## 记忆 `memories/*.md`

```markdown
---
schema: 1
type: memory
title: 外婆的院子
summary: 每年暑假在外婆家院子里乘凉、吃西瓜，外婆用蒲扇给我扇风。
narrator: 我
event_date: 1990s 夏天
recorded: 2026-11-14
people: [外婆]
places: [江西老家]
mood: 温暖
tags: [童年, 暑假]
---

（正文：讲述者第一人称的叙述，长度跟着素材走，一般不超过 600 字）

## 原话

> 「外婆那把蒲扇，扇一下就要说一句『心静自然凉』。」

## 相关

- 人物：[[外婆]]
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | 是 | 简短、具体，像一篇短文的标题 |
| `summary` | 是 | 一句话摘要，会进入 INDEX.md |
| `narrator` | 是 | 讲述者。用户本人填「我」，采访家人时填称呼，如「爸爸」 |
| `event_date` | 否 | 事情发生的时间，照用户的原话写，允许模糊：`1998`、`1990s 夏天`、`大学二年级` |
| `year` | 否 | 用于时间线排序的年份：`1998` 或年代 `1990s`。`event_date` 里已经有四位年份时可以不填；只在能从用户说过的事实推出时填 |
| `recorded` | 是 | 记录日期，`YYYY-MM-DD` |
| `people` | 否 | 涉及的人，用与 `people/` 文件名一致的称呼。家人讲到用户本人时写「我」（英文库写 `me`），不会建档案 |
| `places` | 否 | 地点 |
| `mood` | 否 | 一个词：温暖、快乐、平静、怀念、遗憾、难过、骄傲、复杂 等 |
| `tags` | 否 | 2～4 个标签。加上 `私密`（英文库用 `private`）后，INDEX 和时间线只显示标题，`search --no-private` 会排除它，详见 safety.md |
| `interview`、`segment` | 否 | 来自采访时由脚本成对写入。对应原始转写及其中一段，段号从 1 起 |

媒体引用位于记忆的 `## 原始素材`（英文 `## Original sources`）小节，使用可随库移动的相对 Markdown 链接，支持步骤编号和时间位置。该小节仅供本地回看。采访的 `session.json` 保存原文件名、原文行号范围和原件清单；确认状态以已归档记忆中的采访 id 和段号为准。操作示例见[原始素材和采访](sources.md)。

## 人物 `people/*.md`

```markdown
---
schema: 1
type: person
name: 外婆
relation: 外婆
birth: 1932
alive: false
---

（简介：用户讲过的关于这个人的要点，几句话即可，随记忆增加慢慢补充）

## 相关记忆

- [[2026-11-14-外婆的院子]]
```

`birth`、`alive`、`relation` 不知道就不写。`aliases: [姥姥]` 保存用户确认的其他称呼。脚本自动建的档案只有 `name`，`relation` 等知道了再补。

一段记忆链接到的人物 = `people` 里的人 + 讲述者（讲述者是用户本人时除外）。他们的档案都要在「相关记忆」里列出这段记忆。

同一件事有不同讲述者的版本时，分开存，在各自的「相关」小节里互相链接：

```markdown
## 相关

- 人物：[[外婆]]
- 另一个讲法：[[2026-12-01-外婆的院子]]
```

## 胶囊 `capsules/*.md`

```markdown
---
schema: 1
type: capsule
title: 给女儿的十八岁
to: 女儿
deliver_mode: date
deliver_value: 2040-06-01
recorded: 2026-11-14
status: draft
---

（信的正文）
```

- `deliver_mode`：`date`（某天）、`location`（某地）、`event`（某个时刻，由用户决定）、`after_gone`（我不在以后）
- `deliver_value`：日期、地点名或事件描述；`after_gone` 时留空
- `status`：skill 只会写 `draft`。送达由 Memory app 负责。
- `tags`（可选）：信里引用了私密内容时写 `[私密]`，INDEX 里会标出，`search --no-private` 会排除它。

## profile.md

```markdown
---
schema: 1
type: profile
name: 小明
---

## 关于我

（基本信息：在哪长大、做什么、家里有谁，用户愿意说多少写多少）

## 说话方式

（用户的口头禅、语气特点，写作时参考）
```

## TIMELINE.md

由脚本和 INDEX.md 一起生成，按年代分组：有 `year`（或 `event_date` 里有四位年份）的记忆按年份排，人物档案里有 `birth` 的显示为出生；推不出年份的放在最后的「时间未知」。

```markdown
# 时间线

## 1930 年代

- 1932 · [[外婆]] 出生

## 1990 年代

- 1990s 夏天 · [[2026-11-14-外婆的院子]] · 讲述：我 — 每年暑假在外婆家院子里乘凉……

## 时间未知

- 毕业那年 · [[2026-11-14-第一份工作]] · 讲述：我 — ……
```

## INDEX.md

由 `python scripts/memory_vault.py index <vault_path>` 生成（`add`、`remove`、`check --fix` 也会顺带重建），不要手工大改。英文记忆库（`language: en`）的标题和标签用英文。格式：

```markdown
# 记忆索引

共 3 段记忆 · 2 位人物 · 1 封信

## 记忆

- 2026-11-14 · [[2026-11-14-外婆的院子]] · 讲述：我 · 外婆 · 温暖 — 每年暑假在外婆家院子里乘凉……

## 人物

- [[外婆]] · 外婆 · 2 段记忆

## 信件

- [[2026-11-14-给女儿的十八岁]] · 给 女儿 · date 2040-06-01 · draft
```

脚本无法运行时，手动按上面格式追加一行即可，下次脚本运行会重新生成整个文件。
