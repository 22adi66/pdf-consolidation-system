# eCRF PDF Consolidation Tool - Streamlit App

## Overview
Web application for consolidating multiple versions of eCRF PDFs into a single document with version tracking and bookmark preservation.

## Features
- 📤 **ZIP File Upload**: Upload a compressed folder containing multiple PDF versions
- 🔄 **Automatic Processing**: Automatic version detection and sequential comparison
- 📑 **Bookmark Preservation**: Maintains all bookmarks including duplicates
- 🏷️ **Version Tracking**: Creates version children for modified sections
- 📥 **Easy Download**: One-click download of consolidated PDF

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify Installation**
   ```bash
   python -c "import streamlit; import PyPDF2; print('All dependencies installed!')"
   ```

## Running the Application

### Start the Streamlit Server

```bash
streamlit run app.py
```

The application will automatically open in your default web browser at `http://localhost:8501`

### Alternative: Specify Port

```bash
streamlit run app.py --server.port 8080
```

### Run in Background (Windows)

```powershell
Start-Process streamlit -ArgumentList "run app.py" -WindowStyle Hidden
```

## Usage Guide

### Step 1: Prepare Your Files

1. Collect all versions of your eCRF PDFs
2. Ensure filenames contain version numbers in format: `x-x-x` or `x.x.x`
   - Example: `study-design-1-0-16.pdf`
   - Example: `ecrf-2-0-1.pdf`
3. Place all PDFs in a folder
4. Create a ZIP archive of the folder

### Step 2: Upload and Process

1. Open the web application (it will open automatically when you run streamlit)
2. Click "Browse files" or drag-and-drop your ZIP file
3. Click "🚀 Process PDFs" button
4. Wait for processing to complete (progress will be shown)

### Step 3: Download Result

1. Once processing is complete, you'll see a summary with statistics
2. Click "📥 Download Consolidated PDF" button
3. The file will be downloaded with timestamp: `consolidated_ecrf_YYYYMMDD_HHMMSS.pdf`

## Features Explained

### Version Detection
- Automatically extracts version numbers from filenames
- Sorts PDFs by version (oldest to newest)
- Uses oldest version as base

### Bookmark Handling
- **Duplicate Bookmarks**: Preserves multiple bookmarks with same name
- **New Bookmarks**: Inserts in correct position without version children
- **Modified Bookmarks**: Creates version hierarchy (Version 1, Version 2, etc.)

### Comparison Algorithm
- **Pass 1**: Finds 100% identical pages
- **Pass 2**: Heuristic matching (bookmark + form name + proximity)
- **Pass 3**: Global matching for remaining pages

### Output Structure
```
Consolidated PDF
├── Bookmark 1 (unchanged)
├── Bookmark 2 (modified)
│   ├── Version 1 (original)
│   └── Version 2 (updated)
├── Bookmark 3 (unchanged)
├── Bookmark 4 (new - added in v2)
└── ...
```

## Troubleshooting

### Port Already in Use
If port 8501 is already in use:
```bash
streamlit run app.py --server.port 8080
```

### Browser Doesn't Open
Manually navigate to: `http://localhost:8501`

### Memory Issues with Large PDFs
Increase available memory:
```bash
streamlit run app.py --server.maxUploadSize 500
```

### Dependencies Not Found
Reinstall requirements:
```bash
pip install --upgrade -r requirements.txt
```

## Project Structure

```
GBS/
├── app.py                           # Streamlit frontend
├── pdf_consolidation_backend.py     # Backend pipeline module
├── comparison_engine_core.py        # PDF comparison logic
├── pdf_consolidator.py              # PDF consolidation logic
├── requirements.txt                 # Python dependencies
├── README_STREAMLIT.md              # This file
└── OUTPUT/                          # Output directory (auto-created)
```

## Configuration

### Streamlit Configuration
Create `.streamlit/config.toml` for custom settings:

```toml
[server]
port = 8501
maxUploadSize = 200

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

## API Usage (Backend Only)

If you want to use the backend without the web interface:

```python
from pdf_consolidation_backend import PDFConsolidationPipeline

# Initialize pipeline
pipeline = PDFConsolidationPipeline(
    input_dir="path/to/pdfs",
    output_dir="path/to/output"
)

# Run consolidation
result = pipeline.run()

if result['success']:
    print(f"Output: {result['output_path']}")
    print(f"Pages: {result['stats']['total_pages']}")
else:
    print(f"Error: {result['error']}")
```

## Development

### Running in Development Mode
```bash
streamlit run app.py --server.runOnSave true
```

### Debug Mode
```bash
streamlit run app.py --logger.level debug
```

## Support

For issues or questions, please refer to the main project documentation.

## License

© 2025 - eCRF PDF Consolidation Tool
