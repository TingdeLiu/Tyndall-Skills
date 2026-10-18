# 踩坑与内部机制

> 本文记录已检查实现的行为。接口、路径和 token 数量可能随版本变化，请以当前安装版本为准。


按「最可能浪费时间」排序。前两条是决定性的，其余是操作细节。

## 目录

- [1. workspace 绑定：装了但界面看不见](#1-workspace-绑定装了但界面看不见)
- [2. install 与 import 是两回事](#2-install-与-import-是两回事)
- [3. 品牌视图那三块为什么永远是空的](#3-品牌视图那三块为什么永远是空的)
- [4. PowerShell 脚本必须存成 UTF-8 带 BOM](#4-powershell-脚本必须存成-utf-8-带-bom)
- [5. 卸载顺序不能反](#5-卸载顺序不能反)
- [6. 其他零碎](#6-其他零碎)

## 1. workspace 绑定：装了但界面看不见

**症状**：文件在盘上、裸调 API 查得到、界面上就是没有。

**原因**：登录 workspace 后，`GET /api/design-systems` 会过滤掉 `source: "user"`
且 `app.sqlite` 的 `workspace_resources` 表里没有绑定记录的包：

```js
const visibleSystems = workspaceId && workspaceMemberId ? catalog.filter((system) => {
  if (system.source !== "user") return true;              // 内置包恒可见
  const teamBinding = getWorkspaceResourceByResourceId(db, "design_system",
      workspaceTeamDesignSystemBindingResourceId(workspaceId, system.id));
  if (teamBinding?.workspaceId === workspaceId && teamBinding.visibility === "team"
      && teamBinding.resourceState !== "deleted") return true;
  const personalBinding = getWorkspaceResourceByResourceId(db, "design_system", system.id);
  return personalBinding?.workspaceId === workspaceId
      && personalBinding.visibility !== "team"
      && personalBinding.resourceState !== "deleted"
      && personalBinding.createdByWorkspaceMemberId === workspaceMemberId;
}) : catalog;
```

技能同理，判定在 `skillVisibleFromBinding`，没有绑定时 `!ownerId` 分支
**返回 false**（隐藏），不是放行。

**关键陷阱**：不带 workspace 头调 API 时不过滤，所以用 curl 能看到、界面看不到，
很容易误判成"已经装好了"。**验证一定要带上两个头**：

```
x-od-workspace-id: <workspaceId>
x-od-workspace-member-id: <memberId>
```

**绑定记录长这样**（`claimImportedDesignSystem` 写的）：

```
resource_type='design_system'  resource_id='user:<id>'  workspace_id=<ws>
visibility='personal'  resource_state='active'
created_by_workspace_member_id=<member>  updated_by_workspace_member_id=<member>
sync_state=NULL  version=1
```

技能是 `resource_type='skill'`，`resource_id` 不带 `user:` 前缀。

**身份从哪读**：

- `workspaceId` → `logs\daemon\latest.log` 里 `workspace verified workspaceId=...`
- `memberId` → `user-data\session\Local Storage\leveldb\*.ldb`，按 latin1 读出来正则
  `Member.{0,4}?([a-z0-9]{20,28})`

**别手写数据库**。调 install 接口让官方代码写绑定，更安全也更省事。

## 2. install 与 import 是两回事

| | 接口 | 行为 | 界面上有入口吗 |
|---|---|---|---|
| **install** | `POST /api/design-systems/install`<br>`POST /api/skills/install` | **原样安装**：`installFromLocal` 建 junction 链接、`installFromGithub` 是 `git clone`，内容一个字不改，并自动 claim | **没有** |
| **import** | `/api/design-systems/import/{local,github,shadcn}` | **重新生成**：`scanProject` 只扫源目录里**最多 80 个** CSS 变量，然后用模板重写 `DESIGN.md`、重建 token 契约 | 有（就是界面上那三个「导入」按钮） |

所以精心做的包**必须走 install**。走界面导入的实际后果（实测）：背景色被认成奶油色、
强调色取成了另一个表面的蓝、字体全变 Inter、色名把整句话吞进去当名字。

`installFromLocal` 建的是 **junction**，源目录必须长期存在 → 先把内容复制到一个固定
位置（如 `%LOCALAPPDATA%\OpenDesignPackages\`）再对那个位置 install，安装包本身就能删。

安装后的目录名 = `basename(源路径)`，所以源目录名要跟 `manifest.id` 对齐。

`requireLocalOrigin` 要求请求带 `Origin: http://127.0.0.1:<port>`。

## 3. 品牌视图那三块为什么永远是空的

设计系统详情页里的 **Logo / 字体排版 / 图像** 读的是 `brand.json` 的
`logo` / `typography` / `imagery`，而 daemon 只从 **brands 目录**（`readBrand(brandsRoot, id)`）
或**项目目录**（`readProjectTextOrNull(projectsRoot, projectId, "brand.json")`）读它，
**不从设计系统包目录读**。而且 logo 的图片 URL 是：

```js
n = e => projectId ? projectRawUrl(projectId, e, ...) : null
```

没有关联项目直接返回 null。

**结论**：`od-design-system-project` 形态的包填不进那三个卡片，这是形态差异不是缺文件。
内置的 152 个包（Claude、Airbnb…）同样是空的——可以用它们对照验证。

要那三块有内容，得走「品牌」那条产品线：`POST /api/brands` → 写 brand.json →
`POST /api/brands/:id/logo` → `finalize`。**代价**：finalize 会用它自己的模板重新生成
`DESIGN.md` 和 `system/` 那套 Ant Design 风格的 `--brand-color-*`，精确 token 会被盖掉。
除非用户明确要，否则不值得。

包里放一份内容正确的 `brand.json` 是无害的（将来若走品牌流程可直接用），但要明确
告诉用户：**它现在不会被界面读取**。

## 4. PowerShell 脚本必须存成 UTF-8 带 BOM

Windows PowerShell 5.1 用系统 ANSI 代码页读无 BOM 的 UTF-8 文件，中文全变乱码，
而且往往直接导致**语法报错**（乱码吃掉引号→括号失配）。

```powershell
$c = Get-Content -Raw -Encoding UTF8 $p
Set-Content -Path $p -Value $c -Encoding UTF8   # 5.1 的 -Encoding UTF8 就是带 BOM
```

改完必检：

```powershell
$errs = $null
[System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$null, [ref]$errs) | Out-Null
```

另外在脚本开头设 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`，
否则输出在部分终端（尤其被 Git Bash 管道接住时）还是乱码。

`$PSScriptRoot` 不可靠：脚本被管道执行、或用户 profile 里有 `Set-Location` 时会指偏
（实测被解析成了 `~\Documents\WindowsPowerShell`）。逐级兜底并验证。

## 5. 卸载顺序不能反

**先**在界面里（或调 `DELETE /api/design-systems/:id`、`DELETE /api/skills/:id`）删除，
**再**删 `%LOCALAPPDATA%\OpenDesignPackages\` 下的目录。

反过来的话：junction 目标没了 → `canMutateUserDesignSystem` 检查过不去 → 删除接口
返回 403 → 留下断链和数据库里的孤儿绑定记录。

**踩了怎么救**：把内容重新复制回 `OpenDesignPackages` 让 junction 重新有效，再走正常删除。

## 6. 其他零碎

- **端口每次启动都变**，写死没用，每次从 `logs\daemon\latest.log` 现读。
- **目录是每次请求都扫描的**，改完文件不用重启应用，切换页面刷新列表即可。
- **升级不影响用户数据**：换的是 `launcher\...\versions\<版本>\payload\`，数据在
  `namespaces\<ns>\data\`，namespace 名不变就原地不动。
- **`Compress-Archive` 遇到名为 `nul` 的文件会整个失败**（Windows 保留设备名）。
  Git Bash 里的 `2>/dev/null` 在某些情况下会在当前目录留下一个真的叫 `nul` 的文件。
  打包前扫一遍：`Get-ChildItem -Recurse -Force | Where-Object { $_.Name -in @('nul','con','prn','aux') }`
- **Windows 自带解压向导会自动多套一层同名文件夹**。给非技术用户写说明时要写检查点，
  或者干脆让 `Expand-Archive` 代劳（它不套层）。
- **技能 id 冲突返回 409，body 是空的**，只能靠状态码判断；技能重复安装则返回 400。
  稳妥做法是装之前先查一遍名单（且必须带 workspace 头查，否则永远判断成"没装过"）。
