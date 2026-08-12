# AI Architecture Diagram — Reusable Patterns

可直接复制粘贴的 JSON 片段，配合 SKILL.md §3 使用。所有片段使用 `fontFamily: 5`、`roughness: 1`、`roundness: {type: 3}`。

---

## 1. 模块盒（Module Box）

矩形容器 + 多行文本。文本通过 `containerId` 绑定到容器，自动居中。

### 1.1 Vision Encoder 盒

```json
{
  "id": "vision_encoder_box",
  "type": "rectangle",
  "x": 240, "y": 240,
  "width": 200, "height": 120,
  "angle": 0,
  "strokeColor": "#1e40af",
  "backgroundColor": "#dbeafe",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [], "frameId": null,
  "index": "a3",
  "roundness": {"type": 3},
  "seed": 100001, "version": 1, "versionNonce": 100002,
  "isDeleted": false,
  "boundElements": [{"id": "vision_encoder_text", "type": "text"}],
  "updated": 1751928342106, "link": null, "locked": false
}
```

```json
{
  "id": "vision_encoder_text",
  "type": "text",
  "x": 250, "y": 255,
  "width": 180, "height": 90,
  "angle": 0,
  "strokeColor": "#1e40af",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100,
  "groupIds": [], "frameId": null,
  "index": "a4",
  "roundness": null,
  "seed": 100003, "version": 1, "versionNonce": 100004,
  "isDeleted": false, "boundElements": [],
  "updated": 1751928342106, "link": null, "locked": false,
  "text": "Vision Encoder\n━━━━━━\n• DINOv2 ViT-L\n• (B, 256, 1024)",
  "rawText": "Vision Encoder\n━━━━━━\n• DINOv2 ViT-L\n• (B, 256, 1024)",
  "fontSize": 16, "fontFamily": 5,
  "textAlign": "center", "verticalAlign": "middle",
  "containerId": "vision_encoder_box",
  "originalText": "Vision Encoder\n━━━━━━\n• DINOv2 ViT-L\n• (B, 256, 1024)",
  "autoResize": true, "lineHeight": 1.25
}
```

### 1.2 LLM/Language 盒（紫色系）

只列差异字段：

```jsonc
{
  "strokeColor": "#6d28d9",
  "backgroundColor": "#ede9fe",
  "text": "Qwen-VL-2.5「7B」\n━━━━━━\n• 语言理解\n• 空间推理\n• (B, seq, 4096)"
}
```

### 1.3 Fusion / Cross-Attention 盒（粉色系）

```jsonc
{
  "strokeColor": "#be185d",
  "backgroundColor": "#fce7f3",
  "text": "Cross-Attention\n━━━━━━\n• Q: latent\n• K/V: vision tokens\n• (B, 32, 512)"
}
```

### 1.4 Policy / Diffusion 盒（绿色系）

```jsonc
{
  "strokeColor": "#047857",
  "backgroundColor": "#d1fae5",
  "text": "Diffusion Policy\n━━━━━━\n• U-Net「12M」\n• DDIM 采样\n• [M, 3] 轨迹"
}
```

### 1.5 Controller 盒（灰色系）

```jsonc
{
  "strokeColor": "#475569",
  "backgroundColor": "#f1f5f9",
  "text": "MPC Controller\n━━━━━━\n• 轨迹跟踪\n• 30 Hz"
}
```

---

## 2. 子系统分组框（Subsystem Container）

半透明虚线大矩形，框住一组模块。**index 设为 `a0`** 让它沉到底层。

```json
{
  "id": "system2_group",
  "type": "rectangle",
  "x": 200, "y": 180,
  "width": 900, "height": 280,
  "angle": 0,
  "strokeColor": "#475569",
  "backgroundColor": "#f8fafc",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "dashed",
  "roughness": 0,
  "opacity": 60,
  "groupIds": [], "frameId": null,
  "index": "a0",
  "roundness": {"type": 3},
  "seed": 200001, "version": 1, "versionNonce": 200002,
  "isDeleted": false, "boundElements": [],
  "updated": 1751928342106, "link": null, "locked": false
}
```

配套标题（自由文本，贴在框顶部内侧）：

```jsonc
{
  "type": "text",
  "x": 220, "y": 195,
  "text": "System 2: 高层规划「Slow, 2 Hz」",
  "fontSize": 18,
  "fontFamily": 5,
  "strokeColor": "#1e40af",
  "textAlign": "left"
}
```

---

## 3. 张量形状标注（Free-Floating Tensor Shape）

不带容器的小字标签，贴在箭头中段或模块旁边。

```jsonc
{
  "id": "shape_anno_1",
  "type": "text",
  "x": 460, "y": 320,
  "width": 100, "height": 18,
  "text": "(B, 256, 1024)",
  "rawText": "(B, 256, 1024)",
  "fontSize": 14,
  "fontFamily": 5,
  "strokeColor": "#b45309",
  "backgroundColor": "transparent",
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": null,
  "lineHeight": 1.25,
  "autoResize": true
}
```

常用张量形状写法：
- 通用：`(B, N, D)`、`(B, seq_len, d_model)`
- 图像：`(B, C, H, W)`、`B × 3 × 224 × 224`
- 序列：`[N, 256] tokens`
- 轨迹：`[M, 3]`、`[T, 7-DOF]`
- 中间维度：`(B, n_query, 4096)`

---

## 4. 频率/延迟标注（Latency Tag）

虚线小框，金色背景：

