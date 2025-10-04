# Deck Compress Web Application

A web-based interface for the Deck Compress tool, built with FastAPI and modern web technologies.

## Features

- **Web Interface**: Easy-to-use drag-and-drop file upload
- **Real-time Progress**: Visual progress indicators during compression
- **Multiple File Types**: Support for PowerPoint, Word, Video, and Image files
- **Compression Options**: Quality control, ultra mode, and custom settings
- **Download Results**: Direct download of compressed files
- **Responsive Design**: Works on desktop and mobile devices

## Quick Start

### 1. Install Dependencies

```bash
pip install -r web_app/requirements.txt
```

### 2. Run the Web Application

```bash
python web_app/run.py
```

### 3. Open in Browser

Navigate to `http://localhost:8000` to use the web interface.

## API Endpoints

- `GET /` - Web interface
- `POST /upload/` - Upload and compress files
- `GET /download/{filename}` - Download compressed files
- `GET /health` - Health check
- `GET /docs` - API documentation

## Usage

1. **Select File**: Click the upload area or drag and drop a file
2. **Configure Settings**: Adjust quality, max width, and other options
3. **Enable Ultra Mode**: Check the ultra mode checkbox for maximum compression
4. **Compress**: Click the "Compress File" button
5. **Download**: Download the compressed file when processing is complete

## Supported File Types

- **Documents**: .pptx, .ppt, .docx, .doc
- **Videos**: .mp4, .avi, .mov, .wmv, .mkv, .m4v, .flv, .webm
- **Images**: .jpg, .jpeg, .png, .bmp, .tiff, .gif

## Compression Options

- **Image Quality**: 1-100 (default: 85)
- **Max Width**: Maximum image width in pixels (default: 1920)
- **Video Quality**: 0-51 CRF value (default: 28)
- **Ultra Mode**: Maximum compression with 50-80% size reduction

## Development

The web application uses:
- **FastAPI**: Modern, fast web framework
- **Jinja2**: Template engine for HTML rendering
- **Uvicorn**: ASGI server for running the application
- **Modern CSS**: Responsive design with gradients and animations

## File Structure

```
web_app/
├── main.py              # FastAPI application
├── run.py               # Application runner
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html      # Web interface template
└── static/
    └── uploads/        # Temporary file storage
```
