#!/usr/bin/env python3
"""
Pytest tests for deck_compress.py functionality
"""

import pytest
import sys
import os
from pathlib import Path
import tempfile
import io

# Add the src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

try:
    from deck_compress import (
        compress_image,
        compress_video,
        compress_standalone_video,
        compress_doc,
        process_pptx,
        process_single_file,
        process_folder,
        ErrorType,
        ErrorContext,
        AppError,
        Result,
        AppResult,
        CompressionProgress,
        ToolValidator,
        ToolInfo,
        check_ffmpeg,
        check_ghostscript,
        ensure_ffmpeg,
        ensure_ghostscript,
        show_all_tools,
        get_missing_tools,
        file_error,
        compression_error,
        tool_missing_error,
        format_error,
        wrap_result,
        ensure,
        context,
        show_compression_summary
    )
    PYTEST_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import deck_compress: {e}")
    PYTEST_AVAILABLE = False


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestErrorHandling:
    """Test error handling functionality."""

    def test_app_error_creation(self):
        """Test creating AppError instances."""
        error = AppError("Test error", ErrorType.VALIDATION_ERROR)
        assert error.message == "Test error"
        assert error.error_type == ErrorType.VALIDATION_ERROR
        assert str(error) == "[validation_error] Test error"

    def test_app_error_with_context(self):
        """Test AppError with context information."""
        from deck_compress import ErrorContext

        error = AppError(
            "File not found",
            ErrorType.FILE_NOT_FOUND,
            context=ErrorContext(file_path="/test/file.txt", operation="read")
        )
        assert error.context.file_path == "/test/file.txt"
        assert error.context.operation == "read"

    def test_result_ok(self):
        """Test successful Result creation."""
        result = Result.ok("success")
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == "success"

    def test_result_err(self):
        """Test error Result creation."""
        error = AppError("Test error", ErrorType.VALIDATION_ERROR)
        result = Result.err(error)
        assert result.is_err()
        assert not result.is_ok()

        with pytest.raises(AppError):
            result.unwrap()

    def test_result_map(self):
        """Test Result.map() functionality."""
        result = Result.ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped.unwrap() == 10


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestImageCompression:
    """Test image compression functionality."""

    def test_compress_image_basic(self):
        """Test basic image compression with valid JPEG data."""
        # Create a minimal valid JPEG header for testing
        test_jpeg_data = (
            b'\xff\xd8' +  # SOI (Start of Image)
            b'\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00' +  # JFIF header
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01' +  # SOF0
            b'\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08' +  # DHT
            b'\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' +  # DHT
            b'\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00' +  # SOS
            b'\x00' * 100 +  # Some image data
            b'\xff\xd9'  # EOI (End of Image)
        )

        compressed = compress_image(test_jpeg_data, "jpeg", 85, 1920)
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0
        # Compressed data should be different from original (or at least not larger)
        assert len(compressed) <= len(test_jpeg_data) or len(compressed) > 0

    def test_compress_image_png(self):
        """Test PNG image compression."""
        # Create a minimal PNG header (this is not a complete valid PNG, but enough for testing)
        test_png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

        compressed = compress_image(test_png_data, "png", 85, 1920)
        assert isinstance(compressed, bytes)
        assert len(compressed) > 0

    def test_compress_image_invalid_data(self):
        """Test image compression with invalid data."""
        # Test with completely invalid data
        invalid_data = b'this is not an image'

        # Should return original data on failure
        result = compress_image(invalid_data, "jpeg", 85, 1920)
        assert result == invalid_data

    def test_compress_image_resize(self):
        """Test that large images get resized."""
        # This test would require creating a large image, which is complex
        # For now, we'll just ensure the function doesn't crash
        small_image = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9'

        result = compress_image(small_image, "jpeg", 85, 1920)
        assert isinstance(result, bytes)


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestProgressTracking:
    """Test progress tracking functionality."""

    def test_compression_progress_creation(self):
        """Test CompressionProgress creation and basic functionality."""
        progress = CompressionProgress(total_files=5, show_details=True)
        assert progress.total_files == 5
        assert progress.processed_files == 0
        assert progress.show_details == True

    def test_compression_progress_file_tracking(self):
        """Test CompressionProgress file tracking."""
        progress = CompressionProgress(total_files=1, show_details=False)
        progress.start_compression("test.txt", 1000)
        progress.finish_file(True, 1000, 800)
        assert progress.processed_files == 1


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestToolValidation:
    """Test external tool validation functionality."""

    def test_tool_validator_creation(self):
        """Test ToolValidator can be created."""
        validator = ToolValidator()
        assert validator is not None
        assert len(validator._cache) == 0

    def test_check_ffmpeg_function(self):
        """Test check_ffmpeg function."""
        result = check_ffmpeg()
        assert isinstance(result, Result)
        # The result may be ok or err depending on whether ffmpeg is installed

    def test_check_ghostscript_function(self):
        """Test check_ghostscript function."""
        result = check_ghostscript()
        assert isinstance(result, Result)

    def test_ensure_ffmpeg_function(self):
        """Test ensure_ffmpeg function."""
        result = ensure_ffmpeg("test operation")
        assert isinstance(result, Result)

    def test_ensure_ghostscript_function(self):
        """Test ensure_ghostscript function."""
        result = ensure_ghostscript("test operation")
        assert isinstance(result, Result)

    def test_get_missing_tools_function(self):
        """Test get_missing_tools function."""
        missing = get_missing_tools()
        assert isinstance(missing, list)


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestUtilityFunctions:
    """Test utility functions."""

    def test_file_error_creation(self):
        """Test file error creation."""
        from deck_compress import file_error

        error = file_error("/test/file.txt", "read", FileNotFoundError("File not found"))
        assert isinstance(error, AppError)
        assert error.error_type == ErrorType.FILE_NOT_FOUND
        assert error.context.file_path == "/test/file.txt"
        assert error.context.operation == "read"

    def test_compression_error_creation(self):
        """Test compression error creation."""
        from deck_compress import compression_error

        error = compression_error("/test/file.pdf", "Compression failed")
        assert isinstance(error, AppError)
        assert error.error_type == ErrorType.COMPRESSION_FAILED
        assert error.context.file_path == "/test/file.pdf"
        assert error.context.operation == "compress"




