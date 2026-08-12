# 工作进度页

数据源是 OpenSpec 工作区（`openspec/changes/`）。收割用 `scripts/harvest_openspec.py`，
它不依赖 git（OpenSpec 工件常在版本控制之外），一切判断走目录结构 + 文件 mtime。

完整示例见 `assets/project.html` 的「在途工作 / 已归档 / 里程碑」三节。

## 目录

- [收割数据](#收割数据)
- [JSON 结构](#json-结构)
- [组件：change 条目](#组件change-条目)
- [组件：任务清单](#组件任务清单)
- [组件：进度条](#组件进度条)
- [组件：里程碑时间线](#组件里程碑时间线)
- [页面怎么组织](#页面怎么组织)
- [没有 OpenSpec 时](#没有-openspec-时)

---

## 收割数据

```bash
python scripts/harvest_openspec.py <项目根或 openspec 目录> --days 7 --out progress.json
```

- 第一个参数给项目根即可，脚本会自己找 `openspec/changes`（也会往上找两层）。
- `--days N` 只保留最近 N 天有文件改动的在途 change，和最近 N 天归档的 change；不给就是全部。
- `--out` 写 UTF-8 文件；不给则打到 stdout（已处理 Windows 控制台编码）。
- 项目在 WSL 里、Claude 跑在 Windows 侧时，用 `\\wsl.localhost\<发行版>\home\<用户>\<项目>` 这个路径；
  或者直接在 WSL 侧的 Claude Code 里跑。**路径不写死在任何文件里**，每次运行时给。

读到 JSON 后按下面的组件渲染，不要把 JSON 原样贴进页面。

## JSON 结构

```jsonc
{
  "root": "…/openspec",
  "generated_at": "2026-08-01 21:17",
  "window_days": 7,
  "totals": { "active": 1, "new": 1, "ready": 0, "archived": 1,
              "tasks_done": 3, "tasks_total": 7 },
  "active": [{
    "slug": "add-topo-memory",
    "title": "拓扑记忆模块",          // proposal.md 的一级标题，缺失时退回 slug
    "done": 3, "total": 5, "pct": 60,
    "status": "active",              // new(0 完成) / active(部分) / ready(全完成待归档)
    "last_modified": "2026-08-01",
    "why":  "…",                     // proposal.md 的 ## Why 段
    "what": "…",                     // proposal.md 的 ## What Changes 段
    "open_tasks": ["在 val-unseen 上跑完整评测", "…"],
    "has_evidence": true
  }],
  "archived": [{ "slug", "title", "date", "done", "total", "why" }],
  "specs": ["navigation", "perception"]
}
```

`status` 的三种值对应三种徽章：`new` → `<span class="badge">新立案</span>`，
`active` → `<span class="badge accent">在途</span>`，`ready` → `<span class="badge ok">待归档</span>`。

## 组件：change 条目

```html
<div class="changes">
  <div class="change">
    <div class="change-head">
      <span class="change-name">拓扑记忆模块</span>
      <span class="change-slug">add-topo-memory</span>
      <span class="badge accent">在途</span>
      <span class="change-date">最后改动 2026-08-01</span>
    </div>
    <div class="progress"><span style="width:60%"></span></div>
    <div class="progress-meta"><span>3 / 5 任务</span><span>60%</span></div>
    <div class="change-why">长程回环时反复重访同一区域，SR 卡在 41%。根因是没有跨 episode 的空间记忆。</div>
    <ul class="tasks">…</ul>
  </div>
</div>
```

已归档的加 `.is-archived`（灰底），且**不要放进度条**——它必然是 100%，画出来是噪音。

`change-why` 用 `why` 字段，压缩到 1–2 句。**不要照抄整段 proposal**，也不要把 `what` 和 `why` 都堆上去：
读者扫进度页时要的是「为什么做这件事」，具体改了什么在展开的任务清单里已经有了。

## 组件：任务清单

```html
<ul class="tasks">
  <li class="done">设计拓扑图数据结构</li>
  <li class="doing">在 val-unseen 上跑完整评测</li>
  <li>消融：去掉记忆 token</li>
</ul>
```

三态：`done`（绿底白勾）/ `doing`（橙框橙点）/ 无类（空框）。
`tasks.md` 里只有勾和没勾两态，**`doing` 要由你判断**——通常是 `open_tasks` 的第一条，或结合 `evidence/` 的最新文件推断。判断不出来就都留空框，不要瞎标。

任务超过 8 条时只列未完成的，已完成的用 `progress-meta` 的 `n/m` 概括。

## 组件：进度条

```html
<div class="progress"><span style="width:60%"></span></div>
<div class="progress-meta"><span>3 / 5 任务</span><span>60%</span></div>
```

`.progress.ok` 把填充色换成绿色，用于已达成目标的项。宽度直接用 `pct` 字段。
`total` 为 0（还没写 tasks.md）时**不要画 0% 的条**，改成一句 `<div class="bar-empty">任务尚未拆解</div>`。

## 组件：里程碑时间线

```html
<ul class="timeline">
  <li class="done">
    <div class="t-date">2026-07-28</div>
    <div class="t-title">baseline 复现完成</div>
    <div class="t-desc">CMA baseline 对齐官方评测协议，SR 41.0%。</div>
  </li>
  <li class="now">…</li>
  <li>…</li>
</ul>
```

`done` 绿点、`now` 橙点带光晕、无类是空心点。时间线是**人工维护的**——它表达的是项目节奏，不是 change 列表的另一种排版，别把每条 change 都塞进去。

## 页面怎么组织

进度页的推荐顺序：

1. **报头**：一句话说清当前状态（不是"本页展示进度"，而是"SR 从 41% 提到 46.2%，瓶颈转移到指代消解"）
2. **关键指标** `.stats`：领域指标（SR / SPL / NE / 延迟）优先于过程指标（完成了几个任务）
3. **架构图**：读者要先知道系统长什么样，才看得懂进度在说什么
4. **在途工作** `.changes`：按 `last_modified` 倒序
5. **已归档**：只列窗口期内的，一条一行
6. **里程碑** `.timeline`：往前看的部分
7. **说明** `.notes`：数据口径（单次运行还是多 seed？收割窗口多长？）

指标数字**必须标口径**——`SR 46.2%` 后面要能查到是哪个 split、单次还是平均。研究页面里没标口径的数字等于没有。

## 没有 OpenSpec 时

脚本找不到 `openspec/changes` 会退出并报错，这时直接手写 `.changes` / `.tasks` / `.timeline` 三个组件即可，结构完全一样。
也可以从别的来源填：GitHub issues、TODO 注释、实验日志目录——只要能给出「标题 + 完成度 + 为什么做」这三样。
