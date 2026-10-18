# 论文精读与配图归档：快速开始

适合需要阅读 PDF、解释方法细节、引用原图并保留本地笔记的场景。
只需要标题或链接的快速摘要，可用同仓库的 `paper-summary-simple`。

## 安装

将整个 `paper-summary/` 目录复制到 AI 工具的技能目录，例如 Claude Code 的
`~/.claude/skills/`。下面的终端命令从这个技能目录执行。

抽图推荐使用独立环境。Poppler 必须显式安装，创建 conda 环境不会自动带上它：

```bash
conda create -n paper-summary python=3.10 -y
conda activate paper-summary
conda install -c conda-forge poppler -y
python -m pip install -r scripts/requirements.txt
pdfinfo -v
```

不用 conda 也可以：在 Python 虚拟环境安装同一份依赖，并通过系统包管理器安装
Poppler，让 `pdfinfo` 和 `pdftoppm` 出现在 PATH。Windows 下载入口见
[Poppler for Windows](https://github.com/oschwartz10612/poppler-windows)。
PyTorch 的 GPU 构建按[官方安装说明](https://pytorch.org/get-started/locally/)选择；
CPU 也能运行当前脚本。首次抽图会下载 [TF-ID 模型](https://huggingface.co/yifeihu/TF-ID-base)，
需要网络及模型缓存空间。兼容性依赖固定为 `transformers==4.45.0`；不要与其他项目共用环境。

`process_images.py` 使用 Python 标准库，可以独立运行。可选安装 FFmpeg 以尝试
无损 WebP 转换；没有 FFmpeg 或使用 `--no-webp` 时保留 PNG。

## 直接让 AI 执行

> 请精读这份 PDF，生成带关键原图的中文摘要，放到我指定的笔记目录。
> 先解释输入、模块处理和输出，区分论文结果与个人判断。

AI 负责读论文、决定抽哪些页、解释方法与核对结果。脚本负责抽图和整理文件，
不会独立生成摘要，也不会上传博客。

## 手动操作示例

将一篇 PDF 放到当前目录，命名为 `paper.pdf`。从实体 PDF 的第 1 页开始计数，
不要使用论文页脚的印刷页码。

```bash
python scripts/extract_images.py paper.pdf -o work/paper/extracted -t figure --pages 1,3,6
```

阅读 `work/paper/extracted/image_index.md`，并查看抽出的图片。然后编写
`work/paper/summary.md`，例如下面的引用（文件名以实际抽出的图为准）：

```html
<div align="center">
  <img src="images/Paper-method.png" width="100%" />
<!-- RENAME: figure_01.png -> Paper-method.png -->
<figcaption>方法概览：替换为对原图的准确说明。</figcaption>
</div>
```

先预演，再执行：

```bash
python scripts/process_images.py work/paper/summary.md -d work/paper/extracted -o outputs/paper/images --md-output-dir outputs/paper --dry-run
python scripts/process_images.py work/paper/summary.md -d work/paper/extracted -o outputs/paper/images --md-output-dir outputs/paper
```

最终结果为 `outputs/paper/summary.md` 和 `outputs/paper/images/`。
脚本改图片文件名，不改引用的目录前缀，因此摘要应提前使用最终位置的相对路径。
最后打开 Markdown，确认图、公式和 Mermaid 均可正常查看。

## 图片清理的范围

`-d` 使用本篇专用的抽图工作目录；`-o` 才是最终归档目录。
脚本可能删除工作目录内未被引用的图片。它默认拒绝父目录名为 `images` 的归档路径，
并在缺少 `image_index.json` 时跳过图片删除；这些守卫不能替代正确的目录选择。
手动提供图片时直接复制到最终目录，不需要运行清理。

完整参数见 [脚本说明](scripts/README.md)，摘要写法见 [SKILL.md](SKILL.md)。
