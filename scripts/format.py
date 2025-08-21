#!/usr/bin/env python3
"""Script to format code using black and isort."""

import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return True if successful."""
    print(f"Running {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"[OK] {description} completed successfully")
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
    """Main function to run formatting tools."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    
    success = True
    
    # Run isort first to organize imports
    success &= run_command(
        ["uv", "run", "isort", str(src_dir)],
        "import sorting with isort"
    )
    
    # Run black for code formatting
    success &= run_command(
        ["uv", "run", "black", str(src_dir)],
        "code formatting with black"
    )
    
    if success:
        print("\nAll formatting completed successfully!")
        return 0
    else:
        print("\nSome formatting steps failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())