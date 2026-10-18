# Open Design 资源安装脚本（通用版）
#
#     powershell -ExecutionPolicy Bypass -File .\install.ps1
#     powershell -ExecutionPolicy Bypass -File .\install.ps1 -PackageRoot "D:\某个安装包"
#
# 安装包结构（子目录名即资源 id，脚本不关心具体叫什么，扫到几个装几个）：
#     <PackageRoot>\design-system\<id>\   ← 每个是一个 od 设计系统包（必须含 DESIGN.md）
#     <PackageRoot>\skill\<name>\         ← 每个是一个技能（必须含 SKILL.md）
#
# 为什么走接口而不是把文件夹拷进 data 目录：登录 workspace 后，daemon 会把
# workspace_resources 表里没有绑定记录的用户资源从列表里过滤掉，界面上就是看不见。
# install 接口会顺带写好绑定，而且是原样安装——界面上那三个「导入」入口
# （local / github / shadcn）都会用模板重写内容。

[CmdletBinding()]
param(
    [string] $PackageRoot,
    [string] $Namespace,
    [string] $InstallRoot = (Join-Path $env:LOCALAPPDATA 'OpenDesignPackages')
)

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

function Step($m) { Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    $m" -ForegroundColor Green }
function Note($m) { Write-Host "    $m" -ForegroundColor Gray }
function Warn($m) { Write-Host "    $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host ""; Write-Host "!!  $m" -ForegroundColor Red; exit 1 }

# $PSScriptRoot 并不总是可靠：脚本被管道执行、或用户 profile 里有 Set-Location 时会指偏。
# 逐级兜底，每个候选都用「有没有 design-system 子目录」验一下。
if (-not $PackageRoot) {
    $candidates = @()
    if ($PSScriptRoot) { $candidates += $PSScriptRoot }
    if ($MyInvocation.MyCommand.Path) { $candidates += (Split-Path -Parent $MyInvocation.MyCommand.Path) }
    $candidates += (Get-Location).Path
    foreach ($c in $candidates) {
        if ($c -and (Test-Path (Join-Path $c 'design-system'))) { $PackageRoot = $c; break }
    }
    if (-not $PackageRoot -and $candidates.Count -gt 0) { $PackageRoot = $candidates[0] }
}

# ── 1. 定位数据目录 ────────────────────────────────────────────────────
Step '定位 Open Design 数据目录'
$nsRoot = Join-Path $env:APPDATA 'Open Design\namespaces'
if (-not (Test-Path $nsRoot)) { Die "没找到 $nsRoot —— 请先安装并至少运行过一次 Open Design。" }
$namespaces = @(Get-ChildItem -LiteralPath $nsRoot -Directory)
if ($Namespace) {
    $ns = $namespaces | Where-Object { $_.Name -eq $Namespace } | Select-Object -First 1
} elseif ($namespaces.Count -eq 1) {
    $ns = $namespaces[0]
} elseif ($namespaces.Count -gt 1) {
    Die "发现多个 namespace，请用 -Namespace 指定一个：$($namespaces.Name -join ', ')"
} else { $ns = $null }
if ($null -eq $ns) { Die "$nsRoot 下没有 namespace 目录。" }
$nsPath = $ns.FullName
Ok "namespace: $($ns.Name)"

# ── 2. 连接 daemon ─────────────────────────────────────────────────────
Step '连接正在运行的 Open Design'
$log = Join-Path $nsPath 'logs\daemon\latest.log'
if (-not (Test-Path $log)) { Die "没找到 daemon 日志：$log —— 请先把 Open Design 打开。" }
$logText = Get-Content $log -Raw
$portMatches = [regex]::Matches($logText, '127\.0\.0\.1:(\d{2,5})')
if ($portMatches.Count -eq 0) { Die '日志里没有端口 —— 请先把 Open Design 打开再运行。' }
$port = $portMatches[$portMatches.Count - 1].Groups[1].Value
$base = "http://127.0.0.1:$port"
Note "端口: $port（每次启动都会变，所以每次都要现读）"

$headers = @{ 'Origin' = $base }
try { Invoke-RestMethod -Uri "$base/api/design-systems" -Headers $headers -TimeoutSec 15 | Out-Null }
catch { Die "连不上 $base —— Open Design 没在运行，或端口已经变了。打开它再重试。" }
Ok '已连接'

# ── 3. workspace 身份 ──────────────────────────────────────────────────
Step '读取 workspace 身份'
$workspaceId = $null; $memberId = $null
$wsMatch = [regex]::Match($logText, 'workspaceId=([A-Za-z0-9_-]{8,40})')
if ($wsMatch.Success) { $workspaceId = $wsMatch.Groups[1].Value }

$ldbDir = Join-Path $nsPath 'user-data\session\Local Storage\leveldb'
if (Test-Path $ldbDir) {
    $latin1 = [System.Text.Encoding]::GetEncoding(28591)
    foreach ($f in (Get-ChildItem $ldbDir -File | Sort-Object LastWriteTime -Descending)) {
        try { $text = $latin1.GetString([System.IO.File]::ReadAllBytes($f.FullName)) } catch { continue }
        if (-not $memberId) {
            $m = [regex]::Match($text, 'Member.{0,4}?([a-z0-9]{20,28})')
            if ($m.Success) { $memberId = $m.Groups[1].Value }
        }
        if (-not $workspaceId) {
            $m = [regex]::Match($text, 'workspace.{0,6}?([a-z0-9]{20,28})')
            if ($m.Success) { $workspaceId = $m.Groups[1].Value }
        }
        if ($memberId -and $workspaceId) { break }
    }
}

if ($workspaceId -and $memberId) {
    $headers['x-od-workspace-id'] = $workspaceId
    $headers['x-od-workspace-member-id'] = $memberId
    Ok "workspace: $workspaceId"
    Note "member:    $memberId"
} else {
    Warn '没读到 workspace 身份 —— 按未登录处理（未登录时本来就不过滤，照样能用）。'
    Note '若装完界面上看不到，说明其实是登录状态：在界面里随便做一次导入再重跑本脚本。'
}

# ── 4. 找出要装什么 ────────────────────────────────────────────────────
Step '扫描安装包'
$dsDir    = Join-Path $PackageRoot 'design-system'
$skillDir = Join-Path $PackageRoot 'skill'
$dsSources    = @(); $skillSources = @()
if (Test-Path $dsDir)    { $dsSources    = @(Get-ChildItem $dsDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'DESIGN.md') }) }
if (Test-Path $skillDir) { $skillSources = @(Get-ChildItem $skillDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') }) }

if ($dsSources.Count -eq 0 -and $skillSources.Count -eq 0) {
    Die @"
在这个目录下没找到可安装的内容：$PackageRoot
    期望的结构：
        <安装包>\design-system\<id>\DESIGN.md
        <安装包>\skill\<name>\SKILL.md
    请切到安装包目录里运行，或显式指定：
        powershell -ExecutionPolicy Bypass -File .\install.ps1 -PackageRoot "<安装包目录>"
"@
}
Note "安装包: $PackageRoot"
foreach ($d in $dsSources)    { Ok "设计系统: $($d.Name)" }
foreach ($s in $skillSources) { Ok "技能:     $($s.Name)" }

# ── 5. 预检已安装资源，再复制到按类型分开的稳定目录 ────────────────────
Step '检查资源并复制到稳定目录'
$dsBefore = (Invoke-RestMethod -Uri "$base/api/design-systems" -Headers $headers -TimeoutSec 15).designSystems
$skillsBefore = (Invoke-RestMethod -Uri "$base/api/skills" -Headers $headers -TimeoutSec 15).skills
$installBase = [System.IO.Path]::GetFullPath($InstallRoot)
$plan = @()
foreach ($item in ($dsSources + $skillSources)) {
    $isDs = $dsSources -contains $item
    $kind = if ($isDs) { 'design-system' } else { 'skill' }
    $dest = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $installBase $kind) $item.Name))
    $prefix = $installBase.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if (-not $dest.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { Die '安装目标超出 InstallRoot。' }
    $existing = if ($isDs) { @($dsBefore) } else { @($skillsBefore) }
    $alreadyInstalled = @($existing | Where-Object { $_.id -eq $item.Name -or $_.id -eq "user:$($item.Name)" }).Count -gt 0
    $plan += [pscustomobject]@{
        Name = $item.Name; Source = $item.FullName; Dest = $dest; IsDs = $isDs
        Endpoint = if ($isDs) { '/api/design-systems/install' } else { '/api/skills/install' }
        Label = if ($isDs) { '设计系统' } else { '技能' }
        AlreadyInstalled = $alreadyInstalled
    }
    if (-not $alreadyInstalled -and (Test-Path -LiteralPath $dest)) {
        Die "稳定目录已有未注册内容，已停止且未覆盖：$dest。请检查后更换 -InstallRoot 或先整理该目录。"
    }
}
foreach ($p in $plan) {
    if ($p.AlreadyInstalled) { continue }
    $parent = Split-Path -Parent $p.Dest
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Copy-Item -LiteralPath $p.Source -Destination $p.Dest -Recurse
}
Ok "$installBase"

