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

# Add the src directory to the path to import deck_compress
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from deck_compress import process_single_file, CompressionProgress
    from rich.console import Console
except ImportError:
    print("Error: Could not import deck_compress module")
    print("Make sure the src directory is properly structured")
    raise

app = FastAPI(title="Deck Compress Web", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="web_app/static"), name="static")
templates = Jinja2Templates(directory="web_app/templates")

# Create upload directory
UPLOAD_DIR = Path("web_app/static/uploads")
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
    ultra_mode: bool = Form(False)
):
    # Validate file type
    allowed_extensions = {'.pptx', '.ppt', '.docx', '.doc', '.mp4', '.avi', '.mov', 
                         '.wmv', '.mkv', '.m4v', '.flv', '.webm', '.jpg', '.jpeg', 
                         '.png', '.bmp', '.tiff', '.gif'}
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    # Create unique filename
    file_id = str(uuid.uuid4())
    input_filename = f"{file_id}{file_ext}"
    output_filename = f"compressed_{file_id}{file_ext}"
    
    input_path = UPLOAD_DIR / input_filename
    output_path = UPLOAD_DIR / output_filename
    
    try:
        # Save uploaded file
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the file
        success = process_single_file(
            input_path, output_path, quality, max_width, video_crf, ultra_mode
        )
        
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
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
