#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Trace Analysis Web Demo startup script
"""

import os
import sys
import subprocess


def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import importlib.util

        if importlib.util.find_spec("flask") is not None:
            print("✓ Flask installed")
            return True
        else:
            raise ImportError("Flask not found")
    except ImportError:
        print("✗ Flask not installed")
        print("Please use the following command to install dependencies:")
        print("  uv sync")
        print("or:")
        print("  uv pip install -r requirements.txt")
        return False


def install_dependencies():
    """Install dependencies (recommended to use uv)"""
    print("Installing dependencies...")
    try:
        # Try using uv first
        try:
            subprocess.check_call(["uv", "sync"])
            print("✓ Dependencies installed using uv")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fall back to pip
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
            )
            print("✓ Dependencies installed using pip")
            return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install dependencies")
        print("Please run manually: uv sync or pip install -r requirements.txt")
        return False


def main():
    """Main function"""
    import argparse

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Trace Analysis Web Demo")
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=5000,
        help="Specify port number (default: 5000)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Trace Analysis Web Demo")
    print("=" * 50)

    # Check dependencies
    if not check_dependencies():
        print("\nInstalling dependencies...")
        if not install_dependencies():
            print(
                "Please install dependencies manually: pip install -r requirements.txt"
            )
            return

    # Check JSON files
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    json_files = [
        f for f in os.listdir(os.path.join(parent_dir, "..")) if f.endswith(".json")
    ]

    if not json_files:
        print("\nWarning: No JSON files found in parent directory")
        print(
            "Please ensure there are trace JSON files in the trace_analyze/ directory"
        )
    else:
        print(f"\nFound {len(json_files)} JSON files:")
        for file in json_files[:5]:  # Show only first 5
            print(f"  - {file}")
        if len(json_files) > 5:
            print(f"  ... and {len(json_files) - 5} other files")

    # Start application
    print("\nStarting web application...")
    print(f"Application will run at http://localhost:{args.port}")
    print("Press Ctrl+C to stop the application")
    print("=" * 50)

    try:
        from app import app

        app.run(debug=True, host="0.0.0.0", port=args.port)
    except KeyboardInterrupt:
        print("\nApplication stopped")
    except Exception as e:
        print(f"\nFailed to start application: {e}")


if __name__ == "__main__":
    main()
