# 组件速查

`assets/claude.css` 提供的全部组件，类名都在 `.ch` 作用域下。
组合原则：**一个章节只用一种主组件**。

## 目录

- [报头 header](#报头-header)
- [提示块 callout](#提示块-callout)
- [章节 section](#章节-section)
- [指标卡 stats](#指标卡-stats)
- [长文 prose / 引述 quote](#长文-prose--引述-quote)
- [卡片 cards](#卡片-cards)
- [徽章与标签](#徽章与标签)
- [按钮 btn](#按钮-btn)
- [偏离条 bar](#偏离条-bar)
- [数据表 panel](#数据表-panel)
- [条目流 feed](#条目流-feed)
- [分组小卡 grid](#分组小卡-grid)
- [收尾组件](#收尾组件)
- [语义文本色](#语义文本色)

---

## 报头 header

整篇只有一个。`eyebrow` 是橙色小标题（**不要大写、不要加宽字距**），`h1.title` 是唯一用衬线的标题，`sub` 用无衬线常规体承接一句话概述。

```html
<header>
  <div class="eyebrow">产品季度复盘</div>
  <h1 class="title">2026 Q2 产品复盘<span class="sub">增长来自渠道而非产品，留存下滑与 5 月改版同期。</span></h1>
  <div class="meta">
    <span><span class="dot ok"></span>数据完整</span>
    <span>数据截止 <b>2026-06-30</b></span>
    <span>覆盖 <b>18</b> 个指标</span>
  </div>
</header>
```

`sub` 写一句真正有信息量的概述（页面结论是什么），不要写"本报告分析了……"这类空话。
`meta` 是一行弱化文字，`<b>` 标出值；状态用 `.dot`（`.ok` 绿 / `.bad` 红 / 无修饰灰），**不要用一排彩色胶囊**。

## 提示块 callout

放免责声明、口径说明、关键前提。淡底圆角，无边框无图标。整篇最多 1–2 条。

```html
<div class="callout">口径说明：本文所有指标基于内部埋点，与财务口径存在 1–3% 的差异。</div>
<div class="callout info">…</div>   <!-- 中性信息：蓝底 -->
<div class="callout warn">…</div>   <!-- 需要注意：琥珀底 -->
```

## 章节 section

```html
<section>
  <div class="sec-head"><h2>核心指标</h2><span class="hint">对比 2026 Q1</span></div>
  <!-- 主组件 -->
</section>
```

需要连续编号的长报告才加序号，且必须从头到尾都加：

```html
<div class="sec-head"><span class="sec-num">03</span><h2>行动项</h2></div>
```

## 指标卡 stats

首屏概览，给 3–6 个。**独立卡片 + 12px 间距**，不要用发丝线网格挤在一起。

```html
<div class="stats">
  <div class="stat">
    <div class="s-label">月活用户</div>
    <div class="s-value">128.4k</div>
    <div class="s-sub"><span class="pos">+12.3%</span> 环比</div>
  </div>
</div>
```

数值单位用小一号的弱化文字缀在后面，别和数字同样大：

```html
<div class="s-value">412<span style="font-size:18px;color:var(--text-3)">ms</span></div>
```

## 长文 prose / 引述 quote

**这是全页第二处（也是最后一处）用衬线的地方。** 结论、综述、模型输出用 `.prose`，多段落直接写 `<p>`。

```html
<div class="prose">
  <p>本季度的增长几乎全部来自投放：新增 MAU 中 68% 由三个付费渠道贡献。</p>
  <p>付费转化的改善集中在新用户首周，老用户转化率反而下滑 0.3pt。</p>
</div>
```

需要一个带底色的块（例如原样引用模型回复）时用：

```html
<blockquote class="quote">连续 6 周低于基线。
换行会被保留（white-space: pre-wrap）。</blockquote>
```

`.prose` 限宽 680px（阅读行宽），不要撑满整行。

## 卡片 cards

并列的几组榜单/分类。**卡顶没有彩色装饰条**，靠标题和分隔线区分层级。

```html
<div class="cards">
  <div class="card">
    <div class="card-top">
      <div class="card-title">高优先级</div>
      <div class="card-meta"><span class="badge accent">本季度内</span><span>阻塞其他工作</span></div>
    </div>
    <div class="row is-marked">
      <div class="row-head">
        <span class="rank">1</span>
        <span class="key">留存归因<span class="key-sub">改版影响</span></span>
        <span class="val">−2.1pt</span>
      </div>
      <div class="badges">…</div>
      <div class="row-note">连续 6 周低于基线，改版是首要嫌疑</div>
    </div>
  </div>
</div>
```

- `rank` 用普通数字 `1`/`2`，不用 `01` 这种排版化写法。
- `row.is-marked` 给行加淡橙底，用于「与读者直接相关」的条目——**这类条目应该排到榜首**，而不是靠高亮埋在中间。

## 徽章与标签

```html
<span class="badge">中性</span>
<span class="badge accent">橙色强调</span>
<span class="badge ok">风险 低</span>
<span class="badge bad">风险 高</span>
<span class="badge warn">需要注意</span>
<span class="tag">描边标签</span>
```

`badge` 是淡底无边框，`tag` 是描边无底。同一处只用一种。

## 按钮 btn

```html
<a class="btn primary" href="#">主操作</a>
<a class="btn" href="#">次操作</a>
```

一屏里**只有一个 primary**。报告类页面通常一个按钮都不需要。

## 偏离条 bar

表达「当前值相对某个基准的偏离」。轨道中心固定是基准（0 偏离），低于基准向左走绿色，高于基准向右走红色。用**纯色**填充，不要渐变。

```html
<div class="bar">
  <div class="bar-track">
    <span class="bar-zero"></span>
    <span class="bar-fill" style="left:24%;width:26%;background:var(--success)"></span>
  </div>
  <div class="bar-caption"><span>悲观 −4.0pt</span><span class="mid">目标 0.0pt（当前 −2.1pt）</span><span>乐观 +1.0pt</span></div>
</div>
```

宽度计算见 `patterns.md`。**没有基准数据时不要画条**：

```html
<div class="bar-empty">暂无基线数据</div>
```

## 数据表 panel

必须用 `.panel` 包一层——它负责圆角、裁切和窄屏横向滚动。

```html
<div class="panel">
  <table>
    <thead><tr><th>渠道</th><th class="num">新增</th><th class="num">CAC</th><th>说明</th></tr></thead>
    <tbody>
      <tr>
        <td class="code">SEARCH</td>
        <td class="num">41,208</td>
        <td class="num">$4.52</td>
        <td class="why-cell">品牌词占比上升，边际成本仍可控</td>
      </tr>
    </tbody>
  </table>
</div>
```

- `td.code`：标识符列（代号、股票代码、ID），**这是 mono 字体唯一该出现的地方**。普通名称列用 `td.sym`（无衬线加粗）。
- `td.num` + `th.num`：数字列，右对齐 + tabular-nums。**表头也要加**，否则表头和数字不对齐。
- `td.why-cell`：说明列，限宽 340px 的弱化文字。
- 缺数据填 `<span class="muted">—</span>`，不要留空单元格。
- 行内展开明细见 `patterns.md`。

## 条目流 feed

时间线式的事件/新闻/变更列表。

```html
<div class="feed">
  <div class="feed-item"><span class="src">发布</span><a href="#">v4.2 导航改版全量</a><time>05-14</time></div>
  <div class="feed-item"><span class="src">组织</span><span class="h">增长组并入产品线</span><time>06-21</time></div>
</div>
```

没有链接时用 `<span class="h">` 代替 `<a>`，保持字号一致。

## 分组小卡 grid

按实体分组的短清单（每组 2–5 条）。

```html
<div class="grid">
  <div class="mini">
    <h3>新手引导</h3>
    <ul>
      <li><a href="#">首屏步骤过多</a> <span class="pub">用研 · 12 例</span></li>
    </ul>
  </div>
</div>
```

`mini h3` 是普通无衬线小标题，**不要染成橙色、不要用全大写代号**。

## 收尾组件

```html
<ul class="notes"><li>SOCIAL 渠道 6 月 12–14 日埋点缺失，已用前后均值补齐。</li></ul>

<div class="empty">本次未抓取到数据（可能为网络问题，详见说明）。</div>

<footer>
  <span>仅供内部复盘使用</span>
  <span>生成于 2026-07-02 09:14</span>
</footer>
```

`empty` 用于章节有位置但无数据——**保留章节 + 说明原因**，别整节删掉。

## 语义文本色

```html
<span class="pos">+12.3%</span>   <!-- 正向：土绿 -->
<span class="neg">−2.1pt</span>   <!-- 负向：土红 -->
<span class="flat">持平</span>     <!-- 无变化 -->
<span class="muted">—</span>      <!-- 缺失 -->
```

负号建议用 U+2212（−）而不是连字符（-），和数字等宽对齐更好看。
