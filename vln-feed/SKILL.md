---
name: vln-feed
description: 抓取并分析具身导航（VLN / VLA / VN / Embodied Navigation）领域的最新资料，生成增量 Markdown 资料库和结构清晰的中文研究周报。通过 RSS 拉取微信公众号与 arXiv，执行关键词过滤、去重和跨源合并；周报以结论、优先阅读清单、重点工作分析、主题速览和研究建议组织，全篇用列表不用表格，禁止嵌入图片。用于“抓取具身导航最新资料”“更新 VLN 选题库”“分析最近 VLN/VLA 论文”“生成 VLN 周报”或“vln-feed”等请求。
---

# vln-feed — 具身导航资料抓取

把 VLN / VLA / VN / 具身导航 的最新资讯收成一个本地选题库：
**RSS 源 → 关键词过滤 → 去重 → 每条一份 md + 总索引**。增量运行，
重复跑只补新条目。抓到的内容用作做视频 / 博客的素材与选题。

## 环境与路径

- Python: 系统 `python`（3.11），依赖见 `requirements.txt`
  （`feedparser` / `requests` / `beautifulsoup4` / `lxml` / `PyYAML`）
- 首次安装依赖：`python -m pip install -r requirements.txt`
- 脚本：`scripts/fetch_vln.py`
- 配置：`feeds.yaml`（资料源 + 关键词 + `output_dir` 输出目录）
- 输出：默认技能内 `./output`，可在 feeds.yaml 的 `output_dir` 改到别处
  （优先级 `--out` > `output_dir` > 技能内 `./output`）。下文 `<资料库目录>`
  都指这个目录
  - `index.md` — 总索引表（日期 / 标题 / 来源 / **领域** / **基准** / 原文 / 本地）
  - `items/*.md` — 每条一份（保持原文语言，不做中文化，见下）
  - `seen.json` — 去重状态（勿手动删，删了会重复抓）
  - `reports/*.md` — 每次抓取后由 Codex/Claude 撰写的结构化中文研究周报（见下）

## 「领域」分池：周报只深读主池（2026-09-19 加）

**起因**：用户指出资料库里全是 VLA 论文，却抓不到具身 Agent / AgentOS 方向。
核查属实且比预想严重——某期 70 条里 52 条（74%）通篇不提导航，全从 query 里
那个无约束的 `vision-language-action` 分支涌进来；全库 887 条中 515 条
（58%）是纯操作论文。同期还漏掉了约 25 条真正相关的工作。

用户选择**分池而非砍掉**：VLA 动态仍要跟，但不能与导航论文等权重混在一起。
故每条自动打一个 `- 领域:` 字段，取值与优先级为：

| 领域 | 含义 | 是否主池 |
|---|---|---|
| `导航` | VLN / ObjectNav / 语义/社会/地形导航、航点、R2R 等 | ✅ |
| `具身Agent` | agent harness / runtime / AgentOS、具身记忆、长程规划 | ✅ |
| `自动驾驶` | 驾驶策略 | ❌ |
| `VLA·操作` | 机械臂 / 力控 / 灵巧手 / 遥操作 | ❌ |
| `其他` | 以上都不是 | ❌ |

**写周报时只对主池（导航 + 具身Agent）做深度分析**，次池按主题压成速览列表。
筛选直接查字段：

```bash
grep -l "^- 领域: 导航" items/*.md
grep -l "^- 领域: 具身Agent" items/*.md
```

分池规则调完必须重算存量，否则 index.md 的主池计数与周报筛选依据会和规则脱节：

```bash
python scripts/backfill_domain.py --out <资料库目录> --dry-run
python scripts/backfill_domain.py --out <资料库目录>
```

### 调分池规则时别踩回去的四个坑

实测踩过一遍，主池一度被灌到 61 条、一半是噪声：

- **`navigation` 在非具身语境里同样高频**。实测混进来的有知识图谱的
  「Multi-Hop Graph Navigation」、软件工程的「Navigating architecture」、
  GUI 的「GUI Navigation」、RAG 的「Navigating Sparse Evidence」。
  `NON_EMBODIED_NAV` 负责挖掉这些，改规则时只能往里加词，不能删。
