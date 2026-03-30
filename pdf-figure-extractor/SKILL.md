---
name: pdf-figure-extractor
description: Extract figures and/or tables from PDF files using the TF-ID model (Florence2-based object detection). Outputs cropped images with a Markdown index. Use when user wants to extract figures, tables, or images from a PDF file — e.g., "extract all figures from this PDF", "get the tables from paper.pdf", "extract images from pages 3-7". Requires conda TF-ID environment with pdf2image, transformers, pillow.
---

# PDF Figure Extractor

Extract figures and tables from PDF files using TF-ID (Florence2-based) object detection.

## Environment

- Conda env: `TF-ID`
- Dependencies: `pdf2image`, `transformers`, `pillow`

## Usage

### Windows (recommended — avoids encoding issues)

```bash
cmd //c "pdf-figure-extractor\scripts\extract_images.bat" "<pdf_path>" "<pages>"
```

Examples:
```bash
# Extract all pages
cmd //c "pdf-figure-extractor\scripts\extract_images.bat" "paper.pdf" ""

# Extract specific pages
cmd //c "pdf-figure-extractor\scripts\extract_images.bat" "paper.pdf" "2,5,10,11"

# Extract page range
cmd //c "pdf-figure-extractor\scripts\extract_images.bat" "paper.pdf" "3-7,10"
```

### Direct Python (cross-platform)

```bash
conda run -n TF-ID python pdf-figure-extractor/scripts/extract_images.py <pdf_path> -o <output_dir> -t figure table --pages <pages>
```

## Parameters

| Flag | Description | Default |
|------|-------------|---------|
| `pdf_path` | Input PDF file | required |
| `-o / --output` | Output directory | `./images` |
| `-t / --type` | `figure`, `table`, or both | `figure` |
| `--pages / -p` | Pages to process, e.g. `1,3,5` or `2-6,10` | all pages |
| `--model` | TF-ID model ID | `yifeihu/TF-ID-base` |

## Output

- `<output_dir>/figure_01.png`, `figure_02.png`, ... — cropped figures
- `<output_dir>/table_01.png`, `table_02.png`, ... — cropped tables (if requested)
- `<output_dir>/image_index.json` — machine-readable index
- `<output_dir>/image_index.md` — human-readable index with page numbers

## Workflow

1. Ask user for PDF path (and optionally: output dir, types to extract, page range)
2. Run extraction via bat script (Windows) or `conda run` (other OS)
3. Read `image_index.md` to report what was extracted
4. Show user the output directory and extracted items summary

## Notes

- The bat script hardcodes output to `.\images` relative to the skill directory; for custom output dir use direct Python invocation
- When page list is unknown, extract all pages first, then let user filter
- TF-ID detects layout elements — it works best on typical academic paper layouts
- For large PDFs, specify target pages to save time and memory
