#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 PDF 中提取图片和表格
基于 TF-ID 模型自动检测和裁剪

环境要求: conda TF-ID
依赖: pdf2image, transformers, pillow
"""

import os
import sys
import json
import argparse
from pathlib import Path

# 设置标准输出为 UTF-8 编码（解决 Windows conda run 编码问题）
# line_buffering=True: 否则输出重定向到文件/管道时是块缓冲，
# 逐页处理的进度看不到，进程被中断时缓冲区内容还会整个丢失
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True
    )


def tf_id_detection(image, model, processor):
    """使用 TF-ID 模型检测图片和表格"""
    prompt = "<OD>"
    inputs = processor(text=prompt, images=image, return_tensors="pt")
    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        do_sample=False,
        num_beams=3
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    annotation = processor.post_process_generation(
        generated_text, task="<OD>", image_size=(image.width, image.height)
    )
    return annotation["<OD>"]


def extract_images_from_pdf(
    pdf_path,
    output_dir,
    model_id="yifeihu/TF-ID-base",
    extract_types=["figure", "table"],
    pages=None
):
    """
    从 PDF 提取图片和表格

    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        model_id: TF-ID 模型 ID
        extract_types: 要提取的类型列表，可选 "figure", "table"
        pages: 要提取的页面列表（从1开始），None表示提取所有页面
    """
    from pdf2image import convert_from_path, pdfinfo_from_path

    print(f"加载 PDF: {pdf_path}")
    total_pages = int(pdfinfo_from_path(str(pdf_path))["Pages"])
    print(f"PDF 页数: {total_pages}")
    if pages is not None:
        invalid_pages = [p for p in pages if p < 1 or p > total_pages]
        if not pages or invalid_pages:
            raise ValueError(f"无效页码: {invalid_pages or pages} (PDF 共 {total_pages} 页)")
        pages_to_process = sorted(set(pages))
        print(f"指定提取页面: {pages_to_process}")
    else:
        pages_to_process = list(range(1, total_pages + 1))
        print(f"警告: 未指定 --pages，将处理全部 {total_pages} 页；建议先选关键页。")

    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"输出目录非空，请为本次抽图选择新目录: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 页面确定后再加载模型
    from transformers import AutoProcessor, AutoModelForCausalLM

    print(f"加载模型: {model_id}")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        attn_implementation="eager"  # 解决Florence2的SDPA兼容性问题
    )
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

    # 提取计数器
    figure_count = 1
    table_count = 1

    # 索引数据
    index_data = {
        "pdf_path": str(pdf_path),
        "total_pages": total_pages,
        "target_pages": sorted(pages_to_process) if pages else "all",
        "extracted_items": []
    }

    print("\n" + "=" * 50)
    print("开始提取图片和表格")
    print("=" * 50)

    # 仅渲染目标页，一次持有一页，避免长论文的整篇图像占用内存。
    for page_num in pages_to_process:
        print(f"\n处理第 {page_num}/{total_pages} 页...")
        image = convert_from_path(str(pdf_path), first_page=page_num, last_page=page_num)[0]

        # 检测当前页的图表
        annotation = tf_id_detection(image, model, processor)

        # 遍历检测到的对象
        for i, (bbox, label) in enumerate(zip(annotation['bboxes'], annotation['labels'])):
            # 根据类型过滤
            if label not in extract_types:
                continue

            # 生成文件名
            if label == "figure":
                filename = f"figure_{figure_count:02d}.png"
                figure_count += 1
            elif label == "table":
                filename = f"table_{table_count:02d}.png"
                table_count += 1
            else:
                continue

            # 裁剪并保存
            x1, y1, x2, y2 = bbox
            cropped_image = image.crop((x1, y1, x2, y2))
            output_path = output_dir / filename
            cropped_image.save(output_path)

            # 记录索引
            index_data["extracted_items"].append({
                "filename": filename,
                "type": label,
                "page": page_num,
                "bbox": [float(x) for x in bbox]  # 转换为可序列化的类型
            })

            print(f"  ✓ 提取 {label}: {filename} (第 {page_num} 页)")

    # 保存索引文件
    index_path = output_dir / "image_index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    # 生成可读的 Markdown 索引
    md_index_path = output_dir / "image_index.md"
    with open(md_index_path, 'w', encoding='utf-8') as f:
        f.write(f"# 图片索引\n\n")
        f.write(f"PDF: `{Path(pdf_path).name}`\n\n")
        if pages:
            f.write(f"**已处理页面**: {len(pages_to_process)} / {total_pages} (目标: {sorted(pages_to_process)})\n\n")
        else:
            f.write(f"**已处理页面**: {total_pages} / {total_pages} (全部)\n\n")
        f.write(f"## 提取的图片 ({len(index_data['extracted_items'])} 个)\n\n")
        for item in index_data["extracted_items"]:
            f.write(f"- `{item['filename']}` - {item['type']} (第 {item['page']} 页)\n")

    print("\n" + "=" * 50)
    print(f"提取完成！")
    if pages:
        print(f"已处理页面: {len(pages_to_process)} 页 (共 {total_pages} 页)")
        print(f"目标页面: {sorted(pages_to_process)}")
    else:
        print(f"已处理页面: {total_pages} 页 (全部)")
    print(f"总计: {figure_count - 1} 个图片, {table_count - 1} 个表格")
    print(f"输出目录: {output_dir}")
    print(f"索引文件: {index_path}")
    print(f"Markdown 索引: {md_index_path}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="从 PDF 中提取图片和表格",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 只提取图片
  python extract_images.py paper.pdf --output ./images --type figure

  # 只提取表格
  python extract_images.py paper.pdf --output ./images --type table

  # 提取图片和表格
  python extract_images.py paper.pdf --output ./images --type figure table

  # 只提取特定页面的图片（页面2, 5, 10, 11）
  python extract_images.py paper.pdf --output ./images --type figure --pages 2,5,10,11

  # 提取页面范围（页面3-7和第10页）
  python extract_images.py paper.pdf --output ./images --type figure --pages 3-7,10
        """
    )

    parser.add_argument("pdf_path", help="PDF 文件路径")
    parser.add_argument(
        "--output", "-o",
        default="./images",
        help="输出目录 (默认: ./images)"
    )
    parser.add_argument(
        "--type", "-t",
        nargs="+",
        choices=["figure", "table"],
        default=["figure"],
        help="要提取的类型 (默认: figure)"
    )
    parser.add_argument(
        "--model",
        default="yifeihu/TF-ID-base",
        help="TF-ID 模型 ID (默认: yifeihu/TF-ID-base)"
    )
    parser.add_argument(
        "--pages", "-p",
        type=str,
        default=None,
        help="要提取的页面，用逗号分隔 (例如: 1,3,5 或 1-5,7,9-11)，不指定则提取所有页面"
    )

    args = parser.parse_args()

    pages = None
    if args.pages is not None:
        pages = set()
        try:
            for part in args.pages.split(','):
                bounds = part.strip().split('-')
                if len(bounds) == 1:
                    page = int(bounds[0])
                    if page < 1:
                        raise ValueError()
                    pages.add(page)
                elif len(bounds) == 2:
                    start, end = map(int, bounds)
                    if start < 1 or end < start:
                        raise ValueError()
                    pages.update(range(start, end + 1))
                else:
                    raise ValueError()
        except ValueError:
            parser.error("--pages 应为正整数页码或升序区间，例如 1,3-5")
        pages = sorted(pages)

    if not Path(args.pdf_path).is_file():
        parser.error(f"PDF 文件不存在: {args.pdf_path}")
    try:
        extract_images_from_pdf(
            pdf_path=args.pdf_path, output_dir=args.output,
            model_id=args.model, extract_types=args.type, pages=pages
        )
    except (ValueError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
