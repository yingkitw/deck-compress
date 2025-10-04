# Deck Compress Architecture

## Project Structure

```
deck-compress/
├── web_app/                      # Centralized application (CLI + Web)
│   ├── main.py                  # FastAPI web application
│   ├── deck_compress.py         # Core compression logic (CLI + Web)
│   ├── requirements.txt         # All dependencies
│   ├── templates/
│   │   └── index.html           # Web interface template
│   ├── static/
│   │   └── uploads/             # Temporary file storage
│   ├── .do/
│   │   └── app.yaml             # DigitalOcean deployment config
│   ├── Dockerfile               # Docker configuration
│   ├── test_local.py            # Local testing script
│   └── QUICK_DEPLOY.md          # Deployment guide
├── tests/                        # Test suite
│   ├── __init__.py              # Test package init
│   └── test_deck_compress.py    # Comprehensive test suite
├── docs/                         # Documentation
│   └── index.html               # Landing page
├── config/                       # Configuration files (legacy)
│   └── requirements.txt         # CLI dependencies
├── run_tests.py                 # Test runner script
├── pytest.ini                  # Pytest configuration
├── README.md                    # Project documentation
├── ARCHITECTURE.md              # This file
└── TODO.md                      # Task tracking
```

## Core Architecture

### Module Organization

The application follows a modular architecture with clear separation of concerns:

#### 1. Error Handling Module
- **`ErrorType`**: Enum defining error categories
- **`AppError`**: Custom exception class with context
- **`Result[T, E]`**: Rust-like Result type for error handling
- **Utility functions**: `file_error()`, `compression_error()`, etc.

#### 2. Progress Tracking Module
- **`CompressionProgress`**: Simple progress tracker
- **`show_compression_summary()`**: Summary display function

#### 3. Tools Validation Module
- **`ToolInfo`**: External tool metadata
- **`ToolValidator`**: Tool availability checking
- **Tool definitions**: FFmpeg, Ghostscript, ImageMagick, LibreOffice

#### 4. Compression Engine
- **Image compression**: `compress_image()`
- **Video compression**: `compress_video()`, `compress_standalone_video()`
- **Document processing**: `compress_doc()`, `process_pptx()`
- **File processing**: `process_single_file()`, `process_folder()`

#### 5. Web Application Module
- **FastAPI Application**: `web_app/main.py`
- **Web Interface**: `web_app/templates/index.html`
- **Core Logic**: `web_app/deck_compress.py` (shared with CLI)
- **Deployment**: `web_app/.do/app.yaml`, `web_app/Dockerfile`
- **File Upload/Download**: REST API endpoints
- **Progress Display**: Real-time progress tracking
- **Static File Serving**: Upload directory management

#### 6. CLI Interface
- **`main()`**: Command-line argument parsing
- **Argument validation**: File types, quality ranges, etc.

## Centralized Architecture

### Key Design Decisions

The project has been restructured to use a **centralized architecture** where all core functionality is contained within the `web_app/` directory:

#### **Benefits of Centralization:**
- **Simplified Deployment**: Single directory contains everything needed
- **Reduced Complexity**: No complex path resolution or module discovery
- **Better Maintainability**: All related code in one location
- **Easier Testing**: Local testing script validates entire application
- **Cloud-Ready**: Optimized for DigitalOcean App Platform deployment

#### **Shared Code Approach:**
- **`deck_compress.py`**: Contains all compression logic
- **CLI Interface**: Direct execution of `deck_compress.py`
- **Web Interface**: Imports functions from `deck_compress.py`
- **No Duplication**: Single source of truth for all functionality

#### **Deployment Strategy:**
- **DigitalOcean**: Uses `.do/app.yaml` configuration
- **Docker**: Self-contained container with all dependencies
- **Local Development**: Simple `python main.py` execution
- **Testing**: `test_local.py` validates all components

## Data Flow

