#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动处理论文总结中的图片：重命名和清理
基于 Markdown 文档中的 RENAME 注释自动重命名图片,并删除未使用的图片
"""

import os
import re
import sys
import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Set, List, Tuple

# =============================================================================
# 修复 Windows 编码问题
# =============================================================================
# 强制 stdout 和 stderr 使用 UTF-8 编码,解决 Windows 下中文输出问题
# line_buffering=True: 否则输出重定向到文件/管道时是块缓冲，
# 中断或异常退出会丢掉已打印的处理进度，事后无从判断做到哪一步
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', line_buffering=True
    )


def parse_rename_directives(markdown_content: str) -> List[Tuple[str, str]]:
    """
    解析 Markdown 中的 RENAME 指令

    格式: <!-- RENAME: old_name.png -> new_name.png -->

    Returns:
        List of (old_name, new_name) tuples
    """
    pattern = r'<!--\s*RENAME:\s*(\S+)\s*->\s*(\S+)\s*-->'
    matches = re.findall(pattern, markdown_content)
    return matches


def extract_image_references(markdown_content: str) -> Set[str]:
    """
    提取 Markdown 中引用的所有图片文件名

    支持的格式:
    - <img src="/images/xxx.png" ... />
    - <img src="xxx.png" ... />
    - ![](xxx.png)

    Returns:
        Set of image filenames
    """
    images = set()

    # 匹配 <img src="..." /> 格式
    img_pattern = r'<img\s+[^>]*src=["\']([^"\']+)["\']'
    for match in re.finditer(img_pattern, markdown_content):
        src = match.group(1)
        # 提取文件名（去掉路径）
        filename = Path(src).name
        images.add(filename)

    # 匹配 ![alt](path) 格式
    md_img_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
    for match in re.finditer(md_img_pattern, markdown_content):
        src = match.group(1)
        filename = Path(src).name
        images.add(filename)

    return images


def rename_images(
    rename_directives: List[Tuple[str, str]],
    image_dir: Path,
    dry_run: bool = False
) -> Tuple[Dict[str, str], Set[str]]:
    """
    根据重命名指令重命名图片

    Returns:
        (renamed_map, conflict_sources):
          renamed_map: old_name -> new_name for successful renames
          conflict_sources: 源图名集合，这些图因为目标已存在而未重命名，
                            必须加入保留集避免被当作"未使用"删掉
    """
    renamed = {}
    conflict_sources: Set[str] = set()

    for old_name, new_name in rename_directives:
        old_path = image_dir / old_name
        new_path = image_dir / new_name

        if not old_path.exists():
            print(f"  ⚠ 警告: 源文件不存在: {old_name}")
            continue

        if old_path.resolve() == new_path.resolve():
            renamed[old_name] = new_name
            continue

        if new_path.exists():
            print(f"  ✗ 错误: 目标文件已存在，跳过重命名（源图将被保留）: {old_name} -> {new_name}")
            conflict_sources.add(old_name)
            continue

        if dry_run:
            print(f"  [模拟] 重命名: {old_name} -> {new_name}")
        else:
            shutil.move(str(old_path), str(new_path))
            print(f"  ✓ 重命名: {old_name} -> {new_name}")

        renamed[old_name] = new_name

    return renamed, conflict_sources


def _rgba_digest(path: Path) -> str:
    """
    把图片解码成原始 RGBA 像素流后取哈希。

    用来判断转换前后是否逐像素完全一致 —— 直接比文件字节没有意义
    （编码方式本来就不同），必须比解码结果。
    """
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
         "-pix_fmt", "rgba", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0 or not proc.stdout:
        return ""
    return hashlib.sha256(proc.stdout).hexdigest()


def convert_images_to_webp(
    names: List[str],
    directory: Path,
    dry_run: bool = False
) -> Dict[str, str]:
    """
    把 PNG 转成无损 WebP，仅在「逐像素一致 且 体积更小」时才替换。

    只在解码后的 RGBA 像素相同且文件更小时替换，具体节省比例随图片而变。

    转换失败、像素不一致、或转完反而更大的，一律保留原 PNG。实践中会被
    拦下的典型情况：带 alpha 的 16-bit PNG（WebP 只有 8-bit，半透明像素
    混合结果会变），以及本身是 JPEG/WebP 却误用 .png 后缀的文件。

    Returns:
        png_name -> webp_name，只包含真正完成替换的条目
    """
    converted: Dict[str, str] = {}

    if not shutil.which("ffmpeg"):
        print("  ⚠ 未找到 ffmpeg，跳过 WebP 转换（图片保持 PNG）")
        return converted

    for name in names:
        if not name.lower().endswith(".png"):
            continue
        src = directory / name
        if not src.exists():
            continue
        dst = src.with_suffix(".webp")

        if dry_run:
            print(f"  [模拟] 转 WebP: {name} -> {dst.name}")
            converted[name] = dst.name
            continue

        if dst.exists():
            print(f"  ✗ 同名 .webp 已存在，跳过（保持 PNG）: {name}")
            continue

        enc = subprocess.run(
            ["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(src),
             "-c:v", "libwebp", "-lossless", "1", "-compression_level", "6",
             str(dst)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if enc.returncode != 0 or not dst.exists():
            print(f"  ✗ 编码失败，保持 PNG: {name}")
            dst.unlink(missing_ok=True)
            continue

        src_digest = _rgba_digest(src)
        if not src_digest or src_digest != _rgba_digest(dst):
            print(f"  ✗ 像素不一致，保持 PNG: {name}")
            dst.unlink(missing_ok=True)
            continue

        src_size, dst_size = src.stat().st_size, dst.stat().st_size
        if dst_size >= src_size:
            print(f"  ✗ 转换后未变小，保持 PNG: {name}")
            dst.unlink(missing_ok=True)
            continue

        src.unlink()
        converted[name] = dst.name
        print(f"  ✓ 转 WebP: {name} -> {dst.name}  (-{100 * (1 - dst_size / src_size):.0f}%)")

    return converted


def looks_like_archive_dir(image_dir: Path) -> bool:
    """
    判断 image_dir 是否疑似博客的最终归档目录（如 .../images/vln/）而非本次抽图的工作目录。

    判据：父目录名为 images。
      - 工作目录 new_paper/images  -> parent 是 new_paper，不命中
      - 归档目录 blog/images/vln   -> parent 是 images，命中

    命中说明 -d 很可能指错了，此时执行删除会清空整个 topic 目录的历史配图。
    """
    return image_dir.resolve().parent.name.lower() == "images"


def delete_unused_images(
    image_dir: Path,
    used_images: Set[str],
    dry_run: bool = False
) -> List[str]:
    """
    删除未被引用的图片

    Args:
        image_dir: 图片目录
        used_images: 被引用的图片文件名集合
        dry_run: 是否仅模拟运行

    Returns:
        List of deleted image filenames
    """
    deleted = []

    # 遍历图片目录中的所有文件
    for file_path in image_dir.glob("*"):
        if not file_path.is_file():
            continue

        # 跳过非图片文件
        if file_path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.tiff', '.gif', '.webp']:
            continue

        # 跳过索引文件
        if file_path.name in ['image_index.json', 'image_index.md']:
            continue

        # 检查是否被引用
        if file_path.name not in used_images:
            if dry_run:
                print(f"  [模拟] 删除未使用的图片: {file_path.name}")
            else:
                file_path.unlink()
                print(f"  ✓ 删除未使用的图片: {file_path.name}")
            deleted.append(file_path.name)

    return deleted


def remove_rename_comments(markdown_content: str) -> str:
    """移除 Markdown 中的 RENAME 注释"""
    pattern = r'<!--\s*RENAME:\s*\S+\s*->\s*\S+\s*-->\n?'
    cleaned_content = re.sub(pattern, '', markdown_content)
    return cleaned_content


def update_markdown_file(
    markdown_path: Path,
    renamed_map: Dict[str, str],
    remove_comments: bool = True
) -> None:
    """
    更新 Markdown 文件：
    1. 更新图片引用（如果有重命名）
    2. 移除 RENAME 注释

    Args:
        markdown_path: Markdown 文件路径
        renamed_map: old_name -> new_name 映射
        remove_comments: 是否移除 RENAME 注释
    """
    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新图片引用
    for old_name, new_name in renamed_map.items():
        # 替换 src 中的文件名（保留路径部分）
        content = re.sub(
            rf'(src=["\'][^"\']*/)?' + re.escape(old_name),
            lambda m: (m.group(1) or '') + new_name,
            content
        )

    # 移除 RENAME 注释
    if remove_comments:
        content = remove_rename_comments(content)

    # 写回文件
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(content)


def process_paper_summary(
    markdown_path: str,
    image_dir: str,
    dry_run: bool = False,
    keep_comments: bool = False,
    output_dir: str = None,
    md_output_dir: str = None,
    allow_archive_dir: bool = False,
    force_delete: bool = False,
    no_webp: bool = False
) -> None:
    """
    处理论文总结文档和图片

    Args:
        markdown_path: Markdown 文件路径
        image_dir: 图片目录路径
        dry_run: 是否仅模拟运行（不实际修改文件）
        keep_comments: 是否保留 RENAME 注释
        output_dir: 最终图片输出目录（可选）
        md_output_dir: 最终 Markdown 输出目录（可选）
        allow_archive_dir: 允许 image_dir 是归档目录（默认拒绝，防止清空历史配图）
        force_delete: 缺少 image_index.json 时仍执行删除（默认跳过）
        no_webp: 跳过无损 WebP 转换，图片保持 PNG
    """
    markdown_path = Path(markdown_path)
    image_dir = Path(image_dir)
    if output_dir:
        output_dir = Path(output_dir)
    if md_output_dir:
        md_output_dir = Path(md_output_dir)

    # 检查文件是否存在
    if not markdown_path.exists():
        raise SystemExit(f"错误: Markdown 文件不存在: {markdown_path}")

    if not image_dir.exists():
        raise SystemExit(f"错误: 图片目录不存在: {image_dir}")

    # 守卫: 在做任何修改之前拦截指错的 image_dir。
    # 若指向了博客的最终归档目录，后续的"删除未使用图片"会清空该 topic 下
    # 所有历史论文的配图，且无法恢复。
    if looks_like_archive_dir(image_dir) and not allow_archive_dir:
        print("=" * 60)
        print("已中止: --image-dir 疑似指向最终归档目录，而非本次抽图的工作目录")
        print("=" * 60)
        print(f"  传入路径: {image_dir.resolve()}")
        print(f"  判定依据: 其父目录名为 'images'")
        print()
        print("  若继续执行，该目录下所有未被本篇 MD 引用的图片都会被删除，")
        print("  包括其他论文的历史配图。")
        print()
        print("  正确用法: -d 应指向本次抽图独立的工作目录，")
        print("            由 -o 负责把重命名后的图片移入归档目录。")
        print("  确认无误要继续: 追加 --allow-archive-dir")
        print("=" * 60)
        raise SystemExit(1)

    print("=" * 60)
    print("论文图片自动处理工具")
    print("=" * 60)
    print(f"Markdown 文件: {markdown_path}")
    print(f"图片目录: {image_dir}")
    if dry_run:
        print("⚠ 模拟运行模式（不会实际修改文件）")
    print()

    # 读取 Markdown 内容
    with open(markdown_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # 1. 解析重命名指令
    print("步骤 1: 解析重命名指令")
    print("-" * 60)
    rename_directives = parse_rename_directives(markdown_content)

    # 在任何重命名、移动或清理前检查目标，避免改动已有的归档图片。
    new_names = set()
    for old_name, new_name in rename_directives:
        for name in (old_name, new_name):
            if name in (".", "..") or any(c in name for c in '/\\:'):
                raise SystemExit(f"错误: RENAME 只接受文件名，不接受路径: {name}")
        if new_name in new_names:
            raise SystemExit(f"错误: 重复的目标文件名: {new_name}")
        new_names.add(new_name)
        source = image_dir / old_name
        local_target = image_dir / new_name
        if not source.is_file():
            raise SystemExit(f"错误: 重命名源文件不存在: {old_name}")
        if old_name != new_name and local_target.exists():
            raise SystemExit(f"错误: 目标文件已存在: {local_target}")
        if output_dir and output_dir.resolve() != image_dir.resolve():
            final_target = output_dir / new_name
            if final_target.exists():
                raise SystemExit(f"错误: 归档目录有同名文件: {final_target}")
    if md_output_dir:
        final_md = md_output_dir / markdown_path.name
        if final_md.exists() and final_md.resolve() != markdown_path.resolve():
            raise SystemExit(f"错误: 最终 Markdown 已存在: {final_md}")

    if rename_directives:
        print(f"找到 {len(rename_directives)} 个重命名指令:")
        for old, new in rename_directives:
            print(f"  - {old} -> {new}")
    else:
        print("未找到重命名指令")
    print()

    # 2. 执行重命名
    print("步骤 2: 重命名图片")
    print("-" * 60)
    renamed_map, conflict_sources = rename_images(rename_directives, image_dir, dry_run)
    if not renamed_map:
        print("  无图片需要重命名")
    if conflict_sources:
        print(f"  ⚠ {len(conflict_sources)} 个源图因目标重名未被重命名，将保留在源目录")
    print()

    # 3. 移动图片到最终输出目录（如果指定）
    # 使用 move 而不是 copy，避免源目录残留已用图片造成长期堆积
    if output_dir and renamed_map:
        print("步骤 3: 移动图片到最终输出目录")
        print("-" * 60)
        if not output_dir.exists():
            if dry_run:
                print(f"  [模拟] 创建输出目录: {output_dir}")
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"  ✓ 创建输出目录: {output_dir}")

        for new_name in renamed_map.values():
            src = image_dir / new_name
            dst = output_dir / new_name
            if src.exists():
                if dry_run:
                    print(f"  [模拟] 移动: {new_name} -> {output_dir}")
                elif dst.exists():
                    print(f"  ✗ 错误: 目标目录已存在同名文件，跳过: {new_name}")
                else:
                    shutil.move(str(src), str(dst))
                    print(f"  ✓ 移动: {new_name} -> {output_dir}")
        print()

    # 3.5 转为无损 WebP，与博客其余配图保持同一格式
    # 放在移动之后、提取引用之前，此时图片已在最终位置。
    #
    # 注意映射的键取「重命名后」的名字：markdown 的 src 里写的就是重命名后的
    # 文件名（RENAME 注释只声明 figure_NN -> 新名，src 直接写新名），所以要让
    # 引用改写生效，必须以新名为键追加一条 xxx.png -> xxx.webp，而不是去改
    # renamed_map 里那条 figure_NN.png -> xxx.png 的值。
    if renamed_map and not no_webp:
        print("步骤 3.5: 转换为无损 WebP")
        print("-" * 60)
        webp_map = convert_images_to_webp(
            list(renamed_map.values()),
            output_dir if output_dir else image_dir,
            dry_run
        )
        if webp_map:
            renamed_map.update(webp_map)
        else:
            print("  无图片被转换")
        print()

    # 4. 提取图片引用（考虑已重命名的）
    print("步骤 4: 提取图片引用")
    print("-" * 60)

    # 更新 markdown_content 中的引用（用于提取）
    temp_content = markdown_content
    for old_name, new_name in renamed_map.items():
        temp_content = re.sub(
            rf'(src=["\'][^"\']*/)?' + re.escape(old_name),
            lambda m: (m.group(1) or '') + new_name,
            temp_content
        )

    used_images = extract_image_references(temp_content)

    if used_images:
        print(f"文档中引用了 {len(used_images)} 个图片:")
        for img in sorted(used_images):
            print(f"  - {img}")
    else:
        print("文档中未引用任何图片")
    print()

    # 5. 删除未使用的图片（冲突未重命名的源图加入保留集，避免被误删）
    print("步骤 5: 删除未使用的图片")
    print("-" * 60)
    preserved = used_images | conflict_sources
    deleted = []

    # image_index.json 由 extract_images.py 生成，是"这是本次抽图工作目录"的凭证。
    # 缺失时目录来源不明（手动放图的 Manual Fallback、或重复运行），一律不删。
    has_index = (image_dir / "image_index.json").exists()
    if not has_index and not force_delete:
        print("  ⚠ 跳过删除: 目录中没有 image_index.json")
        print("    该文件由 extract_images.py 生成，缺失说明这不是本次抽图的工作目录")
        print("    （手动提供图片、或脚本重复运行时属正常情况）")
        print("    确需删除未引用图片: 追加 --force-delete")
    else:
        deleted = delete_unused_images(image_dir, preserved, dry_run)
        if not deleted:
            print("  无未使用的图片需要删除")
    print()

    # 6. 更新 Markdown 文件
    if not dry_run and (renamed_map or not keep_comments):
        print("步骤 6: 更新 Markdown 文件")
        print("-" * 60)
        update_markdown_file(
            markdown_path,
            renamed_map,
            remove_comments=not keep_comments
        )
        print("  ✓ Markdown 文件已更新")
        print()

    # 7. 清理 image_index 文件
    if not dry_run:
        print("步骤 7: 清理临时索引文件")
        print("-" * 60)
        index_files = [
            image_dir / "image_index.json",
            image_dir / "image_index.md"
        ]
        cleaned = 0
        for index_file in index_files:
            if index_file.exists():
                try:
                    index_file.unlink()
                    print(f"  ✓ 删除: {index_file.name}")
                    cleaned += 1
                except Exception as e:
                    print(f"  ✗ 删除失败: {index_file.name} - {e}")
        if cleaned == 0:
            print("  无临时索引文件需要清理")
        print()

    # 8. 移动 Markdown 文件到最终目录
    if not dry_run and md_output_dir:
        print("步骤 8: 移动 Markdown 文件")
        print("-" * 60)
        if not md_output_dir.exists():
            md_output_dir.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ 创建目录: {md_output_dir}")

        new_md_path = md_output_dir / markdown_path.name
        try:
            shutil.move(str(markdown_path), str(new_md_path))
            print(f"  ✓ 移动文件到: {new_md_path}")
            # 更新路径以便总结报告正确的最终路径
            markdown_path = new_md_path
        except Exception as e:
            print(f"  ✗ 移动文件失败: {e}")
        print()


    # 总结
    print("=" * 60)
    print("处理完成！")
    print(f"  - 最终 Markdown: {markdown_path}")
    print(f"  - 重命名: {len(renamed_map)} 个")
    print(f"  - 删除: {len(deleted)} 个")
    print(f"  - 保留: {len(used_images)} 个")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="自动处理论文总结中的图片：重命名和清理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  python process_images.py summary.md --image-dir ./images

  # 指定最终图片和Markdown输出目录
  python process_images.py summary.md -d ./images -o outputs/paper/images --md-output-dir outputs/paper

  # 模拟运行（不实际修改文件）
  python process_images.py summary.md -d ./images -n

  # 保留 RENAME 注释
  python process_images.py summary.md -d ./images -k

安全守卫:
  - -d 若指向最终归档目录（父目录名为 images，如 .../images/vln），直接中止，
    避免清空该 topic 下其他论文的历史配图；确认无误可加 --allow-archive-dir
  - -d 目录中缺少 image_index.json 时跳过删除步骤（手动放图或重复运行的情况），
    确需删除可加 --force-delete
        """
    )

    parser.add_argument(
        "markdown_path",
        help="Markdown 总结文件路径"
    )
    parser.add_argument(
        "--image-dir", "-d",
        required=True,
        help="图片目录路径"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="模拟运行，不实际修改文件"
    )
    parser.add_argument(
        "--keep-comments", "-k",
        action="store_true",
        help="保留 RENAME 注释"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="最终图片输出目录（可选，如未指定则保留在原目录）"
    )
    parser.add_argument(
        "--md-output-dir",
        help="最终 Markdown 输出目录（可选，如果指定，文件将被移动）"
    )
    parser.add_argument(
        "--allow-archive-dir",
        action="store_true",
        help="允许 --image-dir 指向归档目录（默认拒绝，防止误删历史配图）"
    )
    parser.add_argument(
        "--force-delete",
        action="store_true",
        help="即使目录中没有 image_index.json 也执行删除步骤"
    )
    parser.add_argument(
        "--no-webp",
        action="store_true",
        help="跳过无损 WebP 转换，图片保持 PNG（默认会转换）"
    )

    args = parser.parse_args()

    process_paper_summary(
        markdown_path=args.markdown_path,
        image_dir=args.image_dir,
        dry_run=args.dry_run,
        keep_comments=args.keep_comments,
        output_dir=args.output_dir,
        md_output_dir=args.md_output_dir,
        allow_archive_dir=args.allow_archive_dir,
        force_delete=args.force_delete,
        no_webp=args.no_webp
    )


if __name__ == "__main__":
    main()