- **不要加「弱导航信号」**。曾试过「标题判不出时，摘要里出现光秃秃的
  navigation 就归导航」，初测影响面只有 1 条看着很划算，加入 Agent 源后
  ClinAgent、Theseus、SWE-Agent、EconSkills 等十几条全靠摘要里随口一句
  navigation 挤进主池。已删除，注释留在 `fetch_vln.py` 里。
- **agent 类词必须过具身语境闸门**（`EMBODIED_CTX`）。没有它，MUSE 故事
  引擎（"Theory-Harnessed"）、NetOps 运维 agent、Self-Evolving Search Index、
  Wiki Foundation Model 只要提一句 agent harness / agent memory 就进主池。
- **标题优先于摘要**。摘要常顺带列举多个应用领域——World-Action Models 综述
  只因摘要里一句「manipulation, navigation, and autonomous driving」就被归进
  自动驾驶。现在标题判不出才退到摘要。
- **`waypoint` 不能单列**，否则会拉进纯航路点跟踪的控制论文；要求它与
  robot / embodied / navigat / mobile 在 300 字符内同现。

## 摘要长度与「基准」字段（2026-08-22 修）

**摘要不再硬截断在 1200 字符。** 旧版对所有源统一截断，而 arXiv 摘要通常
1000~2500 字符，实验结果（R2R-CE / SR / SPL 等数字）恰好落在摘要末尾被切掉
——某次抓取的 46 条里 40 条正好卡在 1200，导致按指标 grep 出现**假阴性**。
现按源类型区分：`arxiv` 不截断 / `wechat` 1200（另有 `## 正文` 存全文）/
`generic` 4000，可用 `--summary-maxlen N` 覆盖（`0` = 不限）。

**每条条目自动标注 `- 基准:` 字段**，识别 R2R-CE / RxR-CE / VLN-CE / R2R /
RxR / REVERIE / ObjectNav / HM3D / MP3D / LIBERO 等，并同步到 `index.md` 的
基准列。于是筛选可以直接查字段，不必再对全文写正则：

```bash
grep -l "^- 基准: .*R2R-CE" items/*.md
```

两个已踩过的坑，改规则时别踩回去：

- **不能用 `\b` 做词边界**。Python 正则的 `\w` 把中文也算单词字符，公众号里
  「零样本R2R-CE导航基准」两侧都不构成 `\b`，整条会漏。已改用
  `(?<![A-Za-z0-9])` / `(?![A-Za-z0-9])`，容纳中文紧邻又不误命中 `XR2R`。
- **CE 变体与离散版本分开识别**。R2R-CE（连续环境）与离散 R2R 不可直接比较，
  混在一起会误导横向对比。`BENCHMARK_SUBSUMES` 保证命中 R2R-CE 时不再重复标 R2R。
- `SOON` 必须大小写敏感，否则命中普通英文词 soon。

## 常用命令

```bash
# 增量抓取（默认最近 30 天，抓公众号全文）
python scripts/fetch_vln.py

# 只看有哪些新条目，不写文件、不抓正文
python scripts/fetch_vln.py --list-only

# 只要最近 14 天、每源最多 10 条
python scripts/fetch_vln.py --days 14 --max 10

# 不抓微信全文（更快，只存标题+摘要+链接）
python scripts/fetch_vln.py --no-full

# 探测微信频控/授权状态（周流程第 1 步，5 秒出结果）
python scripts/probe_wechat.py

# 手动喂公众号文章链接（免 RSS，见下「微信公众号·方式A」）
python scripts/fetch_vln.py --urls wechat_urls.txt --no-feeds
python scripts/fetch_vln.py --no-feeds --url "https://mp.weixin.qq.com/s/xxxx"

# 覆盖摘要保留长度（0 = 完全不截断）
python scripts/fetch_vln.py --summary-maxlen 0

# 回填历史条目的完整摘要 + 重算「基准」字段（先 --dry-run 看影响面）
python scripts/backfill_abstracts.py --out <资料库目录> --dry-run
python scripts/backfill_abstracts.py --out <资料库目录>

# 重算全部条目的「领域」分池字段（改过分池规则后必跑）
python scripts/backfill_domain.py --out <资料库目录> --dry-run
python scripts/backfill_domain.py --out <资料库目录>
```

