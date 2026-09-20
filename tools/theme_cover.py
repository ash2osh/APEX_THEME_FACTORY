#!/usr/bin/env python3
"""Capture a theme cover through the project's shared Chrome DevTools daemon."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import struct
import tempfile
from typing import Any

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import NAME_REGEX


PAGE_500 = "http://localhost:8181/ords/r/demo/ut/getting-started"
CAPTURE_VIEWPORT = "1280x700x0.75"
EXPECTED_WIDTH = 960


@dataclass(frozen=True)
class CoverReport:
    status: str
    theme: str
    url: str
    output: Path
    written: bool
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "theme": self.theme,
            "url": self.url,
            "output": str(self.output),
            "written": self.written,
            "width": self.width,
            "height": self.height,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    def to_human(self) -> str:
        dimensions = "" if self.width is None else f" dimensions={self.width}x{self.height}"
        return (
            f"THEME_COVER status={self.status} theme={self.theme} url={self.url} "
            f"output={self.output} written={'yes' if self.written else 'no'}{dimensions}"
        )


def _content_blocks(result: Any) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    content = result.get("content", [])
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def _text(result: Any) -> str:
    return "\n".join(
        str(block.get("text", "")) for block in _content_blocks(result)
        if block.get("type") == "text"
    )


def _json_result(result: Any) -> dict[str, Any]:
    text = _text(result)
    fenced = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    payload = fenced.group(1) if fenced else text[text.find("{"):text.rfind("}") + 1]
    try:
        decoded = json.loads(payload, strict=False)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PackageError("Chrome returned an unreadable page verification result") from exc
    if not isinstance(decoded, dict):
        raise PackageError("Chrome returned an invalid page verification result")
    return decoded


def _selected_page_id(result: Any) -> int:
    matches = re.findall(r"^(\d+): .*\[selected\]", _text(result), re.MULTILINE)
    if len(matches) != 1:
        raise PackageError("Chrome did not identify the newly opened background tab")
    return int(matches[0])


def _screenshot_bytes(result: Any) -> bytes:
    for block in _content_blocks(result):
        if block.get("type") != "image" or not isinstance(block.get("data"), str):
            continue
        payload = block["data"]
        if payload.startswith("data:"):
            payload = payload.split(",", 1)[-1]
        try:
            return base64.b64decode(payload, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise PackageError("Chrome returned invalid base64 screenshot data") from exc
    raise PackageError("Chrome returned no screenshot image")


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    offset = 2
    size_markers = {
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
    }
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            return None
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        if marker in size_markers and offset + 7 <= len(data):
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            return width, height
        if length < 2:
            return None
        offset += length
    return None


def _runtime_script(theme: str) -> str:
    theme_class = json.dumps(f"app-theme-{theme}")
    theme_name = json.dumps(theme)
    return f"""async () => {{
        const root = document.documentElement;
        [...root.classList]
          .filter((name) => name.startsWith('app-theme-'))
          .forEach((name) => root.classList.remove(name));
        root.classList.add({theme_class});
        root.dataset.appThemeCurrent = {theme_name};
        let coverStyle = document.getElementById('theme-factory-cover-style');
        if (!coverStyle) {{
          coverStyle = document.createElement('style');
          coverStyle.id = 'theme-factory-cover-style';
          coverStyle.textContent = '#apexDevToolbar {{ display: none !important; }}';
          document.head.appendChild(coverStyle);
        }}
        if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
        if (document.fonts && document.fonts.ready) await document.fonts.ready;
        return {{
          appId: String(window.apex?.env?.APP_ID ?? ''),
          pageId: String(window.apex?.env?.APP_PAGE_ID ?? ''),
          theme: root.dataset.appThemeCurrent,
          fontsStatus: document.fonts?.status ?? 'unsupported'
        }};
    }}"""


def _console_errors(result: Any) -> list[str]:
    return [
        line.strip() for line in _text(result).splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
        and not line.lstrip().startswith("Emulating viewport:")
        and "no console messages" not in line.lower()
    ]


def _failed_requests(result: Any) -> list[str]:
    failures = []
    for line in _text(result).splitlines():
        if re.search(r"\[(?:4|5)\d\d\]|\bstatus\s+(?:4|5)\d\d\b|\bfailed\b|net::ERR", line,
                     re.IGNORECASE):
            failures.append(line.strip())
    return failures


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            temporary = Path(stream.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def capture_cover(client: Any, theme: str, output: Path, apply: bool, overwrite: bool) -> CoverReport:
    """Capture one isolated theme cover, or report the intended action in dry-run mode."""

    if not NAME_REGEX.fullmatch(theme):
        raise PackageError(f"Theme name '{theme}' must match {NAME_REGEX.pattern}")
    output = Path(output)
    if not apply:
        return CoverReport("DRY_RUN", theme, PAGE_500, output, False)
    if output.exists() and not overwrite:
        raise PackageError(f"Cover already exists at {output}; use --apply --overwrite to replace it")
    if client is None:
        raise PackageError("Cover capture requires the project Chrome daemon client")

    page_id: int | None = None
    try:
        opened = client.call_tool("new_page", {"url": PAGE_500, "background": True})
        page_id = _selected_page_id(opened)
        client.call_tool("emulate", {"pageId": page_id, "viewport": CAPTURE_VIEWPORT})
        client.call_tool("navigate_page", {"pageId": page_id, "url": PAGE_500})
        runtime = _json_result(client.call_tool(
            "evaluate_script", {"pageId": page_id, "function": _runtime_script(theme)}
        ))
        if runtime.get("appId") != "102" or runtime.get("pageId") != "500":
            raise PackageError(
                "Cover capture requires APEX app 102 page 500; "
                f"found app {runtime.get('appId')!r} page {runtime.get('pageId')!r}"
            )
        if runtime.get("theme") != theme:
            raise PackageError(f"Chrome did not apply theme '{theme}' in the capture tab")
        if runtime.get("fontsStatus") not in {"loaded", "unsupported"}:
            raise PackageError("Theme fonts were not ready before capture")

        console = _console_errors(client.call_tool(
            "list_console_messages", {"pageId": page_id, "types": ["error"]}
        ))
        network = _failed_requests(client.call_tool("list_network_requests", {"pageId": page_id}))
        if console or network:
            details = "; ".join((*console, *network))
            raise PackageError(f"Cover capture blocked by runtime errors: {details}")

        screenshot = client.call_tool("take_screenshot", {
            "pageId": page_id, "format": "jpeg", "quality": 90, "fullPage": False,
        })
        data = _screenshot_bytes(screenshot)
        dimensions = _jpeg_dimensions(data)
        if dimensions is None:
            raise PackageError("Chrome screenshot is not a readable JPEG")
        width, height = dimensions
        if width != EXPECTED_WIDTH:
            raise PackageError(f"Chrome screenshot width is {width}px; expected {EXPECTED_WIDTH}px")
        _atomic_write(output, data)
        return CoverReport("CAPTURED", theme, PAGE_500, output, True, width, height)
    finally:
        if page_id is not None:
            try:
                client.call_tool("close_page", {"pageId": page_id})
            except Exception:
                pass