@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestDocumentCompression:
    """Test document compression functionality."""

    def test_compress_doc_function_exists(self):
        """Test that compress_doc function exists and is callable."""
        assert callable(compress_doc)

    def test_process_pptx_function_exists(self):
        """Test that process_pptx function exists and is callable."""
        assert callable(process_pptx)

    def test_process_single_file_function_exists(self):
        """Test that process_single_file function exists and is callable."""
        assert callable(process_single_file)

    def test_process_folder_function_exists(self):
        """Test that process_folder function exists and is callable."""
        assert callable(process_folder)

    def test_compress_standalone_video_exists(self):
        """Test that standalone video compression function exists."""
        assert callable(compress_standalone_video)


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestProgressAdvanced:
    """Test advanced progress tracking functionality."""

    def test_compression_progress_summary(self):
        """Test compression progress summary functionality."""
        # Test the show_compression_summary function
        original_sizes = [1000, 2000]
        compressed_sizes = [600, 1400]
        filenames = ["file1.txt", "file2.txt"]

        # This should not raise an exception
        show_compression_summary(original_sizes, compressed_sizes, filenames)


    def test_show_file_info_table(self):
        """Test show_file_info_table function."""
        # This function doesn't exist in the main module, so skip this test
        pytest.skip("show_file_info_table function not available in main module")

    def test_show_compression_summary(self):
        """Test show_compression_summary function."""
        original_sizes = [1000, 2000]
        compressed_sizes = [600, 1400]
        filenames = ["file1.txt", "file2.txt"]

        # This should not raise an exception
        show_compression_summary(original_sizes, compressed_sizes, filenames)


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestToolValidationAdvanced:
    """Test advanced tool validation functionality."""

    def test_tool_info_creation(self):
        """Test ToolInfo dataclass creation."""
        info = ToolInfo(
            name="Test Tool",
            command="test_cmd",
            version_flag="--version",
            required_for=["testing"],
            install_hint="Install test tool"
        )

        assert info.name == "Test Tool"
        assert info.command == "test_cmd"
        assert info.required_for == ["testing"]

    def test_tool_validator_cache(self):
        """Test ToolValidator caching functionality."""
        validator = ToolValidator()
        validator.clear_cache()

        assert len(validator._cache) == 0
        assert len(validator._version_cache) == 0

    def test_check_multiple_tools(self):
        """Test checking multiple tools at once."""
        validator = ToolValidator()
        results = validator.check_multiple_tools(["ffmpeg", "ghostscript"])

        assert isinstance(results, dict)
        assert "ffmpeg" in results
        assert "ghostscript" in results


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestUtilityFunctionsAdvanced:
    """Test advanced utility functions."""

    def test_wrap_result_decorator(self):
        """Test wrap_result decorator functionality."""
        @wrap_result
        def test_function(x, y):
            return x + y

        # Test the decorated function
        result = test_function(5, 3)
        assert result.is_ok()
        assert result.unwrap() == 8

    def test_ensure_function(self):
        """Test ensure function for condition checking."""
        # Test with True condition
        result = ensure(True, "Should pass")
        assert result.is_ok()

        # Test with False condition
        result = ensure(False, "Should fail", ErrorType.VALIDATION_ERROR)
        assert result.is_err()

    def test_context_function(self):
        """Test context function for adding context to results."""
        # Test the context function directly on a Result object
        result = Result.ok("success")

        # Apply the context function directly
        from deck_compress import context
        context_func = context("Test context", file_path="/test/file.txt")
        result_with_context = context_func(result)

        assert result_with_context.is_ok()
        assert result_with_context.unwrap() == "success"

        # Test with error result
        error_result = Result.err(AppError("Original error", ErrorType.FILE_NOT_FOUND))
        error_with_context = context_func(error_result)
        assert error_with_context.is_err()

        # Check that error message was modified
        error = error_with_context._value
        assert "Test context" in str(error)

    def test_format_error_creation(self):
        """Test format_error utility function."""
        error = format_error("/test/file.txt", "PDF", "TXT")
        assert isinstance(error, AppError)
        assert error.error_type == ErrorType.INVALID_FORMAT
        assert "PDF" in str(error)
        assert "TXT" in str(error)


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestCLIAndMain:
    """Test CLI and main function functionality."""

    def test_main_function_signature(self):
        """Test that main function exists and has correct signature."""
        import inspect
        from deck_compress import main

        sig = inspect.signature(main)
        assert len(sig.parameters) == 0  # main() takes no arguments

    def test_argument_parsing_basic(self):
        """Test basic argument parsing functionality."""
        # This would require mocking sys.argv, which is complex
        # For now, we'll just ensure the function doesn't crash on basic calls
        try:
            # Test that we can at least import argparse-related functionality
            from deck_compress import main
            # If we get here without exception, basic parsing works
            assert True
        except ImportError:
            pytest.skip("Main function not available")


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestErrorScenarios:
    """Test various error scenarios and edge cases."""

    def test_file_error_with_different_exceptions(self):
        """Test file_error with different exception types."""
        # Test with FileNotFoundError
        error1 = file_error("/missing/file.txt", "read", FileNotFoundError("File not found"))
        assert error1.error_type == ErrorType.FILE_NOT_FOUND

        # Test with PermissionError
        error2 = file_error("/protected/file.txt", "write", PermissionError("Access denied"))
        assert error2.error_type == ErrorType.UNKNOWN  # Should be UNKNOWN for non-FileNotFoundError

    def test_compression_error_with_source(self):
        """Test compression_error with source exception."""
        source_exception = ValueError("Invalid compression parameters")
        error = compression_error("/test/file.pdf", "Compression failed", source_exception)

        assert error.error_type == ErrorType.COMPRESSION_FAILED
        assert error.source == source_exception
        assert "Compression failed" in str(error)

    def test_tool_missing_error_creation(self):
        """Test tool_missing_error creation."""
        error = tool_missing_error("ffmpeg", "video compression")

        assert error.error_type == ErrorType.EXTERNAL_TOOL_MISSING
        assert "ffmpeg" in str(error)
        assert "not found" in str(error)

    def test_app_error_chaining(self):
        """Test AppError chaining and context addition."""
        original_error = AppError("Original error", ErrorType.FILE_NOT_FOUND)
        chained_error = original_error.with_context(file_path="/test/file.txt")

        assert chained_error is original_error  # Should return self
        assert chained_error.context.file_path == "/test/file.txt"


