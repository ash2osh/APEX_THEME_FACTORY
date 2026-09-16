#!/usr/bin/env python3
"""Minimal stand-in for the two `apex validate` compiler checks that bit the live matrix.

  MISSING_PROPERTY_VALUE  - `fileUrls:` with no value or an empty list
  REFERENCE_NOT_FOUND     - a `file "..."` entry in static-files.apx without the physical file

Prints `APEXlang Compile Errors` lines like SQLcl and exits 1 when anything is wrong.
"""

from pathlib import Path
import re
import sys


def lint(export_dir: Path) -> list[str]:
    errors = []
    for path in export_dir.rglob("*.apx"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"fileUrls:[ \t]*(\[\s*\]|\n|$)", text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"File: {path.relative_to(export_dir)}\nLine: {line}\nType: MISSING_PROPERTY_VALUE\n"
                          "Error: Invalid property (specified property has to have a value): fileUrls")
        if path.name == "static-files.apx":
            for match in re.finditer(r'^file\s+("?)([^"\n]+?)\1\s*\(', text, re.MULTILINE):
                if not (path.parent / "static-files" / match.group(2)).is_file():
                    errors.append(f"File: shared-components/static-files.apx\nType: REFERENCE_NOT_FOUND\n"
                                  f"Error: referenced file shared-components/static-files/{match.group(2)} in the fileName property is not found")
    return errors


if __name__ == "__main__":
    problems = lint(Path(sys.argv[1]))
    if problems:
        print("APEXlang Compile Errors:")
        print("\n\n".join(problems))
        sys.exit(1)
    print("Validation successful.")
