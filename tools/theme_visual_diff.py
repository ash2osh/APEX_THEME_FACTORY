#!/usr/bin/env python3
"""Deterministic visual-difference summaries for theme cover review."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile

from PIL import Image, UnidentifiedImageError

from lib.theme_factory.errors import PackageError


REVIEW_THRESHOLD_PERCENT = 2.0


@dataclass(frozen=True)
class VisualDiffReport:
    status: str
    baseline: Path
    candidate: Path
    width: int
    height: int
    changed_pixel_percentage: float
    mean_absolute_channel_delta: float
    heatmap_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "baseline": str(self.baseline),
            "candidate": str(self.candidate),
            "width": self.width,
            "height": self.height,
            "changedPixelPercentage": self.changed_pixel_percentage,
            "meanAbsoluteChannelDelta": self.mean_absolute_channel_delta,
            "heatmapPath": str(self.heatmap_path),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)


def _open_rgba(path: Path) -> Image.Image:
    try:
        with Image.open(path) as image:
            return image.convert("RGBA")
    except (OSError, UnidentifiedImageError) as exc:
        raise PackageError(f"Unable to read comparison image: {path}") from exc


def _heatmap_path(baseline: Path, candidate: Path, root: Path) -> Path:
    digest = hashlib.sha256()
    for path in (baseline, candidate):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    name = f"{baseline.stem}-vs-{candidate.stem}-{digest.hexdigest()[:12]}.png"
    return root / name


def _atomic_save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".png", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
        image.save(temporary, format="PNG", optimize=False)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def compare_images(
    baseline: Path,
    candidate: Path,
    *,
    heatmap_root: Path | None = None,
) -> VisualDiffReport:
    """Compare same-sized images and emit neutral metrics plus a review heatmap."""

    baseline = Path(baseline)
    candidate = Path(candidate)
    baseline_image = _open_rgba(baseline)
    candidate_image = _open_rgba(candidate)
    if baseline_image.size != candidate_image.size:
        raise PackageError(
            "Visual diff requires matching dimensions; "
            f"baseline is {baseline_image.width}x{baseline_image.height}, "
            f"candidate is {candidate_image.width}x{candidate_image.height}"
        )

    baseline_bytes = baseline_image.tobytes()
    candidate_bytes = candidate_image.tobytes()
    pixel_count = baseline_image.width * baseline_image.height
    changed_pixels = 0
    absolute_delta = 0
    heatmap_pixels: list[tuple[int, int, int, int]] = []
    for offset in range(0, len(baseline_bytes), 4):
        channel_deltas = [
            abs(baseline_bytes[offset + channel] - candidate_bytes[offset + channel])
            for channel in range(4)
        ]
        maximum = max(channel_deltas)
        if maximum:
            changed_pixels += 1
        absolute_delta += sum(channel_deltas)
        heatmap_pixels.append((maximum, 0, 0, 255))

    changed_percentage = (changed_pixels / pixel_count) * 100.0 if pixel_count else 0.0
    mean_delta = absolute_delta / (pixel_count * 4) if pixel_count else 0.0
    root = Path(heatmap_root) if heatmap_root is not None else Path.cwd() / "scratch/theme-diffs"
    heatmap_path = _heatmap_path(baseline, candidate, root)
    heatmap = Image.new("RGBA", baseline_image.size)
    heatmap.putdata(heatmap_pixels)
    _atomic_save(heatmap, heatmap_path)

    return VisualDiffReport(
        "REVIEW" if changed_percentage > REVIEW_THRESHOLD_PERCENT else "NO_REVIEW",
        baseline,
        candidate,
        baseline_image.width,
        baseline_image.height,
        changed_percentage,
        mean_delta,
        heatmap_path,
    )