> Windows 上若中文乱码，脚本已强制 UTF-8 输出；如仍异常可加 `PYTHONUTF8=1`。

## 配置资料源（feeds.yaml）

每个源字段：`name` / `url` / `type`(wechat|arxiv|generic) / `keep_all` / `enabled`。

- **arXiv·具身导航最新**：开箱即用，无需任何外部服务，覆盖 VLN/VLA/VN/具身导航，
  以及 PointNav、3D 视觉语言模型、导航 agent、导航数据集/benchmark（2026-07-05
  按用户要求扩充，query 构造与噪声取舍见 feeds.yaml 里该源上方的注释）。
  `max_results=120`（原 40 / 100 都实测过会在 10 天窗口内截断）。
  2026-09-19 补漏：原 query 只认 `visual/embodied/object navigation` 这几种
  固定搭配，`robot / social / terrain / legged / egocentric navigation` 一个
  没收，同一 10 天窗口漏了 16 条（其中约 12 条有价值）——包括 LEAP（四足导航）、
  EgoPathBench（导航 benchmark）、UDAV（VLM 航点规划）、GLAM（全局时空记忆）。
  已补齐这些搭配。
  arXiv 对频繁请求会返回 429，脚本已内置退避重试；短时间多次跑被限流时
  等几分钟再试即可。

  **⚠ 406 → 自动改走 OAI-PMH（2026-09-27 加）**：arXiv 自 2026-09 中旬起负载高时
  只放行命中 varnish 缓存的检索，未缓存的一律 `406`（空正文，`X-Cache: MISS, MISS`）。
  我们两条 query 是定制长串，永远不会被别人缓存，于是被**持续**拒绝——实测 3 分钟
  10 次全 406，换 UA / Accept / 去代理 / POST 都无效，连未缓存的 `id_list` 也 406。
  **不是脚本 bug，别去改 query 或 header。** 现在 API 失败时 `fetch_vln.py` 自动
  降级：从 `oaipmh.arxiv.org` 按日期拉 cs + eess 全量元数据（`arXivRaw`，11 天约
  1 分钟），在本地用 feeds.yaml 里**原样的** search_query 匹配。日志出现
  `[API 失败] 406 … 改走 OAI-PMH 本地匹配` 即为此路径，属正常。
  - 已验证：09-09~09-18 窗口与当时 API 结果对照，导航源召回 98%（91 篇漏 2），
    主池召回 38/41；漏掉的 3 篇关键短语只在**标题**里，当前 query 全用 `abs:`
    本来也抓不到，不是降级误差。
  - 降级路径**不套用** `max_results`（那是 API 分页上限，套用会白丢条目）。
  - 本地匹配只做轻量词干（去复数 s），与 arXiv 的 Lucene 分词不完全一致。
- **arXiv·具身Agent/AgentOS**（2026-09-19 新增）：独立源便于单独调噪。覆盖
  ① agent 架构 / harness / OS ② 具身记忆与长期规划 ③ Agent 化的物体查找与探索
  ④ 通用 agent 但只收架构性主题。**所有 agent 词都 AND 了具身语境，并用
  `ANDNOT` 排掉 web/GUI/coding/SWE/知识图谱/RAG/叙事/临床/运维/推荐/文献**——
  不加这两层时实测噪声 50%+ 且直接把主池灌爆（MUSE 故事引擎、NetOps、
  ClinAgent、Theseus 知识图谱、EconSkills 全部涌入）。收窄后窗口内 22 条、
  噪声约 27%，而 Harness Robotic OS、Finder、AeroWeaver、GLAM、RoboFind、
  DeliveryGym 等目标论文一篇没丢。
  代价：完全不沾具身的通用 agent 架构论文会被挡掉（如「How Do Agent Harnesses
  Create Value?」）。这是刻意取舍，不加具身约束就守不住主池。
