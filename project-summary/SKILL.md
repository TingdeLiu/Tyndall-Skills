---
name: project-summary
description: Analyze GitHub projects and generate comprehensive architecture documentation (architecture.md). Use when users request project analysis, architecture summaries, or documentation of code structure. Triggers on queries like "analyze this GitHub project", "generate architecture.md", "summarize project structure", or "document the codebase architecture".
---

# Project Summary

## Overview

This skill helps analyze GitHub projects and generate a comprehensive `architecture.md` file that documents the project's structure, key components, file purposes, and architectural decisions.

## Workflow

### Step 1: Gather Project Information

Before analyzing, collect the necessary information:

1. **Get the GitHub repository URL or local path**
   - If URL is provided, use web scraping to fetch README and repository structure
   - If local path is provided, use bash tools to explore the directory

2. **Identify the project type**
   - Detect programming language(s) from file extensions
   - Identify frameworks (React, Django, Flask, etc.)
   - Determine build tools (package.json, requirements.txt, Cargo.toml, etc.)

### Step 2: Analyze Project Structure

Systematically explore and document the project:

1. **Map the directory structure**
   ```bash
   # Get high-level directory tree
   tree -L 3 -I 'node_modules|__pycache__|.git|dist|build'
   ```

2. **Identify key directories and their purposes**
   - `/src` or `/app` - Main source code
   - `/tests` or `/test` - Test files
   - `/docs` - Documentation
   - `/config` - Configuration files
   - `/public` or `/static` - Static assets
   - `/scripts` - Build/deployment scripts

3. **Catalog important files**
   - Configuration files (package.json, setup.py, Cargo.toml, etc.)
   - Entry points (main.py, index.js, main.rs, etc.)
   - Documentation (README.md, CONTRIBUTING.md, etc.)

### Step 3: Analyze Code Architecture

Examine the codebase systematically:

1. **Identify architectural patterns**
   - MVC, MVVM, microservices, monolithic, etc.
   - Component structure (for frontend projects)
   - Module organization (for backend projects)

2. **Document key components**
   - Core modules and their responsibilities
   - API endpoints or routes
   - Database models or schemas
   - Service layers
   - Utility functions

3. **Map dependencies and relationships**
   - Internal module dependencies
   - External library usage
   - Data flow between components

### Step 4: Generate ASCII Architecture Diagrams

**IMPORTANT: Always include ASCII diagrams to visually represent the architecture. Use the decision tree below to auto-select the diagram style — do NOT manually guess.**

#### 4.0 Auto-Select Diagram Style (Decision Tree)

Run through these checks **in order** after Step 2–3 analysis. Use the **first matching** pattern:

```
项目分析结果
│
├─ 存在 docker-compose.yml / kubernetes/ / 多个独立 service 目录?
│   └─▶ Pattern 4: 微服务交互图
│
├─ 存在 DAG / pipeline / workflow / etl / airflow / prefect 关键词?
│   └─▶ Pattern 1: 线性处理流水线
│
├─ 存在 components/ / pages/ / views/ (前端框架特征)?
│   ├─ 嵌套层级 ≥ 3 层?  └─▶ Pattern 6: 嵌套组件架构
│   └─ 否则           └─▶ Pattern 3: 模块依赖树
│
├─ 存在明显中间件链 (middleware/ / interceptor / filter / handler)?
│   └─▶ Pattern 5: 请求处理流水线
│
├─ 存在清晰分层目录 (controllers/ + services/ + models/ / repositories/)?
│   └─▶ Pattern 2: 垂直分层架构
│
└─ 以上均不明显?
    └─▶ Pattern 3: 模块依赖树 (最通用兜底)
```

**复合项目**（如全栈）：后端用 Pattern 2 或 5，前端用 Pattern 6，**分开画两张图**。

#### 4.1 Width Adaptation（宽度自适应）

在生成 ASCII 图前，**先确定目标宽度**：

| 场景 | 目标宽度 | 说明 |
|------|----------|------|
| 默认（未指定） | **80 列** | 兼容所有终端和 GitHub PR 预览 |
| 用户指定 `--wide` 或宽屏 | **120 列** | 允许更多节点并排 |
| 简单项目（≤5 个模块） | **60 列** | 避免空白过多 |

**宽度控制规则：**

```
每个 box 的宽度 = ceil(最长标签字符数 / 2) * 2 + 4   (含边框，保持偶数)

水平 Pattern 1 节点数上限:
  80 列模式:  最多 4 个节点并排  (每节点 ~14 列 + 5 列箭头)
  120 列模式: 最多 6 个节点并排

超出节点数时，折行处理:
  ┌──────┐     ┌──────┐     ┌──────┐
  │  A   │────▶│  B   │────▶│  C   │
  └──────┘     └──────┘     └──┬───┘
                               │
               ┌──────┐        ▼
               │  E   │◀───┌──────┐
               └──────┘    │  D   │
                           └──────┘
```

