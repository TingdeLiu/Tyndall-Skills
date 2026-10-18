---
name: claude-design-to-open-design
description: 把 Claude Design 导出的 design system（zip 里是 SKILL.md + readme.md + tokens/ + components/ + ui_kits/ 那种结构）改造成 Open Design 桌面版的包契约，装进本机让「设计体系」里能选到，并打包成别人能一键安装的可移植安装包。四步：摸清源包 → 改造成设计系统包+技能两份产物 → 装本机并验证 → 打包分发。也用于单独诊断 Open Design 里用户设计系统/技能不显示、导入后颜色字体全变样、卸载报 403。触发词示例：「把这个 design system 装到 Open Design」「Claude Design 导出的怎么在 Open Design 用」「做个安装包给别人装」「Open Design 里看不到我的设计系统」。
---

# Claude Design 设计系统 → Open Design

源包是 Claude Design 导出的 zip（`SKILL.md` + `readme.md` + `tokens/` + `components/` +
`ui_kits/` + `assets/`）。终点是：本机 Open Design 的「设计体系」里能选到它，
并且有一个压缩包能发给别人，他解压跑一下就装好。

## 支持范围与前置条件

- 面向 Windows 上的 Open Design 桌面版；安装脚本使用 Windows PowerShell 5.1+。
- 本技能不包含任何品牌包。用户提供自己要转换的源 zip，保留其中的来源和素材许可。
- 以下接口、workspace 绑定、56 个共享 token 和目录结构来自实际使用过的实现，
  不视作所有版本的稳定契约。执行前检查当前安装的 schema 与 daemon 接口；
  版本不匹配时先调整包契约，不要猜测字段或直接写数据库。
- 安装时 Open Design 必须正在运行。脚本仅连接本机 `127.0.0.1`，
  从本机日志和会话存储识别 workspace 身份，并把身份用于本机安装与可见性查询。
- `metadata.json` 的 `status: published` 是本地包状态，不代表上传云端。
- 命令和安装器已做静态及模拟验证；真实安装仍应在用户当前版本完成可见性检查。

## 安装行为与已知限制

在已检查的实现中，需要区分以下两种行为：

**1. 已检查实现中的「导入」会重新生成内容。** local / github / shadcn 三个导入入口都是*重新生成*型：
只扫源目录里最多 80 个 CSS 变量，然后套模板重写 `DESIGN.md`。实测后果——背景色认错、
强调色取成另一个表面的、字体全变 Inter、色名把整句话吞进去。**保留原始内容时使用 `install` 接口**
（原样安装），但界面上没有这个按钮，只能调 API。

**2. 已检查实现中，光把文件夹拷进 `data\design-systems\` 不够。** 登录 workspace 后，daemon 会把数据库里
没有绑定记录的用户资源从名单里过滤掉——文件在盘上、不带 workspace 头调 API 也查得到，
界面上就是不显示。`install` 接口会顺带写好那条绑定。

机制细节见 [references/pitfalls.md](references/pitfalls.md)。

## 第 1 步 · 摸清源包

解压到临时目录，**先完整读 `readme.md`**——它是唯一的真相来源，通常已经写明了哪些值是从
源文件量出来的、哪些是替代品、哪些故意留空。这些区分必须原样传下去，别抹平成「看起来
完整」的样子。

同时看清楚：源系统有几个**表面**（例如官网一套 + 演示文稿一套），它们是否共用调色板。
这决定后面 `tokens.css` 怎么分主契约和扩展段。

## 第 2 步 · 改造成两份产物

一个源包产出两样东西，**都要装**：

| 产出 | 装到哪 | 作用 |
|---|---|---|
| **设计系统包** | `data\design-systems\<id>\` | token 契约 + 品牌散文 + 组件夹具 + 预览页，参与 prompt 组合 |
| **技能** | `data\skills\<name>\` | 组件源码、UI kit、模板、素材，agent 要抄真东西时用 |

设计系统包管「守规矩」，技能管「有料可抄」。

完整的改造步骤——token 怎么映射、`DESIGN.md` 怎么从 `readme.md` 重组、哪些文件必须有——
见 [references/conversion.md](references/conversion.md)；字段定义和 56 个共享 token 的名单见
[references/od-package-contract.md](references/od-package-contract.md)。

改造时最容易做错的三件事：

- **为了凑齐而发明值**。源里没有的（`--focus-ring`、状态色），从品牌内部已有的颜色里取，
  别引入通用蓝/通用红。凡是补的都要在 `tokens.css` 注释和 `source/evidence.md` 里点名。
- **把具体数字压缩成形容词**。「卡片阴影是 `3px 10px 18px rgba(175,164,142,.27)`，暖的、
  偏移的，中性灰阴影一眼出戏」——改成「使用柔和阴影」这份文档就废了。
- **漏掉 `metadata.json`**。用户包没有它会被当成 `draft`，界面对个人来源的草稿包有额外
  判断，可能不可用。`status` 要 `published`，且**别带 `workspaceId`**（那是机器专属的，
  install 时会自动写）。

改完校验 56 个 token 齐备（命令在 contract 文档里），缺一个都会在 artifact 里静默失效。

## 第 3 步 · 装本机并验证

按可移植结构组织，然后用 `scripts/install.ps1`（**前提：Open Design 正在运行**）：

```
<安装包>/
├── install.ps1               从本 skill 的 scripts/ 复制，注意转 UTF-8 BOM
├── design-system/<id>/       目录名必须等于 manifest.id
└── skill/<name>/
```

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -PackageRoot "D:\某个安装包"
powershell -ExecutionPolicy Bypass -File .\install.ps1 -PackageRoot "D:\某个安装包" -Namespace "<实际 namespace 名>"
```