- **微信公众号**：公众号文章没有公开 API，两种接入方式：

  **方式 A — 手动喂链接（免费、立即可用，推荐起步）**
  「视觉语言导航」不在任何免费 RSS 列表里，最省事的是直接喂文章链接：
  1. 微信里打开公众号文章 → 右上角「…」→ 复制链接
  2. 把链接粘进 `wechat_urls.txt`（一行一个，可反复追加）
  3. 运行 `python scripts/fetch_vln.py --urls wechat_urls.txt --no-feeds`
  会自动抓全文正文+图片+标题+发布日期，去重入库。也可临时单篇：
  `python scripts/fetch_vln.py --no-feeds --url "https://mp.weixin.qq.com/s/xxxx"`

  **方式 B — 自建 we-mp-rss（2026-09-05 从 wewe-rss 迁移）**
  1. 先把 `we-mp-rss/docker-compose.yml` 里的 `PASSWORD` 改掉，再启动：`cd we-mp-rss && docker compose up -d`
  2. 面板 http://localhost:8001，登录 `admin` / compose 里的 `PASSWORD`
     （模板里是占位的 `change-me`，首次启动前先改掉）
  3. 用**你自己的微信公众号**扫码授权登录微信公众平台（个人订阅号即可，
     不用发文章，只是拿来调后台接口）。授权信息存在 `/app/data/{key.lic,wx.lic}`。
  4. 订阅管理里搜索并添加「视觉语言导航」「具身智能导航」
  5. 抓取前在面板点「更新」拉取新文章
  - 聚合 RSS：`http://localhost:8001/feed/all.rss`（feeds.yaml 已指向这里）；
    也支持 `all.atom` / `all.json` / `all.xml`。
  - **不走微信读书**：`driver/wx.py` 只连 `mp.weixin.qq.com/cgi-bin/home`，
    因此不受微信读书接口封禁影响。

  ### ⚠ wewe-rss 已永久失效，不要再尝试修复（2026-09-05 确认）
  wewe-rss 把所有请求转发给作者部署的中转 `https://weread.111965.xyz`。该中转跑在
  **Deno Deploy Classic 上，平台 2026-07-20 下线**，部署已不存在——主域名走 Cloudflare
  回源到死后端恒返 502，官方镜像 `weread.965111.xyz` 直接返回 `DEPLOYMENT_NOT_FOUND`。
  症状是「添加读书账号一直加载不出来」（要二维码的请求根本到不了微信读书）。
  中转地址虽可用环境变量 `PLATFORM_URL` 覆盖，但没有可用的替代部署；
  项目本身 2026-05-11 已归档。本仓库因此不再附带它的 compose 文件，
  feeds.yaml 里那条源保持 `enabled: false` 仅作记录。

  ### ⚠ we-mp-rss 的两个坑
  - **必须用 named volume，不能用 `./data` bind mount。** Docker Desktop for Windows
    以 **9p 文件系统**把宿主目录挂进容器，SQLite 建不了 WAL 所需的 shared-memory 映射，
    一读一写就报 `unable to open database file`（2026-09-05 实测：挂载目录连 select
    都失败，容器内 /tmp 则 WAL 正常）。compose 已改用 `wemp_data` 卷。
    备份：`docker cp we-mp-rss:/app/data <目标目录>`。
    恢复时**先删掉卷里陈旧的 `we_mp_rss.db-wal` / `-shm`** 再拷入 `.db`，
    否则空库的 WAL 会被重放、覆盖掉刚拷进去的数据。
  - **微信公众平台有频控，且当前是长期封控，不是等一晚就好。**
    新授权的公众号权重低，采集报 `频率限制, 第N次重试` →
    `frequencey control, stop at 0` → `成功0条`。

    ### 2026-09-13 完整诊断：这条路当前走不通，别再反复试
    直接向后台发请求拿到的是 `{"err_msg": "freq control", "ret": 200013}`。
    **关键：token 是有效的** —— 授权失效返回的会是 `200003 Invalid Session`，
    微信正常受理了请求才会给业务错误码。所以订阅完好、授权完好，
    纯粹是微信对这个账号的**账号级频控**。五种采集模式全部实测失败：

    | 模式 | 结果 |
    |---|---|
    | `web`（原默认，作者标为旧版） | 频控 |
    | `free_publish` / `publish` | 返回非 JSON |
    | `appmsgpublish` / `appmsg` | 频控 |
    | `playwright`（真实浏览器 + 已存 cookie） | 拦不到 API 响应，0 条 |

    0.54 秒即返回，不是软限流。自 2026-09-05 迁移至今**入库 0 条**，
    资料库最后一条公众号内容停在 2026-08-29（还是旧 wewe-rss 抓的）。

    已把 compose 的 `GATHER.MODEL` 从默认 `web` 改成 `auto`
    （四端点降级 + Playwright 兜底），频控恢复后命中率更高。

    **`weread_mp`（微信读书通道）也别指望**：新版微信读书废弃了列表接口
    `/web/mp/articles`（恒返回 -2041），只剩 `/api/mp/cover` 取**最新一篇**，
    无法回补历史（见容器内 `core/wx/model/weread_mp.py` 的 docstring）。
    周更场景不适用。

    **当前唯一可用路径是方式 A 手动喂链接** —— 它直接抓
    mp.weixin.qq.com 文章页，不受频控影响（2026-09-13 实测：无 cookie
    直抓，标题与 5750 字正文全部拿到）。

