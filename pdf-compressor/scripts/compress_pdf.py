#!/usr/bin/env python3
"""
PDF Compression Script using Ghostscript

Compresses PDF files while maintaining acceptable quality.
Supports multiple compression levels and automatic fallback.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


class PDFCompressor:
    """Handles PDF compression using Ghostscript"""

    # Ghostscript settings for different compression levels
    COMPRESSION_SETTINGS = {
        'screen': {
            'desc': 'Low quality (72 dpi) - smallest file size',
            'dpi': 72
        },
        'ebook': {
            'desc': 'Medium quality (150 dpi) - balanced',
            'dpi': 150
        },
        'printer': {
            'desc': 'High quality (300 dpi) - larger file',
            'dpi': 300
        },
        'prepress': {
            'desc': 'Very high quality (300 dpi) - print ready',
            'dpi': 300
        }
    }

    def __init__(self):
        self.gs_path = self._find_ghostscript()

    def _find_ghostscript(self):
        """Find Ghostscript executable on the system"""
        # Common Ghostscript command names
        gs_commands = ['gswin64c', 'gswin32c', 'gs']

        for cmd in gs_commands:
            if shutil.which(cmd):
                return cmd

        # Check common installation paths on Windows
        if sys.platform == 'win32':
            common_paths = [
                r'C:\Program Files\gs\gs*\bin\gswin64c.exe',
                r'C:\Program Files (x86)\gs\gs*\bin\gswin32c.exe',
            ]
            import glob
            for pattern in common_paths:
                matches = glob.glob(pattern)
                if matches:
                    return matches[0]

        return None

    def is_available(self):
        """Check if Ghostscript is available"""
        return self.gs_path is not None

    def get_file_size_mb(self, file_path):
        """Get file size in MB"""
        return os.path.getsize(file_path) / (1024 * 1024)

    def compress(self, input_path, output_path=None, quality='ebook', backup=True):
        """
        Compress a PDF file

        Args:
            input_path: Path to input PDF
            output_path: Path to output PDF (None = overwrite input)
            quality: Compression quality level (screen/ebook/printer/prepress)
            backup: Whether to backup original file before overwriting

        Returns:
            dict with compression results
        """
        input_path = Path(input_path).resolve()

        if not input_path.exists():
            return {'success': False, 'error': f'Input file not found: {input_path}'}

        if not self.is_available():
            return {'success': False, 'error': 'Ghostscript not found. Please install Ghostscript.'}

        if quality not in self.COMPRESSION_SETTINGS:
            return {'success': False, 'error': f'Invalid quality level: {quality}'}

        # Get original file size
        original_size = self.get_file_size_mb(input_path)

        # Determine output path
        if output_path is None:
            # Overwrite mode: compress to temp file first
            temp_output = input_path.parent / f"{input_path.stem}_temp_compressed.pdf"
            overwrite = True
        else:
            temp_output = Path(output_path).resolve()
            overwrite = False

        # Build Ghostscript command
        gs_command = [
            self.gs_path,
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS=/{quality}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={temp_output}',
            str(input_path)
        ]

        try:
            # Run Ghostscript
            result = subprocess.run(
                gs_command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Ghostscript error: {result.stderr}'
                }

            # Check if output was created
            if not temp_output.exists():
                return {
                    'success': False,
                    'error': 'Compression failed: output file not created'
                }

            # Get compressed file size
            compressed_size = self.get_file_size_mb(temp_output)

            # Handle overwrite mode
            if overwrite:
                # Backup original if requested
                if backup:
                    backup_path = input_path.parent / f"{input_path.stem}_backup.pdf"
                    shutil.copy2(input_path, backup_path)

                # Replace original with compressed version
                shutil.move(str(temp_output), str(input_path))
                final_path = input_path
            else:
                final_path = temp_output

            # Calculate compression ratio
            compression_ratio = (1 - compressed_size / original_size) * 100

            return {
                'success': True,
                'original_size_mb': round(original_size, 2),
                'compressed_size_mb': round(compressed_size, 2),
                'compression_ratio': round(compression_ratio, 1),
                'output_path': str(final_path),
                'quality': quality
            }

        except subprocess.TimeoutExpired:
            if temp_output.exists():
                temp_output.unlink()
            return {
                'success': False,
                'error': 'Compression timeout (file too large or complex)'
            }
        except Exception as e:
            if temp_output.exists():
                temp_output.unlink()
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Compress PDF files using Ghostscript',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quality levels:
  screen    - Low quality (72 dpi) - smallest file size
  ebook     - Medium quality (150 dpi) - balanced (default)
  printer   - High quality (300 dpi) - larger file
  prepress  - Very high quality (300 dpi) - print ready

Examples:
  python compress_pdf.py input.pdf
  python compress_pdf.py input.pdf -o output.pdf
  python compress_pdf.py input.pdf -q screen
  python compress_pdf.py input.pdf --no-backup
        """
    )

    parser.add_argument('input', help='Input PDF file')
    parser.add_argument('-o', '--output', help='Output PDF file (default: overwrite input)')
    parser.add_argument('-q', '--quality', default='ebook',
                       choices=['screen', 'ebook', 'printer', 'prepress'],
                       help='Compression quality (default: ebook)')
    parser.add_argument('--no-backup', action='store_true',
                       help='Do not backup original file when overwriting')

    args = parser.parse_args()

    # Create compressor
    compressor = PDFCompressor()

    if not compressor.is_available():
        print("ERROR: Ghostscript not found!")
        print("\nPlease install Ghostscript:")
        print("  Windows: https://ghostscript.com/releases/gsdnld.html")
        print("  Mac: brew install ghostscript")
        print("  Linux: sudo apt-get install ghostscript")
        sys.exit(1)

    # Compress
    print(f"Compressing: {args.input}")
    print(f"Quality: {args.quality} ({PDFCompressor.COMPRESSION_SETTINGS[args.quality]['desc']})")
    print()

    result = compressor.compress(
        args.input,
        args.output,
        args.quality,
        backup=not args.no_backup
    )

    if result['success']:
        print("SUCCESS!")
        print(f"Original size: {result['original_size_mb']} MB")
        print(f"Compressed size: {result['compressed_size_mb']} MB")
        print(f"Compression: {result['compression_ratio']}% reduction")
        print(f"Output: {result['output_path']}")
    else:
        print(f"FAILED: {result['error']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
