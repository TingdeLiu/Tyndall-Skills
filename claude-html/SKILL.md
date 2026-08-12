---
name: claude-html
description: 用 Anthropic / Claude 的简约视觉风格制作 HTML —— 象牙暖底 + 陶土橙（clay #D97757）克制点缀、无衬线主导 UI、衬线只用于大标题与长文、克制土色状态色、细边框低阴影、大量留白、零 JS 纯 CSS 交互、内联 SVG、明暗双主题。内置四类架构图（系统管线 / 模型分层 / 模块依赖 / 训练闭环）和工作进度看板（可从 OpenSpec 自动收割）。在这些情况下使用：(1) 要把项目架构或模型结构画成 HTML —— VLA、Transformer、Diffusion Policy、感知-规划-控制管线、ROS 2 节点图、训练与评测闭环；(2) 要展示工作进度、已完成与待办、里程碑，尤其项目用 OpenSpec（openspec/changes）管理时；(3) 用户要求做 HTML 报告/复盘/总结/仪表盘/落地页/文档页且未指定其他风格；(4) 用户提到「Claude 风格」「Anthropic 风格」「Tyndall Labs 风格」「陶土橙」「简约风格」「暖纸/象牙底」；(5) 要产出严格 CSP 下可渲染的自包含 HTML artifact 片段；(6) 已有页面要改造成这套风格。
---

# Claude 简约风格 HTML

设计 token 取自 Anthropic 设计系统：clay 陶土橙 + kraft 暖中性 + ivory 象牙底。
风格气质是**产品界面**，不是杂志排版——靠层级、留白和克制的用色成立，不靠装饰。

## 快速开始

1. **挑模板**（都能直接在浏览器打开，改内容比从零写快得多）：
   - `assets/project.html` —— **项目架构 + 工作进度**。四类架构图、指标卡、change 看板、任务清单、里程碑时间线。
   - `assets/starter.html` —— **数据报告 / 复盘**。指标卡、长文结论、数据表、条目流、分组小卡。
2. **确定交付形态**：整页 HTML 文件 → 直接用模板；Artifact / 内嵌片段 → 只输出一个 `<div class="ch">` 根节点，样式内联，删掉 Web 字体外链（字体栈会自动退回系统字体）。详见 `references/patterns.md`。
3. **内联样式**：把 `assets/claude.css` 全文粘进 `<style>`。不要改 token 值，也不要引入 Tailwind/Bootstrap——这套系统是自洽的。
4. **查组件**：通用组件看 `references/components.md`；架构图看 `references/architecture.md`；进度看板看 `references/progress.md`；交互与内联 SVG 看 `references/patterns.md`。

## 三类典型任务

**画项目 / 模型架构** → 读 `references/architecture.md`，从四类里挑 2–3 类（管线 / 分层 / 模块 / 闭环），一个页面别四类全上。
关键在标注：频率、延迟、参数量、张量维度、`frozen`/`新增` 状态、真实 topic 与模块名。方框本身不传递信息。

**做工作进度页** → 项目用 OpenSpec 时先收割：

```bash
python scripts/harvest_openspec.py <项目根或 openspec 目录> --days 7 --out progress.json
```

再按 `references/progress.md` 把 JSON 渲染成 change 看板 + 任务清单 + 里程碑。路径运行时给，不写死。没有 OpenSpec 就手写同样的组件。

**做数据报告 / 复盘** → 用 `assets/starter.html`，组件查 `references/components.md`。

## 风格铁律

1. **无衬线主导**。UI、标签、表格、数字全部用 `--sans`（Hanken Grotesk）。
   `--serif`（Newsreader）**只用于两处**：页面主标题 `h1.title`，和 `.prose` / `blockquote` 长文段落。
   `--mono`（Fira Code）**只用于代码和标识符**（渠道代号、股票代码、ID、哈希）——不要拿它排普通标签或指标数值。
