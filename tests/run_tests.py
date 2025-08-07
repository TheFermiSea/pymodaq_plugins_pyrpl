#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Runner for PyMoDAQ PyRPL Plugin Tests

This script provides a convenient way to run different categories of tests
for the PyMoDAQ PyRPL plugin functionality.

Usage Examples:
    python tests/run_tests.py --all          # Run all tests (default)
    python tests/run_tests.py --mock         # Run only mock tests
    python tests/run_tests.py --hardware     # Run hardware tests (requires PYRPL_TEST_HOST)
    python tests/run_tests.py --integration  # Run integration tests
    python tests/run_tests.py --performance  # Run performance tests
    python tests/run_tests.py --coverage     # Run with coverage report

Author: Claude Code
License: MIT
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    if description:
        print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Run PyMoDAQ PyRPL Plugin Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Test category options
    parser.add_argument('--all', action='store_true', 
                       help='Run all tests (default)')
    parser.add_argument('--mock', action='store_true',
                       help='Run only mock hardware tests')
    parser.add_argument('--hardware', action='store_true',
                       help='Run real hardware tests (requires PYRPL_TEST_HOST env var)')
    parser.add_argument('--integration', action='store_true',
                       help='Run integration tests')
    parser.add_argument('--thread-safety', action='store_true',
                       help='Run thread safety tests')
    parser.add_argument('--error-handling', action='store_true',
                       help='Run error handling tests')
    parser.add_argument('--performance', action='store_true',
                       help='Run performance tests')
    
    # Output options
    parser.add_argument('--coverage', action='store_true',
                       help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet output (minimal)')
    
    args = parser.parse_args()
    
    # Default to all tests if no specific category chosen
    if not any([args.mock, args.hardware, args.integration, args.thread_safety,
                args.error_handling, args.performance]):
        args.all = True
    
    # Base pytest command
    base_cmd = ['python', '-m', 'pytest', 'tests/test_pyrpl_functionality.py']
    
    # Add output options
    if args.verbose:
        base_cmd.append('-v')
    elif args.quiet:
        base_cmd.extend(['-q', '--tb=line'])
    
    # Add coverage if requested
    if args.coverage:
        base_cmd.extend(['--cov=pymodaq_plugins_pyrpl', '--cov-report=html', '--cov-report=term'])
    
    success = True
    
    if args.all:
        cmd = base_cmd.copy()
        success &= run_command(cmd, "All PyRPL functionality tests")
    
    if args.mock:
        cmd = base_cmd + ['-m', 'mock']
        success &= run_command(cmd, "Mock hardware tests")
    
    if args.hardware:
        # Check if hardware environment is set
        if not os.getenv('PYRPL_TEST_HOST'):
            print("\nWARNING: PYRPL_TEST_HOST environment variable not set.")
            print("Hardware tests will be skipped.")
            print("\nTo run hardware tests, set the environment variable:")
            print("export PYRPL_TEST_HOST=your-redpitaya-hostname")
        
        cmd = base_cmd + ['-m', 'hardware']
        success &= run_command(cmd, "Real hardware tests")
    
    if args.integration:
        cmd = base_cmd + ['-m', 'integration']
        success &= run_command(cmd, "Integration tests")
    
    if args.thread_safety:
        cmd = base_cmd + ['-m', 'thread_safety']
        success &= run_command(cmd, "Thread safety tests")
    
    if args.error_handling:
        cmd = base_cmd + ['-m', 'error_handling']
        success &= run_command(cmd, "Error handling tests")
    
    if args.performance:
        cmd = base_cmd + ['-m', 'performance']
        success &= run_command(cmd, "Performance tests")
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    if success:
        print("✅ All requested tests passed!")
        return_code = 0
    else:
        print("❌ Some tests failed.")
        return_code = 1
    
    # Additional information
    print(f"\nTest files location: {Path('tests').absolute()}")
    print("\nAvailable test markers:")
    print("  - mock: Tests with mock hardware only")
    print("  - hardware: Tests requiring real Red Pitaya")
    print("  - integration: Integration tests")
    print("  - thread_safety: Thread safety validation") 
    print("  - error_handling: Error handling and recovery")
    print("  - performance: Performance and timing tests")
    
    print("\nFor more options, run: pytest tests/test_pyrpl_functionality.py --help")
    
    return return_code


if __name__ == '__main__':
    sys.exit(main())