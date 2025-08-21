#!/usr/bin/env python3
"""Pre-commit hook to run quality checks before commits."""

import subprocess
import sys
from pathlib import Path


def run_quality_checks() -> bool:
    """Run quality checks and return True if all pass."""
    script_dir = Path(__file__).parent
    quality_check_script = script_dir / "quality-check.py"
    
    print("Running pre-commit quality checks...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(quality_check_script)], 
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Main function for pre-commit hook."""
    if not run_quality_checks():
        print("\nQuality checks failed. Commit aborted.")
        print("Please fix the issues above and try again.")
        return 1
    
    print("\nAll quality checks passed. Proceeding with commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())