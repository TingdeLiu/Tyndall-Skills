# Open Design 包契约

> 本文记录已检查实现的行为。接口、路径和 token 数量可能随版本变化，请以当前安装版本为准。


## 目录

- [路径](#路径)
- [设计系统包结构](#设计系统包结构)
- [manifest.json](#manifestjson)
- [metadata.json](#metadatajson)
- [tokens.css 的 56 个共享 token](#tokenscss-的-56-个共享-token)
- [技能结构](#技能结构)
- [权威副本在哪](#权威副本在哪)

## 路径

用户数据根（`<ns>` 通常是 `release-stable-win`）：

```
%APPDATA%\Open Design\namespaces\<ns>\data\
├── design-systems\<id>\        用户安装的设计系统，对外 id 为 user:<id>
├── skills\<name>\              用户技能
├── app.sqlite                  workspace_resources / projects 等表
└── ...
```

程序本体（内置包在这儿，只读参考）：

```
%APPDATA%\Open Design\launcher\channels\stable\namespaces\<ns>\versions\<版本>\payload\resources\
├── open-design\design-systems\     152 个内置包 + _schema\
├── open-design\skills\             内置技能
└── app\prebundled\daemon\chunks\   daemon 代码（要查行为就 grep 这里）
```

`%LOCALAPPDATA%\Programs\Open Design\` 只是引导壳，它的 `open-design-config.json`
里的 `appVersion` **不随升级更新**，别拿它判断版本；实际版本看
`logs\desktop\latest.log`。

daemon 端口每次启动都变，从 `logs\daemon\latest.log` 里 grep `127.0.0.1:(\d+)`。

## 设计系统包结构

`schemaVersion` 为 `od-design-system-project/v1`。三个必需文件：

```
<id>/
├── manifest.json      发现用的元数据、来源、声明的文件路径
├── DESIGN.md          给 agent 的品牌散文（至少 7 个 H2 才符合仓库规范）
└── tokens.css         编译后的语义 token 表
```

可选（声明在 manifest 里才会被接口暴露）：

```
USAGE.md                    读取顺序与 do/avoid
components.html             独立组件夹具
components.manifest.json    从 components.html + tokens.css 派生的缓存
design-tokens.json          Design Tokens JSON（派生）
tailwind-v4.css             Tailwind v4 映射（派生）
assets/  fonts/  preview/  source/
metadata.json               用户包专有，见下
```

只有 `DESIGN.md` 的旧式目录也能被发现（兼容路径），但不是新内容的目标形态。

## manifest.json

顶层允许的键：`schemaVersion` `id` `name` `category` `description` `source`
`files` `usage` `componentsManifest` `importMode` `craft` `fonts` `preview`
`sourceFiles` `runtime`。

- `id` 必须等于文件夹名（安装后目录名由 `basename(源路径)` 决定，所以打包时就要对齐）
- `files` 允许：`design` `tokens` `designTokens` `tailwind` `components`
- `source.type`：`bundled` | `local` | `github` | `shadcn`，每种允许的键不同
  - `local` → `{type, path, importedAt}`
  - `bundled` → `{type, origin}`
- `importMode`：`normalized` | `hybrid` | `verbatim`
- `category` 是自由文本，不是枚举（内置包里能看到 "Editorial · Studio" 这类一次性值）
- `preview.pages[]`：`{path, role, title}`，`role` 也是自由文本
- `sourceFiles` 允许：`scanned` `evidence` `tokens` `report` `snippets`
- 每个声明的路径必须安全、相对、且真实存在

```json
{
  "schemaVersion": "od-design-system-project/v1",
  "id": "acme",
  "name": "Acme",
  "category": "Productivity & SaaS",
  "description": "一句话英文目录摘要。",
  "source": { "type": "local", "path": "D:\\...", "importedAt": "2026-08-30T00:00:00.000Z" },
  "files": { "design": "DESIGN.md", "tokens": "tokens.css", "components": "components.html" },
  "usage": "USAGE.md",
  "importMode": "verbatim",
  "craft": { "applies": [], "suggested": ["color", "accessibility-baseline"], "exemptions": [] },
  "preview": { "dir": "preview", "pages": [{ "path": "preview/colors.html", "role": "colors", "title": "Colors" }] },
  "sourceFiles": { "evidence": "source/evidence.md" }
}
```

## metadata.json

**用户包必须有**。没有它，daemon 会套默认值 `status: "draft"`，而界面对个人来源的
包有 `A = 非个人 || 已发布` 的判断，草稿态会被当成不可用。

```json
{
  "title": "显示名（界面上显示的就是它）",
  "category": "自由文本",
  "surface": "web",
  "status": "published",
  "artifactMode": "agent-managed",
  "createdAt": "2026-08-30T09:00:00.000Z",
  "updatedAt": "2026-08-30T09:00:00.000Z",
  "provenance": { "sourceNotes": "来源说明" }
}
```

- `surface`：`web` | `image` | `video` | `audio`
- `status`：`draft` | `published`
- `artifactMode`：`generated` | `agent-managed`（手工维护的内容用后者，避免生成器逻辑介入）
- `workspaceId` 字段由 install 接口的 claim 自动写入，**打包时不要带**，那是机器专属的

## tokens.css 的 56 个共享 token

每个包都必须声明全部 56 个——artifact 是把某一个品牌的 `:root` 粘进单个 `<style>`
里的，没有全局样式表兜底，缺一个就静默失效。

抄名单最快的办法（拿内置包当模板）：

```bash
grep -oh -- "^\s*--[a-z0-9-]*:" "<payload>/resources/open-design/design-systems/claude/tokens.css" \
  | tr -d ' :' | sort -u
```

分组（56 个）：

| 组 | token |
|---|---|
| 表面 3 | `--bg` `--surface` `--surface-warm` |
| 前景 4 | `--fg` `--fg-2` `--muted` `--meta` |
| 边框 2 | `--border` `--border-soft` |
| 强调 4 | `--accent` `--accent-on` `--accent-hover` `--accent-active` |
| 语义 3 | `--success` `--warn` `--danger` |
| 字体 3 | `--font-display` `--font-body` `--font-mono` |
| 字号 8 | `--text-xs` `--text-sm` `--text-base` `--text-lg` `--text-xl` `--text-2xl` `--text-3xl` `--text-4xl` |
| 行距 3 | `--leading-body` `--leading-tight` `--tracking-display` |
| 间距 8 | `--space-1` `--space-2` `--space-3` `--space-4` `--space-5` `--space-6` `--space-8` `--space-12` |
| 段落纵距 3 | `--section-y-desktop` `--section-y-tablet` `--section-y-phone` |
| 圆角 4 | `--radius-sm` `--radius-md` `--radius-lg` `--radius-pill` |
| 立体 3 | `--elev-flat` `--elev-ring` `--elev-raised` |
| 焦点 1 | `--focus-ring` |
| 动效 3 | `--motion-fast` `--motion-base` `--ease-standard` |
| 容器 4 | `--container-max` `--container-gutter-desktop` `--container-gutter-tablet` `--container-gutter-phone` |

品牌自有的、不在这套契约里的 token 作为扩展追加在同一个 `:root` 后半段即可，
没有数量限制。**把源系统原有的变量名一并保留**，这样源包里的组件源码不用改就能跑。

校验完整性：

```bash
grep -oh -- "^\s*--[a-z0-9-]*:" 内置包/tokens.css | tr -d ' :' | sort -u > /tmp/req.txt
grep -oh -- "^\s*--[a-z0-9-]*:" 我的包/tokens.css | tr -d ' :' | sort -u > /tmp/got.txt
comm -23 /tmp/req.txt /tmp/got.txt   # 输出为空即齐备
```

## 技能结构

就是 `SKILL.md` + 附属文件，跟 Claude Code 的技能结构直接兼容。frontmatter 里加
`od` 块可以归类：

```yaml
---
name: my-skill
description: |
  多行描述
triggers:
  - "触发词"
od:
  mode: design-system
  category: design-systems
---
```

`od.mode` 取 `design-system` 时会被归到设计系统类。技能 id 取自 frontmatter 的
`name`（没有则用文件夹名），**安装时 id 冲突会返回 409**。

## 权威副本在哪

行为存疑时直接查 daemon 代码，比猜快：

```bash
cd "<payload>/resources/app/prebundled/daemon/chunks"
grep -l "关键字" *.mjs
```

- 路由定义：`server-*.mjs` 里 `app.get("/api/...")` / `app.post(...)`
- 契约 schema：`<payload>/resources/open-design/design-systems/_schema/`
  （`manifest.schema.ts` `tokens.schema.ts` `defaults.css` `AGENTS.md`）
- 内置包写法参考：`<payload>/resources/open-design/design-systems/claude/`
