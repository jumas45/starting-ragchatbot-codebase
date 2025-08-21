#!/usr/bin/env python3
"""Script to run all code quality checks."""

import subprocess
import sys
from pathlib import Path


def run_script(script_name: str) -> bool:
    """Run a quality check script and return True if successful."""
    script_path = Path(__file__).parent / script_name
    try:
        result = subprocess.run([sys.executable, str(script_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Main function to run all quality checks."""
    print("Running comprehensive code quality checks...\n")
    
    success = True
    
    # Run formatting first
    print("=" * 50)
    print("FORMATTING")
    print("=" * 50)
    success &= run_script("format.py")
    
    print("\n" + "=" * 50)
    print("LINTING")
    print("=" * 50)
    success &= run_script("lint.py")
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if success:
        print("All quality checks completed successfully!")
        return 0
    else:
        print("Some quality checks failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())