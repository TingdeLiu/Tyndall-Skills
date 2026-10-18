# 论文图片处理脚本

环境安装和完整示例见 [QUICKSTART.md](../QUICKSTART.md)。两个脚本职责不同：
抽图脚本需要模型环境，归档脚本只使用 Python 标准库。

## extract_images.py

```bash
python scripts/extract_images.py paper.pdf -o work/paper/extracted -t figure table --pages 1,3-5
python scripts/extract_images.py --help
```

- `--pages` / `-p`：实体 PDF 页码，从 1 开始，支持逗号及区间；先读 PDF 选关键页。
- `--type` / `-t`：`figure`、`table` 或两者；默认为 `figure`。
- `--model`：默认 `yifeihu/TF-ID-base`，可换成兼容的 TF-ID 模型。
- `--output` / `-o`：本篇专用的工作目录，不要复用有其他论文图片的目录。
- 输出：裁剪图片、`image_index.json` 和 `image_index.md`。
- 只渲染指定页；无效页码会报错，非空输出目录会被拒绝，防止覆盖上次抽图。

检测框需要人工核对，确认没有裁掉坐标、图例或子图。图像检测不负责翻译图中文字。

## process_images.py

```bash
python scripts/process_images.py work/paper/summary.md -d work/paper/extracted -o outputs/paper/images --md-output-dir outputs/paper --dry-run
python scripts/process_images.py --help
```

根据 `<!-- RENAME: figure_01.png -> Paper-method.png -->` 重命名图片，
移动到 `-o`，清理工作目录内未使用图片，更新引用文件名，移除 RENAME 注释和抽图索引，
最后将 Markdown 移到 `--md-output-dir`。不自动改变引用的目录前缀。

- `--dry-run`：预演，不改文件；核对后去掉此参数再运行。
- `--no-webp`：保留 PNG。默认有 FFmpeg 时尝试无损 WebP，仅在像素完全一致且文件更小时替换。
- `--keep-comments`：保留重命名注释。
- `--allow-archive-dir`：覆盖归档路径守卫，仅在确认输入目录用途后使用。
- `--force-delete`：缺少索引也删除未用图片，常规流程不需要。

同名目标图片或 Markdown 会在任何修改前中止处理。RENAME 只接受文件名，不能包含目录路径。
文件名应加论文前缀。
不要在整个历史图片库上运行清理，也不要把不同论文放入同一抽图工作目录。

## 常见问题

- 找不到 `pdfinfo` / `pdftoppm`：安装 Poppler 并让其 bin 目录进入当前终端 PATH。
- Florence2 / GenerationMixin 兼容性问题：使用独立环境和随包提供的依赖版本。
- 中文输出异常：Windows 设置 `PYTHONUTF8=1`，再用正确环境的 Python 运行。
- 模型无法下载：检查网络与 Hugging Face 缓存；可以手动提供原图继续写摘要。

## 离线验证

在技能目录运行 `python -m unittest discover -s tests -v`，无需下载模型。
覆盖归档后引用、预演不写文件、同名内容保护、路径越界拒绝、删除守卫和指定页渲染。
渲染与检测测试使用替身，真实模型的检测效果需要在所选论文上检查。
