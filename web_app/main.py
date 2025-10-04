from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
from pathlib import Path
import tempfile
import uuid
from typing import Optional
import sys

# Import deck_compress from the same directory
try:
    from deck_compress import process_single_file, CompressionProgress
    from rich.console import Console
except ImportError as e:
    print(f"Error: Could not import deck_compress module: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Files in current directory: {os.listdir('.')}")
    raise

app = FastAPI(title="Deck Compress Web", version="1.0.0")

# Mount static files and templates
static_dir = Path("static")
templates_dir = Path("templates")

# Try different paths for static files
if not static_dir.exists():
    static_dir = Path("web_app/static")
if not templates_dir.exists():
    templates_dir = Path("web_app/templates")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Create upload directory
UPLOAD_DIR = static_dir / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)

console = Console()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return templates.TemplateResponse("index.html", {"request": {}})

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    quality: int = Form(85),
    max_width: int = Form(1920),
    video_crf: int = Form(28),
    ultra_mode: str = Form("false")
):
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate file type
    allowed_extensions = {'.pptx', '.ppt', '.docx', '.doc', '.mp4', '.avi', '.mov', 
                         '.wmv', '.mkv', '.m4v', '.flv', '.webm', '.jpg', '.jpeg', 
                         '.png', '.bmp', '.tiff', '.gif'}
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
    
    # File size validation (500MB limit for web uploads)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB. Your file is {file_size // (1024*1024)}MB. Please use the CLI version for larger files."
        )
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file provided")
    
    # Convert ultra_mode string to boolean
    ultra_mode_bool = ultra_mode.lower() == "true"
    
    # Create unique filename
    file_id = str(uuid.uuid4())
    input_filename = f"{file_id}{file_ext}"
    output_filename = f"compressed_{file_id}{file_ext}"
    
    input_path = UPLOAD_DIR / input_filename
    output_path = UPLOAD_DIR / output_filename
    
    try:
        # Save uploaded file (reset file pointer after size check)
        file.file.seek(0)
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the file with timeout protection
        import signal
        import time
        
        def timeout_handler(signum, frame):
            raise TimeoutError("File processing timed out")
        
        # Set timeout based on file size (5 minutes base + 1 minute per 50MB)
        timeout_seconds = 300 + (file_size // (50 * 1024 * 1024)) * 60
        timeout_seconds = min(timeout_seconds, 1800)  # Max 30 minutes
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            success = process_single_file(
                input_path, output_path, quality, max_width, video_crf, ultra_mode_bool
            )
        finally:
            signal.alarm(0)  # Cancel timeout
        
        if success and output_path.exists():
            return {
                "success": True,
                "message": "File compressed successfully",
                "original_size": input_path.stat().st_size,
                "compressed_size": output_path.stat().st_size,
                "compression_ratio": (1 - output_path.stat().st_size / input_path.stat().st_size) * 100,
                "download_url": f"/download/{output_filename}",
                "original_filename": file.filename
            }
        else:
            raise HTTPException(status_code=500, detail="Compression failed")
            
    except Exception as e:
        # Clean up files on error
        if input_path.exists():
            input_path.unlink()
        if output_path.exists():
            output_path.unlink()
        console.print(f"[red]Error processing file: {str(e)}[/red]")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    finally:
        # Clean up input file
        if input_path.exists():
            input_path.unlink()

@app.get("/download/{filename}")
async def download_file(filename: str, original_name: str = None):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Use original filename if provided, otherwise extract from compressed filename
    if original_name:
        download_filename = original_name
    else:
        # Extract original filename from the compressed filename
        # Remove "compressed_" prefix and keep the original extension
        download_filename = filename.replace("compressed_", "")
    
    return FileResponse(
        file_path,
        filename=download_filename,
        media_type="application/octet-stream"
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Deck Compress Web App is running", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
