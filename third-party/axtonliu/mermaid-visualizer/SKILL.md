---
name: mermaid-visualizer
description: Transform text content into professional Mermaid diagrams for presentations and documentation. Use when users ask to visualize concepts, create flowcharts, or make diagrams from text. Supports process flows, system architectures, comparisons, mindmaps, and more with built-in syntax error prevention. Also covers in-conversation plain-text views of code structure - call trees, component trees, shallow file trees, and structural diffs - used when explaining the shape of existing code rather than a concept.
---

# Mermaid Visualizer

## Overview

Convert text content into clean, professional Mermaid diagrams optimized for presentations and documentation. Automatically handles common syntax pitfalls (list syntax conflicts, subgraph naming, spacing issues) to ensure diagrams render correctly in Obsidian, GitHub, and other Mermaid-compatible platforms.

## Quick Start

When creating a Mermaid diagram:

1. **Analyze the content** - Identify key concepts, relationships, and flow
2. **Choose diagram type** - Select the most appropriate visualization (see Diagram Types below)
3. **Select configuration** - Determine layout, detail level, and styling
4. **Generate diagram** - Create syntactically correct Mermaid code
5. **Output in markdown** - Wrap in proper code fence with optional explanation

**Default assumptions:**
- Vertical layout (TB) unless horizontal requested
- Medium detail level (balanced between simplicity and information)
- Professional color scheme with semantic colors
- Obsidian/GitHub compatible syntax

## Diagram Types

### 1. Process Flow (graph TB/LR)
**Best for:** Workflows, decision trees, sequential processes, AI agent architectures

**Use when:** Content describes steps, stages, or a sequence of actions

**Key features:**
- Swimlanes via subgraph for grouping related steps
- Arrow labels for transitions
- Feedback loops and branches
- Color-coded stages

**Configuration options:**
- `layout`: "vertical" (TB), "horizontal" (LR)
- `detail`: "simple" (core steps only), "standard" (with descriptions), "detailed" (with annotations)
- `style`: "minimal", "professional", "colorful"

### 2. Circular Flow (graph TD with circular layout)
**Best for:** Cyclic processes, continuous improvement loops, agent feedback systems

**Use when:** Content emphasizes iteration, feedback, or circular relationships

**Key features:**
- Central hub with radiating elements
- Curved feedback arrows
- Clear cycle indicators

### 3. Comparison Diagram (graph TB with parallel paths)
**Best for:** Before/after comparisons, A vs B analysis, traditional vs modern systems

**Use when:** Content contrasts two or more approaches or systems

**Key features:**
- Side-by-side layout
- Central comparison node
- Clear differentiation via color/style

### 4. Mindmap
**Best for:** Hierarchical concepts, knowledge organization, topic breakdowns

**Use when:** Content is hierarchical with clear parent-child relationships

**Key features:**
- Radial tree structure
- Multiple levels of nesting
- Clean visual hierarchy

### 5. Sequence Diagram
**Best for:** Interactions between components, API calls, message flows

**Use when:** Content involves communication between actors/systems over time

**Key features:**
- Timeline-based layout
- Clear actor separation
- Activation boxes for processes

### 6. State Diagram
**Best for:** System states, status transitions, lifecycle stages

**Use when:** Content describes states and transitions between them

**Key features:**
- Clear state nodes
- Labeled transitions
- Start and end states

## Critical Syntax Rules

**Always follow these rules to prevent parsing errors (Mermaid 10.9.5):**

### Rule 0: Use `flowchart` NOT `graph` (Mermaid 10.x)
```
❌ WRONG: graph TD    → Old syntax, deprecated in 10.x
❌ WRONG: graph TB
✅ RIGHT: flowchart TD   → Use flowchart keyword for all new diagrams
✅ RIGHT: flowchart LR
✅ RIGHT: flowchart TB
```
`graph TD` may still work but `flowchart TD` is the correct 10.x syntax and avoids edge-case parsing failures.

### Rule 1: Avoid List Syntax Conflicts
```
❌ WRONG: [1. Perception]       → Triggers "Unsupported markdown: list"
✅ RIGHT: [1.Perception]         → Remove space after period
✅ RIGHT: [① Perception]         → Use circled numbers (①②③④⑤⑥⑦⑧⑨⑩)
✅ RIGHT: [(1) Perception]       → Use parentheses
✅ RIGHT: [Step 1: Perception]   → Use "Step" prefix
```

### Rule 2: Subgraph Naming
```
❌ WRONG: subgraph AI Agent Core  → Space in name without quotes
✅ RIGHT: subgraph agent["AI Agent Core"]  → Use ID with display name
✅ RIGHT: subgraph agent          → Use simple ID only
```

### Rule 3: Node References
```
❌ WRONG: Title --> AI Agent Core  → Reference display name directly
✅ RIGHT: Title --> agent          → Reference subgraph ID
```

