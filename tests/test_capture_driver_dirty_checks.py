"""Structural check for plan Task 4: the capture drivers must re-check the working tree inside
their per-unit-of-work loops, not only once before them. A call to assert_clean_source() that sits
above the loop (like the original single startup check) would satisfy a naive "is it called
anywhere" grep but not the actual defect - a tree that goes dirty mid-run must abort within the
operation it corrupts, not after.

This walks the AST of each driver's main() rather than running it, since a real run needs SQLcl /
Chrome MCP; the property being protected is structural (call site is nested inside a For loop),
so an AST check is the honest, correctly-scoped test for it.
"""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent


def _main_function(module_path: Path) -> ast.FunctionDef:
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError(f"{module_path} has no top-level main()")


def _calls_assert_clean_source_inside_a_for_loop(func: ast.FunctionDef) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.For):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call):
                    name = inner.func.id if isinstance(inner.func, ast.Name) else getattr(inner.func, "attr", None)
                    if name == "assert_clean_source":
                        return True
    return False


class DirtyTreeReCheckedPerUnitOfWorkTests(unittest.TestCase):
    def test_live_matrix_checks_before_each_consumers_lifecycle(self):
        func = _main_function(ROOT / "tools" / "live_matrix.py")
        self.assertTrue(
            _calls_assert_clean_source_inside_a_for_loop(func),
            "live_matrix.py's main() must call assert_clean_source() inside the per-target loop, "
            "not only once before it",
        )

    def test_browser_matrix_checks_before_each_row(self):
        func = _main_function(ROOT / "tools" / "browser_matrix.py")
        self.assertTrue(
            _calls_assert_clean_source_inside_a_for_loop(func),
            "browser_matrix.py's main() must call assert_clean_source() inside the per-row loop, "
            "not only once before it",
        )


if __name__ == "__main__":
    unittest.main()