新增任意通用 RSS（实验室博客、Google News 等）：加一条 `type: generic`，
`keep_all: false` 让它走底部 `keywords` 关键词过滤。

## 关键词（范围 = 具身导航整体）

`feeds.yaml` 底部 `keywords` 控制 `keep_all=false` 的源：标题或摘要命中
任一关键词即保留。已含 VLN / VLA / VN / embodied navigation / object
navigation / habitat / 具身导航 / 视觉导航 等，按需增删。

## 与其他 skill 衔接

- 选好题后，把 arXiv 条目的标题或链接交给 **paper-summary-simple**（本仓库）
  出结构化中文摘要；需要论文插图时配合 **pdf-figure-extractor**。
- 资料库 `index.md` 本身就是一张选题表，可以直接作为视频 / 博客流水线的输入。

## 文件结构

```
vln-feed/
  SKILL.md            ← 本文件
  feeds.yaml          ← 资料源 + 关键词配置
  wechat_urls.txt     ← 手动公众号文章链接清单（免 RSS）
  requirements.txt    ← Python 依赖
  scripts/
    fetch_vln.py      ← 抓取主脚本（解析→过滤→去重→写 md→建索引）
    backfill_abstracts.py ← 回填被截断的 arXiv 摘要 + 重算「基准」字段
    backfill_domain.py    ← 重算「领域」分池字段（改过分池规则后必跑）
    validate_report.py ← 发布前校验报告结构、图片禁令和链接异常
    probe_wechat.py   ← 5 秒探测微信频控/授权状态，周流程第 1 步
  references/
    report-format.md  ← 周报固定结构、列表写法（禁用表格）与分析准则
  we-mp-rss/
    docker-compose.yml ← 自建公众号转 RSS（走微信公众平台；数据在 docker 卷 wemp_data）
  output/             ← 运行后生成：index.md / items/ / seen.json / reports/
```

## 每周手动抓取（当前模式）

> ⚠ **触发本 skill 时，第 1 步先跑探针，别直接叫用户去面板点「更新」。**
> 频控期间点更新必然是 0 条，纯浪费时间。这是用户明确选择的纯手动流程
> （自动链路因不确定性已停用）。

每周日手动跑，四步：

