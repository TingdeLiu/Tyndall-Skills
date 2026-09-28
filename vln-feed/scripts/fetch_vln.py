#!/usr/bin/env python3
"""
vln-feed — 抓取具身导航（VLN / VLA / VN / 具身导航）领域最新资料。

从 feeds.yaml 配置的 RSS / Atom 源（微信公众号经 wechat2rss 转出的 RSS、
arXiv API、任意通用 RSS）增量拉取条目，按关键词过滤、去重，整理成一个
结构化「选题/资料库」：每条一份 Markdown，外加一个总索引 index.md。

用法:
    python fetch_vln.py                      # 用默认 feeds.yaml，增量抓取
    python fetch_vln.py --days 14            # 只保留最近 14 天的条目
    python fetch_vln.py --list-only          # 只列新条目，不抓正文、不写文件
    python fetch_vln.py --no-full            # 写条目但不抓微信全文正文
    python fetch_vln.py --feeds path.yaml --out somedir

状态文件 output/seen.json 记录已抓过的条目，重复运行只增量补新。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    sys.exit("缺少 feedparser，请先 pip install -r requirements.txt")
try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    sys.exit("缺少 requests，请先 pip install -r requirements.txt")
try:
    import yaml
except ImportError:
    sys.exit("缺少 PyYAML，请先 pip install -r requirements.txt")
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # 正文抽取可降级

SKILL_DIR = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 摘要保留长度，按源类型区分（0 = 不截断）。
# 2026-08-22 修：原先所有源硬截断在 1200 字符，而 arXiv 摘要通常 1000~2500
# 字符，实验结果（R2R-CE / SR / SPL 等数字）恰好落在摘要末尾，一律被切掉。
# 实测某次抓取的 46 条里 40 条正好卡在 1200，导致按指标筛选出现假阴性。
# arXiv 摘要本身已是定长摘要，不再截断；微信条目另有「## 正文」保存全文，
# 其 summary 只作预览，保留上限。
SUMMARY_MAXLEN = {"arxiv": 0, "wechat": 1200, "generic": 4000}
SUMMARY_MAXLEN_DEFAULT = 4000

# 常见导航 / 具身 benchmark。命中后写入条目的「基准」字段，便于后续直接按
# 指标筛选（例如只看报了 R2R-CE 的工作），无需再对全文做正则。
# CE（连续环境）变体与离散版本分开识别：R2R-CE 与离散 R2R 不可直接比较，
# 混在一起会误导横向对比。
# 不能用 \b 做边界：Python 正则的 \w 把中文也算作单词字符，公众号里的
# 「零样本R2R-CE导航基准」两侧都不构成 \b，会整条漏掉。改用显式断言，只
# 排除 ASCII 字母数字相邻的情况（既容纳中文紧邻，也不会命中 XR2R / R2R-CEX）。
_L = r"(?<![A-Za-z0-9])"
_R = r"(?![A-Za-z0-9])"


def _b(pattern: str) -> str:
    """给一组 | 分支整体加上中文友好的词边界。"""
    return _L + r"(?:" + pattern + r")" + _R


BENCHMARKS = [
    # (标签, 正则, 是否忽略大小写)
    ("R2R-CE",    _b(r"R2R[-_ ]?CE"), False),
    ("RxR-CE",    _b(r"RxR[-_ ]?CE"), False),
    ("VLN-CE",    _b(r"VLN[-_ ]?CE"), False),
    ("R2R",       _b(r"R2R|Room[-_ ]?to[-_ ]?Room"), False),
    ("RxR",       _b(r"RxR|Room[-_ ]?Across[-_ ]?Room"), False),
    ("REVERIE",   _b(r"REVERIE"), False),
    ("R4R",       _b(r"R4R"), False),
    ("CVDN",      _b(r"CVDN"), False),
    ("SOON",      _b(r"SOON"), False),        # 大小写敏感，避免命中普通词 soon
    ("ObjectNav", _b(r"ObjectNav|object[-\s]?goal navigation"), True),
    ("PointNav",  _b(r"PointNav|point[-\s]?goal navigation"), True),
    ("ImageNav",  _b(r"ImageNav|image[-\s]?goal navigation"), True),
    ("HM3D",      _b(r"HM3D"), False),
    ("MP3D",      _b(r"MP3D|Matterport ?3D"), False),
    ("Gibson",    _b(r"Gibson"), False),
    ("Habitat",   _b(r"Habitat"), False),
    ("AI2-THOR",  _b(r"AI2[-_ ]?THOR|RoboTHOR|ProcTHOR"), False),
    ("LIBERO",    _b(r"LIBERO"), False),
]
# 命中前者时后者是冗余信息，不重复列出。
BENCHMARK_SUBSUMES = {"R2R-CE": "R2R", "RxR-CE": "RxR"}

# ---------------------------------------------------------------------------
# 「领域」分池（2026-09-19 加）
#
# 起因：某期 70 条里 52 条（74%）是通篇不提导航的 VLA 论文——机械臂、力控、
# 灵巧手、水下双臂乃至生物湿实验室机器人，全从 query 里那个无约束的
# "vision-language-action" 分支涌进来，把真正的导航工作稀释到 20%。
# 用户的选择是「分池而不是砍掉」：VLA 动态仍要跟，但不能和导航论文等权重
# 混在一个池子里。故给每条打一个「领域」标签，周报只对主池（导航 + 具身
# Agent）做深度分析，次池压成一张速览表。
#
# 判定取第一个命中而非多标签：一条只进一个池，避免周报里重复计数。顺序即
# 优先级，导航最高——HarnessVLN、Navi-Agent 这类既是导航又是 Agent 的工作
# 应当留在导航池，它们正是要深读的对象。
#
# 坑：navigation 一词在 GUI / web / 代码库 / 文档语境里同样高频（实测捞到过
# AnchorGUI 的「GUI Navigation」和 SWE-Agent 的「Navigating architecture」）。
# 这类必须先排除，否则会污染主池。排除只挖掉紧邻 navigat 的那段，而不是
# 全局出现即否决——否则一篇正经导航论文提一句 web agent 就被误杀。
NON_EMBODIED_NAV = re.compile(
    r"(?:GUI|GUIs|web|website|webpage|browser|menu|UI|code|codebase|software|"
    r"repository|document|catalog|graph|knowledge[-\s]?graph|multi[-\s]?hop|"
    r"evidence|literature|manuscript|architecture|latent|search|index|"
    r"information|hierarchy|taxonomy|ontology|dialog|dialogue|conversation)"
    r"[-\s]?navigat",
    re.IGNORECASE)

NAV_TERMS = _b(
    r"vision[-\s]?and[-\s]?language navigation|vision[-\s]?language navigation|VLN|"
    r"embodied navigation|visual navigation|object navigation|ObjectNav|"
    r"PointNav|ImageNav|point[-\s]?goal navigation|object[-\s]?goal navigation|"
    r"robot navigation|navigation policy|navigation agent|goal[-\s]?directed navigation|"
    r"social navigation|topological navigation|semantic navigation|map[-\s]?free navigation|"
    r"off[-\s]?road navigation|terrain navigation|indoor navigation|outdoor navigation|"
    r"legged navigation|quadruped navigation|humanoid navigation|aerial navigation|"
    r"egocentric navigation|autonomous navigation|navigation benchmark|navigation dataset|"
    r"R2R|RxR|REVERIE|CVDN|HM3D|MP3D|Matterport|Habitat|"
    r"视觉语言导航|具身导航|视觉导航|导航")

# waypoint 不能单列进 NAV_TERMS：实测它会把「Distributed Stochastic Optimal
# Control for Pattern-Oriented...」这类纯航路点跟踪的控制论文拉进主池。
# 要求它与具身 / 移动语境在同一段落内同现。
_WAYPOINT_CTX = re.compile(r"robot|embodied|navigat|mobile|UAV|drone|agent",
                           re.IGNORECASE)


def _waypoint_is_embodied(blob: str) -> bool:
    for m in re.finditer(r"waypoint", blob, re.IGNORECASE):
        if _WAYPOINT_CTX.search(blob[max(0, m.start() - 300): m.end() + 300]):
            return True
    return False

# 具身 Agent：agent 架构 / harness / 运行时 / 具身记忆 / 长程规划。
# 2026-09-19 实测漏抓的 Harness Robotic OS（具身 Agent 运行时）就该落这里。
#
# agentic 不能单独作判据：实测 GRAVA（自动驾驶）只因摘要里一句「agentic GRA
# data construction pipeline」就被误判进来——那说的是数据流水线，不是论文
# 本体。故 agentic 必须与具身/导航语境词同现才算数。
AGENT_TERMS = _b(
    r"embodied agent|embodied agents|embodied[-\s]?agent|agent harness|agent harnesses|"
    r"agent runtime|agent operating system|AgentOS|robotic OS|"
    r"agentic\s+(?:closed[-\s]?loop|object|navigation|exploration|embodied|"
    r"robot navigation|search|planner|planning)|"
    r"spatial memory|episodic memory|long[-\s]?horizon task planning|"
    r"agent memory|tool[-\s]?calling|具身智能体")

# 具身语境闸门：agent 类词必须落在具身 / 机器人语境里才算「具身Agent」。
# 没有这道闸，MUSE 故事引擎、NetOps 运维 agent、Self-Evolving Search Index、
# Wiki Foundation Model 这些只要提一句 agent harness / agent memory 就会进主池。
EMBODIED_CTX = re.compile(
    r"robot|embodied|navigat|manipulat|locomotion|mobile base|drone|UAV|"
    r"humanoid|quadruped|gripper|physical world|机器人|具身", re.IGNORECASE)

DRIVE_TERMS = _b(r"autonomous driving|self[-\s]?driving|driving policy|驾驶")

VLA_TERMS = _b(
    r"vision[-\s]?language[-\s]?action|VLA|VLAs|manipulation|manipulator|"
    r"grasping|grasp|gripper|dexterous|tactile|force[-\s]?control|teleoperation|"
    r"操作|抓取")


# 曾经在这里放过一个「弱导航信号」：标题判不出时，摘要里出现光秃秃的
# navigation 就归导航。初测影响面只有 1 条（救回 World-Action Models 综述），
# 看着很划算，实际上灾难性——加入具身 Agent 源后，ClinAgent、Theseus 知识图谱、
# SWE-Agent、EconSkills、FlashVector 等十几条全靠摘要里随口一句 navigation 挤进
# 主池，而 NON_EMBODIED_NAV 只能挡住紧邻 navigat 的那种写法，挡不住散落在别处的。
# 已删除：宁可让个别跨领域综述落到次池，也不能让主池失守。


def _domain_of(blob: str) -> str | None:
    """在一段文本里判池；判不出返回 None。顺序即优先级。"""
    # 先把 GUI / web / 图 / 代码语境的 navigation 挖掉，再判是否属于导航
    clean = NON_EMBODIED_NAV.sub(" ", blob)
    if re.search(NAV_TERMS, clean, re.IGNORECASE) or _waypoint_is_embodied(clean):
        return "导航"
    # 自动驾驶排在具身 Agent 之前：驾驶论文提 agent / agentic 的概率很高，
    # 先归驾驶可避免它们混进主池。
    if re.search(DRIVE_TERMS, blob, re.IGNORECASE):
        return "自动驾驶"
    if (re.search(AGENT_TERMS, blob, re.IGNORECASE)
            and EMBODIED_CTX.search(blob)):
        return "具身Agent"
    if re.search(VLA_TERMS, blob, re.IGNORECASE):
        return "VLA·操作"
    return None


def detect_domain(title: str, *rest: str) -> str:
    """把条目归入一个池：导航 / 具身Agent / 自动驾驶 / VLA·操作 / 其他。

    标题优先于摘要：标题体现论文主题，摘要常顺带列举多个应用领域。实测
    World-Action Models 综述只因摘要里一句「manipulation, navigation, and
    autonomous driving」就被归进自动驾驶，而它其实是跨领域综述。标题判不
    出时才退到摘要。

    导航优先于 Agent，使 HarnessVLN、Navi-Agent 这类「Agent 化的导航工作」
    留在主池——它们正是要深读的对象。
    """
    return (_domain_of(title or "")
            or _domain_of("\n".join(t for t in rest if t))
            or "其他")


# 主池 = 周报做深度分析的范围；次池只在周报里压成一张速览表。
PRIMARY_DOMAINS = {"导航", "具身Agent"}


def clip_summary(text: str, ftype: str, override: int | None = None) -> str:
    """按源类型截断摘要；override 来自 --summary-maxlen，0 表示不限。"""
    limit = (SUMMARY_MAXLEN.get(ftype, SUMMARY_MAXLEN_DEFAULT)
             if override is None else override)
    return text if limit <= 0 else text[:limit]


def detect_benchmarks(*texts: str) -> list[str]:
    """在标题 / 摘要里识别出现过的 benchmark 名，返回去重后的标签列表。"""
    blob = "\n".join(t for t in texts if t)
    hits = [label for label, pat, icase in BENCHMARKS
            if re.search(pat, blob, re.IGNORECASE if icase else 0)]
    for strong, weak in BENCHMARK_SUBSUMES.items():
        if strong in hits and weak in hits:
            hits.remove(weak)
    return hits


# Windows 控制台默认 GBK，强制 UTF-8 避免中文乱码
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def fetch_feed(url: str, retries: int = 3):
    """用 requests 拉取（带证书 + 容错 + 429/406 退避），再交给 feedparser 解析。
    避免 feedparser 内置 urllib 在 Windows 上的 SSL 证书问题。
    arXiv 等源对频繁请求会返回 429，需要退避重试。
    406 同样是限流：arXiv 自 2026-09 中旬起在负载高时对未命中 varnish 缓存的
    检索一律回 406（空正文，header 怎么换都没用），见 arxiv_oai_fallback()。"""
    verify = True
    headers = {"User-Agent": UA,
               "Accept": "application/atom+xml, application/rss+xml, application/xml;q=0.9, */*;q=0.8"}
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=45, verify=verify)
        except requests.exceptions.SSLError:
            verify = False
            continue
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code in (429, 406):
            if attempt == retries - 1:
                raise RuntimeError(f"{r.status_code} 限流，请稍后再试")
            time.sleep(8 * (attempt + 1))
            continue
        r.raise_for_status()
        return feedparser.parse(r.content)
    raise RuntimeError("拉取失败")


# --------------------------------------------------------------------------- #
# arXiv 备用通道：OAI-PMH 全量拉取 + 本地执行同一条 search_query
# --------------------------------------------------------------------------- #
# 2026-09-27 查实：arXiv 检索 API 在负载高时只放行命中 varnish 缓存的请求，
# 未缓存的一律 406（响应头 X-Cache: MISS, MISS，正文为空）。我们的两条 query
# 都是定制长串，永远不会被别人缓存，于是被持续拒绝——实测连续 3 分钟 10 次全
# 406，换 UA / Accept / 去代理 / POST 都无效，连未缓存的 id_list 也 406。
# 同期不少 arXiv 抓取项目报告同样症状（最早 09-13）。
#
# OAI-PMH（oaipmh.arxiv.org）是 arXiv 给批量采集的专用接口，不走这套限流，
# 单页 1300 条约 3 秒。于是改为：按日期拉 cs + eess 全量元数据，在本地用
# feeds.yaml 里原样的 search_query 做匹配。这样调好的 query 与噪声取舍一字
# 不用改，API 恢复后自动切回（仅在 API 失败时才走这里）。
#
# 与 API 的差异（本地匹配是近似）：
# - 只做轻量词干（去复数 s），arXiv 的 Lucene 分词/词干细节无法完全复刻；
# - 只拉 cs / eess 两个大类，完全不沾这两类的论文会漏（具身导航几乎不会）。
OAI_URL = "https://oaipmh.arxiv.org/oai"
OAI_SETS = ("cs", "eess")
_OAI_NS = {"oai": "http://www.openarchives.org/OAI/2.0/",
           "raw": "http://arxiv.org/OAI/arXivRaw/"}
_oai_cache: dict[str, list[dict]] = {}


def _oai_get(params: dict, retries: int = 6) -> str:
    for attempt in range(retries):
        try:
            r = requests.get(OAI_URL, params=params, timeout=180,
                             headers={"User-Agent": UA})
        except requests.exceptions.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 503:        # OAI 规范的「稍后再来」，带 Retry-After
            wait = int(r.headers.get("Retry-After", "20") or 20)
            time.sleep(min(wait, 120))
            continue
        r.raise_for_status()
        return r.text
    raise RuntimeError("OAI-PMH 多次重试仍失败")


def _norm_tokens(text: str) -> str:
    """小写 → 非字母数字换空格 → 轻量词干（robots→robot）。两侧同规则。"""
    toks = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    toks = [t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss")
            else t for t in toks]
    return " " + " ".join(toks) + " "


def oai_harvest(since: datetime) -> list[dict]:
    """拉取 datestamp ≥ since 的 cs/eess 记录，按 v1 提交时间过滤。同次运行缓存。"""
    key = since.strftime("%Y-%m-%d")
    if key in _oai_cache:
        return _oai_cache[key]
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime

    recs: dict[str, dict] = {}
    for oai_set in OAI_SETS:
        params = {"verb": "ListRecords", "metadataPrefix": "arXivRaw",
                  "set": oai_set, "from": key}
        page = 0
        while True:
            page += 1
            root = ET.fromstring(_oai_get(params))
            for rec in root.iterfind(".//oai:record", _OAI_NS):
                meta = rec.find("oai:metadata/raw:arXivRaw", _OAI_NS)
                if meta is None:        # 已删除记录只有 header
                    continue
                aid = (meta.findtext("raw:id", "", _OAI_NS) or "").strip()
                versions = meta.findall("raw:version", _OAI_NS)
                if not aid or not versions or aid in recs:
                    continue
                try:
                    v1 = parsedate_to_datetime(
                        versions[0].findtext("raw:date", "", _OAI_NS))
                except (TypeError, ValueError):
                    continue
                if v1 < since:           # 老论文的新版本，与 API 按 v1 日期取窗口一致
                    continue
                title = re.sub(r"\s+", " ", meta.findtext("raw:title", "", _OAI_NS)).strip()
                abstract = re.sub(r"\s+", " ", meta.findtext("raw:abstract", "", _OAI_NS)).strip()
                authors = re.sub(r"\s+", " ", meta.findtext("raw:authors", "", _OAI_NS)).strip()
                recs[aid] = {
                    "aid": aid, "ver": versions[-1].get("version", "v1"),
                    "v1": v1, "title": title, "abstract": abstract,
                    "authors": [a.strip() for a in re.split(r",\s*|\s+and\s+", authors) if a.strip()],
                    "categories": meta.findtext("raw:categories", "", _OAI_NS).split(),
                    "_ti": _norm_tokens(title), "_abs": _norm_tokens(abstract),
                }
            tok = root.find(".//oai:resumptionToken", _OAI_NS)
            print(f"    [OAI] {oai_set} 第 {page} 页，累计候选 {len(recs)} 篇",
                  file=sys.stderr)
            if tok is None or not (tok.text or "").strip():
                break
            params = {"verb": "ListRecords", "resumptionToken": tok.text.strip()}
            time.sleep(3)                # arXiv 建议连续请求间隔 3 秒
    out = list(recs.values())
    _oai_cache[key] = out
    return out


def compile_arxiv_query(q: str):
    """把 arXiv search_query（abs:/ti:/all:/cat: + AND/OR/ANDNOT + 括号）
    编译成对 oai_harvest() 记录的判定函数。同层运算符按从左到右结合，
    feeds.yaml 里混用运算符处都已加括号，不依赖优先级。"""
    toks = re.findall(r'\(|\)|\bANDNOT\b|\bAND\b|\bOR\b|\w+:"[^"]*"|\w+:[^\s()]+', q)
    pos = 0

    def term():
        nonlocal pos
        t = toks[pos]
        pos += 1
        if t == "(":
            f = expr()
            pos += 1                     # 跳过 ")"
            return f
        field, _, val = t.partition(":")
        val = val.strip('"')
        if field == "cat":
            return lambda r, v=val: any(c == v or c.startswith(v + ".") for c in r["categories"])
        needle = _norm_tokens(val)
        keys = {"abs": ("_abs",), "ti": ("_ti",)}.get(field, ("_ti", "_abs"))
        return lambda r, n=needle, ks=keys: any(n in r[k] for k in ks)

    def expr():
        nonlocal pos
        f = term()
        while pos < len(toks) and toks[pos] in ("AND", "OR", "ANDNOT"):
            op = toks[pos]
            pos += 1
            g = term()
            if op == "AND":
                f = (lambda a, b: lambda r: a(r) and b(r))(f, g)
            elif op == "OR":
                f = (lambda a, b: lambda r: a(r) or b(r))(f, g)
            else:
                f = (lambda a, b: lambda r: a(r) and not b(r))(f, g)
        return f

    return expr()


def arxiv_oai_fallback(url: str, since: datetime):
    """用 OAI-PMH 复现一个 arXiv API 源，返回与 feedparser 结果同形的对象。"""
    from urllib.parse import parse_qs, urlparse
    qs = parse_qs(urlparse(url).query)
    query = qs.get("search_query", [""])[0]
    if not query:
        raise RuntimeError("URL 里没有 search_query，无法本地复现")
    # 故意不套用 URL 里的 max_results：那是 API 分页上限，历史上多次因它截断
    # 丢条目；OAI 已按日期圈定窗口，再截只会白丢（09-27 实测 11 天窗口截掉 35 条）。
    match = compile_arxiv_query(query)
    hits = sorted((r for r in oai_harvest(since) if match(r)),
                  key=lambda r: r["v1"], reverse=True)
    entries = []
    for r in hits:
        ref = f"arxiv.org/abs/{r['aid']}{r['ver']}"
        entries.append({
            # id / link 与 API 返回的写法一致，seen.json 的 eid 才能对上
            "id": f"http://{ref}", "link": f"https://{ref}",
            "title": r["title"], "summary": r["abstract"],
            # feedparser 对 arXiv Atom 的 entry.author 取的是最后一位作者，保持一致
            "author": r["authors"][-1] if r["authors"] else "",
            "published_parsed": r["v1"].astimezone(timezone.utc).timetuple(),
        })
    return feedparser.FeedParserDict(entries=entries, bozo=False)


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def slugify(text: str, maxlen: int = 50) -> str:
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"[^\w一-鿿\-]", "", text)
    return text[:maxlen].strip("-") or "untitled"


def entry_id(entry: dict) -> str:
    raw = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha1(raw.encode("utf-8", "ignore")).hexdigest()[:16]


def norm_title(t: str) -> str:
    """标题归一化，用作 eid 之外的第二重去重键。

    需要它的两个原因（2026-09-19 查实）：
    ① arXiv 的 entry id 带版本号，同一篇的 v1 / v2 生成不同 eid，seen 里会
       记成两条，而文件名由标题决定、后者覆盖前者——磁盘上只有一个文件，
       每期的「新增 N 条」却被抬高。历史累积了 12 组这样的重复。
    ② 一篇论文可能同时命中导航源与具身 Agent 源，同一次运行里被处理两遍。
    不直接改 entry_id 去掉版本号，是因为那会让 seen.json 里已有的 800 多个
    键全部失效，下次运行把整个资料库当新条目重抓一遍。
    """
    return re.sub(r"[^a-z0-9]", "", t.lower())


def entry_dt(entry: dict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def strip_html(html: str) -> str:
    if BeautifulSoup:
        return BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    return re.sub(r"<[^>]+>", " ", html)


def matches_keywords(entry: dict, keywords: list[str]) -> bool:
    if not keywords:
        return True
    blob = (entry.get("title", "") + " " +
            strip_html(entry.get("summary", ""))).lower()
    return any(k.lower() in blob for k in keywords)


# --------------------------------------------------------------------------- #
# 微信公众号正文抽取
# --------------------------------------------------------------------------- #
def fetch_wechat_article(url: str) -> dict:
    """返回 {title, author, date, text, images:[url], ok, error}。失败不抛异常。"""
    out = {"title": "", "author": "", "date": "", "text": "",
           "images": [], "ok": False, "error": ""}
    if BeautifulSoup is None:
        out["error"] = "bs4 未安装，跳过正文抽取"
        return out
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
        r.encoding = r.apparent_encoding or "utf-8"
        soup = BeautifulSoup(r.text, "lxml")
        # 标题
        h1 = soup.find(id="activity-name") or soup.find("h1")
        og = soup.find("meta", property="og:title")
        out["title"] = (h1.get_text(strip=True) if h1 else
                        (og.get("content", "").strip() if og else "")) or "微信文章"
        # 作者
        nick = soup.find(id="js_name")
        if nick:
            out["author"] = nick.get_text(strip=True)
        # 日期：页面 JS 里 ct = "时间戳" 或 publish_time
        m = re.search(r'var ct = "?(\d{10})"?', r.text)
        if m:
            out["date"] = datetime.fromtimestamp(int(m.group(1))).strftime("%Y-%m-%d")
        # 正文
        content = soup.find(id="js_content") or soup.find("div", class_="rich_media_content")
        if content:
            for img in content.find_all("img"):
                src = img.get("data-src") or img.get("src")
                if src:
                    out["images"].append(src)
            out["text"] = content.get_text("\n", strip=True)
            out["ok"] = bool(out["text"])
        else:
            out["error"] = "未找到正文容器（可能已被删/需验证）"
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def item_from_url(url: str) -> dict | None:
    """从一条文章 URL 直接构造 item（用于手动喂链接，免 RSS）。"""
    is_wx = "mp.weixin.qq.com" in url
    art = fetch_wechat_article(url) if is_wx else {"title": "", "author": "",
            "date": "", "text": "", "images": [], "ok": False, "error": "非微信链接，仅记录"}
    title = art["title"] or url
    return {
        "eid": hashlib.sha1(url.encode("utf-8", "ignore")).hexdigest()[:16],
        "feed": "手动链接·视觉语言导航" if is_wx else "手动链接",
        "type": "wechat" if is_wx else "generic",
        "title": title,
        "link": url,
        "author": art["author"],
        "date": art["date"] or datetime.now().strftime("%Y-%m-%d"),
        "summary": clip_summary(art["text"], "wechat" if is_wx else "generic") if art["ok"] else "",
        "_full": art,  # 已抓好的正文，write_item 复用，避免二次请求
    }


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"seen": {}}


def save_state(state_path: Path, state: dict) -> None:
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def collect_new_items(cfg: dict, state: dict, days: int, max_per_feed: int,
                      summary_maxlen: int | None = None) -> list[dict]:
    keywords = cfg.get("keywords", [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=days) if days else None
    seen = state.setdefault("seen", {})
    # 第二重去重键：见 norm_title()。seen_titles 拦同一篇的新版本，
    # taken_titles 拦同一次运行里被多个源重复返回的同一篇。
    seen_titles = {norm_title(v.get("title", "")) for v in seen.values()}
    taken_titles: set[str] = set()
    items: list[dict] = []

    for feed in cfg.get("feeds", []):
        if not feed.get("enabled", True):
            continue
        url = (feed.get("url") or "").strip()
        if not url or url.startswith("REPLACE_ME"):
            print(f"  [跳过] {feed.get('name')}：url 未配置", file=sys.stderr)
            continue
        name = feed.get("name", url)
        ftype = feed.get("type", "generic")
        keep_all = feed.get("keep_all", False)
        print(f"  抓取源: {name} …", file=sys.stderr)
        try:
            parsed = fetch_feed(url)
        except Exception as e:  # noqa: BLE001
            if ftype != "arxiv":
                print(f"    [错误] 解析失败: {e}", file=sys.stderr)
                continue
            print(f"    [API 失败] {str(e)[:80]}，改走 OAI-PMH 本地匹配…",
                  file=sys.stderr)
            try:
                parsed = arxiv_oai_fallback(
                    url, cutoff or datetime.now(timezone.utc) - timedelta(days=14))
            except Exception as e2:  # noqa: BLE001
                print(f"    [错误] OAI-PMH 也失败: {e2}", file=sys.stderr)
                continue
            print(f"    [OAI] 本地匹配命中 {len(parsed.entries)} 篇", file=sys.stderr)
        if parsed.bozo and not parsed.entries:
            print(f"    [警告] 源无有效条目: {parsed.get('bozo_exception')}",
                  file=sys.stderr)
            continue

        kept = updated = 0
        for entry in parsed.entries:
            if max_per_feed and kept >= max_per_feed:
                break
            eid = entry_id(entry)
            if eid in seen:
                continue
            title = entry.get("title", "无标题").strip()
            ntitle = norm_title(title)
            if ntitle in taken_titles:      # 本次已由另一个源收录，跳过
                continue
            dt = entry_dt(entry)
            if cutoff and dt and dt < cutoff:
                continue
            if not keep_all and not matches_keywords(entry, keywords):
                continue
            taken_titles.add(ntitle)
            # 已有同名条目 = 同一篇的新版本：照常重写文件让内容保持最新，
            # 但不计入「新增」，否则每期统计会虚高。
            is_update = ntitle in seen_titles
            items.append({
                "eid": eid,
                "feed": name,
                "type": ftype,
                "title": title,
                "link": entry.get("link", ""),
                "author": entry.get("author", ""),
                "date": dt.strftime("%Y-%m-%d") if dt else "",
                "summary": clip_summary(
                    strip_html(entry.get("summary", "")), ftype, summary_maxlen),
                "_update": is_update,
            })
            if is_update:
                updated += 1
            else:
                kept += 1
        msg = f"    新增 {kept} 条"
        if updated:
            msg += f"（另有 {updated} 条是已有论文的新版本，只更新不计新增）"
        print(msg, file=sys.stderr)
    # 新条目按日期倒序
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def write_item(item: dict, items_dir: Path, fetch_full: bool) -> Path:
    date = item["date"] or datetime.now().strftime("%Y-%m-%d")
    fname = f"{date}-{slugify(item['title'])}.md"
    path = items_dir / fname
    full = item.get("_full") or {"text": "", "images": [], "ok": False, "error": ""}
    if not full.get("ok") and fetch_full and item["type"] == "wechat" and item["link"]:
        full = fetch_wechat_article(item["link"])
        time.sleep(1)  # 温柔点，避免被风控

    lines = [
        f"# {item['title']}", "",
        f"- 来源: {item['feed']}",
        f"- 类型: {item['type']}",
        f"- 日期: {item['date'] or '未知'}",
    ]
    if item["author"]:
        lines.append(f"- 作者: {item['author']}")
    if item["link"]:
        lines.append(f"- 链接: {item['link']}")
    # 微信条目的实质内容在正文里，摘要只是预览，两者都要看
    body_text = full.get("text", "") if full.get("ok") else ""
    benches = detect_benchmarks(item["title"], item["summary"], body_text)
    if benches:
        lines.append(f"- 基准: {', '.join(benches)}")
    lines.append(f"- 领域: {detect_domain(item['title'], item['summary'], body_text)}")
    lines += ["", "## 摘要", "", item["summary"] or "（源未提供摘要）", ""]
    if full["ok"]:
        lines += ["## 正文", "", full["text"], ""]
        if full["images"]:
            lines += ["## 图片", ""]
            lines += [f"![img]({u})" for u in full["images"]]
            lines.append("")
    elif fetch_full and item["type"] == "wechat" and full["error"]:
        lines += [f"> 正文抓取失败: {full['error']}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def rebuild_index(items_dir: Path, index_path: Path) -> int:
    """根据 items/ 下所有 md 重建索引表（不依赖本次新增，全量重扫）。"""
    rows = []
    for md in items_dir.glob("*.md"):
        title, source, date, link, bench, domain = md.stem, "", "", "", "", ""
        for line in md.read_text(encoding="utf-8").splitlines()[:15]:
            if line.startswith("# "):
                title = line[2:].strip()
            elif line.startswith("- 来源: "):
                source = line[len("- 来源: "):].strip()
            elif line.startswith("- 日期: "):
                date = line[len("- 日期: "):].strip()
            elif line.startswith("- 链接: "):
                link = line[len("- 链接: "):].strip()
            elif line.startswith("- 基准: "):
                bench = line[len("- 基准: "):].strip()
            elif line.startswith("- 领域: "):
                domain = line[len("- 领域: "):].strip()
        rows.append((date, title, source, md.name, link, bench, domain))
    rows.sort(reverse=True)

    primary = sum(1 for r in rows if r[6] in PRIMARY_DOMAINS)
    out = ["# 具身导航资料库（VLN / VLA / VN）", "",
           f"> 共 {len(rows)} 条 · 其中主池（导航 + 具身Agent） {primary} 条"
           f" · 更新于 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
           "", "| 日期 | 标题 | 来源 | 领域 | 基准 | 原文 | 本地 |",
           "|------|------|------|------|------|------|------|"]
    for date, title, source, fname, link, bench, domain in rows:
        t = title.replace("|", "/")
        orig = f"[原文]({link})" if link else "—"
        out.append(f"| {date or '—'} | {t} | {source or '—'} | {domain or '—'} "
                   f"| {bench or '—'} | {orig} | [md](items/{fname}) |")
    index_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(rows)


def check_wechat_token(cfg: dict, out_dir: Path) -> bool:
    """检查 wewe-rss 微信读书账号 token 是否失效。
    失效则打印醒目提醒 + 在 out_dir 写 TOKEN_EXPIRED.flag（供定时任务弹通知），
    返回 True；正常则清除旧 flag，返回 False。只读打开 db，避免与容器抢锁。"""
    feeds = cfg.get("feeds", [])
    has_wechat = any(
        f.get("type") == "wechat" and f.get("enabled", True)
        and "localhost:4000" in (f.get("url") or "")
        for f in feeds
    )
    flag = out_dir / "TOKEN_EXPIRED.flag"
    if not has_wechat:
        return False
    db = SKILL_DIR / "wewe-rss" / "data" / "wewe-rss.db"
    if not db.exists():
        return False
    try:
        import sqlite3
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro&immutable=1",
                              uri=True, timeout=5)
        rows = con.execute("select name, status from accounts").fetchall()
        con.close()
    except Exception:  # noqa: BLE001  db 锁/损坏时不阻断主流程
        return False
    dead = [n for n, s in rows if s != 1]  # status: 1=正常, 0=失效
    if dead:
        try:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text(
                "微信读书 token 已失效，公众号停止更新。\n"
                "请打开 http://localhost:4000 （授权码见 wewe-rss compose 的 AUTH_CODE）重新扫码登录。\n",
                encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        bar = "!" * 60
        print(f"\n{bar}", file=sys.stderr)
        print(f"⚠ 微信读书账号 token 已失效：{', '.join(dead)}", file=sys.stderr)
        print("  公众号已停止同步新文章，本次抓到的公众号内容可能不全。", file=sys.stderr)
        print("  → 打开 http://localhost:4000 （授权码见 wewe-rss compose 的 AUTH_CODE）", file=sys.stderr)
        print("    账号管理 → 重新扫码登录，别勾「24h 自动退出」", file=sys.stderr)
        print(f"{bar}\n", file=sys.stderr)
        return True
    if flag.exists():
        try:
            flag.unlink()
        except Exception:  # noqa: BLE001
            pass
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feeds", default=str(SKILL_DIR / "feeds.yaml"))
    ap.add_argument("--out", default=None,
                    help="输出目录；缺省时用 feeds.yaml 的 output_dir，再缺省用 ./output")
    ap.add_argument("--days", type=int, default=30, help="只保留最近 N 天（0=不限）")
    ap.add_argument("--max", type=int, default=0, help="每个源最多取 N 条新条目（0=不限）")
    ap.add_argument("--no-full", action="store_true", help="不抓微信公众号全文正文")
    ap.add_argument("--list-only", action="store_true", help="只列出新条目，不写文件")
    ap.add_argument("--url", action="append", default=[],
                    help="手动添加单篇文章 URL（可重复），免 RSS 直接抓全文")
    ap.add_argument("--urls", help="从文件读取文章 URL（每行一个，# 开头为注释）")
    ap.add_argument("--no-feeds", action="store_true",
                    help="只处理 --url/--urls，跳过 feeds.yaml 里的 RSS 源")
    ap.add_argument("--summary-maxlen", type=int, default=None,
                    help="覆盖摘要保留长度（0=不截断）。默认按源类型："
                         "arxiv 不截断 / wechat 1200 / generic 4000")
    args = ap.parse_args()

    cfg = load_config(Path(args.feeds))
    # 输出目录优先级：--out > feeds.yaml:output_dir > 技能内 ./output
    out_dir = Path(args.out or cfg.get("output_dir") or (SKILL_DIR / "output"))
    items_dir = out_dir / "items"
    state_path = out_dir / "seen.json"
    index_path = out_dir / "index.md"

    state = load_state(state_path)

    # 收集手动 URL
    manual_urls: list[str] = list(args.url)
    if args.urls:
        for line in Path(args.urls).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                manual_urls.append(line)

    print("开始抓取具身导航资料…", file=sys.stderr)
    items: list[dict] = []
    if not args.no_feeds:
        items += collect_new_items(cfg, state, args.days, args.max,
                                   args.summary_maxlen)

    seen = state.setdefault("seen", {})
    for u in manual_urls:
        eid = hashlib.sha1(u.encode("utf-8", "ignore")).hexdigest()[:16]
        if eid in seen:
            print(f"  [已存在] {u}", file=sys.stderr)
            continue
        print(f"  手动抓取: {u} …", file=sys.stderr)
        it = item_from_url(u)
        if it:
            items.append(it)
    print(f"\n共发现 {len(items)} 条新条目。\n", file=sys.stderr)

    # 抓完即检查公众号 token 是否失效（手动跑时终端会看到提醒，0 条也检查）
    if not args.no_feeds:
        check_wechat_token(cfg, out_dir)

    if not items:
        print("没有新条目。")
        return

    if args.list_only:
        for it in items:
            print(f"- [{it['date'] or '?'}] {it['title']}  ({it['feed']})")
            if it["link"]:
                print(f"    {it['link']}")
        return

    items_dir.mkdir(parents=True, exist_ok=True)
    written, refreshed = [], []
    for it in items:
        path = write_item(it, items_dir, fetch_full=not args.no_full)
        state["seen"][it["eid"]] = {"title": it["title"], "date": it["date"]}
        (refreshed if it.get("_update") else written).append(path)
        print(f"  {'更新' if it.get('_update') else '写入'} {path.name}",
              file=sys.stderr)

    total = rebuild_index(items_dir, index_path)
    save_state(state_path, state)

    tail = f"，另更新 {len(refreshed)} 条已有论文的新版本" if refreshed else ""
    print(f"\n完成：本次新增 {len(written)} 条{tail}，资料库共 {total} 条。")
    print(f"索引: {index_path}")


if __name__ == "__main__":
    main()
