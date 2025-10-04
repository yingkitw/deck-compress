#!/usr/bin/env python3
"""
PowerPoint Deck Compressor CLI
Compresses images and videos embedded in PowerPoint files.
"""

import argparse
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import io
from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    FileSizeColumn,
    TransferSpeedColumn,
    SpinnerColumn,
    MofNCompleteColumn
)
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
import time
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, Generic, Union, Optional, Callable, Any, Dict, List, Tuple
import traceback
import sys
import signal

console = Console()

# === ERROR HANDLING MODULE ===
T = TypeVar('T')
E = TypeVar('E')

class ErrorType(Enum):
    """Types of errors that can occur in the application."""
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_FORMAT = "invalid_format"
    COMPRESSION_FAILED = "compression_failed"
    EXTERNAL_TOOL_MISSING = "external_tool_missing"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Additional context for errors."""
    file_path: Optional[str] = None
    operation: Optional[str] = None
    details: Optional[dict] = None

class AppError(Exception):
    """Base application error with context and chaining support."""

    def __init__(self,
                 message: str,
                 error_type: ErrorType = ErrorType.UNKNOWN,
                 context: Optional[ErrorContext] = None,
                 source: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.context = context or ErrorContext()
        self.source = source
        self.traceback_str = traceback.format_exc() if source else None

    def with_context(self, **kwargs) -> 'AppError':
        """Add context to the error."""
        if self.context is None:
            self.context = ErrorContext()

        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                if self.context.details is None:
                    self.context.details = {}
                self.context.details[key] = value

        return self

    def __str__(self) -> str:
        parts = [f"[{self.error_type.value}] {self.message}"]

        if self.context:
            if self.context.file_path:
                parts.append(f"File: {self.context.file_path}")
            if self.context.operation:
                parts.append(f"Operation: {self.context.operation}")
            if self.context.details:
                for key, value in self.context.details.items():
                    parts.append(f"{key}: {value}")

        if self.source:
            parts.append(f"Caused by: {self.source}")

        return " | ".join(parts)

class Result(Generic[T, E]):
    """Result type similar to Rust's Result<T, E>."""

    def __init__(self, value: Union[T, E], is_ok: bool):
        self._value = value
        self._is_ok = is_ok

    @classmethod
    def ok(cls, value: T) -> 'Result[T, E]':
        """Create a successful Result."""
        return cls(value, True)

    @classmethod
    def err(cls, error: E) -> 'Result[T, E]':
        """Create an error Result."""
        return cls(error, False)

    def is_ok(self) -> bool:
        """Check if the result is successful."""
        return self._is_ok

    def is_err(self) -> bool:
        """Check if the result is an error."""
        return not self._is_ok

    def unwrap(self) -> T:
        """Get the value, raising an exception if it's an error."""
        if self._is_ok:
            return self._value
        else:
            if isinstance(self._value, Exception):
                raise self._value
            else:
                raise AppError(f"Result unwrap failed: {self._value}")

    def unwrap_or(self, default: T) -> T:
        """Get the value or return a default if it's an error."""
        return self._value if self._is_ok else default

    def unwrap_or_else(self, func: Callable[[E], T]) -> T:
        """Get the value or compute it from the error."""
        return self._value if self._is_ok else func(self._value)

    def map(self, func: Callable[[T], Any]) -> 'Result':
        """Transform the success value."""
        if self._is_ok:
            try:
                return Result.ok(func(self._value))
            except Exception as e:
                return Result.err(AppError(f"Map operation failed: {e}", source=e))
        else:
            return Result.err(self._value)

    def map_err(self, func: Callable[[E], Any]) -> 'Result':
        """Transform the error value."""
        if self._is_ok:
            return Result.ok(self._value)
        else:
            try:
                return Result.err(func(self._value))
            except Exception as e:
                return Result.err(AppError(f"Map error operation failed: {e}", source=e))

    def and_then(self, func: Callable[[T], 'Result']) -> 'Result':
        """Chain operations that return Results."""
        if self._is_ok:
            try:
                return func(self._value)
            except Exception as e:
                return Result.err(AppError(f"And then operation failed: {e}", source=e))
        else:
            return Result.err(self._value)

# Type alias for common Result patterns
AppResult = Result[T, AppError]