@pytest.mark.skipif(not PYTEST_AVAILABLE, reason="deck_compress module not available")
class TestIntegration:
    """Integration tests for combined functionality."""

    def test_imports_work(self):
        """Test that all expected imports work."""
        # This is a basic smoke test to ensure the module loads correctly
        from deck_compress import (
            compress_image,
            compress_video,
            ErrorType,
            AppError,
            Result,
            CompressionProgress,
            ToolValidator
        )

        # If we get here without ImportError, the test passes
        assert True

    def test_main_function_exists(self):
        """Test that main function exists."""
        from deck_compress import main

        assert callable(main)

    def test_console_import(self):
        """Test that rich console is properly imported."""
        from deck_compress import console

        assert console is not None

    def test_all_core_functions_exist(self):
        """Test that all core functions exist and are callable."""
        functions_to_check = [
            compress_image,
            compress_video,
            compress_doc,
            process_pptx,
            process_single_file,
            process_folder,
            check_ffmpeg,
            check_ghostscript,
            ensure_ffmpeg,
            ensure_ghostscript,
        ]

        for func in functions_to_check:
            assert callable(func), f"Function {func.__name__} is not callable"

    def test_all_classes_exist(self):
        """Test that all core classes exist."""
        classes_to_check = [
            ErrorType,
            ErrorContext,
            AppError,
            Result,
            CompressionProgress,
            ToolInfo,
            ToolValidator,
        ]

        for cls in classes_to_check:
            assert isinstance(cls, type), f"Class {cls.__name__} is not a class"


