#!/usr/bin/env python3
"""Convenience runner script for Kaggle environments and multi-instance training."""

from __future__ import annotations

import os
import sys

# Ensure local 'src' is importable even without editable package installation
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if os.path.isdir(src_path) and src_path not in sys.path:
    sys.path.insert(0, src_path)

from malware_segmentation.cli import main

if __name__ == "__main__":
    # If invoked directly without a subcommand (e.g. python kaggle_runner.py -i 1),
    # automatically default to the 'kaggle' subcommand.
    subcommands = {"download", "preprocess", "visualize", "configs", "train", "predict", "run-all", "kaggle"}
    if len(sys.argv) > 1 and sys.argv[1] not in subcommands and not sys.argv[1].startswith("-h") and sys.argv[1] != "--version":
        sys.argv.insert(1, "kaggle")
    main()
