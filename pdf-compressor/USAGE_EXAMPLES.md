# PDF Compressor Usage Examples

## Scenario 1: Automatic Compression on Large File

**User request:**
```
"Please analyze this research_paper.pdf"
```

**Workflow:**
1. Claude detects the PDF is 28MB (exceeds 10MB threshold)
2. Automatically runs compression:
   ```bash
   python scripts/compress_pdf.py research_paper.pdf -q ebook
   ```
3. Result: Compressed from 28MB to 9MB (68% reduction)
4. Proceeds to analyze the compressed file

**User sees:**
```
I notice the PDF is 28MB, which is quite large. Let me compress it first for better performance.

Compressing research_paper.pdf...
✓ Compressed from 28MB to 9MB (68% reduction)

Now analyzing the compressed PDF...
[analysis continues]
```

## Scenario 2: User Explicitly Requests Compression

**User request:**
```
"This presentation.pdf is too big for email. Can you compress it?"
```

**Workflow:**
1. Claude runs compression with default settings:
   ```bash
   python scripts/compress_pdf.py presentation.pdf -q ebook
   ```
2. Reports results to user

**User sees:**
```
I'll compress presentation.pdf for you.

Compressing with 'ebook' quality (balanced)...
✓ Original size: 15.2 MB
✓ Compressed size: 6.8 MB
✓ Reduction: 55.3%

The compressed file has been saved as presentation.pdf (original backed up as presentation_backup.pdf).
```

## Scenario 3: File Exceeds API Limit

**User request:**
```
"Extract all text from this_scanned_book.pdf"
```

**Workflow:**
1. Claude checks file size: 45MB (exceeds 32MB API limit)
2. Attempts aggressive compression:
   ```bash
   python scripts/compress_pdf.py this_scanned_book.pdf -q screen
   ```
3. Result: Compressed to 18MB
4. Proceeds with text extraction

**User sees:**
```
The PDF is 45MB, which exceeds the processing limit. Let me compress it first.

Applying aggressive compression (screen quality)...
✓ Compressed from 45MB to 18MB (60% reduction)

Now extracting text from the compressed PDF...
[extraction continues]
```

## Scenario 4: Read Failure Triggers Compression

**User request:**
```
"What's in large_document.pdf?"
```

**Workflow:**
1. Claude attempts to read the file
2. Read fails with "File too large" error
3. Automatically triggers compression:
   ```bash
   python scripts/compress_pdf.py large_document.pdf -q ebook
   ```
4. Retries reading the compressed file

**User sees:**
```
The PDF appears to be too large to read directly. Let me compress it first.

Compressing large_document.pdf...
✓ Compressed from 22MB to 8MB (64% reduction)

Now reading the compressed PDF...
[content summary]
```

## Scenario 5: Multiple Quality Levels

**User request:**
```
"Compress report.pdf but keep high quality"
```

**Workflow:**
1. Claude uses 'printer' quality for minimal compression:
   ```bash
   python scripts/compress_pdf.py report.pdf -q printer
   ```

**Alternative - Maximum compression:**
```
"Compress this as small as possible"
```

```bash
python scripts/compress_pdf.py report.pdf -q screen
```

## Scenario 6: Saving to Different File

**User request:**
```
"Create a compressed version of manual.pdf but keep the original"
```

**Workflow:**
```bash
python scripts/compress_pdf.py manual.pdf -o manual_compressed.pdf -q ebook
```

**User sees:**
```
Creating compressed version while preserving the original...

✓ Original: manual.pdf (12.5 MB)
✓ Compressed: manual_compressed.pdf (5.2 MB)
✓ Reduction: 58.4%

Both files are now available.
```

## Scenario 7: Batch Compression

**User request:**
```
"Compress all PDFs in this folder"
```

**Workflow:**
```bash
# For each PDF file
for file in *.pdf; do
    python scripts/compress_pdf.py "$file" -q ebook
done
```

## Scenario 8: Ghostscript Not Installed

**User request:**
```
"Compress this PDF"
```

**Workflow:**
1. Script checks for Ghostscript
2. Not found - provides installation instructions

**User sees:**
```
Ghostscript is not installed, which is required for PDF compression.

To install Ghostscript:

Windows:
1. Download from https://ghostscript.com/releases/gsdnld.html
2. Run the installer
3. Verify: gswin64c -version

macOS:
brew install ghostscript

Linux:
sudo apt-get install ghostscript

After installation, try the compression again.
```

## Scenario 9: Compression Doesn't Help

**User request:**
```
"Make this smaller: already_compressed.pdf"
```

**Workflow:**
1. Runs compression
2. Result: 10MB → 9.5MB (only 5% reduction)

**User sees:**
```
Compressing already_compressed.pdf...

✓ Original size: 10.0 MB
✓ Compressed size: 9.5 MB
✓ Reduction: 5.0%

This PDF appears to be already well-optimized. The compression achieved minimal size reduction. This is normal for PDFs that are already compressed or contain mostly text.
```

## Tips for Users

### Quality Selection Guide

- **screen (72 dpi)** - Use when file size is critical, images not important
  - Best for: Text documents, very large files
  - File size: Smallest

- **ebook (150 dpi)** - Balanced quality and size (recommended default)
  - Best for: General documents, presentations, reports
  - File size: Medium

- **printer (300 dpi)** - High quality images preserved
  - Best for: Documents for printing, image-heavy PDFs
  - File size: Larger

- **prepress (300 dpi)** - Print-ready quality
  - Best for: Professional printing, publishing
  - File size: Largest

### Compression Expectations

**Scanned documents:**
- Usually compress 60-80%
- Images are the main contributor to size

**Text-heavy PDFs:**
- Usually compress 30-50%
- Text compresses less than images

**Already compressed PDFs:**
- Usually compress 10-20%
- Limited gains possible

### When to Compress

- ✅ PDF > 10MB and need to process
- ✅ PDF > 32MB (API limit)
- ✅ Sharing via email
- ✅ Uploading to size-restricted platforms
- ❌ Already compressed PDFs
- ❌ Print-ready files (unless size critical)
