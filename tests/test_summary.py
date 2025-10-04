#!/usr/bin/env python3
"""
Test summary script to show test coverage and structure
"""

import sys
import os

def count_tests():
    """Count the number of tests in each test class."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        # Import test classes dynamically to avoid import errors
        from test_deck_compress import (
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
        )

        test_classes = [
            ("TestErrorHandling", TestErrorHandling),
            ("TestImageCompression", TestImageCompression),
            ("TestProgressTracking", TestProgressTracking),
            ("TestToolValidation", TestToolValidation),
            ("TestUtilityFunctions", TestUtilityFunctions),
            ("TestDocumentCompression", TestDocumentCompression),
            ("TestProgressAdvanced", TestProgressAdvanced),
            ("TestToolValidationAdvanced", TestToolValidationAdvanced),
            ("TestUtilityFunctionsAdvanced", TestUtilityFunctionsAdvanced),
            ("TestCLIAndMain", TestCLIAndMain),
            ("TestErrorScenarios", TestErrorScenarios),
            ("TestIntegration", TestIntegration),
        ]

        print("🧪 Deck Compress Test Suite Summary")
        print("=" * 50)

        total_tests = 0
        for class_name, test_class in test_classes:
            test_methods = [method for method in dir(test_class) if method.startswith('test_')]
            num_tests = len(test_methods)
            total_tests += num_tests

            print(f"{class_name"25"} | {num_tests"2d"} tests | {', '.join(test_methods[:3])}{'...' if len(test_methods) > 3 else ''}")

        print("-" * 50)
        print(f"{'TOTAL'"25"} | {total_tests"2d"} tests")
        print()
        print("📋 Test Categories:")
        print("  • Error Handling - AppError, Result types, context management")
        print("  • Image Compression - JPEG/PNG handling, resizing, error cases")
        print("  • Progress Tracking - OperationType enum, ProgressTracker functionality")
        print("  • Tool Validation - External tool checking (ffmpeg, ghostscript)")
        print("  • PDF Compression - Multiple compression strategies")
        print("  • Document Processing - PPTX, DOCX, single file processing")
        print("  • Advanced Progress - ProgressStats, MultiFileProgressTracker")
        print("  • Advanced Tool Validation - ToolInfo, caching, batch checking")
        print("  • Utility Functions - Decorators, condition checking")
        print("  • CLI & Main - Main function, argument parsing")
        print("  • Error Scenarios - Edge cases, exception handling")
        print("  • Integration - Import verification, function existence")

        return total_tests

    except ImportError as e:
        print(f"❌ Could not import test classes: {e}")
        return 0

if __name__ == "__main__":
    count_tests()
