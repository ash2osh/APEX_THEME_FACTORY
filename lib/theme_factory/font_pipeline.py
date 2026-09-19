"""Pinned, isolated conversion of bilingual variable fonts into static WOFF2 faces."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Protocol
import urllib.parse
import urllib.request

from lib.theme_factory.errors import PackageError
from lib.theme_factory.manifest import VALID_WEIGHTS, load_manifest
from lib.theme_factory.recipe import FontFaceSpec, FontRoleSpec, load_recipe, render_manifest


FONTTOOLS_VERSION = "4.60.1"
BROTLI_VERSION = "1.1.0"
PINNED_TOOL_PYTHON = "3.12"
USE_MANAGED_TOOL_PYTHON = sys.version_info >= (3, 14)
BASIC_LATIN = frozenset(range(0x20, 0x7F))
ARABIC_RANGE = range(0x0600, 0x0700)
PROVENANCE_START = "<!-- theme-factory-font-provenance:start -->"
PROVENANCE_END = "<!-- theme-factory-font-provenance:end -->"


@dataclass(frozen=True)
class FontRequest:
    metadata_url: str
    source_revision: str
    weights: tuple[int, ...]
    family: str = ""

    def __post_init__(self) -> None:
        if not self.source_revision:
            raise PackageError("A pinned source revision is required")
        if not re.fullmatch(r"[0-9A-Fa-f]{40}", self.source_revision):
            raise PackageError("The source revision must be a 40-character Git SHA")
        if not self.metadata_url.startswith("https://"):
            raise PackageError("The metadata URL must use HTTPS")
        if not self.weights or any(not isinstance(weight, int) or isinstance(weight, bool) for weight in self.weights):
            raise PackageError("Font weights must be a non-empty integer list")
        if len(self.weights) != len(set(self.weights)):
            raise PackageError("Font weights must be unique")
        if not self.family.strip():
            raise PackageError("A font family is required")


@dataclass(frozen=True)
class FontMetadata:
    family: str
    license: str
    repository_url: str
    source_commit: str
    fonts: tuple[tuple[int, str], ...]
    weight_min: int | None
    weight_max: int | None
    subsets: tuple[str, ...]

    @property
    def filenames(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(filename for _, filename in self.fonts))


@dataclass(frozen=True)
class InstalledFace:
    file: str
    weight: int
    sha256: str


@dataclass(frozen=True)
class FontInstallResult:
    family: str
    source_filename: str
    faces: tuple[InstalledFace, ...]
    dry_run: bool


class FontRunner(Protocol):
    def fetch(self, url: str) -> bytes: ...

    def convert(
        self,
        source_fonts: dict[int, Path],
        outputs: dict[int, Path],
        requirements: Path,
    ) -> dict[int, set[int]]: ...


def _quoted(text: str, field: str, *, anchored: bool = False) -> str:
    prefix = "^" if anchored else ""
    match = re.search(rf"(?m){prefix}{re.escape(field)}\s*:\s*\"([^\"]+)\"", text)
    if not match:
        raise PackageError(f"Font metadata is missing '{field}'")
    return match.group(1)


def _blocks(text: str, field: str) -> tuple[str, ...]:
    blocks = []
    pattern = re.compile(rf"(?m)^\s*{re.escape(field)}\s*\{{")
    for match in pattern.finditer(text):
        index = match.end()
        depth = 1
        quote = False
        escaped = False
        while index < len(text) and depth:
            character = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quote = False
            elif character == '"':
                quote = True
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
            index += 1
        if depth:
            raise PackageError(f"Unterminated '{field}' block in font metadata")
        blocks.append(text[match.end():index - 1])
    return tuple(blocks)


def inspect_metadata(text: str) -> FontMetadata:
    """Read only the official METADATA.pb fields required by the pipeline."""

    family = _quoted(text, "name", anchored=True)
    license_name = _quoted(text, "license", anchored=True)
    source_blocks = _blocks(text, "source")
    if not source_blocks:
        raise PackageError("Font metadata is missing a source repository URL")
    repository_url = _quoted(source_blocks[0], "repository_url")
    fonts = []
    for block in _blocks(text, "fonts"):
        filename = _quoted(block, "filename")
        weight_match = re.search(r"(?m)^\s*weight\s*:\s*([0-9]+)", block)
        if not weight_match:
            raise PackageError(f"Font metadata entry '{filename}' has no weight")
        fonts.append((int(weight_match.group(1)), filename))
    if not fonts:
        raise PackageError("Font metadata contains no source filenames")
    subsets = tuple(sorted(set(re.findall(r'(?m)^\s*subsets\s*:\s*"([^"]+)"', text))))

    weight_axis = None
    for block in _blocks(text, "axes"):
        if _quoted(block, "tag") == "wght":
            minimum = re.search(r"(?m)^\s*min_value\s*:\s*([0-9.]+)", block)
            maximum = re.search(r"(?m)^\s*max_value\s*:\s*([0-9.]+)", block)
            if not minimum or not maximum:
                raise PackageError("The wght axis is missing its minimum or maximum")
            weight_axis = (int(float(minimum.group(1))), int(float(maximum.group(1))))
            break
    source_commit = _quoted(source_blocks[0], "commit")
    return FontMetadata(
        family=family,
        license=license_name,
        repository_url=repository_url.rstrip("/"),
        source_commit=source_commit,
        fonts=tuple(fonts),
        weight_min=weight_axis[0] if weight_axis else None,
        weight_max=weight_axis[1] if weight_axis else None,
        subsets=subsets,
    )


def _pinned_metadata_url(url: str, revision: str) -> str:
    github = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+)/blob/[^/]+/(.+)", url)
    if github:
        owner, repository, path = github.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repository}/{revision}/{path}"
    raw = re.fullmatch(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/[^/]+/(.+)", url)
    if raw:
        owner, repository, path = raw.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repository}/{revision}/{path}"
    raise PackageError("The metadata URL must be a GitHub blob or raw.githubusercontent.com URL")


def _sibling_url(metadata_url: str, filename: str) -> str:
    return metadata_url.rsplit("/", 1)[0] + "/" + urllib.parse.quote(filename, safe="")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise PackageError("Font family cannot be converted to a safe asset name")
    return slug


class DefaultFontRunner:
    def fetch(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": "APEX-Theme-Factory/1"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as exc:
            raise PackageError(f"Unable to download pinned font source {url}: {exc}") from exc

    def convert(
        self,
        source_fonts: dict[int, Path],
        outputs: dict[int, Path],
        requirements: Path,
    ) -> dict[int, set[int]]:
        configuration = {
            "sources": {str(weight): str(path) for weight, path in source_fonts.items()},
            "outputs": {str(weight): str(path) for weight, path in outputs.items()},
        }
        helper = r'''
import json
import sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

config = json.loads(sys.argv[1])
coverage = {}
for raw_weight, output in config["outputs"].items():
    weight = int(raw_weight)
    source = TTFont(config["sources"][raw_weight])
    if "fvar" in source:
        axes = {axis.axisTag: axis for axis in source["fvar"].axes}
        if "wght" not in axes or not axes["wght"].minValue <= weight <= axes["wght"].maxValue:
            raise ValueError(f"weight {weight} is outside the variable font wght axis")
        location = {tag: axis.defaultValue for tag, axis in axes.items()}
        location["wght"] = weight
        instance = instantiateVariableFont(source, location, inplace=False)
    else:
        instance = source
    instance.flavor = "woff2"
    instance.save(output)
    reopened = TTFont(output)
    coverage[raw_weight] = sorted({codepoint for table in reopened["cmap"].tables for codepoint in table.cmap})
print(json.dumps(coverage, separators=(",", ":")))
'''
        with tempfile.TemporaryDirectory(prefix="theme-font-tools-") as temporary:
            environment = Path(temporary) / "venv"
            _create_isolated_venv(environment)
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            install = subprocess.run(
                [str(python), "-m", "pip", "install", "--no-deps", "-r", str(requirements)],
                check=False,
                capture_output=True,
                text=True,
            )
            if install.returncode:
                raise PackageError(f"Unable to install pinned font tools: {install.stderr.strip()}")
            process = subprocess.run(
                [str(python), "-c", helper, json.dumps(configuration, separators=(",", ":"))],
                check=False,
                capture_output=True,
                text=True,
            )
            if process.returncode:
                raise PackageError(f"Unable to convert variable font: {process.stderr.strip()}")
            raw_coverage = json.loads(process.stdout)
        return {int(weight): set(codepoints) for weight, codepoints in raw_coverage.items()}


def _process_error(process: subprocess.CompletedProcess) -> str:
    value = process.stderr or process.stdout or "unknown error"
    return value.decode(errors="replace").strip() if isinstance(value, bytes) else str(value).strip()


def _create_isolated_venv(environment: Path) -> None:
    """Create a temporary venv compatible with the exact pinned binary packages."""

    uv = shutil.which("uv")
    if USE_MANAGED_TOOL_PYTHON:
        if uv is None:
            raise PackageError(
                f"Pinned font tools require Python {PINNED_TOOL_PYTHON}; install uv to provide it"
            )
        managed = subprocess.run(
            [uv, "venv", "--seed", "--python", PINNED_TOOL_PYTHON, str(environment)],
            check=False,
            capture_output=True,
            text=True,
        )
        if managed.returncode:
            raise PackageError(f"Unable to create isolated font environment: {_process_error(managed)}")
        return

    standard = subprocess.run(
        [sys.executable, "-m", "venv", str(environment)],
        check=False,
        capture_output=True,
        text=True,
    )
    if standard.returncode == 0:
        return
    if uv is None:
        raise PackageError(f"Unable to create isolated font environment: {_process_error(standard)}")
    if environment.is_symlink():
        raise PackageError(f"Refusing to replace symlinked font environment: {environment}")
    if environment.exists():
        shutil.rmtree(environment)
    fallback = subprocess.run(
        [uv, "venv", "--seed", "--python", sys.executable, str(environment)],
        check=False,
        capture_output=True,
        text=True,
    )
    if fallback.returncode:
        raise PackageError(f"Unable to create isolated font environment: {_process_error(fallback)}")


def _cached_fetch(cache_root: Path, filename: str, url: str, runner: FontRunner) -> Path:
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / filename
    if not target.is_file():
        data = runner.fetch(url)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)
    return target


def _provenance_section(
    request: FontRequest,
    metadata: FontMetadata,
    source_filename: str,
    faces: tuple[InstalledFace, ...],
) -> str:
    face_lines = "\n".join(
        f"- `{face.file}` — weight {face.weight}, SHA-256 `{face.sha256}`" for face in faces
    )
    return (
        f"{PROVENANCE_START}\n"
        "## Typography and provenance\n\n"
        f"- Family: **{request.family}**\n"
        f"- Metadata: `{request.metadata_url}`\n"
        f"- Source revision: `{request.source_revision}`\n"
        f"- Upstream repository: `{metadata.repository_url}` at `{metadata.source_commit}`\n"
        f"- Variable source: `{source_filename}`\n"
        "- License: SIL Open Font License 1.1 in `licenses/OFL.txt`\n"
        f"- Conversion tools: fonttools {FONTTOOLS_VERSION}; brotli {BROTLI_VERSION}\n"
        f"{face_lines}\n"
        f"{PROVENANCE_END}"
    )


def _replace_provenance(readme: str, section: str) -> str:
    if PROVENANCE_START in readme:
        start = readme.index(PROVENANCE_START)
        end = readme.find(PROVENANCE_END, start)
        if end < 0:
            raise PackageError("README contains an unterminated font provenance section")
        end += len(PROVENANCE_END)
        return readme[:start] + section + readme[end:]
    return readme.rstrip() + "\n\n" + section + "\n"


def _validate_request(recipe, request: FontRequest, metadata: FontMetadata) -> dict[int, str]:
    if metadata.family != request.family:
        raise PackageError(
            f"Metadata family '{metadata.family}' does not match requested family '{request.family}'"
        )
    if recipe.typography.body_family != request.family:
        raise PackageError(
            f"Recipe body family '{recipe.typography.body_family}' does not match requested family '{request.family}'"
        )
    if metadata.license != "OFL":
        raise PackageError(f"Font license must be OFL, got '{metadata.license}'")
    if not metadata.repository_url:
        raise PackageError("Font metadata is missing its source repository URL")
    if not {"arabic", "latin"}.issubset(set(metadata.subsets)):
        raise PackageError("Font metadata must declare both Arabic and Latin subsets")
    for weight in request.weights:
        within_axis = (
            metadata.weight_min is not None
            and metadata.weight_max is not None
            and metadata.weight_min <= weight <= metadata.weight_max
        )
        static_weights = {font_weight for font_weight, _ in metadata.fonts}
        if weight not in VALID_WEIGHTS or not (within_axis or weight in static_weights):
            support = (
                f"{metadata.weight_min}-{metadata.weight_max}"
                if metadata.weight_min is not None
                else ", ".join(str(value) for value in sorted(static_weights))
            )
            raise PackageError(
                f"Weight {weight} is not supported by the declared font weights {support}"
            )
    if metadata.weight_min is not None:
        variable = next(
            (filename for filename in metadata.filenames if "wght" in filename and "[" in filename),
            None,
        )
        if variable is None:
            raise PackageError("Font metadata contains a wght axis but no variable wght source filename")
        return {weight: variable for weight in request.weights}
    static = {weight: filename for weight, filename in metadata.fonts}
    return {weight: static[weight] for weight in request.weights}


def install_font(
    repo_root: Path,
    theme_root: Path,
    request: FontRequest,
    *,
    runner: FontRunner | None = None,
    dry_run: bool = False,
) -> FontInstallResult:
    """Resolve, validate, convert, and install one bilingual body/heading family."""

    repo_root = Path(repo_root).resolve()
    theme_root = Path(theme_root).resolve()
    recipe_path = theme_root / "theme.recipe.json"
    if not recipe_path.is_file():
        raise PackageError(f"Theme has no source recipe: {recipe_path}")
    recipe = load_recipe(recipe_path)
    runner = runner or DefaultFontRunner()
    pinned_metadata_url = _pinned_metadata_url(request.metadata_url, request.source_revision)
    cache_key = hashlib.sha256(
        f"{request.metadata_url}\0{request.source_revision}".encode("utf-8")
    ).hexdigest()
    cache_root = repo_root / ".theme-factory/cache/fonts" / cache_key
    try:
        if dry_run:
            metadata_text = runner.fetch(pinned_metadata_url).decode("utf-8")
        else:
            metadata_path = _cached_fetch(cache_root, "METADATA.pb", pinned_metadata_url, runner)
            metadata_text = metadata_path.read_text(encoding="utf-8")
        metadata = inspect_metadata(metadata_text)
    except UnicodeDecodeError as exc:
        raise PackageError("Pinned METADATA.pb is not UTF-8 text") from exc
    source_files = _validate_request(recipe, request, metadata)
    source_filename = ", ".join(dict.fromkeys(source_files[weight] for weight in sorted(source_files)))
    slug = _slug(request.family)
    planned = tuple(
        InstalledFace(f"fonts/{slug}-{weight}.woff2", weight, "")
        for weight in sorted(request.weights)
    )
    if dry_run:
        return FontInstallResult(request.family, source_filename, planned, True)

    source_paths = {
        weight: _cached_fetch(
            cache_root,
            filename,
            _sibling_url(pinned_metadata_url, filename),
            runner,
        )
        for weight, filename in source_files.items()
    }
    license_path = _cached_fetch(
        cache_root,
        "OFL.txt",
        _sibling_url(pinned_metadata_url, "OFL.txt"),
        runner,
    )
    if not license_path.read_bytes().strip():
        raise PackageError("Downloaded OFL license is empty")

    staging = theme_root / ".font-staging"
    if staging.exists():
        raise PackageError(f"Font staging directory already exists: {staging}")
    validation_root = staging / theme_root.name
    try:
        staged_fonts = validation_root / "fonts"
        staged_fonts.mkdir(parents=True)
        outputs = {
            face.weight: staged_fonts / Path(face.file).name
            for face in planned
        }
        requirements = repo_root / "tools/font-tools-requirements.txt"
        if not requirements.is_file():
            raise PackageError(f"Pinned font tool requirements not found: {requirements}")
        expected_requirements = (
            f"fonttools[woff]=={FONTTOOLS_VERSION}\n"
            f"brotli=={BROTLI_VERSION}\n"
        )
        if requirements.read_text(encoding="utf-8") != expected_requirements:
            raise PackageError("Pinned font tool requirements do not match the pipeline versions")
        coverage = runner.convert(source_paths, outputs, requirements)
        faces = []
        for weight in sorted(outputs):
            output = outputs[weight]
            if not output.is_file() or output.read_bytes()[:4] != b"wOF2":
                raise PackageError(f"Converted weight {weight} is not a valid WOFF2 file")
            codepoints = coverage.get(weight, set())
            if not BASIC_LATIN.issubset(codepoints):
                raise PackageError(f"Converted weight {weight} is missing Basic Latin coverage")
            if not any(codepoint in codepoints for codepoint in ARABIC_RANGE):
                raise PackageError(f"Converted weight {weight} is missing Arabic coverage")
            faces.append(
                InstalledFace(
                    f"fonts/{output.name}",
                    weight,
                    hashlib.sha256(output.read_bytes()).hexdigest(),
                )
            )
        installed_faces = tuple(faces)

        staged_licenses = validation_root / "licenses"
        staged_licenses.mkdir()
        shutil.copy2(license_path, staged_licenses / "OFL.txt")
        role = FontRoleSpec(
            family=request.family,
            fallback=recipe.typography.fallback,
            license="licenses/OFL.txt",
            faces=tuple(FontFaceSpec(face.file, face.weight) for face in installed_faces),
        )

        raw_recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
        raw_recipe["fontProvenance"] = {
            "family": request.family,
            "metadataUrl": request.metadata_url,
            "sourceRevision": request.source_revision.lower(),
            "sourceFilename": source_filename,
            "repositoryUrl": metadata.repository_url,
            "upstreamCommit": metadata.source_commit,
            "license": "OFL-1.1",
            "tools": {"fonttools": FONTTOOLS_VERSION, "brotli": BROTLI_VERSION},
            "faces": [
                {"file": face.file, "weight": face.weight, "sha256": face.sha256}
                for face in installed_faces
            ],
        }
        staged_recipe = validation_root / "theme.recipe.json"
        staged_recipe.write_text(json.dumps(raw_recipe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        updated_recipe = load_recipe(staged_recipe)
        staged_manifest = validation_root / "theme.json"
        staged_manifest.write_text(render_manifest(updated_recipe, {"body": role}), encoding="utf-8")
        load_manifest(staged_manifest, validation_root)

        readme = (theme_root / "README.md").read_text(encoding="utf-8")
        staged_readme = validation_root / "README.md"
        staged_readme.write_text(
            _replace_provenance(
                readme,
                _provenance_section(request, metadata, source_filename, installed_faces),
            ),
            encoding="utf-8",
        )

        target_fonts = theme_root / "fonts"
        backup_fonts = staging / "previous-fonts"
        licenses = theme_root / "licenses"
        replacements = (
            (staged_licenses / "OFL.txt", licenses / "OFL.txt"),
            (staged_manifest, theme_root / "theme.json"),
            (staged_recipe, recipe_path),
            (staged_readme, theme_root / "README.md"),
        )
        originals = {
            target: target.read_bytes() if target.is_file() else None
            for _, target in replacements
        }
        if target_fonts.exists():
            os.replace(target_fonts, backup_fonts)
        try:
            os.replace(staged_fonts, target_fonts)
            licenses.mkdir(exist_ok=True)
            for source, target in replacements:
                temporary = target.with_name(f".{target.name}.font-tmp")
                temporary.write_bytes(source.read_bytes())
                os.replace(temporary, target)
        except Exception:
            if target_fonts.exists():
                shutil.rmtree(target_fonts)
            if backup_fonts.exists():
                os.replace(backup_fonts, target_fonts)
            for _, target in replacements:
                temporary = target.with_name(f".{target.name}.font-tmp")
                temporary.unlink(missing_ok=True)
                original = originals[target]
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(original)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return FontInstallResult(request.family, source_filename, installed_faces, False)