```jsonc
{
  "type": "rectangle",
  "x": 920, "y": 440,
  "width": 110, "height": 32,
  "strokeColor": "#b45309",
  "backgroundColor": "#fef3c7",
  "strokeStyle": "dashed",
  "strokeWidth": 1,
  "roughness": 0,
  "roundness": {"type": 3}
}
```

```jsonc
{
  "type": "text",
  "x": 935, "y": 448,
  "text": "耗时: ~30ms",
  "fontSize": 14,
  "fontFamily": 5,
  "strokeColor": "#b45309"
}
```

---

## 5. 流向箭头 + 标签（Labeled Flow Arrow）

### 主前向流（实线）

```jsonc
{
  "id": "flow_enc_to_fusion",
  "type": "arrow",
  "x": 440, "y": 300,
  "width": 80, "height": 0,
  "points": [[0, 0], [80, 0]],
  "strokeColor": "#374151",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "endArrowhead": "arrow",
  "startBinding": {"elementId": "vision_encoder_box", "focus": 0, "gap": 5},
  "endBinding":   {"elementId": "fusion_box",         "focus": 0, "gap": 5}
}
```

### 残差/Skip 弧线（虚线）

```jsonc
{
  "type": "arrow",
  "points": [[0, 0], [60, -80], [200, -80], [260, 0]],
  "strokeStyle": "dashed",
  "strokeColor": "#9ca3af",
  "strokeWidth": 2,
  "endArrowhead": "arrow"
}
```

中段贴 `+` 标签表示残差相加。

### 反馈/Loss 箭头

```jsonc
{
  "type": "arrow",
  "strokeStyle": "dashed",
  "strokeColor": "#6b7280",
  "endArrowhead": "arrow"
}
```

---

## 6. Transformer Stack 重复标记

单块 + 右下贴 `×N`：

```jsonc
{
  "type": "text",
  "x": 850, "y": 380,
  "text": "× 12",
  "fontSize": 24,
  "fontFamily": 5,
  "strokeColor": "#dc2626",
  "textAlign": "center"
}
```

可选：在主块右下偏移 8px、10px 各画一个相同矩形（半透明），制造「堆叠」错觉。

---

## 7. 侧栏卡片（Sidebar Card）

无矩形容器，纯自由文本，多行内容。放图右侧或下方：

```jsonc
{
  "type": "text",
  "x": 1280, "y": 240,
  "text": "🔑 关键创新点\n\n✓ 双系统解耦\n  Slow + Fast 异频\n\n✓ Latent Query\n  跨模态对齐\n\n✓ Pixel Goal\n  端到端可微",
  "fontSize": 16,
  "fontFamily": 5,
  "strokeColor": "#1f2937",
  "textAlign": "left",
  "verticalAlign": "top",
  "lineHeight": 1.4
}
```

变体：
- 📊 性能指标
- 🚀 推理流程（Stage 1 → Stage 2 → Stage 3）
- ⚙️ 训练配置

---

## 8. 输入/输出椭圆（I/O Ellipse）

起止点用椭圆而非矩形：

```jsonc
{
  "type": "ellipse",
  "x": 80, "y": 280,
  "width": 140, "height": 80,
  "strokeColor": "#0891b2",
  "backgroundColor": "#cffafe",
  "fillStyle": "solid",
  "roundness": {"type": 2}
}
```

文本：`RGB-D\n图像流\n30 Hz`

---

## 9. 决策菱形（Decision Diamond）

CoT 分支、条件路由用：

```jsonc
{
  "type": "diamond",
  "x": 600, "y": 280,
  "width": 160, "height": 100,
  "strokeColor": "#b45309",
  "backgroundColor": "#fef3c7"
}
```

---

## 10. 完整模板：VLA 横向流水线（5 模块）

```
[I/O 椭圆] → [Vision Box] → [Fusion Box] → [LLM Box] → [Policy Box] → [Action 椭圆]
   x=80         x=300           x=560          x=820         x=1080         x=1340
```

每个矩形 width=200，箭头 width=60，整体在 (80–1480, 240–360) 区域。
上方留 200px 给标题，下方留 200px 给张量形状标注，右侧留 250px 给侧栏。

---

## 11. 完整模板：双系统纵向布局（System 1/2）

```
┌─────── System 2 (Slow, 2 Hz) ───────┐    y: 180–460
│  [Vision] → [LLM] → [Pixel Goal]    │
└──────────────────────────────────────┘
              ↓ pixel_goal
┌─────── System 1 (Fast, 30 Hz) ──────┐    y: 540–820
│  [RGB-D] → [Diffusion] → [Trajectory]│
└──────────────────────────────────────┘
              ↓ velocity
         [MPC / PID Controller]              y: 880
              ↓
         [Robot 30 Hz]                       y: 940
```

参考实例：`InternVLA-N1.md`。

---

## 12. ID 命名约定

便于跨片段引用、避免冲突：

- 模块盒：`mod_<name>` → `mod_vit`, `mod_llm`, `mod_diffusion`
- 文本标签：`txt_<name>` 或 `<modid>_text`
- 箭头：`arr_<from>_to_<to>` → `arr_vit_to_fusion`
- 子系统框：`sys_<name>` → `sys_slow`, `sys_fast`
- 标注：`anno_<id>` → `anno_shape_1`, `anno_latency_2`

---

## 13. Seed 命名空间（避免重复）

按区段分配 seed 范围（每个 element 的 `seed` 应不同）：
- 输入层：100000–199999
- 编码层：200000–299999
- 融合层：300000–399999
- 规划层：400000–499999
- 执行层：500000–599999
- 控制层：600000–699999
- 标注/侧栏：900000–999999
