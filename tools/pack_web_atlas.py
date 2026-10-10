"""Pack the AoM sprite animation frames into lossless grid atlases and emit a
named web asset profile.

The web (PygBag) build ships ``AoM/assets/sprites/<set>/`` directories of
independently-encoded PNG frames.  PNG compression is per-file, so neighbouring
near-identical frames cannot share a zlib stream.  Packing the frames into a
single grid atlas (width ``<= MAX_ATLAS_WIDTH``, the common WebGL texture limit)
lets Pillow compress the whole run together and is **lossless** -- slicing the
atlas reproduces the exact source pixels.

Two levers compose (see ``docs/adr`` / AOM-31 analysis):

1. **Atlas packing** -- repack animation frame dirs + collectible spin sets into
   grid atlases, skipping low-gain sets (measured gain below ``--min-gain``,
   e.g. the ``mycena_glow_*`` emissive overlays at ~1.1x).
2. **Named frame profile** -- ``web-10fps`` ships only the frames a 10 fps web
   build can actually display (every 3rd source frame; spin sets resampled
   16 -> 10 fps).  Native / high-fps builds keep the full source frames.

The output is a directory of ``<set>.png`` atlases plus ``manifest.json``
describing the cell grid, the ordered source frames, and the profile.  The
loader swap (AOM-34) consumes the manifest; the pixel-equality test in
``tests/test_web_atlas.py`` proves atlas slices equal the source frames and is
the gate for that swap.

Usage::

    # Report the web-10fps projection without writing anything:
    python3 tools/pack_web_atlas.py --profile web-10fps --report

    # Emit the web-10fps atlas set into a staging directory:
    python3 tools/pack_web_atlas.py --profile web-10fps --out build/web_atlas

    # Apply the profile in place for a web build (removes the atlased source
    # frame dirs; run on a clean checkout -- see scripts/build-web-atlas-bundle.sh):
    python3 tools/pack_web_atlas.py --profile web-10fps --apply
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AOM = REPO_ROOT / "AoM"
SPRITES_SUBPATH = Path("assets") / "sprites"

# Widest atlas we will emit.  4096 covers the WebGL guaranteed maximum texture
# size on essentially every target the browser demo runs on.
MAX_ATLAS_WIDTH = 4096

# A set whose atlas compresses worse than this is left as independent frames:
# the loader complexity is not worth the bytes.
DEFAULT_MIN_GAIN = 1.3

# Named web profiles -> target frame rate.  ``native`` keeps every frame.
PROFILES: dict[str, int | None] = {
    "native": None,
    "web-10fps": 10,
}

# Emissive overlays whose frames are high-entropy brightness/alpha variants;
# atlas packing gains ~1.1x, which the --min-gain threshold already catches.
DEFAULT_SKIP_GLOBS = ("mycena_glow_*",)

SCHEMA = "aom.web_atlas/v1"

ANIMATION_FPS = 30
SPIN_FPS = 16


@dataclass
class SetSpec:
    """A discoverable group of frames that can be packed into one atlas."""

    name: str
    directory: Path
    files: list[Path]
    source_fps: int
    is_walk: bool
    is_spin: bool


@dataclass
class SetResult:
    name: str
    directory: Path
    source_count: int
    source_fps: int
    profile_fps: int | None
    walk_halved: bool
    source_indices: list[int]
    source_files: list[str]
    cell_w: int
    cell_h: int
    cols: int
    rows: int
    atlas: str | None
    original_bytes: int
    atlas_bytes: int
    gain: float
    skipped: bool
    skip_reason: str | None = None

    def to_manifest(self) -> dict:
        return {
            "name": self.name,
            "path": f"{SPRITES_SUBPATH.as_posix()}/{self.name}",
            "atlas": self.atlas,
            "cell_w": self.cell_w,
            "cell_h": self.cell_h,
            "cols": self.cols,
            "rows": self.rows,
            "count": len(self.source_indices),
            "source_count": self.source_count,
            "source_fps": self.source_fps,
            "profile_fps": self.profile_fps,
            "walk_halved": self.walk_halved,
            "source_indices": self.source_indices,
            "source_files": self.source_files,
            "gain": round(self.gain, 4),
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
        }


@dataclass
class ProfileResult:
    profile: str
    profile_fps: int | None
    out_dir: Path | None = None
    sets: list[SetResult] = field(default_factory=list)
    skipped: list[SetResult] = field(default_factory=list)

    @property
    def atlas_sets(self) -> list[SetResult]:
        return [s for s in self.sets if not s.skipped]

    def totals(self) -> dict:
        original = sum(s.original_bytes for s in self.sets)
        atlas = sum(s.atlas_bytes for s in self.sets if not s.skipped)
        packed_original = sum(s.original_bytes for s in self.sets if not s.skipped)
        return {
            "set_count": len(self.sets),
            "atlas_set_count": len(self.atlas_sets),
            "skipped_count": len(self.skipped),
            "original_bytes": original,
            "packed_original_bytes": packed_original,
            "atlas_bytes": atlas,
            "gain": (packed_original / atlas) if atlas else 0.0,
        }

    def to_manifest(self, extra: dict | None = None) -> dict:
        manifest = {
            "schema": SCHEMA,
            "profile": self.profile,
            "profile_fps": self.profile_fps,
            "sets": [s.to_manifest() for s in self.sets],
            "totals": self.totals(),
        }
        if extra:
            manifest.update(extra)
        return manifest


def discover_sets(aom_dir: Path) -> list[SetSpec]:
    """Find the frame groups the packer owns.

    Owned: ``assets/sprites/*_frames`` animation dirs (30 fps) and
    ``assets/sprites/collectibles/*_spin`` sets (16 fps).  Everything else
    (HUD, patterns, ``*_regen_mini``, prop variants, single previews) is out of
    scope for this packer.
    """
    sprites = aom_dir / SPRITES_SUBPATH
    specs: list[SetSpec] = []
    if not sprites.is_dir():
        return specs

    def _pngs(directory: Path) -> list[Path]:
        return sorted(p for p in directory.glob("*.png") if p.is_file())

    for directory in sorted(sprites.glob("*_frames")):
        if not directory.is_dir():
            continue
        files = _pngs(directory)
        if len(files) < 2:
            # A single frame cannot gain from an atlas.
            continue
        specs.append(
            SetSpec(
                name=directory.name,
                directory=directory,
                files=files,
                source_fps=ANIMATION_FPS,
                is_walk="walk" in directory.name,
                is_spin=False,
            )
        )

    collectibles = sprites / "collectibles"
    if collectibles.is_dir():
        for directory in sorted(collectibles.glob("*_spin")):
            if not directory.is_dir():
                continue
            files = _pngs(directory)
            if len(files) < 2:
                continue
            specs.append(
                SetSpec(
                    name=f"collectibles/{directory.name}",
                    directory=directory,
                    files=files,
                    source_fps=SPIN_FPS,
                    is_walk=False,
                    is_spin=True,
                )
            )
    return specs


def effective_indices(spec: SetSpec) -> tuple[list[int], bool]:
    """Return (indices into the sorted source files, halving_already_applied).

    ``MushroomSprites.load_frames`` silently halves walk frames (``frames[::2]``,
    ``AoM/sprites.py:151``).  Frame selection for the 10 fps profile therefore
    runs on the *effective* sequence the runtime actually iterates, so a walk set
    selects every 3rd of the post-halving frames (== every 6th raw frame).
    """
    count = len(spec.files)
    if spec.is_walk:
        return list(range(0, count, 2)), True
    return list(range(count)), False


def profile_indices(effective_count: int, source_fps: int, target_fps: int | None) -> list[int]:
    """Select the frames a ``target_fps`` runtime can display from ``effective``.

    Exact multiples use a simple stride (30 -> 10 keeps every 3rd).  Otherwise
    resample by time (16 -> 10 keeps ``ceil(n * 10/16)`` unique frames).
    """
    if target_fps is None or target_fps >= source_fps:
        return list(range(effective_count))
    if effective_count == 0:
        return []
    if source_fps % target_fps == 0:
        return list(range(0, effective_count, source_fps // target_fps))

    count = math.ceil(effective_count * target_fps / source_fps)
    out: list[int] = []
    for k in range(count):
        index = round(k * source_fps / target_fps)
        index = min(index, effective_count - 1)
        if not out or index != out[-1]:
            out.append(index)
    return out


def _grid_for(count: int, cell_w: int) -> int:
    """Columns for ``count`` cells, preferring a single strip when it fits."""
    if count * cell_w <= MAX_ATLAS_WIDTH:
        return max(1, count)
    return max(1, MAX_ATLAS_WIDTH // cell_w)


def _load_rgba(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGBA")


def pack_set(
    spec: SetSpec,
    source_indices: list[int],
    *,
    profile_fps: int | None,
    walk_halved: bool,
    min_gain: float,
    skip_globs: Iterable[str],
    out_dir: Path | None,
) -> SetResult:
    """Pack ``spec`` (only ``source_indices``) into one atlas.

    When ``out_dir`` is given the atlas PNG is written there.  Gain is measured
    against the bytes of the shipped individual frames, so a low-gain set is
    skipped and its source dir is left untouched.
    """
    files = spec.files
    shipped = [files[i] for i in source_indices]
    original_bytes = sum(p.stat().st_size for p in shipped)

    first = _load_rgba(shipped[0])
    cell_w, cell_h = first.size
    for path in shipped[1:]:
        image = _load_rgba(path)
        if image.size != (cell_w, cell_h):
            raise ValueError(
                f"{spec.name}: frames have mixed sizes "
                f"({cell_w}x{cell_h} vs {image.size} at {path.name}); "
                "cannot pack into a uniform grid"
            )

    count = len(shipped)
    cols = _grid_for(count, cell_w)
    rows = math.ceil(count / cols)
    atlas = Image.new("RGBA", (cols * cell_w, rows * cell_h), (0, 0, 0, 0))
    for index, path in enumerate(shipped):
        cell = _load_rgba(path) if index else first
        atlas.paste(cell, ((index % cols) * cell_w, (index // cols) * cell_h))

    import io

    buffer = io.BytesIO()
    atlas.save(buffer, format="PNG", optimize=True, compress_level=9)
    atlas_bytes = buffer.tell()

    gain = (original_bytes / atlas_bytes) if atlas_bytes else 0.0
    glob_skip = any(fnmatch.fnmatch(spec.name, g) for g in skip_globs)
    low_gain = gain < min_gain
    skip = glob_skip or low_gain

    atlas_name: str | None = None
    if not skip and out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        atlas_name = f"{spec.name.replace('/', '__')}.png"
        (out_dir / atlas_name).write_bytes(buffer.getvalue())

    return SetResult(
        name=spec.name,
        directory=spec.directory,
        source_count=len(files),
        source_fps=spec.source_fps,
        profile_fps=profile_fps,
        walk_halved=walk_halved,
        source_indices=source_indices,
        source_files=[p.name for p in shipped],
        cell_w=cell_w,
        cell_h=cell_h,
        cols=cols,
        rows=rows,
        atlas=atlas_name,
        original_bytes=original_bytes,
        atlas_bytes=atlas_bytes,
        gain=gain,
        skipped=skip,
        skip_reason=(
            "skip-glob" if glob_skip else f"low-gain (<{min_gain:.2f}x)" if low_gain else None
        ),
    )


def slice_atlas(
    atlas: Image.Image, cell_w: int, cell_h: int, cols: int, count: int
) -> list[Image.Image]:
    """Cut a packed grid atlas back into ``count`` RGBA frames (row-major)."""
    frames: list[Image.Image] = []
    for index in range(count):
        left = (index % cols) * cell_w
        top = (index // cols) * cell_h
        frames.append(atlas.crop((left, top, left + cell_w, top + cell_h)).convert("RGBA"))
    return frames


def load_manifest(path: Path) -> dict:
    import json

    return json.loads(Path(path).read_text())


def build_profile(
    aom_dir: Path,
    profile: str,
    *,
    out_dir: Path | None,
    min_gain: float = DEFAULT_MIN_GAIN,
    skip_globs: Iterable[str] = DEFAULT_SKIP_GLOBS,
) -> ProfileResult:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose from {sorted(PROFILES)}")
    profile_fps = PROFILES[profile]
    result = ProfileResult(profile=profile, profile_fps=profile_fps, out_dir=out_dir)

    for spec in discover_sets(aom_dir):
        effective, halved = effective_indices(spec)
        selected_effective = profile_indices(len(effective), spec.source_fps, profile_fps)
        if halved:
            source_indices = [effective[i] for i in selected_effective]
        else:
            source_indices = list(selected_effective)

        set_result = pack_set(
            spec,
            source_indices,
            profile_fps=profile_fps,
            walk_halved=halved,
            min_gain=min_gain,
            skip_globs=skip_globs,
            out_dir=out_dir,
        )
        result.sets.append(set_result)
        if set_result.skipped:
            result.skipped.append(set_result)
    return result


def apply_profile(result: ProfileResult) -> int:
    """Remove the source frame dirs that were replaced by an atlas.

    Only non-skipped sets are removed.  Returns the number of dirs removed.
    """
    removed = 0
    for set_result in result.atlas_sets:
        directory = set_result.directory
        if directory.exists():
            shutil.rmtree(directory)
            removed += 1
    return removed


def _fmt_mb(value: float) -> str:
    return f"{value / 1e6:8.2f} MB"


def print_report(result: ProfileResult, archive_bytes: int | None = None) -> None:
    totals = result.totals()
    print(f"profile: {result.profile}  (target {result.profile_fps or 'full'} fps)")
    print(f"sets   : {totals['set_count']} discovered, "
          f"{totals['atlas_set_count']} atlased, {totals['skipped_count']} skipped")
    print()
    print(f"{'set':40s} {'frames':>7s} {'source':>10s} {'atlas':>10s} {'gain':>6s}")
    for set_result in sorted(result.sets, key=lambda s: -s.original_bytes):
        mark = "skip" if set_result.skipped else f"{set_result.gain:5.2f}x"
        print(f"{set_result.name:40s} {len(set_result.source_indices):7d} "
              f"{_fmt_mb(set_result.original_bytes):>10s} "
              f"{_fmt_mb(set_result.atlas_bytes):>10s} {mark:>6s}")
    print()
    print(f"animation pool originals : {_fmt_mb(totals['original_bytes'])}")
    print(f"atlased originals        : {_fmt_mb(totals['packed_original_bytes'])}")
    print(f"atlas bytes              : {_fmt_mb(totals['atlas_bytes'])}")
    print(f"atlas gain               : {totals['gain']:.2f}x")
    if archive_bytes is not None:
        print(f"aom.tar.gz               : {_fmt_mb(archive_bytes)}")


def _git_clean(aom_dir: Path) -> bool:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--", str(aom_dir)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True
    return not out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aom-dir", default=str(DEFAULT_AOM))
    parser.add_argument("--profile", default="web-10fps", choices=sorted(PROFILES))
    parser.add_argument("--out", help="Directory to write atlases + manifest.json (default: <aom>/build/web_atlas)")
    parser.add_argument("--apply", action="store_true",
                        help="Write atlases into <aom>/assets/atlas and remove atlased source dirs")
    parser.add_argument("--force", action="store_true", help="Allow --apply with a dirty working tree")
    parser.add_argument("--report", action="store_true", help="Print the size breakdown")
    parser.add_argument("--min-gain", type=float, default=DEFAULT_MIN_GAIN)
    parser.add_argument("--skip-glob", action="append", default=list(DEFAULT_SKIP_GLOBS),
                        help="Set glob(s) to skip packing (repeatable)")
    parser.add_argument("--manifest", help="Write the manifest JSON to this path")
    parser.add_argument("--json-totals", action="store_true", help="Print machine-readable totals only")
    args = parser.parse_args(argv)

    aom_dir = Path(args.aom_dir).resolve()
    if not (aom_dir / SPRITES_SUBPATH).is_dir():
        parser.error(f"{aom_dir} does not look like the AoM package")

    if args.apply:
        if not args.force and not _git_clean(aom_dir / "assets"):
            parser.error("refusing --apply: AoM/assets has uncommitted changes (use --force)")
        out_dir = aom_dir / "assets" / "atlas"
        result = build_profile(aom_dir, args.profile, out_dir=out_dir,
                               min_gain=args.min_gain, skip_globs=args.skip_glob)
        removed = apply_profile(result)
        manifest_path = out_dir / "manifest.json"
    else:
        out_dir = Path(args.out).resolve() if args.out else aom_dir / "build" / "web_atlas" / args.profile
        result = build_profile(aom_dir, args.profile, out_dir=out_dir,
                               min_gain=args.min_gain, skip_globs=args.skip_glob)
        removed = 0
        manifest_path = Path(args.manifest).resolve() if args.manifest else out_dir / "manifest.json"

    extra = {"applied": bool(args.apply), "removed_source_dirs": removed}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(result.to_manifest(extra), indent=2) + "\n")

    if args.json_totals:
        print(json.dumps(result.totals()))
        return 0

    if args.report or not args.apply:
        archive = aom_dir / "build" / "web" / "aom.tar.gz"
        print_report(result, archive.stat().st_size if archive.exists() else None)
        print(f"manifest: {manifest_path.relative_to(REPO_ROOT) if manifest_path.is_relative_to(REPO_ROOT) else manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
