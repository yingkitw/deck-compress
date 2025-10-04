#!/usr/bin/env python3
"""
Simple test for video compression without crashing.
"""

import sys
from pathlib import Path

def test_video_compression_safe():
    """Test video compression with safe error handling."""
    try:
        from deck_compress import compress_video_python_native, compress_video_imageio_fallback
        
        print("Testing video compression functions...")
        
        # Test with a non-existent file (should not crash)
        test_input = Path("nonexistent_video.mp4")
        test_output = Path("test_output.mp4")
        
        print("1. Testing with non-existent file (should fail gracefully)...")
        result = compress_video_python_native(test_input, test_output, 28)
        print(f"   Result: {result} (expected: False)")
        
        print("2. Testing imageio fallback with non-existent file...")
        result = compress_video_imageio_fallback(test_input, test_output, 28)
        print(f"   Result: {result} (expected: False)")
        
        print("✅ All tests completed without crashing!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Running safe video compression test...")
    success = test_video_compression_safe()
    sys.exit(0 if success else 1)
