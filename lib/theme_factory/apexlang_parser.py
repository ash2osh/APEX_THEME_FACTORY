"""Balanced APEXLang block parsing and owned-fragment helpers."""

import re
from typing import List, Optional, Tuple

from lib.theme_factory.errors import PackageError


MARKER = "APEX_THEME_FACTORY_MANAGED"
# Ownership must live in data APEX stores and re-exports. APEXLang comment lines are not
# part of the APEX metadata model and never come back from `apex export`, so the managed
# Page 0 regions carry an HTML comment inside their source plus a fixed Static ID, and the
# switcher list entries live in the `theme-factory-` static-id namespace.
MARKER_HTML = f"<!-- {MARKER}:BOOTSTRAP -->"
BOOTSTRAP_REGION_IDS = ("theme_factory_bootstrap", "theme_factory_bootstrap_dialog")
BOOTSTRAP_REGION_NAME_PREFIX = "Theme Factory Bootstrap"
SWITCHER_ENTRY_PREFIX = "theme-factory-"
SWITCHER_PARENT_ID = f"{SWITCHER_ENTRY_PREFIX}switcher-parent"
SWITCHER_ITEM_CLASS = "theme-factory-managed-switcher"
RUNTIME_JS_URL = "#APP_FILES#theme-factory/runtime/theme-factory-runtime.js"


def _find_matching_brace(text: str, open_pos: int) -> int:
    depth = 1
    pos = open_pos + 1
    in_str = False
    quote_char = ""
    in_fence = False
    
    while pos < len(text) and depth > 0:
        c = text[pos]
        if in_fence:
            if text[pos:pos+3] == "```":
                in_fence = False
                pos += 3
                continue
        elif text[pos:pos+3] == "```":
            in_fence = True
            pos += 3
            continue
        elif in_str:
            if c == "\\" and pos + 1 < len(text):
                pos += 2
                continue
            if c == quote_char:
                in_str = False
        else:
            if c == '"':
                in_str = True
                quote_char = c
            elif c in "{([":
                depth += 1
            elif c in "})]":
                depth -= 1
                if depth == 0:
                    return pos
        pos += 1
    return -1


def _iter_blocks(text: str, keyword: str):
    """Yield (start, end, identifier, body) for top-level `<keyword> <id> ( ... )` blocks.

    Blocks are consumed whole, so nested occurrences (for example the word `region`
    inside fenced source code of an earlier block) are never matched again.
    """
    pattern = re.compile(rf"^[ \t]*{keyword}[ \t]+(\"[^\"\n]+\"|[^\s(]+)[ \t]*\(", re.MULTILINE)
    position = 0
    while True:
        match = pattern.search(text, position)
        if not match:
            return
        close = _find_matching_brace(text, match.end() - 1)
        if close == -1:
            raise PackageError(f"Unbalanced {keyword} block in APEXLang source")
        end = close + 1
        yield match.start(), end, match.group(1).strip('"'), text[match.start():end]
        position = end


def _remove_spans(text: str, spans: List[Tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        # swallow the line break that followed the block and any blank line before it
        while end < len(text) and text[end] in "\r\n":
            end += 1
        while start > 0 and text[start - 1] in " \t":
            start -= 1
        text = text[:start] + text[end:]
    return re.sub(r"\n{3,}", "\n\n", text)


def _is_bootstrap_identity(identifier: str, body: str) -> bool:
    if identifier in BOOTSTRAP_REGION_IDS:
        return True
    dom_id = re.search(r"htmlDomId:\s*([A-Za-z0-9_-]+)", body)
    if dom_id and dom_id.group(1) in BOOTSTRAP_REGION_IDS:
        return True
    name = re.search(r"^\s*name:\s*(.+?)\s*$", body, re.MULTILINE)
    return bool(name and name.group(1).startswith(BOOTSTRAP_REGION_NAME_PREFIX))


def _is_bootstrap_owned(body: str) -> bool:
    return MARKER_HTML in body or "window.APEX_THEME_FACTORY_CONFIG" in body


def strip_bootstrap_regions(p0_text: str) -> str:
    """Remove the Theme Factory bootstrap regions from Page 0 APEXLang text.

    Ownership is proven by content APEX round-trips (the HTML marker / config object
    inside the region source), never by APEXLang comments. A region that claims the
    managed identity (static id, DOM id or name) without that content is a collision;
    a region that carries our content under a foreign identity is refused as well.
    """
    cleaned = re.sub(
        rf"\s*(?:--|//) {MARKER}:BEGIN:REGIONS[\s\S]*?(?:--|//) {MARKER}:END:REGIONS\s*",
        "\n",
        p0_text,
    )
    spans: List[Tuple[int, int]] = []
    for start, end, identifier, body in _iter_blocks(cleaned, "region"):
        identity = _is_bootstrap_identity(identifier, body)
        owned = _is_bootstrap_owned(body)
        if identity and owned:
            spans.append((start, end))
        elif identity:
            raise PackageError(
                f"Managed Page 0 region name collision: region '{identifier}' uses the Theme Factory "
                "identity but does not contain Theme Factory content"
            )
        elif owned:
            raise PackageError(
                f"Theme Factory bootstrap content found in unmanaged Page 0 region '{identifier}'"
            )
    return _remove_spans(cleaned, spans)


def strip_switcher_entries(nav_text: str) -> str:
    """Remove Theme Factory switcher entries (static-id namespace `theme-factory-`)."""
    cleaned = re.sub(
        rf"\s*(?:--|//) {MARKER}:BEGIN:SWITCHER[\s\S]*?(?:--|//) {MARKER}:END:SWITCHER\s*",
        "\n",
        nav_text,
    )
    spans = [
        (start, end)
        for start, end, identifier, _body in _iter_blocks(cleaned, "entry")
        if identifier.startswith(SWITCHER_ENTRY_PREFIX)
    ]
    return _remove_spans(cleaned, spans)


def _list_block_span(lists_text: str, alias: str) -> Optional[Tuple[int, int]]:
    for start, end, identifier, _body in _iter_blocks(lists_text, "list"):
        if identifier == alias:
            return start, end
    return None


def list_is_static(list_body: str) -> bool:
    source = re.search(r"\bsource\s*\{", list_body)
    if not source:
        return True
    close = _find_matching_brace(list_body, source.end() - 1)
    source_body = list_body[source.end():close if close != -1 else len(list_body)]
    kind = re.search(r"\btype:\s*([A-Za-z]+)", source_body)
    return kind is None or kind.group(1).lower() == "static"


def insert_switcher_entries(lists_text: str, alias: str, entries_code: str) -> str:
    span = _list_block_span(lists_text, alias)
    if span is None:
        raise PackageError(f"Navigation bar list '{alias}' not found in lists source")
    start, end = span
    block = lists_text[start:end]
    last_paren = block.rfind(")")
    new_block = block[:last_paren].rstrip() + "\n\n" + entries_code.rstrip("\n") + "\n\n)"
    return lists_text[:start] + new_block + lists_text[end:]



