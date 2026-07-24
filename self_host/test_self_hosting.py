#!/usr/bin/env python3
"""
Test script to verify the self-hosted Zap interpreter.
This script runs the self-hosted Zap files via the Zap CLI.
"""

import sys
import os
import subprocess

def run_zap_file(filepath, args=None):
    """Run a Zap file using the Zap CLI."""
    cmd = [sys.executable, "-m", "src", "run", filepath]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)) + "/..")
    return result

def test_basic_self_hosting():
    """Test basic self-hosted functionality."""
    print("Testing Basic Self-Hosting")
    print("=" * 50)
    
    # Test hello.zap
    print("\n1. Running hello.zap...")
    result = run_zap_file("self_host/hello.zap")
    if result.returncode == 0:
        print("   PASSED")
        print(result.stdout)
    else:
        print("   FAILED")
        print(result.stderr)
        return False
    
    # Test tokens.zap
    print("\n2. Running tokens.zap...")
    result = run_zap_file("self_host/tokens.zap")
    if result.returncode == 0:
        print("   PASSED")
        print(result.stdout[:500])  # Truncate output
    else:
        print("   FAILED")
        print(result.stderr)
        return False
    
    # Test self_host_interpreter.zap
    print("\n3. Running self_host_interpreter.zap...")
    result = run_zap_file("self_host/self_host_interpreter.zap")
    if result.returncode == 0:
        print("   PASSED")
        print(result.stdout[:500])
    else:
        print("   FAILED")
        print(result.stderr)
        return False
    
    return True

def test_enhanced_features():
    """Test enhanced features like comprehensions, interpolation."""
    print("\nTesting Enhanced Features")
    print("=" * 50)
    
    # Test with examples that use comprehensions
    print("\n1. Testing comprehensions.zap...")
    result = run_zap_file("examples/comprehensions.zap")
    if result.returncode == 0:
        print("   PASSED")
        print(result.stdout)
    else:
        print("   FAILED")
        print(result.stderr)
        return False
    
    # Test string interpolation
    print("\n2. Testing interp.zap...")
    result = run_zap_file("examples/interp.zap")
    if result.returncode == 0:
        print("   PASSED")
        print(result.stdout)
    else:
        print("   FAILED")
        print(result.stderr)
        return False
    
    return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Self-Hosted Zap Interpreter Test Suite")
        print("=" * 50)
        print("Usage:")
        print("  python test_self_hosting.py                    # Run basic tests")
        print("  python test_self_hosting.py enhanced        # Run enhanced feature tests")
        print("  python test_self_hosting.py all             # Run all tests")
        return 0
    
    print("Self-Hosted Zap Interpreter Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    # Run basic tests
    try:
        if not test_basic_self_hosting():
            all_passed = False
    except Exception as e:
        print(f"Basic tests failed with exception: {e}")
        all_passed = False
    
    # Run enhanced tests if requested
    if "--enhanced" in sys.argv or "all" in sys.argv or len(sys.argv) == 1:
        try:
            if not test_enhanced_features():
                all_passed = False
        except Exception as e:
            print(f"Enhanced tests failed with exception: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("ALL TESTS PASSED! Self-hosting is working correctly!")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())