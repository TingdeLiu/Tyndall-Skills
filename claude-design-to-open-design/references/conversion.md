# Claude Design 导出 → Open Design 包

## 目录

- [输入长什么样](#输入长什么样)
- [产出两样东西](#产出两样东西)
- [tokens.css 怎么写](#tokenscss-怎么写)
- [DESIGN.md 怎么写](#designmd-怎么写)
- [其余文件](#其余文件)
- [技能那一份](#技能那一份)

## 输入长什么样

Claude Design 导出的 zip 解开后大致是：

```
SKILL.md                 Agent Skills frontmatter
readme.md                品牌全文——最有价值的部分，全部规则都在这
styles.css               只有 @import 列表
tokens/                  colors / fonts / typography / spacing / radius /
                         elevation / motion / semantic 八个 .css
components/              分 core/forms/navigation/content/layout，
                         每个组件有 .jsx + .d.ts + .prompt.md
ui_kits/<surface>/       成品页面 + index.html 点击原型
slides/                  演示模板（如果源里有）
guidelines/              规范样张 HTML
assets/                  品牌素材
research/                证据材料
uploads/                 原始上传件（体积大，通常不必带）
_ds_manifest.json        组件索引
_ds_bundle.js            打包产物
```

**先读 `readme.md`**，它是唯一的真相来源。里面通常已经写明了：哪些值是从源文件量出来
的、哪些是替代品、哪些故意留空。这些区分必须原样传递到 `DESIGN.md`，不要抹平成
「看起来完整」的样子。

## 产出两样东西

| 产出 | 装到哪 | 作用 |
|---|---|---|
| **设计系统包** | `data\design-systems\<id>\` | token 契约 + 品牌散文 + 组件夹具 + 预览页，参与 prompt 组合 |
| **技能** | `data\skills\<name>\` | 组件源码、UI kit、模板、素材，agent 要抄真东西时用 |

两个都装。设计系统包管"守规矩"，技能管"有料可抄"。

打包成可移植结构：

```
<安装包>/
├── install.ps1                  （从本 skill 的 scripts/ 复制）
├── design-system/<id>/          注意：目录名必须等于 manifest.id
└── skill/<name>/
```

## tokens.css 怎么写

把源系统的 token 映射到那 56 个共享 token（名单见
[od-package-contract.md](od-package-contract.md)），**再把源系统原有的变量名整套保留在
后半段**——源包里的组件 `.jsx` 引用的是原名，保留了才能直接跑。

映射时守住几条：

- **值全部来自源系统**，不要为了"凑齐"而发明。源里没有的（比如常见的 `--focus-ring`、
  状态色），从品牌内部已有的颜色里取，别引入外来的通用色（不要默认蓝、默认红）。
- **凡是补的、不是量出来的，在 `tokens.css` 注释和 `source/evidence.md` 里点名**。
- **间距/字号阶梯照抄源系统的节奏**。源系统若是 5 的倍数就别改成 4/8；
  8 步契约装不下的档位（如 20、28）作为扩展保留。
- **把源系统最响的那条规矩编进 token 里**。例如"全站方角"就该让
  `--radius-sm/md/lg` 全是 `0`，把唯一的例外单独留成扩展 token。
- **两套互斥的表面**（例如官网红 + 汇报蓝）只能有一套进主契约，另一套作为
  `--deck-*` 之类的扩展段落，并在 `DESIGN.md` 和 `USAGE.md` 里写明不许混用。

写完必须校验 56 个齐备（比对命令见 contract 文档）。

## DESIGN.md 怎么写

以源 `readme.md` 为底，重组成至少 7 个 H2。**不要压缩掉具体数字和出处**——
"卡片阴影是 `3px 10px 18px rgba(175,164,142,.27)`，暖的、偏移的，中性灰阴影一眼出戏"
这种句子才是这份文档的价值，改成"使用柔和阴影"就废了。

必须保留的几类内容：

- 每个值的**出处**（量自哪个文件）
- **故意留空的部分**（源里缺失的素材、字体二进制），明确标注为 gap 而不是补齐
- **替代品说明**（用什么顶替了原字体/图标，为什么）
- **禁止事项**（不许圆角、不许毛玻璃、不许 emoji…），越具体越好
- 若源系统有多个表面，开头就讲清楚它们不共用调色板

如果目标包会被界面读取标题，注意 `metadata.json` 的 `title` 才是显示名。

## 其余文件

- **`USAGE.md`** —— 读取顺序、do/avoid、先选哪个表面。简短。
- **`components.html`** —— 独立夹具，把 `:root` 整段粘进 `<style>`，
  所有可见值走 `var(--*)`。照源系统的组件实现写，别自由发挥。
- **`preview/colors.html` `typography.html` `spacing.html`** —— 用
  `<link rel="stylesheet" href="../tokens.css">` 引 token。
  想让素材在界面里看得见，可以加一页 `brand.html` 把 logo 等**用 data URI 内嵌**
  （素材走不了 static 接口）；注意体积，二维码之类的大图别塞。
- **`assets/`** —— 从源包整个复制。
- **`source/evidence.md`** —— 记录每个值的来源、以及哪些是补的。
- **`metadata.json`** —— 必须有，`status` 要 `published`，别带 `workspaceId`。

## 技能那一份

基本是原样复制，只改 `SKILL.md` 的 frontmatter：

- 保留 `name`（它就是技能 id）和 `description`
- 加 `triggers`（中英文都放，品牌名、表面名都是好触发词）
- 加 `od: {mode: design-system, category: design-systems}`
- 正文补一个包内文件地图，并把最不能违反的规矩列出来

可以删掉 `uploads/`（原始上传件，通常几 MB 且是重复的），`research/` 建议保留。
