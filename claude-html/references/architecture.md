# 架构图

四类图，全部用 CSS 盒子 + border 三角箭头实现——**零 JS、零字体依赖、可选中文字、窄屏自动重排**。
不要为了画架构图引入 Mermaid 或 D3：Mermaid 需要 JS 运行时，artifact 之外的场景都跑不了；
而这四类图的信息量靠盒子和标注就够，连线的精确走向对读者没有价值。

完整示例见 `assets/project.html`。

## 目录

- [选哪一种](#选哪一种)
- [1. 系统管线 pipeline](#1-系统管线-pipeline)
- [2. 模型分层 layers](#2-模型分层-layers)
- [3. 模块依赖 modules](#3-模块依赖-modules)
- [4. 训练闭环 cycle](#4-训练闭环-cycle)
- [标注什么才有用](#标注什么才有用)
- [需要真正的连线图时](#需要真正的连线图时)

---

## 选哪一种

| 要表达 | 用 | 典型内容 |
|---|---|---|
| 数据从哪来、经过谁、到哪去 | `pipeline` | 传感器 → 感知 → 策略 → 规划 → 控制 |
| 一个网络内部怎么堆的 | `layers` | vision/language encoder → cross-attn → action head |
| 有哪些独立进程/包、谁依赖谁 | `modules` | ROS 2 节点 + topic、Python 包结构 |
| 数据和模型怎么循环迭代 | `cycle` | 数据集 → 训练 → 评测 → 难例回流 |

一个页面里放 2–3 种就够。四种全上会让读者失焦。

## 1. 系统管线 pipeline

横向流程，每一级是一个 `.stage`（可含多个并列 `.node`），级间插 `.arrow`。

```html
<div class="pipeline">
  <div class="stage">
    <div class="stage-label">感知输入</div>
    <div class="node">RGB-D<span class="node-meta">30 Hz · 640×480</span></div>
    <div class="node">Odometry<span class="node-meta">100 Hz</span></div>
  </div>
  <div class="arrow"></div>
  <div class="stage">
    <div class="stage-label">决策</div>
    <div class="node accent">VLN 策略<span class="node-meta">10 Hz · 86ms</span></div>
  </div>
</div>
```

- `.node.accent` 标本次改动/新增的环节，`.node.dim` 标未实现或已废弃的环节。
- `.arrow` 必须是 `.stage` 的兄弟节点，不要塞进 stage 里。
- 窄屏（≤640px）自动转纵向，箭头变成向下三角，不需要额外处理。
- 超过 6 级就该拆成两张图，或者把细节收进 `details.fold`。

## 2. 模型分层 layers

纵向堆叠，层间插 `.flow`（向下箭头）。**张量维度用 `.layer-dim`**，它会自动推到右端并用等宽字体——这是 mono 的正当用法（维度字符串本质是代码）。

```html
<div class="layers">
  <div class="layer frozen">
    <div class="layer-name">Vision Encoder<span class="layer-sub">ViT-B/16 · frozen · 86M</span></div>
    <div class="layer-dim">B×T×196×768</div>
  </div>
  <div class="flow"></div>
  <div class="layer accent">
    <div class="layer-name">Memory Token 注入<span class="layer-sub">新增</span></div>
    <div class="layer-dim">B×K×768 (K≤32)</div>
  </div>
</div>
```

- `.layer.frozen`：虚线框 + 灰底，表示冻结/不训练的部分。
- `.layer.accent`：橙框，表示本次新增或正在改的层。
- `.layer-sub` 放结构参数（层数、head 数、参数量、是否冻结）。
- 维度写清 batch 和序列维的含义（`B×T×196×768` 比 `[4,8,196,768]` 好读），可变维度直接写字母并在旁注上界。

## 3. 模块依赖 modules

网格卡片，每个模块列出输入/输出端口。**不画连线**——端口名本身就表达了连接关系，而且改动时不用重排线。

```html
<div class="modules">
  <div class="module">
    <div><span class="module-name">topo_memory</span><span class="module-kind">node · 新增</span></div>
    <div class="module-desc">维护稀疏拓扑图，跨 episode 保留空间记忆</div>
    <div class="ports">
      <div class="port"><span class="port-dir">in</span><span class="port-name">/odom</span></div>
      <div class="port"><span class="port-dir out">out</span><span class="port-name">/memory/topo_graph</span></div>
    </div>
  </div>
</div>
```

`port-dir` 只有 `in` / `out` 两种，`out` 加 `.out` 类显示为橙色。端口名用真实的 topic / 函数 / 文件路径，不要写"输出结果"这种空话——读者要能拿它去 grep。

## 4. 训练闭环 cycle

横排节点 + 底部一条回流线。

```html
<div class="cycle">
  <div class="cycle-track">
    <div class="node">R2R-CE<span class="node-meta">61 scenes</span></div>
    <div class="arrow"></div>
    <div class="node accent">策略训练<span class="node-meta">8×A100 · 18h</span></div>
    <div class="arrow"></div>
    <div class="node">val-unseen 评测<span class="node-meta">SR / SPL / NE</span></div>
  </div>
  <div class="cycle-back"><span class="label">难例回流至采样池</span></div>
</div>
```

`.cycle-back` 是绝对定位的 U 形线，箭头指回第一个节点；`.label` 上的底色取自 `--canvas`，所以**如果你把 cycle 放进了卡片（`--raised` 白底）里，要覆盖 label 的 background**，否则线会从文字后面穿过去。

## 标注什么才有用

架构图的价值在标注，不在方框。每个节点尽量给出：

- **频率 / 延迟**（`30 Hz`、`86ms`）——一眼看出瓶颈在哪
- **规模**（`86M`、`61 scenes`、`8×A100 · 18h`）——一眼看出成本
- **状态**（`frozen`、`新增`、`未实现`）——一眼看出这次改了什么
- **真实标识符**（topic 名、模块名）——能直接拿去搜代码

不要标"重要"、"核心"这类形容词，也不要给每个框都配一句解释——图旁边配一条 `.callout` 说清楚瓶颈或风险，比给十个框各写一句有用。

## 需要真正的连线图时

节点关系确实是网状、必须画线时，用内联 SVG 手绘（`<line>` / `<path>` + `marker` 箭头），颜色用 `var(--line-3)` / `var(--accent)`，文字用 `<text fill="var(--text-2)">`。
但先问一句：**读者真的需要看到线，还是只需要知道谁连谁**？后者用 `modules` 的端口列表表达更清楚，也不会在窄屏上糊成一团。