### CLI Data Flow
```mermaid
graph TD
    A[CLI Input] --> B[File Type Detection]
    B --> C{File Type?}
    
    C -->|PowerPoint| D[Extract PPTX]
    C -->|Word| E[Extract DOCX]
    C -->|Video| F[Direct Video Processing]
    C -->|Image| G[Direct Image Processing]
    
    D --> H[Find Media Files]
    E --> H
    
    H --> I{Media Type?}
    I -->|Image| J[Compress Image]
    I -->|Video| K[Compress Video]
    
    J --> L[Repack Document]
    K --> L
    F --> M[Output Video]
    G --> N[Output Image]
    
    L --> O[Output Document]
    M --> P[Compression Complete]
    N --> P
    O --> P
```

### Web Application Data Flow
```mermaid
graph TD
    A[Web Upload] --> B[File Validation]
    B --> C[Save to Temp Directory]
    C --> D[Process with CLI Engine]
    D --> E[Compress File]
    E --> F[Generate Download URL]
    F --> G[Return Results to Frontend]
    G --> H[Display Progress & Stats]
    H --> I[Download Compressed File]
    I --> J[Cleanup Temp Files]
```

## Error Handling Strategy

The application uses a comprehensive error handling system:

1. **Result Types**: All operations return `Result[T, AppError]`
2. **Error Context**: Errors include file paths, operations, and details
3. **Error Chaining**: Source errors are preserved for debugging
4. **Graceful Degradation**: Non-critical failures don't stop processing

## Progress Tracking

Simple, focused progress tracking:
- File-level progress for single files
- Batch progress for folder processing
- Compression ratio reporting
- Time tracking

## External Dependencies

### Required Tools
- **FFmpeg**: Video compression and format conversion
- **Python libraries**: Pillow, Rich, pytest

### Optional Tools
- **Ghostscript**: PDF processing (removed from current version)
- **ImageMagick**: Advanced image processing
- **LibreOffice**: Document conversion

## Web Application Architecture

### Frontend (HTML/CSS/JavaScript)
- **Responsive Design**: Mobile-first approach with CSS Grid/Flexbox
- **Drag & Drop**: Modern file upload with visual feedback
- **Progress Tracking**: Real-time progress display with step-by-step updates
- **Professional UI**: Clean, monochromatic design with smooth animations
- **File Validation**: Client-side file type and size validation

### Backend (FastAPI)
- **REST API**: RESTful endpoints for file upload/download
- **File Handling**: Secure file upload with temporary storage
- **Error Handling**: Comprehensive error responses with proper HTTP status codes
- **CORS Support**: Cross-origin resource sharing for web interface
- **Static File Serving**: Efficient file serving for downloads

### API Endpoints
- `GET /`: Web interface homepage
- `POST /upload/`: File upload and compression
- `GET /download/{filename}`: Download compressed files
- `GET /health`: Health check endpoint
- `GET /docs`: Auto-generated API documentation

## Testing Architecture

### Test Organization
- **Unit tests**: Individual function testing
- **Integration tests**: End-to-end workflow testing
- **Error scenario tests**: Failure case handling
- **Tool validation tests**: External dependency checking
- **Web API tests**: FastAPI endpoint testing

### Test Categories
- `unit`: Basic unit tests
- `compression`: Compression functionality
- `error_handling`: Error scenarios
- `progress`: Progress tracking
- `integration`: Full workflow tests

## Performance Considerations

1. **Memory Management**: Temporary files for large operations
2. **Timeout Handling**: Prevents hanging on corrupted files
3. **Batch Processing**: Efficient folder processing
4. **Progress Feedback**: Real-time user feedback

## Security Considerations

1. **File Validation**: Input file type checking
2. **Path Sanitization**: Safe file path handling
3. **Temporary Files**: Secure temporary directory usage
4. **Error Information**: No sensitive data in error messages

## Future Extensibility

The modular architecture supports easy extension:
- New file types can be added to the processing pipeline
- New compression algorithms can be integrated
- Additional progress tracking can be implemented
- New external tools can be added to the validation system
