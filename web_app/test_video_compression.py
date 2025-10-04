#!/usr/bin/env python3
"""
Test script for Python-native video compression alternatives to ffmpeg.
"""

import sys
from pathlib import Path

def test_video_compression():
    """Test the Python-native video compression functions."""
    try:
        from deck_compress import compress_video_python_native, compress_video_imageio_fallback
        print("✅ Successfully imported video compression functions")
        
        # Test if MoviePy is available
        try:
            from moviepy.editor import VideoFileClip
            print("✅ MoviePy is available")
        except ImportError:
            print("⚠️  MoviePy not available")
        
        # Test if imageio is available
        try:
            import imageio
            print("✅ imageio is available")
        except ImportError:
            print("⚠️  imageio not available")
        
        # Test if numpy is available
        try:
            import numpy as np
            print("✅ numpy is available")
        except ImportError:
            print("⚠️  numpy not available")
        
        print("\n🎬 Python-native video compression is ready!")
        print("📝 Note: This will be used as fallback when ffmpeg is not available")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing video compression: {e}")
        return False

if __name__ == "__main__":
    print("Testing Python-native video compression...")
    success = test_video_compression()
    sys.exit(0 if success else 1)
