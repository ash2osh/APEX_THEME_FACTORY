"""How a static file is registered in APEXLang `shared-components/static-files.apx`.

Shared by the package installer and the app 102 sync so both write the same block. charSet is
only declared for text content: APEX ignores it for binaries, but declaring one is a false
statement in generated source. image/svg+xml is XML text and keeps it.
"""

from pathlib import PurePosixPath

MIME_BY_SUFFIX = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".map": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".woff2": "font/woff2",
    ".txt": "text/plain",
}
TEXT_MIME_TYPES = frozenset({"application/javascript", "application/json", "image/svg+xml"})


def mime_type(rel: str) -> str:
    return MIME_BY_SUFFIX.get(PurePosixPath(rel).suffix.lower(), "application/octet-stream")


def is_text_mime(mime: str) -> bool:
    return mime.startswith("text/") or mime in TEXT_MIME_TYPES


def file_block(rel: str) -> str:
    """The `file "<rel>" ( ... )` block for one static file, without a trailing newline."""
    mime = mime_type(rel)
    charset = "\n    charSet: utf-8" if is_text_mime(mime) else ""
    return f'file "{rel}" (\n    mimeType: {mime}{charset}\n)'