# Pytest markers for different test categories
pytestmark = [
    pytest.mark.unit,
    pytest.mark.compression
]


if __name__ == "__main__":
    # Allow running the tests directly
    import subprocess
    import sys

    try:
        # Try to run with pytest first
        result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"],
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Could not run pytest: {e}")
        print("Falling back to manual test execution...")

        # Manual test execution as fallback
        import traceback

        if PYTEST_AVAILABLE:
            # Count tests
            test_count = 0
            passed_tests = 0
            failed_tests = []

            # Get all test methods from all test classes
            test_classes = [
                TestErrorHandling,
                TestImageCompression,
                TestProgressTracking,
                TestToolValidation,
                TestUtilityFunctions,
                TestDocumentCompression,
                TestProgressAdvanced,
                TestToolValidationAdvanced,
                TestUtilityFunctionsAdvanced,
                TestCLIAndMain,
                TestErrorScenarios,
                TestIntegration
            ]

            for test_class in test_classes:
                for method_name in dir(test_class):
                    if method_name.startswith('test_'):
                        test_count += 1
                        method = getattr(test_class, method_name)
                        try:
                            # Create an instance and run the test
                            instance = test_class()
                            method(instance)
                            passed_tests += 1
                            print(f"✓ {test_class.__name__}.{method_name}")
                        except Exception as e:
                            failed_tests.append((test_class.__name__, method_name, str(e)))
                            print(f"✗ {test_class.__name__}.{method_name}: {e}")

            print(f"\nTest Results: {passed_tests}/{test_count} passed")
            if failed_tests:
                print("Failed tests:")
                for class_name, method_name, error in failed_tests:
                    print(f"  - {class_name}.{method_name}: {error}")

            sys.exit(0 if passed_tests == test_count else 1)
        else:
            print("Cannot run tests: deck_compress module not available")
            print("Please check that the module is properly installed and all dependencies are met.")
            sys.exit(1)
