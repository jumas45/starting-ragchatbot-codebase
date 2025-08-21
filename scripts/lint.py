#!/usr/bin/env python3
"""Script to run linting checks using flake8 and mypy."""

import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"Running {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"[OK] {description} passed")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description} failed")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False


def main():
    """Main function to run linting tools."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    
    success = True
    
    # Run flake8 for style and error checking
    success &= run_command(
        ["uv", "run", "flake8", str(src_dir)],
        "flake8 style checking"
    )
    
    # Run mypy for type checking
    success &= run_command(
        ["uv", "run", "mypy", str(src_dir)],
        "mypy type checking"
    )
    
    if success:
        print("\nAll linting checks passed!")
        return 0
    else:
        print("\nSome linting checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())