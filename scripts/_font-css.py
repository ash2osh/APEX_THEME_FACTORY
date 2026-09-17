#!/usr/bin/env python3
"""Emit the generated @font-face + font-token CSS for one theme package (empty if it has none)."""
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from lib.theme_factory.manifest import load_manifest
from lib.theme_factory.css_bundle import render_font_css
root = Path(sys.argv[1]) / "sample-themes" / sys.argv[2]
sys.stdout.write(render_font_css(load_manifest(root / "theme.json", root)))
