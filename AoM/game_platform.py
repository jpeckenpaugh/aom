"""Runtime platform helpers for native Python and Pygbag/browser builds."""

import importlib.util
import os
import sys
import sysconfig

WEB_BUILD = sys.platform == "emscripten"

_stdlib_platform = None
_stdlib_path = os.path.join(sysconfig.get_path("stdlib"), "platform.py")
if os.path.exists(_stdlib_path):
    _spec = importlib.util.spec_from_file_location("_stdlib_platform", _stdlib_path)
    if _spec and _spec.loader:
        _stdlib_platform = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_stdlib_platform)
        for _name in dir(_stdlib_platform):
            if _name not in globals():
                globals()[_name] = getattr(_stdlib_platform, _name)


def browser_window():
    try:
        import platform
        window = getattr(platform, "window", None)
        if window is not None:
            return window
    except ImportError:
        pass
    return globals().get("window", getattr(_stdlib_platform, "window", None))


def browser_inner_size():
    if not WEB_BUILD:
        return None
    try:
        window = browser_window()
        return int(window.innerWidth), int(window.innerHeight)
    except (AttributeError, TypeError, ValueError):
        return None


def browser_pointer_clicks():
    if not WEB_BUILD:
        return None
    try:
        return getattr(browser_window(), "__mushPointerClicks", None)
    except AttributeError:
        return None


def browser_framebuffer_key(framebuffer_options):
    if not WEB_BUILD:
        return "high"
    try:
        window = browser_window()
        search = str(window.location.search)
        if "fb=high" in search or "res=720" in search:
            return "high"
        if "fb=standard" in search or "fb=low" in search or "res=540" in search:
            return "standard"
        stored = str(window.localStorage.getItem("mushFramebuffer"))
        if stored in framebuffer_options:
            return stored
    except (AttributeError, ImportError, TypeError):
        pass
    return "standard"


def reload_with_framebuffer(key):
    if not WEB_BUILD:
        return False
    try:
        window = browser_window()
        window.localStorage.setItem("mushFramebuffer", key)
        location = window.location
        pathname = str(getattr(location, "pathname", "/") or "/")
        hash_fragment = str(getattr(location, "hash", "") or "")
        location.href = f"{pathname}?fb={key}{hash_fragment}"
        return True
    except (AttributeError, ImportError, TypeError):
        return False


def __getattr__(name):
    if _stdlib_platform is not None:
        return getattr(_stdlib_platform, name)
    raise AttributeError(name)