def wrap_result(func: Callable[..., T]) -> Callable[..., AppResult[T]]:
    """Decorator to wrap functions to return Results."""
    def wrapper(*args, **kwargs) -> AppResult[T]:
        try:
            result = func(*args, **kwargs)
            return Result.ok(result)
        except AppError as e:
            return Result.err(e)
        except FileNotFoundError as e:
            error = AppError(
                f"File not found: {e}",
                ErrorType.FILE_NOT_FOUND,
                source=e
            )
            return Result.err(error)
        except PermissionError as e:
            error = AppError(
                f"Permission denied: {e}",
                ErrorType.PERMISSION_DENIED,
                source=e
            )
            return Result.err(error)
        except Exception as e:
            error = AppError(
                f"Unexpected error: {e}",
                ErrorType.UNKNOWN,
                source=e
            )
            return Result.err(error)

    return wrapper

def ensure(condition: bool, message: str, error_type: ErrorType = ErrorType.VALIDATION_ERROR) -> AppResult[None]:
    """Ensure a condition is true, returning an error if not."""
    if condition:
        return Result.ok(None)
    else:
        return Result.err(AppError(message, error_type))

def context(message: str, **kwargs) -> Callable[[AppResult[T]], AppResult[T]]:
    """Add context to a Result."""
    def wrapper(result: AppResult[T]) -> AppResult[T]:
        if result.is_err():
            error = result._value
            if isinstance(error, AppError):
                error.message = f"{message}: {error.message}"
                error.with_context(**kwargs)
            return Result.err(error)
        else:
            return result

    return wrapper

# Utility functions for common error scenarios
def file_error(path: str, operation: str, source: Exception) -> AppError:
    """Create a file-related error."""
    error_type = ErrorType.FILE_NOT_FOUND if isinstance(source, FileNotFoundError) else ErrorType.UNKNOWN
    return AppError(
        f"File operation failed: {source}",
        error_type,
        ErrorContext(file_path=path, operation=operation),
        source
    )

def compression_error(path: str, details: str, source: Optional[Exception] = None) -> AppError:
    """Create a compression-related error."""
    return AppError(
        f"Compression failed: {details}",
        ErrorType.COMPRESSION_FAILED,
        ErrorContext(file_path=path, operation="compress"),
        source
    )

def tool_missing_error(tool_name: str, operation: str) -> AppError:
    """Create an external tool missing error."""
    return AppError(
        f"Required tool '{tool_name}' not found",
        ErrorType.EXTERNAL_TOOL_MISSING,
        ErrorContext(operation=operation, details={"tool": tool_name})
    )

def format_error(path: str, expected_format: str, actual_format: str) -> AppError:
    """Create a format validation error."""
    return AppError(
        f"Invalid file format: expected {expected_format}, got {actual_format}",
        ErrorType.INVALID_FORMAT,
        ErrorContext(
            file_path=path,
            operation="format_validation",
            details={"expected": expected_format, "actual": actual_format}
        )
    )

# === PROGRESS TRACKING MODULE ===
class CompressionProgress:
    """Simple progress tracker focused only on compression operations."""

    def __init__(self, total_files: int = 0, show_details: bool = True):
        self.total_files = total_files
        self.processed_files = 0
        self.show_details = show_details
        self.start_time = time.time()

    def start_compression(self, filename: str, original_size: int):
        """Start compressing a file."""
        if self.show_details:
            console.print(f"[blue]Compressing: {filename} ({original_size / (1024*1024):.1f} MB)[/blue]")

    def update_progress(self, processed_size: int, total_size: int):
        """Update compression progress."""
        if self.show_details and total_size > 0:
            percentage = (processed_size / total_size) * 100
            console.print(f"[dim]Progress: {percentage:.1f}% ({processed_size / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)[/dim]", end="\r")

    def finish_file(self, success: bool, original_size: int, compressed_size: int = 0):
        """Mark a file as completed."""
        self.processed_files += 1

        if success and self.show_details:
            if compressed_size > 0:
                ratio = (1 - compressed_size / original_size) * 100
                console.print(f"[green]✓ Compressed: {ratio:.1f}% reduction[/green]")
            else:
                console.print("[green]✓ Processing complete[/green]")
        elif not success and self.show_details:
            console.print("[red]✗ Compression failed[/red]")

    def finish_all(self):
        """Finish processing all files."""
        elapsed = time.time() - self.start_time
        if self.show_details:
            console.print(f"[blue]Processing complete in {elapsed:.1f}s[/blue]")

