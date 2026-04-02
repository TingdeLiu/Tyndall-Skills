#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract figures and tables from PDF files.
Based on TF-ID model for automatic detection and cropping.

Requirements: conda TF-ID
Dependencies: pdf2image, transformers, pillow
"""

import os
import sys
import json
import argparse
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM

# Set standard output to UTF-8 encoding (resolves Windows conda run encoding issues)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def pdf_to_images(pdf_path):
    """Convert PDF to a list of images."""
    images = convert_from_path(pdf_path)
    return images


def tf_id_detection(image, model, processor):
    """Detect figures and tables in an image using TF-ID model."""
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
    Extract figures and tables from a PDF.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Output directory.
        model_id: TF-ID model ID.
        extract_types: List of types to extract, e.g., "figure", "table".
        pages: List of pages to extract (1-indexed), None for all pages.
    """
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load model
    print(f"Loading model: {model_id}")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        attn_implementation="eager"  # Resolves Florence2 SDPA compatibility issues
    )
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)

    # Convert PDF to images
    print(f"Loading PDF: {pdf_path}")
    images = pdf_to_images(pdf_path)
    print(f"PDF pages: {len(images)}")

    # Determine pages to process
    if pages:
        # Validate page range
        invalid_pages = [p for p in pages if p < 1 or p > len(images)]
        if invalid_pages:
            print(f"Warning: The following pages are out of range and will be ignored: {invalid_pages}")
        pages_to_process = [p for p in pages if 1 <= p <= len(images)]
        print(f"Target pages for extraction: {sorted(pages_to_process)}")
    else:
        pages_to_process = list(range(1, len(images) + 1))
        print(f"Extracting all pages")

    # Extraction counters
    figure_count = 1
    table_count = 1

    # Index data
    index_data = {
        "pdf_path": str(pdf_path),
        "total_pages": len(images),
        "target_pages": sorted(pages_to_process) if pages else "all",
        "extracted_items": []
    }

    print("\n" + "=" * 50)
    print("Starting extraction of figures and tables")
    print("=" * 50)

    # Iterate through each page
    for page_num, image in enumerate(images, start=1):
        # Skip pages not in the target list
        if page_num not in pages_to_process:
            continue

        print(f"\nProcessing page {page_num}/{len(images)}...")

        # Detect elements on current page
        annotation = tf_id_detection(image, model, processor)

        # Iterate through detected objects
        for i, (bbox, label) in enumerate(zip(annotation['bboxes'], annotation['labels'])):
            # Filter by type
            if label not in extract_types:
                continue

            # Generate filename
            if label == "figure":
                filename = f"figure_{figure_count:02d}.png"
                figure_count += 1
            elif label == "table":
                filename = f"table_{table_count:02d}.png"
                table_count += 1
            else:
                continue

            # Crop and save
            x1, y1, x2, y2 = bbox
            cropped_image = image.crop((x1, y1, x2, y2))
            output_path = output_dir / filename
            cropped_image.save(output_path)

            # Record index
            index_data["extracted_items"].append({
                "filename": filename,
                "type": label,
                "page": page_num,
                "bbox": [float(x) for x in bbox]  # Convert to serializable type
            })

            print(f"  ✓ Extracted {label}: {filename} (Page {page_num})")

    # Save index file
    index_path = output_dir / "image_index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    # Generate readable Markdown index
    md_index_path = output_dir / "image_index.md"
    with open(md_index_path, 'w', encoding='utf-8') as f:
        f.write(f"# Image Index\n\n")
        f.write(f"PDF: `{Path(pdf_path).name}`\n\n")
        if pages:
            f.write(f"**Processed pages**: {len(pages_to_process)} / {len(images)} (Target: {sorted(pages_to_process)})\n\n")
        else:
            f.write(f"**Processed pages**: {len(images)} / {len(images)} (All)\n\n")
        f.write(f"## Extracted Items ({len(index_data['extracted_items'])} total)\n\n")
        for item in index_data["extracted_items"]:
            f.write(f"- `{item['filename']}` - {item['type']} (Page {item['page']})\n")

    print("\n" + "=" * 50)
    print(f"Extraction completed!")
    if pages:
        print(f"Processed pages: {len(pages_to_process)} (Total: {len(images)})")
        print(f"Target pages: {sorted(pages_to_process)}")
    else:
        print(f"Processed pages: {len(images)} (All)")
    print(f"Total: {figure_count - 1} figures, {table_count - 1} tables")
    print(f"Output directory: {output_dir}")
    print(f"Index file: {index_path}")
    print(f"Markdown index: {md_index_path}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Extract figures and tables from PDF files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=\"\"\"
Examples:
  # Extract figures only
  python extract_images.py paper.pdf --output ./images --type figure

  # Extract tables only
  python extract_images.py paper.pdf --output ./images --type table

  # Extract both figures and tables
  python extract_images.py paper.pdf --output ./images --type figure table

  # Extract figures from specific pages (2, 5, 10, 11)
  python extract_images.py paper.pdf --output ./images --type figure --pages 2,5,10,11

  # Extract from a page range (3-7 and page 10)
  python extract_images.py paper.pdf --output ./images --type figure --pages 3-7,10
        \"\"\"
    )

    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--output", "-o",
        default="./images",
        help="Output directory (default: ./images)"
    )
    parser.add_argument(
        "--type", "-t",
        nargs="+",
        choices=["figure", "table"],
        default=["figure"],
        help="Types to extract (default: figure)"
    )
    parser.add_argument(
        "--model",
        default="yifeihu/TF-ID-base",
        help="TF-ID model ID (default: yifeihu/TF-ID-base)"
    )
    parser.add_argument(
        "--pages", "-p",
        type=str,
        default=None,
        help="Pages to extract, comma-separated (e.g., 1,3,5 or 1-5,7,9-11). Extracts all if not specified."
    )

    args = parser.parse_args()

    # Parse page parameters
    pages = None
    if args.pages:
        pages = []
        for part in args.pages.split(','):
            part = part.strip()
            if '-' in part:
                # Handle range, e.g., "3-5"
                try:
                    start, end = map(int, part.split('-'))
                    pages.extend(range(start, end + 1))
                except ValueError:
                    print(f"Warning: Could not parse page range '{part}', ignoring.")
            else:
                # Handle single page
                try:
                    pages.append(int(part))
                except ValueError:
                    print(f"Warning: Could not parse page '{part}', ignoring.")
        pages = sorted(set(pages))  # Deduplicate and sort

    # Check if PDF exists
    if not os.path.exists(args.pdf_path):
        print(f"Error: PDF file does not exist: {args.pdf_path}")
        return 1

    # Execute extraction
    extract_images_from_pdf(
        pdf_path=args.pdf_path,
        output_dir=args.output,
        model_id=args.model,
        extract_types=args.type,
        pages=pages
    )

    return 0


if __name__ == "__main__":
    exit(main())
