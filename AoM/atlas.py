"""Load sprite animation frames from the packed web atlases (AOM-34).

The ``web-10fps`` asset profile (``tools/pack_web_atlas.py``, AOM-33) replaces the
per-frame PNG directories with lossless grid atlases plus a ``manifest.json``
index (schema ``aom.web_atlas/v1``). On the web build the source directories are
removed by the packer, so sprite loading has to slice frames back out of the
atlas. Native builds keep the original frame directories / horizontal-strip
sheets and never read the manifest, so their frames and playback rate are
unchanged.

The atlas is gated by ``config.WEB_ATLAS_ENABLED`` (derived from ``WEB_BUILD``)
and every failure path returns ``None`` so callers fall back to the existing
directory/sheet loaders and the sim degrades gracefully (null-object defaults).

The manifest records each set's ``cell_w``/``cell_h``/``cols``/``count`` plus the
ordered ``source_indices`` and the ``profile_fps`` at which the shipped frames
should play. ``load_frames`` returns the ``count`` atlas cells (row-major); the
caller uses ``entry`` to pick up the profile frame rate.
"""

import json
from pathlib import Path

import pygame

from config import BASE_DIR, WEB_ATLAS_ENABLED

SCHEMA = "aom.web_atlas/v1"
DEFAULT_ATLAS_DIR = BASE_DIR / "assets" / "atlas"


class AtlasIndex:
    """Resolve sprite set paths to frames sliced from a packed grid atlas."""

    def __init__(self, atlas_dir=None, enabled=None):
        self.atlas_dir = Path(atlas_dir) if atlas_dir is not None else DEFAULT_ATLAS_DIR
        self.enabled = WEB_ATLAS_ENABLED if enabled is None else bool(enabled)
        self._sets = None

    def _index(self):
        if self._sets is None:
            self._sets = self._read_manifest()
        return self._sets

    def _read_manifest(self):
        if not self.enabled:
            return {}
        manifest_path = self.atlas_dir / "manifest.json"
        if not manifest_path.exists():
            return {}
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, ValueError):
            return {}
        if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
            return {}
        sets = {}
        for entry in manifest.get("sets", []):
            if not isinstance(entry, dict):
                continue
            if entry.get("skipped") or not entry.get("atlas"):
                continue
            path = entry.get("path")
            if path:
                sets[path] = entry
        return sets

    def entry(self, sprite_path):
        """Return the manifest entry for ``sprite_path`` or ``None``."""
        return self._index().get(sprite_path)

    def load_frames(self, sprite_path):
        """Return the sliced frames for ``sprite_path`` or ``None`` if not packed.

        ``None`` means "not handled here" so the caller can fall back to the
        per-frame directory or the ``FRAME_SIZE`` horizontal strip.
        """
        entry = self.entry(sprite_path)
        if entry is None:
            return None
        atlas_path = self.atlas_dir / entry["atlas"]
        try:
            sheet = pygame.image.load(str(atlas_path)).convert_alpha()
        except (pygame.error, OSError):
            return None
        count = int(entry.get("count", 0))
        if count <= 0:
            return None
        return slice_frames(
            sheet,
            int(entry["cell_w"]),
            int(entry["cell_h"]),
            int(entry["cols"]),
            count,
        )


def slice_frames(sheet, cell_w, cell_h, cols, count):
    """Cut a packed grid atlas into ``count`` frames (row-major)."""
    frames = []
    for index in range(count):
        left = (index % cols) * cell_w
        top = (index // cols) * cell_h
        frames.append(sheet.subsurface(pygame.Rect(left, top, cell_w, cell_h)).copy())
    return frames


_default_index = None


def default_atlas_index():
    """Shared lazily-built index so the manifest is read at most once."""
    global _default_index
    if _default_index is None:
        _default_index = AtlasIndex()
    return _default_index