def show_compression_summary(original_sizes: List[int], compressed_sizes: List[int], filenames: List[str]):
    """Show a simple compression summary."""
    if not original_sizes or len(original_sizes) != len(compressed_sizes) != len(filenames):
        return

    total_original = sum(original_sizes)
    total_compressed = sum(compressed_sizes)
    total_ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0

    console.print(f"[green]Compression Summary:[/green]")
    console.print(f"  Original: {total_original / (1024*1024):.1f} MB")
    console.print(f"  Compressed: {total_compressed / (1024*1024):.1f} MB")
    console.print(f"  Reduction: {total_ratio:.1f}%")

# === TOOLS VALIDATION MODULE ===
import subprocess
import shutil

@dataclass
class ToolInfo:
    """Information about an external tool."""
    name: str
    command: str
    version_flag: str
    required_for: List[str]
    install_hint: str
    min_version: Optional[str] = None

# Tool definitions
TOOLS = {
    "ffmpeg": ToolInfo(
        name="FFmpeg",
        command="ffmpeg",
        version_flag="-version",
        required_for=["video compression", "video format conversion"],
        install_hint="Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Ubuntu)",
        min_version="4.0"
    ),
    "ghostscript": ToolInfo(
        name="Ghostscript",
        command="gs",
        version_flag="--version",
        required_for=["PDF compression", "PDF optimization"],
        install_hint="Install with: brew install ghostscript (macOS) or apt install ghostscript (Ubuntu)",
        min_version="9.0"
    ),
    "imagemagick": ToolInfo(
        name="ImageMagick",
        command="magick",
        version_flag="-version",
        required_for=["advanced image processing", "image format conversion"],
        install_hint="Install with: brew install imagemagick (macOS) or apt install imagemagick (Ubuntu)",
        min_version="7.0"
    ),
    "libreoffice": ToolInfo(
        name="LibreOffice",
        command="libreoffice",
        version_flag="--version",
        required_for=["document conversion", "legacy document processing"],
        install_hint="Download from: https://www.libreoffice.org/download/",
        min_version="6.0"
    )
}