# ── 6. 安装 ────────────────────────────────────────────────────────────
Step '安装到 Open Design'
$installFailed = $false

foreach ($p in $plan) {
    if ($p.AlreadyInstalled) {
        Warn "$($p.Label) $($p.Name) 已经装过了，跳过。"
        continue
    }
    $body = @{ source = 'local'; path = $p.Dest } | ConvertTo-Json -Compress
    try {
        Invoke-RestMethod -Uri "$base$($p.Endpoint)" -Method Post -Headers $headers `
            -ContentType 'application/json' -Body $body -TimeoutSec 60 | Out-Null
        Ok "$($p.Label) $($p.Name) 安装成功"
    } catch {
        $status = 0
        try { $status = [int]$_.Exception.Response.StatusCode } catch { }
        $detail = ''
        try { $detail = (New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())).ReadToEnd() } catch { }
        $installFailed = $true
        if ($status -eq 409 -or $detail -match 'already installed') {
            Warn "$($p.Label) $($p.Name) 已经装过同名的了。"
            Note '要重装的话，先在 Open Design 界面里删掉旧的，再运行本脚本。'
        } elseif ($detail) {
            Warn "$($p.Label) $($p.Name) 安装失败 (HTTP $status): $detail"
        } else {
            Warn "$($p.Label) $($p.Name) 安装失败 (HTTP $status): $($_.Exception.Message)"
        }
    }
}

# ── 7. 校验 ────────────────────────────────────────────────────────────
Step '校验'
$dsAfter = @(); $skillsAfter = @()
try { $dsAfter     = (Invoke-RestMethod -Uri "$base/api/design-systems" -Headers $headers -TimeoutSec 15).designSystems } catch { }
try { $skillsAfter = (Invoke-RestMethod -Uri "$base/api/skills"         -Headers $headers -TimeoutSec 15).skills        } catch { }

$allOk = -not $installFailed
foreach ($p in $plan) {
    $pool = if ($p.IsDs) { $dsAfter } else { $skillsAfter }
    $hit = @($pool | Where-Object { $_.id -eq $p.Name -or $_.id -eq "user:$($p.Name)" })
    if ($hit.Count -gt 0) {
        $shown = if ($hit[0].title) { $hit[0].title } else { $hit[0].id }
        Ok "$($p.Label)可见: $shown"
    } else {
        Warn "$($p.Label) $($p.Name) 在带 workspace 身份的名单里看不到。"
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host '完成。回 Open Design 切换一下页面刷新列表就能看到。' -ForegroundColor Green
} else {
    Write-Host '安装或可见性验证未全部通过，请根据前面的输出检查。' -ForegroundColor Yellow
    Write-Host '在 Open Design 里随便做一次导入让它写一条绑定记录，然后重跑本脚本。' -ForegroundColor Gray
}
Write-Host ""


if (-not $allOk) { exit 1 }
