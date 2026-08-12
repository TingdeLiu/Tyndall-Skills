# 交付形态与实现模式

## 目录

- [两种交付形态](#两种交付形态)
- [字体策略](#字体策略)
- [纯 CSS 交互三件套](#纯-css-交互三件套)
- [内联 SVG 图表](#内联-svg-图表)
- [偏离条的宽度计算](#偏离条的宽度计算)
- [换强调色](#换强调色)
- [由程序生成 HTML 时](#由程序生成-html-时)

---

## 两种交付形态

先判断产物要去哪里，字体和外链策略不同。

### A. 整页文档（本地 HTML 文件、静态站点、要打印/分享的报告）

以 `assets/starter.html` 为骨架改内容。它包含整页模式的三处附加：

1. Google Fonts 链接（Hanken Grotesk / Newsreader / Fira Code / Noto Sans SC / Noto Serif SC）
2. `body` 的画布底色（含暗色与 `data-theme` 两条路径）
3. `.ch { background: transparent }` + 把中文字体补进 `--sans` / `--serif` 字体栈

交付单文件时，把 `claude.css` 全文粘进 `<style>`，删掉 `<link rel="stylesheet">`。

### B. 自包含片段（Artifact、聊天客户端内嵌、邮件正文）

严格 CSP 环境，**零外部资源**：

- 删掉 Google Fonts 链接。`claude.css` 的字体栈会自动退回系统字体（system-ui / PingFang SC / Georgia / ui-monospace），层级关系不变
- 不写 `<!doctype>` / `<html>` / `<head>` / `<body>`，只输出一个根 `<div class="ch">`
- 样式内联在根 div 里的 `<style>`，全部规则都在 `.ch` 下——绝不写裸 `body{}` 或 `:root{}` 规则，会污染宿主页面
- 不引入任何 JS，不用外链图片；图表一律内联 SVG

```html
<div class="ch" lang="zh-CN">
  <style>/* claude.css 全文 */</style>
  <header>…</header>
  <section>…</section>
  <footer>…</footer>
</div>
```

明暗主题已处理好：默认跟随 `prefers-color-scheme`，宿主在根元素设 `data-theme="dark"|"light"` 时以宿主为准。**两条路径都要留着**，别只写其中一条。

## 字体策略

三个角色的边界要守住，这是这套风格最容易做歪的地方：

| 变量 | 字体 | 只用于 |
|---|---|---|
| `--sans` | Hanken Grotesk | 所有 UI：标题 h2/h3、正文、标签、表格、**全部数值** |
| `--serif` | Newsreader | 页面主标题 `h1.title`、`.prose` / `blockquote.quote` 长文 |
| `--mono` | Fira Code | 代码 `<code>`、标识符列 `td.code`（代号 / 股票代码 / ID / 哈希） |

常见错误：拿 mono 排指标数值和小标签（那是杂志/终端风格，不是 Claude 风格）；拿 serif 排正文和表格（可读性差且过于文学化）。
数字对齐靠 `font-variant-numeric: tabular-nums`（`.ch` 已全局开启），不需要 mono。

中文字形：Hanken Grotesk 和 Newsreader 都不含中文，整页模式要把 Noto Sans SC / Noto Serif SC 补进字体栈（见 `starter.html`）；片段模式退回 PingFang SC / Songti SC 即可。

## 纯 CSS 交互三件套

**这套风格不用 JS。** artifact 和邮件环境都能跑。

### 1. 表格行展开

`<label>` 包一个视觉隐藏的 checkbox，`:has()` 选中时显示下一行。

```html
<tr>
  <td class="code"><label class="sym-toggle"><input type="checkbox" class="row-toggle">SEARCH</label></td>
  <td class="num">41,208</td>
</tr>
<tr class="detail-row"><td colspan="2"><!-- 明细：图表、长文、次级表格 --></td></tr>
```

`colspan` 必须等于表格实际列数。展开箭头是 CSS 三角（`border` 画的），不依赖任何字形。

### 2. radio 标签页

`.tabbed` 内先放 N 个 radio，再放 `.tabs`（label）和 `.panes`（pane），**三者顺序不能变**（CSS 靠 `~` 兄弟选择器匹配）。radio 的 `name` 在整个文档内唯一——同一实体出现在多个章节时最容易撞名。

```html
<div class="tabbed">
  <input class="tab-radio" type="radio" name="tf-perf" id="tf-perf-1" checked>
  <input class="tab-radio" type="radio" name="tf-perf" id="tf-perf-2">
  <div class="tabs">
    <label class="tab" for="tf-perf-1">4 周</label>
    <label class="tab" for="tf-perf-2">季度</label>
  </div>
  <div class="panes">
    <div class="pane">…</div>
    <div class="pane">…</div>
  </div>
</div>
```

最多 6 个标签页（CSS 只写到 `nth-of-type(6)`）；要更多就扩展那两组选择器。

### 3. 折叠块

```html
<details class="fold">
  <summary>趋势</summary>
  <div class="tabbed">…</div>
</details>
```

卡片和指标卡里用 `details`，表格行里用上面的 checkbox 方案（`details` 无法跨 `<tr>` 工作）。

## 内联 SVG 图表

不引图表库。颜色一律用 `var(--success)` / `var(--danger)` —— 跟着主题自动变。线宽用 1.5–1.6px（细一点更符合这套风格），面积填充 `opacity: .1`。

### Sparkline（表格行内，72×22）

```html
<svg class="spark" viewBox="0 0 72 22" width="72" height="22" preserveAspectRatio="none" aria-hidden="true">
  <polyline points="0,18 14,15 29,11 43,12 58,5 72,2" fill="none"
    stroke="var(--success)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

坐标：`x = i * W/(n-1)`，`y = H - (v-lo)/(hi-lo) * H`（`hi==lo` 时分母取 1）。
描边色按 `末值 >= 首值 ? --success : --danger`。

### 面积曲线（展开面板内，640×148）

```html
<svg class="chart-svg" viewBox="0 0 640 148" preserveAspectRatio="none" aria-hidden="true">
  <polygon points="0,148 0,40 128,62 256,48 384,88 512,96 640,120 640,148" fill="var(--success)" opacity=".1"/>
  <polyline points="0,40 128,62 256,48 384,88 512,96 640,120" fill="none"
    stroke="var(--success)" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
<div class="chart-caption"><span>06-01 → 06-28</span><span class="pos">−31.2%</span><span>区间 1.8s–2.9s</span></div>
```

上下留 6px 白边：`y = H - pad - (v-lo)/(hi-lo) * (H-2*pad)`；面积多边形 = `0,H` + 折线点 + `W,H`。
图表下方必须配 `chart-caption` 三段（区间、变化、极值）——**纯曲线没有刻度，不给数字读者读不出量级**。

## 偏离条的宽度计算

```
基准 = target，两端 = low / high，当前值 = value

value <= target:
    p = clamp((target - value) / (target - low), 0, 1)
    left = 50 - p*50 (%)   width = p*50 (%)   background: var(--success)
value > target:
    p = clamp((value - target) / (high - target), 0, 1)
    left = 50 (%)          width = p*50 (%)   background: var(--danger)
```

分母为 0 时取一个极小值兜底。

**铁律：条形长度只能由这个条目自身的数据决定，不能受同一列表里其他条目影响。**
同一个实体经常出现在多个榜单里，如果宽度是"相对本列表最强项的排名分"，它在不同章节就会显示成不同长度，读者一眼就认定是 bug。缺基准数据时用 `bar-empty` 占位，**绝不退化成"相对排名条"**。

## 换强调色

强调色只做点缀。要换品牌色时改这四个变量（亮暗各一组），其余不动：

```
--accent          主强调（主按钮底、bar 高亮、focus ring）
--accent-hover    悬停态
--accent-deep     强调文字（eyebrow、链接、展开态）——亮色下要比 --accent 更深才够对比度
--accent-subtle   强调底色（badge.accent、callout、row.is-marked）
```

暗色下 `--accent-deep` 要反过来取**更浅**的色阶（默认是 `#EBBBA5`），`--accent-subtle` 用半透明橙（`rgba(217,119,87,.16)`）而不是把亮色调暗。
`--success` / `--danger` / `--warning` / `--info` 是语义色，不要跟着品牌改。

## 由程序生成 HTML 时

- 所有插入值都要 HTML 转义
- 把 section 构建器拆成独立函数；如果用了 `.sec-num`，让它们共享同一个计数器，章节增删时编号自动连续
- 缺数据的章节返回空串跳过，或返回 `.empty` 占位——由「这一节读者是否会期待它存在」决定用哪种
- radio / label 的 id 用全局自增计数器生成，避免同一实体在多章节出现时撞名