1. **先探频控**（5 秒，取代过去「去面板逐个点更新」那一步）：

   ```bash
   python scripts/probe_wechat.py
   ```

   需要 Docker Desktop 在跑；没跑的话脚本会直接告诉你。按退出码分支：

   - **`ret=200013` 频控（09-05 ~ 09-19 的状态）** → 公众号走**方式 A 手动喂链接**：
     在微信里打开这两个号的文章，复制链接贴进 `wechat_urls.txt`
     （PC 版微信打开公众号主页逐条复制比手机快），然后
     `python scripts/fetch_vln.py --urls wechat_urls.txt --no-feeds`。
     **没链接可喂就跳过公众号**，本期周报走纯 arXiv —— 这是正常情况，
     2026-09-05 / 09-12 两期本来就是纯 arXiv 产出的，不要为此卡住流程。
   - **`ret=0` 频控已恢复** → 恢复自动链路：面板 http://localhost:8001
     （登录 `admin` / compose 里的 `PASSWORD`）→ 订阅管理 → 逐个点「更新」，再走第 2 步。
   - **`ret=200003` 授权过期**（2026-09-27 探针实测的当前状态）→ 去面板重新
     扫码授权；扫完再跑一次探针，多半会回到 200013 频控，那就照上面走方式 A。
2. **再抓取入库**：`python scripts/fetch_vln.py --days 10`
   `seen.json` 去重，重复跑只补新。公众号源返回空不会中断流水线，会正常降级
   继续抓 arXiv（2026-09-13 实测）。脚本内那段 token 自检针对已废弃的
   `wewe-rss.db`，对 we-mp-rss 静默跳过，**别依赖它判断授权** —— 用第 1 步的探针。
   arXiv 偶发 `Read timed out`，重跑即可，不是故障。
3. **写结构化研究周报**：不中文化 `items/` 里的 arXiv 原文（保持原文语言便于
   检索与核对）。通读本次新增的公众号与 arXiv 条目，按
   [references/report-format.md](references/report-format.md) 的模板撰写报告：
   - 文件名使用 `reports/vln_<撰写日期，YYYY-MM-DD>.md`，不用日期区间命名。
   - **先按「领域」分池**（2026-09-19 起）：深度分析只针对主池
     （`导航` + `具身Agent`），次池（`VLA·操作` / `自动驾驶` / `其他`）按主题
     压成速览列表。用 `grep -l "^- 领域: 导航" items/*.md` 圈定。报告里给出的
     "本期 N 条"要说明是全部条目数还是主池数，两者差一倍以上，混用会失真。
   - 先按论文标题、方法名、arXiv ID、项目链接做**跨源合并**。公众号解读与 arXiv
     原文指向同一工作时只分析一次，优先引用 arXiv/项目页等一手链接；报告中的
     “条目数”和“独立工作数”不要混用。同一篇论文可能被导航源与具身 Agent 源
     同时命中，抓取脚本已按标题去重，但撰写时仍要留意别当成两项工作。
   - **链接必须逐条从 `items/` 里核对**，不要凭记忆写 arXiv ID。实测凭印象填
     速览表时 52 个链接全错。写完用脚本比对报告里出现的 ID 是否都在本次条目中。
   - **优先关注报了 R2R-CE 指标的工作**（用户明确的关注点，2026-08-22 确认）。
     先用 `grep -l "^- 基准: .*R2R-CE" items/*.md` 圈出本次新增里的命中条目，
     它们默认进入优先阅读清单靠前位置。次优先是 RxR-CE / VLN-CE / 离散 R2R。
     报告里必须写明是 **R2R-CE（连续环境）还是离散 R2R** —— 两者不可直接比较，
     混写会误导横向对比。若本期无命中，如实写明"本期 N 篇中 0 篇报 R2R-CE"，
     这本身就是有效结论，不要为凑数把不相关工作抬进清单。
   - 面向地面机器人 VLN / 具身导航研究。直接相关工作进入优先阅读清单；无人机、
     机械臂、自动驾驶工作仅在存在明确可迁移机制时进入“可迁移方法”，否则放入
     低优先级速览。纯控制/几何制导且无语言或语义导航成分的工作只作一行记录。
   - 先给结论与优先阅读清单，再对少量重点工作做深度分析；其余资料按主题分组。
     不要把几十篇论文写成等权重的长段落——次池一个主题一行，只列链接。
   - **全篇不用表格**（2026-09-27 用户反馈）：报告原样发到博客，手机上宽表格要
     左右滑，很难读。一律改成列表或「**标签。** 段落」，写法见 report-format.md
     第二节；`validate_report.py` 会拦截任何 Markdown 表格。
   - 每个重点结论都区分“来源明确陈述”与“本报告判断”。只写条目中可核验的指标，
     同时注明任务、数据集和指标名；信息缺失或摘要截断时明确标注，不补全、不猜测。
   - 使用客观研究语言，避免“重磅、暴涨、完美、极强”等宣传表达。每篇分析回答：
     解决什么问题、方法为何有效、证据是否充分、对地面导航有什么价值或限制。
   - 链接只使用条目中明确出现且能对应当前工作的地址。链接归属不确定、标题与项目页
     不匹配时省略并标注“链接待核验”，不要根据相邻条目或记忆补链接。
   - **报告中禁止任何图片**：不要输出 Markdown 图片、HTML `<img>`、`<figure>`、
     微信 `mmbiz.qpic.cn` 链接或图片占位符。`items/` 中的图片链接仅是抓取归档，
     撰写报告时全部忽略。
   - 不要在标题下写数据源、筛选原则、摘要截断规则等内部方法论前言；直接进入
     “一、本期结论”。方法论只保留在本 skill。
   - 可用抓取命令输出或文件修改时间确定本次新增文件。Windows/PowerShell 优先使用：
     `Get-ChildItem items -Filter *.md | Where-Object LastWriteTime -ge <本次抓取开始时间>`。
   - 写完必须运行：
     `python scripts/validate_report.py reports/vln_<日期>.md`。
     校验失败时先修正报告；不得带着图片、缺失核心章节或明显异常链接交付。

   校验通过即可交付；要发到博客再走第 4 步。

