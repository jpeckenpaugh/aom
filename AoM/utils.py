import pygame

from config import *


def browser_bucket(value, bucket=BROWSER_SURFACE_BUCKET, maximum=None):
    value = max(1, int(round(value)))
    if maximum is not None:
        value = min(value, maximum)
    if value <= bucket * 2:
        return value
    return max(bucket, round(value / bucket) * bucket)


def make_radial_glow(size, color, center_alpha, falloff_power=2.15):
    size = max(8, browser_bucket(size, maximum=BROWSER_MAX_GLOW_SIZE))
    cache_key = (size, color, center_alpha, falloff_power)
    if cache_key in RADIAL_GLOW_CACHE:
        return RADIAL_GLOW_CACHE[cache_key]

    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size / 2
    max_radius = size / 2
    for radius in range(round(max_radius), 0, -2):
        t = min(1, radius / max_radius)
        falloff = (1 - t) ** falloff_power
        alpha = round(center_alpha * falloff)
        if alpha <= 0:
            continue
        rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        rect.center = (round(center), round(center))
        pygame.draw.ellipse(glow, (*color, alpha), rect)

    RADIAL_GLOW_CACHE[cache_key] = glow
    return glow


STEP_RATE = 24.0


def _gen_advance_path(start, n_steps, n_frames, first):
    if first:
        end = min(start + n_steps, n_frames - 1)
        return list(range(start + 1, end + 1))
    path = []
    pos = start
    direction = 1
    while len(path) < n_steps:
        pos += direction
        if pos >= n_frames:
            pos = n_frames - 2
            direction = -1
        elif pos < 0:
            pos = 1
            direction = 1
        path.append(pos)
    return path


def _build_lumen_cycle(numbers, n_frames, start_sprite, first_cycle):
    result = []
    current = start_sprite
    for i, n in enumerate(numbers):
        if i % 2 == 0:
            result.extend([current] * n)
        else:
            first_advance = (first_cycle and i == 1)
            path = _gen_advance_path(current, n, n_frames, first_advance)
            m = len(path)
            for j, sprite in enumerate(path):
                if j == 0 or j == m - 1:
                    fr = 3
                elif j == 1 or j == m - 2:
                    fr = 2
                else:
                    fr = 1
                result.extend([sprite] * fr)
            current = path[-1]
    return result, current


_LUMEN_TIMELINE_CACHE: dict[int, tuple[list[int], list[int]]] = {}


def lumen_timeline_sprite(time, phase_offset, n_frames):
    if n_frames <= 1:
        return 0
    if n_frames not in _LUMEN_TIMELINE_CACHE:
        import random
        rng = random.Random(42)
        numbers = [rng.randint(5, 10) for _ in range(20)]
        first_seg, end_sprite = _build_lumen_cycle(numbers, n_frames, 0, True)
        loop_seg, _ = _build_lumen_cycle(numbers, n_frames, end_sprite, False)
        _LUMEN_TIMELINE_CACHE[n_frames] = (first_seg, loop_seg)
    first_seg, loop_seg = _LUMEN_TIMELINE_CACHE[n_frames]
    frame = int((time + phase_offset * 10) * STEP_RATE)
    if frame < len(first_seg):
        return first_seg[frame]
    return loop_seg[(frame - len(first_seg)) % len(loop_seg)]


def make_elliptical_ring(width, height, band_width, color, center_alpha):
    width = max(8, browser_bucket(width, maximum=BROWSER_MAX_GLOW_SIZE))
    height = max(8, browser_bucket(height, maximum=BROWSER_MAX_GLOW_SIZE))
    band_width = max(2, browser_bucket(band_width, bucket=4, maximum=64))
    cache_key = (width, height, band_width, color, center_alpha)
    if cache_key in ELLIPTICAL_RING_CACHE:
        return ELLIPTICAL_RING_CACHE[cache_key]

    ring = pygame.Surface((width, height), pygame.SRCALPHA)
    steps = max(8, band_width)
    for step in range(steps):
        t = step / max(1, steps - 1)
        smooth = t * t * (3 - 2 * t)
        alpha = round(center_alpha * (1 - smooth))
        if alpha <= 0:
            continue
        inset = step
        rect = pygame.Rect(inset, round(inset * height / width), width - inset * 2, height - round(inset * height / width) * 2)
        if rect.width <= 0 or rect.height <= 0:
            continue
        line_width = 2
        pygame.draw.ellipse(ring, (*color, alpha), rect, line_width)
    ELLIPTICAL_RING_CACHE[cache_key] = ring
    return ring


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def landing_factor(progress, start=0.78):
    if progress <= start:
        return 1.0
    return 1.0 - smoothstep((progress - start) / max(0.001, 1.0 - start))