class ToolValidator:
    """Validates and manages external tool dependencies."""

    def __init__(self):
        self._cache: Dict[str, bool] = {}
        self._version_cache: Dict[str, str] = {}

    def check_tool(self, tool_name: str, show_warnings: bool = True) -> AppResult[bool]:
        """Check if a tool is available and working."""
        if tool_name in self._cache:
            return Result.ok(self._cache[tool_name])

        if tool_name not in TOOLS:
            return Result.err(AppError(
                f"Unknown tool: {tool_name}",
                ErrorType.VALIDATION_ERROR
            ))

        tool_info = TOOLS[tool_name]

        # Check if command exists
        if not shutil.which(tool_info.command):
            self._cache[tool_name] = False
            if show_warnings:
                self._show_missing_tool_warning(tool_info)
            return Result.err(tool_missing_error(tool_name, "availability_check"))

        # Try to run the tool to verify it works
        try:
            result = subprocess.run(
                [tool_info.command, tool_info.version_flag],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self._cache[tool_name] = True
                # Extract and cache version if possible
                version = self._extract_version(result.stdout, tool_name)
                if version:
                    self._version_cache[tool_name] = version
                return Result.ok(True)
            else:
                self._cache[tool_name] = False
                if show_warnings:
                    console.print(f"[yellow]Warning: {tool_info.name} found but not working properly[/yellow]")
                return Result.err(AppError(
                    f"{tool_info.name} is not working properly",
                    ErrorType.EXTERNAL_TOOL_MISSING,
                    source=Exception(f"Return code: {result.returncode}, stderr: {result.stderr}")
                ))

        except subprocess.TimeoutExpired:
            self._cache[tool_name] = False
            if show_warnings:
                console.print(f"[yellow]Warning: {tool_info.name} check timed out[/yellow]")
            return Result.err(AppError(
                f"{tool_info.name} check timed out",
                ErrorType.EXTERNAL_TOOL_MISSING
            ))

        except Exception as e:
            self._cache[tool_name] = False
            if show_warnings:
                console.print(f"[yellow]Warning: Error checking {tool_info.name}: {e}[/yellow]")
            return Result.err(AppError(
                f"Error checking {tool_info.name}",
                ErrorType.EXTERNAL_TOOL_MISSING,
                source=e
            ))

    def check_multiple_tools(self, tool_names: List[str], show_warnings: bool = True) -> Dict[str, AppResult[bool]]:
        """Check multiple tools and return results for each."""
        results = {}
        for tool_name in tool_names:
            results[tool_name] = self.check_tool(tool_name, show_warnings)
        return results

    def ensure_tool(self, tool_name: str, operation: str) -> AppResult[None]:
        """Ensure a tool is available, returning an error if not."""
        result = self.check_tool(tool_name, show_warnings=True)
        if result.is_err():
            error = result._value
            error.with_context(operation=operation)
            return Result.err(error)
        return Result.ok(None)

    def get_tool_version(self, tool_name: str) -> Optional[str]:
        """Get the cached version of a tool."""
        return self._version_cache.get(tool_name)

    def show_tool_status(self, tool_names: Optional[List[str]] = None) -> None:
        """Show the status of tools in a formatted table."""
        if tool_names is None:
            tool_names = list(TOOLS.keys())

        table = Table(title="External Tool Status")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Version", style="dim")
        table.add_column("Required For", style="blue")

        for tool_name in tool_names:
            if tool_name not in TOOLS:
                continue

            tool_info = TOOLS[tool_name]
            result = self.check_tool(tool_name, show_warnings=False)

            if result.is_ok() and result.unwrap():
                status = "[green]✓ Available[/green]"
                version = self._version_cache.get(tool_name, "Unknown")
            else:
                status = "[red]✗ Missing[/red]"
                version = "N/A"

            required_for = ", ".join(tool_info.required_for)
            table.add_row(tool_info.name, status, version, required_for)

        console.print(table)

    def _show_missing_tool_warning(self, tool_info: ToolInfo) -> None:
        """Show a warning about a missing tool."""
        console.print(f"[yellow]Warning: {tool_info.name} not found[/yellow]")
        console.print(f"[dim]Required for: {', '.join(tool_info.required_for)}[/dim]")
        console.print(f"[dim]{tool_info.install_hint}[/dim]")

    def _extract_version(self, version_output: str, tool_name: str) -> Optional[str]:
        """Extract version number from tool output."""
        try:
            lines = version_output.strip().split('\n')
            first_line = lines[0] if lines else ""

            if tool_name == "ffmpeg":
                # FFmpeg version output: "ffmpeg version 4.4.2 Copyright..."
                if "version" in first_line:
                    parts = first_line.split()
                    for i, part in enumerate(parts):
                        if part == "version" and i + 1 < len(parts):
                            return parts[i + 1]

            elif tool_name == "ghostscript":
                # Ghostscript version output: "9.56.1"
                return first_line.strip()

            elif tool_name == "imagemagick":
                # ImageMagick version output: "Version: ImageMagick 7.1.0-4..."
                if "ImageMagick" in first_line:
                    parts = first_line.split()
                    for part in parts:
                        if part.startswith("7.") or part.startswith("6."):
                            return part.split("-")[0]  # Remove build suffix

            elif tool_name == "libreoffice":
                # LibreOffice version output: "LibreOffice 7.4.7.2..."
                if "LibreOffice" in first_line:
                    parts = first_line.split()
                    for part in parts:
                        if part[0].isdigit():
                            return part

            return None

        except Exception:
            return None

    def clear_cache(self) -> None:
        """Clear the tool availability cache."""
        self._cache.clear()
        self._version_cache.clear()

# Global tool validator instance
tool_validator = ToolValidator()

# Convenience functions
def check_ffmpeg() -> AppResult[bool]:
    """Check if FFmpeg is available."""
    return tool_validator.check_tool("ffmpeg")

def check_ghostscript() -> AppResult[bool]:
    """Check if Ghostscript is available."""
    return tool_validator.check_tool("ghostscript")

def ensure_ffmpeg(operation: str = "video processing") -> AppResult[None]:
    """Ensure FFmpeg is available for the given operation."""
    return tool_validator.ensure_tool("ffmpeg", operation)

def ensure_ghostscript(operation: str = "PDF processing") -> AppResult[None]:
    """Ensure Ghostscript is available for the given operation."""
    return tool_validator.ensure_tool("ghostscript", operation)

def show_all_tools() -> None:
    """Show status of all external tools."""
    tool_validator.show_tool_status()

def get_missing_tools() -> List[str]:
    """Get a list of missing required tools."""
    missing = []
    for tool_name in TOOLS.keys():
        result = tool_validator.check_tool(tool_name, show_warnings=False)
        if result.is_err() or not result.unwrap():
            missing.append(tool_name)
    return missing

def compress_image(image_data: bytes, original_format: str, quality: int = 85, max_width: int = 1920) -> bytes:
    """Compress image data while maintaining aspect ratio and original format when possible."""
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            original_format_upper = original_format.upper()

            # Resize if too large
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            output = io.BytesIO()

            # Handle different formats appropriately
            if original_format_upper in ['JPEG', 'JPG']:
                # Convert to RGB if necessary for JPEG
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(output, format='JPEG', quality=quality, optimize=True)
            elif original_format_upper == 'PNG':
                # Keep PNG format to preserve transparency if present
                img.save(output, format='PNG', optimize=True)
            elif original_format_upper in ['BMP', 'TIFF', 'GIF']:
                # Convert these formats to JPEG for better compression
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(output, format='JPEG', quality=quality, optimize=True)
            else:
                # Default to JPEG for unknown formats
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                img.save(output, format='JPEG', quality=quality, optimize=True)

            return output.getvalue()
    except Exception as e:
        console.print(f"[yellow]Warning: Could not compress image: {e}[/yellow]")
        return image_data

def compress_video(video_path: Path, output_path: Path, crf: int = 28) -> bool:
    """Compress video using ffmpeg."""
    try:
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-c:v', 'libx264', '-crf', str(crf),
            '-c:a', 'aac', '-b:a', '128k',
            '-y', str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        console.print("[red]Error: ffmpeg not found. Please install ffmpeg to compress videos.[/red]")
        return False
    except Exception as e:
        console.print(f"[yellow]Warning: Could not compress video: {e}[/yellow]")
        return False

def compress_standalone_video(input_path: Path, output_path: Path, crf: int = 28) -> bool:
    """Compress standalone video file."""
    return compress_video(input_path, output_path, crf)

def compress_doc(input_path: Path, output_path: Path, image_quality: int = 85, max_width: int = 1920, video_crf: int = 28) -> bool:
    """Compress Word document by extracting and compressing embedded media with progress tracking."""

    progress = CompressionProgress(total_files=1, show_details=True)
    progress.start_compression(input_path.name, input_path.stat().st_size)

    try:
            # Word documents (.docx) are ZIP files like PowerPoint
            if input_path.suffix.lower() == '.docx':
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)

                    # Extract DOCX
                    if progress.show_details:
                        console.print("[dim]Extracting document...[/dim]")
                    with zipfile.ZipFile(input_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_path)

                    # Find and compress media files
                    media_dir = temp_path / "word" / "media"
                    if media_dir.exists():
                        media_files = list(media_dir.glob("*"))
                        image_files = [f for f in media_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']]
                        video_files = [f for f in media_files if f.suffix.lower() in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']]

                        total_media = len(image_files) + len(video_files)
                        if total_media > 0:
                            if progress.show_details:
                                console.print(f"[dim]Compressing {total_media} media files...[/dim]")

                            processed = 0

                            # Compress images
                            for media_file in image_files:
                                try:
                                    with open(media_file, 'rb') as f:
                                        original_data = f.read()

                                    original_format = media_file.suffix[1:]
                                    compressed_data = compress_image(original_data, original_format, image_quality, max_width)

                                    with open(media_file, 'wb') as f:
                                        f.write(compressed_data)

                                    processed += 1
                                except Exception as e:
                                    console.print(f"[yellow]Warning: Could not compress image {media_file.name}: {e}[/yellow]")
                                    processed += 1

                            # Compress videos
                            for video_file in video_files:
                                try:
                                    temp_video = temp_path / f"temp_{video_file.name}"
                                    if compress_video(video_file, temp_video, video_crf):
                                        shutil.move(temp_video, video_file)

                                    processed += 1
                                except Exception as e:
                                    console.print(f"[yellow]Warning: Could not compress video {video_file.name}: {e}[/yellow]")
                                    processed += 1

                    # Repack DOCX
                    if progress.show_details:
                        console.print("[dim]Repacking document...[/dim]")
                    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zip_ref:
                        for file_path in temp_path.rglob('*'):
                            if file_path.is_file():
                                arcname = file_path.relative_to(temp_path)
                                zip_ref.write(file_path, arcname)

                    progress.finish_file(True, input_path.stat().st_size, output_path.stat().st_size)
                    return True
            else:
                # For .doc files, just copy (can't compress without complex libraries)
                if progress.show_details:
                    console.print("[dim]Copying legacy document...[/dim]")
                shutil.copy2(input_path, output_path)
                progress.finish_file(True, input_path.stat().st_size, output_path.stat().st_size)
                return True

    except Exception as e:
        console.print(f"[red]Error: Could not compress document: {e}[/red]")
        progress.finish_file(False, input_path.stat().st_size)
        return False

    finally:
        progress.finish_all()

def process_pptx(input_path: Path, output_path: Path, image_quality: int, max_width: int, video_crf: int, progress: CompressionProgress = None):
    """Process PowerPoint file and compress embedded media."""
    if progress is None:
        progress = CompressionProgress(total_files=1, show_details=True)
        progress.start_compression(input_path.name, input_path.stat().st_size)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract PPTX
            if progress.show_details:
                console.print("[dim]Extracting PowerPoint...[/dim]")

            with zipfile.ZipFile(input_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)

            media_dir = temp_path / "ppt" / "media"
            if not media_dir.exists():
                console.print("[yellow]No media folder found in PowerPoint file[/yellow]")
                shutil.copy2(input_path, output_path)
                return

            total_original_size = 0
            total_compressed_size = 0

            # Process media files with simple progress tracking
            media_files = [f for f in media_dir.glob("*") if f.is_file()]
            total_files = len(media_files)

            if progress.show_details:
                console.print(f"[dim]Processing {total_files} media files...[/dim]")

            for i, media_file in enumerate(media_files):
                original_size = media_file.stat().st_size
                total_original_size += original_size

                if progress.show_details:
                    console.print(f"[dim]Processing {media_file.name} ({i+1}/{total_files})...[/dim]", end="\r")

                # Check file type
                suffix = media_file.suffix.lower()

                if suffix in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
                    # Compress image
                    with open(media_file, 'rb') as f:
                        original_data = f.read()

                    # Get original format from file extension
                    original_format = suffix[1:]  # Remove the dot
                    compressed_data = compress_image(original_data, original_format, image_quality, max_width)

                    # Save compressed image with original filename to preserve PowerPoint references
                    with open(media_file, 'wb') as f:
                        f.write(compressed_data)

                    compressed_size = len(compressed_data)
                    total_compressed_size += compressed_size

                elif suffix in ['.mp4', '.avi', '.mov', '.wmv', '.mkv']:
                    # Compress video
                    temp_video = temp_path / f"temp_video{suffix}"
                    if compress_video(media_file, temp_video, video_crf):
                        shutil.move(temp_video, media_file)
                        compressed_size = media_file.stat().st_size
                        total_compressed_size += compressed_size
                        if progress.show_details:
                            console.print(f"[green]✓ Video compressed[/green]")
                    else:
                        total_compressed_size += original_size
                        if progress.show_details:
                            console.print(f"[yellow]⚠ Video compression skipped[/yellow]")
                else:
                    # Keep other files as-is
                    total_compressed_size += original_size

            # Repack PPTX
            if progress.show_details:
                console.print("[dim]Repacking PowerPoint...[/dim]")
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for file_path in temp_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_path)
                        zip_ref.write(file_path, arcname)

            # Show compression results
            if total_original_size > 0:
                show_compression_summary([total_original_size], [total_compressed_size], [input_path.name])

            progress.finish_file(True, input_path.stat().st_size, output_path.stat().st_size)

    finally:
        if progress is not None:
            progress.finish_all()

def process_single_file(input_path: Path, output_path: Path, image_quality: int, max_width: int, video_crf: int) -> bool:
    """Process a single file based on its type."""
    suffix = input_path.suffix.lower()

    # Create progress tracker for single file processing
    progress = CompressionProgress(total_files=1, show_details=True)
    progress.start_compression(input_path.name, input_path.stat().st_size)

    try:
        if suffix in ['.pptx', '.ppt']:
            process_pptx(input_path, output_path, image_quality, max_width, video_crf, progress)
            progress.finish_file(True, input_path.stat().st_size, output_path.stat().st_size)
            return True
        elif suffix in ['.mp4', '.avi', '.mov', '.wmv', '.mkv', '.m4v', '.flv', '.webm']:
            success = compress_standalone_video(input_path, output_path, video_crf)
            progress.finish_file(success, input_path.stat().st_size, output_path.stat().st_size if success else 0)
            return success
        elif suffix in ['.docx', '.doc']:
            success = compress_doc(input_path, output_path, image_quality, max_width, video_crf)
            progress.finish_file(success, input_path.stat().st_size, output_path.stat().st_size if success else 0)
            return success
        else:
            console.print(f"[yellow]Unsupported file type: {suffix}[/yellow]")
            progress.finish_file(False, input_path.stat().st_size)
            return False
    except Exception as e:
        console.print(f"[red]Error processing {input_path.name}: {e}[/red]")
        progress.finish_file(False, input_path.stat().st_size)
        return False
    finally:
        progress.finish_all()

def process_folder(folder_path: Path, min_size_mb: int, image_quality: int, max_width: int, video_crf: int, force: bool, timeout: int = 300):
    """Process all supported files in a folder that are over the minimum size."""

    # Create progress tracker for folder processing
    progress = CompressionProgress(total_files=0, show_details=True)

    # Find all supported files in the folder
    if progress.show_details:
        console.print("[dim]Scanning folder for supported files...[/dim]")

    supported_extensions = [
        "*.pptx", "*.ppt",  # PowerPoint
        "*.mp4", "*.avi", "*.mov", "*.wmv", "*.mkv", "*.m4v", "*.flv", "*.webm",  # Video
        "*.docx", "*.doc"  # Word
    ]

    all_files = []
    for pattern in supported_extensions:
        all_files.extend(folder_path.glob(pattern))

    if not all_files:
        console.print(f"[yellow]No supported files found in {folder_path}[/yellow]")
        console.print("[blue]Supported formats: PPTX, PPT, MP4, AVI, MOV, WMV, MKV, M4V, FLV, WEBM, DOCX, DOC[/blue]")
        return 0

    # Filter files by size
    large_files = []
    min_size_bytes = min_size_mb * 1024 * 1024

    for file in all_files:
        if file.stat().st_size >= min_size_bytes:
            large_files.append(file)

    if not large_files:
        console.print(f"[yellow]No files over {min_size_mb}MB found in {folder_path}[/yellow]")
        return 0

    # Show file information using new utility
    console.print(f"[blue]Found {len(large_files)} files over {min_size_mb}MB:[/blue]")
    show_file_info_table(large_files, f"Files to Process (>{min_size_mb}MB)")

    # Process files with simple progress tracking
    def process_file_with_progress(file_path: Path, **kwargs) -> bool:
        """Process a single file with basic progress tracking."""
        output_file = file_path.with_stem(f"{file_path.stem}_compressed")
        file_timeout = kwargs.get('timeout', timeout)

        # Check if output file exists
        if output_file.exists() and not kwargs.get('force', False):
            console.print(f"[yellow]Skipping (output exists): {output_file.name}[/yellow]")
            return False

        try:
            import signal
            import time

            # Set up timeout handler
            def timeout_handler(signum, frame):
                raise TimeoutError(f"Processing {file_path.name} timed out after {file_timeout} seconds")

            # Set timeout for each file
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(file_timeout)

            start_time = time.time()
            console.print(f"[blue]Processing: {file_path.name} ({file_path.stat().st_size / (1024*1024):.1f} MB)[/blue]")

            success = process_single_file(
                file_path, output_file,
                kwargs['image_quality'], kwargs['max_width'],
                kwargs['video_crf']
            )

            # Cancel timeout
            signal.alarm(0)

            elapsed = time.time() - start_time

            if success and output_file.exists():
                original_size = file_path.stat().st_size
                compressed_size = output_file.stat().st_size
                compression_ratio = (1 - compressed_size / original_size) * 100
                console.print(f"[green]✓ Saved: {output_file.name} ({compression_ratio:.1f}% reduction, {elapsed:.1f}s)[/green]")
            else:
                console.print(f"[yellow]⚠️  Processing completed but no output: {file_path.name} ({elapsed:.1f}s)[/yellow]")

            return success

        except TimeoutError as e:
            signal.alarm(0)
            console.print(f"[red]⏰ TIMEOUT: {file_path.name} - {e}[/red]")
            console.print(f"[yellow]This file may be corrupted or too complex to process[/yellow]")
            return False
        except Exception as e:
            signal.alarm(0)
            console.print(f"[red]✗ Failed to process {file_path.name}: {e}[/red]")
            return False
        finally:
            signal.alarm(0)  # Ensure timeout is always cancelled

    # Process files with simple progress tracking
    for i, file_path in enumerate(large_files, 1):
        if progress.show_details:
            console.print(f"[dim]Processing file {i}/{len(large_files)}...[/dim]")

        success = process_file_with_progress(
            file_path,
            image_quality=image_quality,
            max_width=max_width,
            video_crf=video_crf,
            pdf_quality="ebook",
            force=force,
            timeout=timeout
        )

        if success:
            progress.processed_files += 1

    # Show final summary
    successful_files = progress.processed_files
    total_files = len(large_files)

    if successful_files > 0:
        console.print(f"[green]Successfully processed {successful_files}/{total_files} files[/green]")
        progress.finish_all()
        return 0
    else:
        console.print("[red]No files were successfully processed[/red]")
        progress.finish_all()
        return 1

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Compress images, videos, and documents (PowerPoint, Word, Video files)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compress a single PowerPoint file
  python deck_compress.py presentation.pptx

  # Compress a video file
  python deck_compress.py video.mp4 --video-crf 25

  # Compress a Word document
  python deck_compress.py document.docx

  # Compress all files over 100MB in a folder
  python deck_compress.py /path/to/folder --folder --min-size 100

  # Custom compression settings
  python deck_compress.py input.pptx -q 75 -w 1600 --video-crf 30
        """
    )

    parser.add_argument(
        "input_path",
        help="Input file (.pptx, .docx, .mp4, etc.) or folder path"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (only for single file mode)"
    )
    parser.add_argument(
        "--folder",
        action="store_true",
        help="Process all supported files in the specified folder"
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=100,
        help="Minimum file size in MB to process (default: 100, only for folder mode)"
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=85,
        help="JPEG quality (1-100, default: 85)"
    )
    parser.add_argument(
        "-w", "--max-width",
        type=int,
        default=1920,
        help="Maximum image width in pixels (default: 1920)"
    )
    parser.add_argument(
        "--video-crf",
        type=int,
        default=28,
        help="Video compression factor (0-51, lower = better quality, default: 28)"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite output file if it exists"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for processing each file (default: 300)"
    )

    args = parser.parse_args()

    input_path = Path(args.input_path)

    # Validate input path
    if not input_path.exists():
        console.print(f"[red]Error: Input path '{input_path}' not found[/red]")
        return 1

    # Check if folder mode
    if args.folder or input_path.is_dir():
        if not input_path.is_dir():
            console.print("[red]Error: --folder specified but input is not a directory[/red]")
            return 1

        if args.output:
            console.print("[yellow]Warning: --output ignored in folder mode[/yellow]")

        return process_folder(input_path, args.min_size, args.quality, args.max_width, args.video_crf, args.force, args.timeout)

    # Single file mode - check for supported file types
    supported_extensions = ['.pptx', '.ppt', '.mp4', '.avi', '.mov', '.wmv', '.mkv', '.m4v', '.flv', '.webm', '.docx', '.doc']
    if input_path.suffix.lower() not in supported_extensions:
        console.print(f"[red]Error: Unsupported file type '{input_path.suffix}'[/red]")
        console.print("[blue]Supported formats: PPTX, PPT, MP4, AVI, MOV, WMV, MKV, M4V, FLV, WEBM, DOCX, DOC[/blue]")
        return 1

    # Validate quality range
    if not 1 <= args.quality <= 100:
        console.print("[red]Error: Quality must be between 1 and 100[/red]")
        return 1

    # Validate CRF range
    if not 0 <= args.video_crf <= 51:
        console.print("[red]Error: Video CRF must be between 0 and 51[/red]")
        return 1

    # Set output file
    if args.output is None:
        output_path = input_path.with_stem(f"{input_path.stem}_compressed")
    else:
        output_path = Path(args.output)

    # Check if output file exists
    if output_path.exists() and not args.force:
        console.print(f"[red]Error: Output file '{output_path}' already exists. Use --force to overwrite[/red]")
        return 1

    file_type = input_path.suffix.upper()[1:]  # Remove dot and uppercase
    console.print(f"[blue]Input:[/blue] {input_path}")
    console.print(f"[blue]Output:[/blue] {output_path}")
    console.print(f"[blue]File type:[/blue] {file_type}")
    console.print(f"[blue]Image quality:[/blue] {args.quality}")
    console.print(f"[blue]Max width:[/blue] {args.max_width}px")
    console.print(f"[blue]Video CRF:[/blue] {args.video_crf}")
    console.print()

    original_size = input_path.stat().st_size
    success = process_single_file(input_path, output_path, args.quality, args.max_width, args.video_crf)

    if success and output_path.exists():
        compressed_size = output_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100
        console.print(f"[green]✓ Compression complete![/green]")
        console.print(f"Original size: {original_size / (1024*1024):.1f} MB")
        console.print(f"Compressed size: {compressed_size / (1024*1024):.1f} MB")
        console.print(f"Compression ratio: {compression_ratio:.1f}%")

        console.print(f"[green]✓ Compressed file saved to: {output_path}[/green]")

        return 0
    else:
        console.print(f"[red]Error: Failed to compress {input_path.name}[/red]")
        return 1




if __name__ == "__main__":
    exit(main())
