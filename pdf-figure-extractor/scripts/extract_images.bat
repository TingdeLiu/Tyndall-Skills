@echo off
REM ==========================================================
REM PDF Figure/Table Extractor (Windows)
REM Usage: extract_images.bat <pdf_path> [pages] [output_dir] [types]
REM   pages:      e.g. "2,5,10-11" or "" for all pages
REM   output_dir: default .\images
REM   types:      "figure", "table", or "figure table" (default: figure)
REM ==========================================================

chcp 65001 > nul
set PYTHONIOENCODING=utf-8

if "%~1"=="" (
    echo Error: PDF path is required
    echo Usage: extract_images.bat ^<pdf_path^> [pages] [output_dir] [types]
    exit /b 1
)

set PDF_PATH=%~1
set PAGES=%~2
set OUTPUT_DIR=%~3
set TYPES=%~4

if "%OUTPUT_DIR%"=="" set OUTPUT_DIR=.\images
if "%TYPES%"=="" set TYPES=figure

echo ==========================================================
echo Running PDF figure extraction...
echo PDF:    %PDF_PATH%
echo Pages:  %PAGES%
echo Output: %OUTPUT_DIR%
echo Types:  %TYPES%
echo ==========================================================

if "%PAGES%"=="" (
    python "%~dp0extract_images.py" "%PDF_PATH%" -o "%OUTPUT_DIR%" -t %TYPES%
) else (
    python "%~dp0extract_images.py" "%PDF_PATH%" -o "%OUTPUT_DIR%" -t %TYPES% --pages "%PAGES%"
)

if %errorlevel% neq 0 (
    echo.
    echo Error: Extraction failed
    exit /b %errorlevel%
)

echo.
echo ==========================================================
echo Extraction completed! Check %OUTPUT_DIR%\image_index.md
echo ==========================================================