### Rule 4: Special Characters in Node Text
```
✅ Use quotes for text with spaces: ["Text with spaces"]
✅ Escape or avoid: quotation marks → use 『』instead
✅ Escape or avoid: ASCII parentheses in unquoted nodes → wrap in quotes ["用户(管理员)"]
✅ Line breaks in circle nodes only: ((Text<br/>Break))
```

### Rule 5: Arrow Types
- `-->` solid arrow
- `-.->` dashed arrow (for supporting systems, optional paths)
- `==>` thick arrow (for emphasis)
- `~~~` invisible link (for layout only)

### Rule 6: NO Full-Width / Chinese Punctuation in Syntax Positions
Full-width characters look identical to ASCII but break the parser silently.
```
❌ WRONG: A --> B：说明        → Chinese colon ：(U+FF1A)
✅ RIGHT: A -->|说明| B        → Use arrow label syntax instead
✅ RIGHT: A --> B              → Or keep label in node text

❌ WRONG: A（用户）            → Chinese parentheses （）
✅ RIGHT: A["用户"]            → Use ASCII brackets with quotes

❌ WRONG: A --> B　C --> D    → Full-width space between statements
✅ RIGHT: A --> B              → Each statement on its own line
         C --> D
```

**Forbidden full-width characters in Mermaid syntax:**
| Bad (full-width) | Good (ASCII) |
|-----------------|-------------|
| ：(U+FF1A)      | : (U+003A)  |
| （U+FF08）      | ( (U+0028)  |
| ）U+FF09        | ) (U+0029)  |
| 　(U+3000)      | space       |
| ，(U+FF0C)      | , (U+002C)  |
| 「 」(CJK)      | use quotes  |

### Rule 7: No Invisible Characters or Tab Mixing
Content copied from web pages or Word documents often contains:
- Non-breaking spaces (U+00A0)
- Zero-width spaces (U+200B)
- Full-width spaces (U+3000)
- Mixed tabs and spaces

```
❌ WRONG: A[Text​with​ZWSP]   → Zero-width spaces break parsing
❌ WRONG: 	A --> B           → Leading tab instead of spaces
✅ RIGHT: Always use plain ASCII spaces for indentation
✅ RIGHT: Re-type node text instead of copy-pasting from formatted sources
```

### Rule 8: sequenceDiagram Strict Indentation
```
❌ WRONG:
sequenceDiagram
A->>B: message
  B-->>A: response    ← inconsistent indentation

✅ RIGHT:
sequenceDiagram
    participant A
    participant B
    A->>B: message
    B-->>A: response
```
Every statement inside `sequenceDiagram` must be at the **same indentation level** (4 spaces recommended).

### Rule 9: classDef Syntax (10.9.5)
```
❌ WRONG: classDef myClass fill:#f9f,stroke:#333,stroke-width:4px;
          class A,B myClass;

✅ RIGHT: classDef myClass fill:#f9f,stroke:#333,stroke-width:4px
          class A myClass
          class B myClass
```
- No semicolons after `classDef` or `class` statements in 10.9.5
- Apply to one node per `class` statement to avoid ambiguity

For complete syntax reference and edge cases, see [references/syntax-rules.md](references/syntax-rules.md)

## Configuration Options

All diagrams accept these parameters:

**Layout:**
- `direction`: "vertical" (TB), "horizontal" (LR), "right-to-left" (RL), "bottom-to-top" (BT)
- `aspect`: "portrait" (default), "landscape" (wide), "square"

**Detail Level:**
- `simple`: Core elements only, minimal labels
- `standard`: Balanced detail with key descriptions (default)
- `detailed`: Full annotations, explanations, and metadata
- `presentation`: Optimized for slides (larger text, fewer details)

**Style:**
- `minimal`: Monochrome, clean lines
- `professional`: Semantic colors, clear hierarchy (default)
- `colorful`: Vibrant colors, high contrast
- `academic`: Formal styling for papers/documentation

**Additional Options:**
- `show_legend`: true/false - Include color/symbol legend
- `numbered`: true/false - Add sequence numbers to steps
- `title`: string - Add diagram title

## Example Usage Patterns

**Pattern 1: Basic request**
```
User: "Visualize the software development lifecycle"
Response: [Analyze → Choose graph TB → Generate with standard detail]
```

**Pattern 2: With configuration**
```
User: "Create a horizontal flowchart of our sales process with lots of detail"
Response: [Analyze → Choose graph LR → Generate with detailed level]
```

**Pattern 3: Comparison**
```
User: "Compare traditional AI vs AI agents"
Response: [Analyze → Choose comparison layout → Generate with contrasting styles]
```

## Workflow

1. **Understand the content**
   - Identify main concepts, entities, and relationships
   - Determine hierarchy or sequence
   - Note any comparisons or contrasts

2. **Select diagram type**
   - Match content structure to diagram type
   - Consider user's presentation context
   - Default to process flow if ambiguous

3. **Choose configuration**
   - Apply user-specified options
   - Use sensible defaults for unspecified options
   - Optimize for readability