2. **陶土橙是点缀，不是主色**。它只出现在：eyebrow 小标题、链接、主按钮、`badge.accent`、少量高亮底（`--accent-subtle`）。**标题、正文、表头一律用中性墨色**，不要为了"有设计感"把标题染成橙色。
3. **状态色用土色**：`--success #5A7052` / `--danger #BF4D43` / `--warning #B07B3C` / `--info #4F6B8F`。不要换成鲜艳的 #22c55e / #ef4444，那一眼就不是这套系统。
4. **不用装饰**。没有 ✦ 之类的符号前缀、没有渐变填充、没有大写字母加宽间距的 eyebrow、没有卡片顶部的彩色条。**要视觉分隔就用留白和 1px 细线**。
5. **边框细而淡，阴影几乎不用**。卡片默认 `1px solid var(--line)` + 圆角 10–14px，不加阴影；只有浮层才用 `--shadow-md`。
6. **圆角克制**：控件/卡片 10px，大容器 14px。**不要到处 999px 胶囊**——只有真正的标记性小标签才用圆角 6px。
7. **留白是内容的一部分**：章节间距 56px、报头上方 64px、页脚上方 72px。不要为了塞进一屏而压缩。
8. **数字右对齐 + tabular-nums**（`.ch` 已全局开启）。表格数字列加 `class="num"`，表头同样加 `th class="num"`。
9. **正负色由数值符号决定，不由好坏决定**：`−12%` 就是红色，哪怕它是成本下降这种好事。好坏用文案或徽章说明。
10. **零 JavaScript**。交互一律用 radio / checkbox / details 的纯 CSS 方案，图表一律内联 SVG。artifact、邮件、离线存档环境里 JS 经常被禁。
11. **明暗双主题都要成立**：跟随 `prefers-color-scheme`，同时支持宿主的 `:root[data-theme]` 覆盖。两条路径都留着。
12. **缺数据显式降级**：填 `<span class="muted">—</span>`、`.bar-empty` 占位或 `.empty` 空态说明原因。**不要留空白，也不要整节删掉**——读者要能分清「没有」和「忘了做」。

## 内容组织

- **读者最关心的排第一**，不是按数据来源或生成顺序排。如果页面里有「与读者直接相关」的部分（他的持仓、他负责的模块、他提的问题），它就是第一节。
- **榜单里命中读者自身的条目排到榜首**并加 `row.is-marked`，而不是让它按分数埋在中间。
- **每个章节只用一种主组件**。同一节里既堆指标卡又堆表格又堆卡片，节奏就散了。
- **先结论后明细**：指标卡 → 结论长文 → 分类卡片 → 明细表格 → 条目流 → 说明。明细用折叠/展开藏起来，默认视图保持干净。
- **标题只写标题**，口径、来源、条目数放 `sec-head` 右侧的 `.hint`。
- **章节默认不编号**。只有确实需要「按顺序读」的长报告才用 `.sec-num`，且要从头到尾连续。
- 免责声明和口径差异统一收进最后的说明章节，只有最关键的一条放报头下的 `.callout`。

## 定制

换品牌色时只改 `--accent` / `--accent-hover` / `--accent-deep` / `--accent-subtle`（亮暗各一组），保持「强调色只做点缀」的结构不变。`--success` / `--danger` 是语义色，不要跟着品牌改。详见 `references/patterns.md`。

## 资源

- `assets/claude.css` —— 完整设计系统，作用域全在 `.ch` 下，可安全内嵌任意宿主页面
- `assets/project.html` —— 架构 + 进度模板（四类架构图、change 看板、里程碑）
- `assets/starter.html` —— 数据报告模板（指标卡、长文、数据表、条目流）
- `scripts/harvest_openspec.py` —— 从 `openspec/changes` 收割进度为 JSON，不依赖 git
- `references/components.md` —— 通用组件：报头、指标卡、卡片、数据表、长文、条目流
- `references/architecture.md` —— 四类架构图的结构与标注原则
- `references/progress.md` —— 进度看板组件、收割脚本用法、JSON 字段含义
- `references/patterns.md` —— 交付形态、字体策略、纯 CSS 交互、内联 SVG、换色、程序化生成