**中英文混排对齐规则（中文字符占 2 列）：**

```python
# 计算可见宽度（用于对齐 padding）
def visual_width(s):
    return sum(2 if '\u4e00' <= c <= '\u9fff' else 1 for c in s)

# box 内标签居中
def center_label(label, box_inner_width):
    vw = visual_width(label)
    pad = box_inner_width - vw
    return ' ' * (pad // 2) + label + ' ' * (pad - pad // 2)
```

生成时按此逻辑心算或手工校对，确保框内文字视觉居中。

#### ASCII Diagram Style Reference

Use these box-drawing character sets:

| 用途 | 字符集 |
|------|--------|
| 普通模块框 | `┌─┐ │ └─┘` |
| 强调/顶层框 | `╔═╗ ║ ╚═╝` |
| 虚线/可选框 | `┌╌╌┐ ╎ └╌╌┘` |
| 箭头 | `──▶  ──▷  ←──  │  ▼  ▲` |
| 分支/汇合 | `├──  └──  ┬  ┴  ┼` |

#### Pattern 1: 线性处理流水线（水平）

For sequential data/request processing pipelines:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  输入层  │────▶│  处理层  │────▶│  业务层  │────▶│  输出层  │
│  Input   │     │ Process  │     │ Business │     │  Output  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

#### Pattern 2: 垂直分层架构

For layered/tiered system architecture:

```
╔══════════════════════════════════════╗
║           表示层 (UI Layer)          ║
║     React Components / Templates     ║
╠══════════════════════════════════════╣
║         业务逻辑层 (Service Layer)   ║
║      Controllers / Use Cases         ║
╠══════════════════════════════════════╣
║         数据访问层 (Data Layer)      ║
║       Repositories / ORM Models      ║
╠══════════════════════════════════════╣
║           数据库 (Database)          ║
║         PostgreSQL / Redis           ║
╚══════════════════════════════════════╝
```

#### Pattern 3: 模块依赖图（树形）

For showing module/component dependencies:

```
┌─────────────────────────────────────┐
│              主应用入口              │
│            main.py / index.js        │
└──────┬──────────────┬───────────────┘
       │              │
       ▼              ▼
┌──────────┐    ┌──────────┐
│  模块 A  │    │  模块 B  │
│  auth/   │    │  api/    │
└────┬─────┘    └────┬─────┘
     │               │
     ▼               ▼
┌──────────┐    ┌──────────┐
│  工具库  │    │  数据库  │
│  utils/  │    │   db/    │
└──────────┘    └──────────┘
```

#### Pattern 4: 微服务/组件交互图

For distributed systems or service interactions:

```
           ┌─────────────────┐
           │   API Gateway   │
           └────────┬────────┘
          ┌─────────┼─────────┐
          │         │         │
          ▼         ▼         ▼
   ┌──────────┐ ┌────────┐ ┌────────┐
   │ Auth Svc │ │User Svc│ │ Order  │
   │  :8001   │ │ :8002  │ │  Svc   │
   └──────────┘ └────┬───┘ │ :8003  │
                     │     └───┬────┘
                     ▼         ▼
              ┌──────────────────┐
              │     数据库集群    │
              │  PostgreSQL/Redis │
              └──────────────────┘
```

#### Pattern 5: 请求处理流水线（带注释）

For detailed request/data flow with annotations:

```
用户请求
    │
    ▼
┌───────────────────────────────────────┐
│              Middleware                │
│  [认证] ──▶ [限流] ──▶ [日志记录]    │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│               Router                  │
│  /api/v1/* ──▶ APIHandler             │
│  /static/*  ──▶ StaticHandler         │
└───────────────────┬───────────────────┘
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
   ┌─────────────┐    ┌──────────────┐
   │  Controller │    │    Cache     │
   │  (业务处理) │    │   (Redis)    │
   └──────┬──────┘    └──────────────┘
          │
          ▼
   ┌─────────────┐
   │   Database  │
   │  (读/写分离) │
   └─────────────┘
```

#### Pattern 6: 嵌套组件架构

For frontend component hierarchies or nested modules:

```
┌────────────────────────────────────────┐
│                 App                    │
│  ┌──────────────────────────────────┐  │
│  │            Layout                │  │
│  │  ┌──────────┐  ┌──────────────┐  │  │
│  │  │  Navbar  │  │   Sidebar    │  │  │
│  │  └──────────┘  └──────────────┘  │  │
│  │  ┌──────────────────────────────┐ │  │
│  │  │          Main Content        │ │  │
│  │  │  ┌────────┐  ┌────────────┐ │ │  │
│  │  │  │ List   │  │   Detail   │ │ │  │
│  │  │  └────────┘  └────────────┘ │ │  │
│  │  └──────────────────────────────┘ │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

**Diagram Selection Guide:**
- **Pipeline (Pattern 1)**: CI/CD, data processing, ETL pipelines
- **Layered (Pattern 2)**: Web apps, backend services with clear tiers
- **Dependency tree (Pattern 3)**: Libraries, monorepos, module graphs
- **Service mesh (Pattern 4)**: Microservices, distributed systems
- **Request flow (Pattern 5)**: API servers, middleware-heavy apps
- **Nested (Pattern 6)**: Frontend frameworks, plugin architectures

### Step 5: Generate architecture.md

**IMPORTANT: Generate the architecture.md document in Chinese (Simplified Chinese).**

Create a comprehensive architecture document with the following structure in Chinese:

```markdown
# 项目架构

## 项目概述
[项目的简要描述及其目的]

## 技术栈
- **编程语言**: [例如：Python 3.9+, TypeScript]
- **框架**: [例如：React 18, Django 4.2]
- **数据库**: [例如：PostgreSQL, MongoDB]
- **构建工具**: [例如：Webpack, Vite]
- **测试工具**: [例如：Jest, pytest]

## 项目结构

```
[带注释的目录树]
```

## 架构总览

[根据项目类型选择并生成合适的 ASCII 架构图，参考 Step 4 的模式。
必须包含至少一个 ASCII 图展示模块关系或处理流程。]

```
[在此插入 ASCII 架构图]
```

## 处理流水线

[如果项目有明显的数据/请求处理流程，用 ASCII 流水线图展示：
- 数据进入系统后经过哪些模块
- 各模块的处理职责
- 最终输出形式]

```
[在此插入处理流水线 ASCII 图（如适用）]
```

## 核心组件

### [组件/模块名称]
- **位置**: `path/to/component`
- **用途**: [该组件的功能说明]
- **关键文件**:
  - `file1.ext` - [简要描述]
  - `file2.ext` - [简要描述]
- **依赖关系**: [该组件依赖的其他部分]

[为每个主要组件重复此结构]

## 架构模式

[描述使用的架构模式，例如：MVC、分层架构等]

## 数据流

[说明数据如何在系统中流动，配合 ASCII 流向图]

## 配置说明

[记录重要的配置文件和环境变量]

## 构建与部署

[说明构建过程和部署流程（如果明显）]

## 关键设计决策

[值得注意的架构或设计决策]

## 测试策略

[测试方法和结构概述]
```

### Step 6: Review and Refine

Before finalizing:

1. **Verify completeness**
   - All major components documented
   - Key files have purpose descriptions
   - Relationships are clear
   - At least one ASCII diagram is present

2. **Check accuracy**
   - File paths are correct
   - Component descriptions match actual code
   - Technology versions are accurate
   - ASCII diagrams accurately reflect actual architecture

3. **Ensure clarity**
   - Use clear, concise language
   - Include examples where helpful
   - Avoid overly technical jargon unless necessary
   - ASCII diagrams are readable at standard terminal widths (≤80 chars preferred)

## Best Practices

1. **Use Chinese (Simplified Chinese) for all content in architecture.md** - All descriptions, explanations, and documentation should be in Chinese
2. **Always include ASCII architecture diagrams** - At minimum: one overview diagram + one data/request flow diagram
3. **Use the decision tree (Step 4.0) to select diagram style** - Never manually guess; run through the tree in order and use the first match
4. **Respect width budget (Step 4.1)** - Default 80 cols; fold to next row when nodes exceed the limit; verify Chinese character double-width alignment
5. **Be thorough but concise** - Document all important aspects without overwhelming detail
6. **Use examples** - Include code snippets or file excerpts when they clarify concepts
7. **Focus on "why" not just "what"** - Explain architectural decisions and their rationale
8. **Make it actionable** - Help new developers understand how to navigate and contribute

## ASCII Diagram Quick Reference

```
Box styles:
  普通  ┌──┐  │  └──┘
  强调  ╔══╗  ║  ╚══╝
  圆角  ╭──╮  │  ╰──╯

Connectors:
  水平  ────  ════
  垂直  │     ║
  箭头  ──▶   ──▷   ◀──   ▼   ▲
  分叉  ├──   └──   ┬   ┴   ┼

Labels inline:
  ──[标签]──▶   ══[强调]══▶
```

## Common Project Types

### Frontend Projects (React/Vue/Angular)
- Focus on component hierarchy
- Document state management approach
- Note routing structure
- Explain build configuration

### Backend Projects (Django/Flask/Express)
- Document API structure
- Explain database models
- Note middleware and authentication
- Describe service layers

### Full-stack Projects
- Clearly separate frontend and backend documentation
- Document API contracts
- Explain data synchronization
- Note deployment architecture

### Library/Package Projects
- Focus on public API
- Document internal modules
- Explain build and distribution process
- Note testing and examples