4. **（可选）发布到 Jekyll 博客**：用户若有 Jekyll 博客仓库，先问清仓库路径和
   周报放在哪个 `_posts/` 子目录，再照下面的约定落盘。

   - 文件名 `_posts/<子目录>/<报告日期，YYYY-MM-DD>-VLN-Weekly.md`。
     Jekyll 要求日期开头，同一天只会有一篇，天然去重。
   - front matter 参考下面的字段（`title` 用**覆盖区间**，不是报告日期；
     `author` 等字段以该博客现有文章为准）：

     ```yaml
     ---
     layout: post
     title: "具身导航周报（2026-08-20 ~ 2026-08-29）"
     date:   2026-08-30
     permalink: /vln-weekly-2026-08-30/
     tags: [VLN, VLA, Embodied Navigation, Weekly Digest, arXiv]
     categories: weekly
     comments: true
     author: <你的名字>
     toc: true
     excerpt: "两三句话讲清本期最硬的结论，带上可核验数字。"
     ---
     ```

   - 正文 = `reports/vln_<日期>.md` 全文，**只删掉顶部那行 `# 具身导航周报（…）`**
     （front matter 的 `title` 已承担），其余 `## 一、二、三…` / `### 1. xxx`
     **层级原样保留，不要提升**。
   - 提交信息用 conventional commits：
     `docs(weekly): add VLN weekly report for <日期>`，正文写清覆盖区间与本期核心结论。
   - **push 前先把文章内容给用户确认**——这是对外可见操作。

**不做全自动链路**：定时任务要依赖开机登录 + Docker 自启 + 微信授权不过期，
三者任一掉链子就静默产出 0 条，实测太脆弱，所以保持每周手动跑上面四步。

> **token 自检**：`fetch_vln.py` 里的自检逻辑针对已废弃的 `wewe-rss.db`，对
> we-mp-rss 无效，会静默跳过。判断 we-mp-rss 授权状态直接跑
> `python scripts/probe_wechat.py` —— 它区分频控（200013）、授权过期（200003）
> 和正常（0），比翻日志快。`wx.lic` 存在只说明扫过码，不代表 token 还有效。

## 管理 we-mp-rss 容器

```bash
cd we-mp-rss
docker compose up -d        # 启动（开机后需先启动 Docker Desktop）
docker compose logs -f      # 看日志（频控/授权问题都在这里）
docker compose down         # 停止（数据保留在 docker 卷 wemp_data）
docker cp we-mp-rss:/app/data ./data.bak   # 备份授权与数据库
```