4. **Generate Mermaid code**
   - Follow all syntax rules strictly
   - Use semantic naming (descriptive IDs)
   - Apply consistent styling
   - Test for common errors:
     * No "number. space" patterns in node text
     * All subgraphs use ID["display name"] format
     * All node references use IDs not display names

5. **Output with context**
   - Wrap in ```mermaid code fence
   - Add brief explanation of diagram structure
   - Mention rendering compatibility (Obsidian, GitHub, etc.)
   - Offer to adjust or create variations

## Color Scheme Defaults

Standard professional palette:
- Green (#d3f9d8/#2f9e44): Input, perception, start states
- Red (#ffe3e3/#c92a2a): Planning, decision points
- Purple (#e5dbff/#5f3dc4): Processing, reasoning
- Orange (#ffe8cc/#d9480f): Actions, tool usage
- Cyan (#c5f6fa/#0c8599): Output, execution, results
- Yellow (#fff4e6/#e67700): Storage, memory, data
- Pink (#f3d9fa/#862e9c): Learning, optimization
- Blue (#e7f5ff/#1971c2): Metadata, definitions, titles
- Gray (#f8f9fa/#868e96): Neutral elements, traditional systems

## Common Patterns

### Swimlane Pattern (Grouping)
```mermaid
flowchart TB
    subgraph core["Core Process"]
        A --> B --> C
    end
    subgraph support["Supporting Systems"]
        D
        E
    end
    core -.-> support
```

### Feedback Loop Pattern
```mermaid
flowchart TB
    A[Start] --> B[Process]
    B --> C[End]
    C -.->|Feedback| A
```

### Hub and Spoke Pattern
```mermaid
flowchart TB
    Central[Hub]
    A[Spoke 1] --> Central
    B[Spoke 2] --> Central
    C[Spoke 3] --> Central
```

## Explaining Code Structure

Not every "show me" calls for a rendered diagram. When the reader already understands the
identifiers — they can read `<SessionToolbar>` and a diff — what is missing is the **shape**,
not the concepts. The four views below are plain code fences, not Mermaid. They are
in-conversation and disposable: each sits next to the sentence it supports, and none of them
is saved as a document artifact.

**Pick the smallest view that settles the question.** One form per explanation is normal —
it is unlikely you will need more than one, and never open with all four.

### Call Tree
**Best for:** "where does this get called from", "what breaks if I change this"

Indentation for depth. Annotate only the nodes the question turns on; leave the rest bare.

```
handleSubmit()                    ← entry, src/forms/Session.tsx:88
  validate()
    checkRequired()
    checkFormat()                 ← the regex you're changing
  persist()
    db.write()                    ← async, callers do NOT await
  onDone()
```

### Component Tree
**Best for:** UI nesting questions, "which component owns this state"

Show ownership inline — props flowing down, state living somewhere. Prune every branch that
does not touch the question.

```
<SessionPage>
  state: session, isDirty
  ├─ <SessionToolbar session>
  │    └─ <SaveButton disabled={!isDirty}>
  └─ <SessionBody session onEdit>       ← setIsDirty fires here
```

### Shallow File Tree
**Best for:** orienting someone in an unfamiliar area of the repo

List only the paths the current question touches, one line of purpose each. Never dump a
full recursive tree — depth beyond what the question needs is noise.

```
src/sim/
  runner.py        builds the system prompt, injects skills
  world.py         tick loop
  skills/          agent-facing skill markdown (NOT .claude/skills)
```

### Diff
**Best for:** the surrounding shape already exists and only the change matters

When you would otherwise redraw an entire diagram to move one box, show the delta instead.
Works on all three trees above plus control flow:

- **Component tree diff** — a node moves, or state relocates to a different owner
- **File layout diff** — files added, moved, or split
- **Call stack diff** — a hop is inserted or removed from a path
- **Control flow diff** — a branch, guard, or early return changes

```
  persist()
-   db.write()
+   queue.push()
+   worker.drain()      ← now awaited
```

## Quality Checklist

Before outputting, verify:
- [ ] Using `flowchart TD/LR/TB` (NOT `graph TD`) for Mermaid 10.x
- [ ] No "number. space" patterns in any node text
- [ ] All subgraphs use proper `id["Display Name"]` syntax
- [ ] All arrows use correct syntax (-->, -.->)
- [ ] Colors applied consistently
- [ ] Layout direction specified
- [ ] Style declarations present (no semicolons on classDef/class lines)
- [ ] No ambiguous node references (ID only, never display text)
- [ ] No full-width/Chinese punctuation in syntax positions (：（）　，)
- [ ] No invisible characters or mixed tabs/spaces in indentation
- [ ] sequenceDiagram statements at consistent 4-space indentation
- [ ] Compatible with Obsidian/GitHub renderers
- [ ] **No Emoji** in any node text - use text labels or color coding instead

## References

For detailed syntax rules and troubleshooting, see:
- [references/syntax-rules.md](references/syntax-rules.md) - Complete syntax reference and error prevention