脚本自己找数据目录、读端口、读 workspace 身份、复制到稳定目录、调 install、最后校验。
它扫 `design-system/` 和 `skill/` 下的子目录，扫到几个装几个，不关心具体叫什么名字。
有多个 namespace 时必须用 `-Namespace` 指定，避免把资源装进错误的空间。
稳定副本按类型分别存放在 `%LOCALAPPDATA%\OpenDesignPackages\design-system\<id>` 和
`%LOCALAPPDATA%\OpenDesignPackages\skill\<name>`。已安装资源在复制前跳过；
未注册但已存在的稳定目录会中止安装，不会被覆盖。需要更新时先在 Open Design 卸载旧资源，
再检查和处理对应的稳定副本，或选择新的 `-InstallRoot`。

**必须确认输出里每项都有「安装成功」（或已安装）和「可见」。**「可见」那步是带 workspace 身份查的——
不带身份的查询会给出假阳性，这是最容易误判「已经装好了」的地方。

复制脚本后必做（PowerShell 5.1 读无 BOM 的 UTF-8 中文会乱码并直接语法报错）：

```powershell
$p = "<安装包>\install.ps1"
$c = Get-Content -Raw -Encoding UTF8 $p; Set-Content -Path $p -Value $c -Encoding UTF8
$errs = $null
[System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$errs) | Out-Null
if ($errs.Count -eq 0) { "语法通过" } else { $errs | ForEach-Object { $_.Message } }
```

## 第 4 步 · 打包给别人

1. 写 `README.md`：装什么、怎么装、为什么不能直接拷、怎么卸载
2. 面向非技术用户时，用 `assets/end-user-guide-template.md` 生成 `安装步骤.md`，替换掉
   占位符。那份模板里的步骤（搜索框打开 PowerShell、opencode 提示词、不用 AI 的两行
   备用命令）都是实测过的
3. 打包前扫保留名文件——`Compress-Archive` 遇到名为 `nul` 的文件会整个失败，而 Git Bash
   的 `2>/dev/null` 有时会真在目录里留一个：

```powershell
Get-ChildItem <安装包> -Recurse -Force | Where-Object { $_.Name -in @('nul','con','prn','aux') }
Compress-Archive -Path <安装包> -DestinationPath <安装包>.zip -CompressionLevel Optimal
```

4. 交付时必须说清楚：装完安装包可以删，但 `%LOCALAPPDATA%\OpenDesignPackages\`
   **不能删**（install 建的是 junction 链接，指向那里）

对方机器上的两条路都验证过：让 opencode 读 README 自己装，或者直接跑
`install.ps1 -PackageRoot <目录>`。后者对不熟电脑的人反而更稳（无需启动 AI、结果确定）。

## 卸载

**顺序不能反**：先删注册项，再删文件。

```powershell
$h = @{ 'Origin' = $base; 'x-od-workspace-id' = $ws; 'x-od-workspace-member-id' = $member }
Invoke-RestMethod -Uri "$base/api/design-systems/$([uri]::EscapeDataString('user:<id>'))" -Method Delete -Headers $h
Invoke-RestMethod -Uri "$base/api/skills/<name>" -Method Delete -Headers $h
```

删除注册项成功后，再手动删除对应的稳定副本目录：
`%LOCALAPPDATA%\OpenDesignPackages\design-system\<id>` 和
`%LOCALAPPDATA%\OpenDesignPackages\skill\<name>`。
如安装时指定了 `-InstallRoot`，以该目录为准；不要删除其他包。

先删了 `OpenDesignPackages` 的话，junction 目标没了，删除接口返 403，留下断链和孤儿绑定
记录。救法：把内容复制回去让链接重新有效，再走正常删除。

## 排查

出问题**先查 daemon 代码，别猜**：

```bash
cd "$APPDATA/Open Design/launcher/channels/stable/namespaces/<ns>/versions/<版本>/payload/resources/app/prebundled/daemon/chunks"
grep -l "关键字" *.mjs
```

界面看不见、导入后内容变样、Logo/字体排版/图像三块永远是空的、卸载 403、端口每次变、
解压套两层——全部记在 [references/pitfalls.md](references/pitfalls.md)。
