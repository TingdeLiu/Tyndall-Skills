# Ghostscript Installation Guide

The pdf-compressor skill requires Ghostscript to be installed on your system.

## Windows

1. Download Ghostscript from: https://ghostscript.com/releases/gsdnld.html
2. Choose the appropriate version:
   - **64-bit Windows**: Download "Ghostscript 10.x.x for Windows (64 bit)"
   - **32-bit Windows**: Download "Ghostscript 10.x.x for Windows (32 bit)"
3. Run the installer (.exe file)
4. Follow the installation wizard (default settings are fine)
5. Verify installation:
   ```cmd
   gswin64c -version
   ```

## macOS

Using Homebrew:
```bash
brew install ghostscript
```

Verify installation:
```bash
gs -version
```

## Linux

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ghostscript
```

### CentOS/RHEL
```bash
sudo yum install ghostscript
```

### Fedora
```bash
sudo dnf install ghostscript
```

Verify installation:
```bash
gs -version
```

## Troubleshooting

### Ghostscript not found after installation

**Windows:**
- Check if Ghostscript is in your PATH
- The installer usually adds it automatically
- If not, add the `bin` directory of your Ghostscript installation to your PATH (e.g. `C:\Program Files\gs\gs10.xx.x\bin`)

**macOS/Linux:**
- Ensure Homebrew or package manager completed successfully
- Try running `which gs` to find the installation path

### Permission issues

**Windows:**
- Run Command Prompt as Administrator
- Reinstall Ghostscript

**macOS/Linux:**
- Use `sudo` when running installation commands
- Check file permissions

## Testing Ghostscript

After installation, test with:

```bash
# Windows
gswin64c -version

# macOS/Linux
gs -version
```

You should see output like:
```
GPL Ghostscript 10.x.x (2024-xx-xx)
Copyright (C) 2024 Artifex Software, Inc.  All rights reserved.
```

## Alternative: Python-only compression

If you cannot install Ghostscript, consider using Python libraries like:
- `PyPDF2` (basic compression)
- `pikepdf` (better compression)

However, Ghostscript provides the best compression results.
