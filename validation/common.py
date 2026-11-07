"""Shared loading helpers for the post-freeze validation layer."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_MODULES: dict[str, object] = {}


def load_module(name: str, relative_path: str, *, add_dir: bool = False):
    """Load a frozen module by path without changing the frozen tree.

    Every module is registered under a unique validation-local name. When
    ``add_dir`` is true, the module directory is added to ``sys.path`` so a
    frozen runner can import its siblings.
    """
    key = f"validation_{name}_{relative_path.replace('/', '_').replace('\\', '_')}"
    if key in _MODULES:
        return _MODULES[key]
    path = ROOT / relative_path
    if add_dir:
        directory = str(path.parent)
        if directory not in sys.path:
            sys.path.insert(0, directory)
    spec = importlib.util.spec_from_file_location(key, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    _MODULES[key] = module
    return module


def build12_module():
    return load_module("build12", "theory_development/build_12/build_12.py", add_dir=True)


def vg20_module():
    return load_module("vg20", "virtual_ground/build_20/virtual_ground.py", add_dir=True)


def gd22_module():
    return load_module("gd22", "virtual_ground/build_22/ground_discovery.py", add_dir=True)


def gs23_module():
    return load_module("gs23", "virtual_ground/build_23/ground_synthesis.py", add_dir=True)


def lg24_module():
    return load_module(
        "lg24",
        "virtual_ground/build_25/legacy/build24/latent_ground.py",
        add_dir=True,
    )


def rb29_module():
    return load_module("rb29", "virtual_ground/build_29/run_build29.py", add_dir=True)


def sc30_module():
    return load_module("sc30", "virtual_ground/build_30/signal_code.py", add_dir=True)


def rb30_module():
    return load_module("rb30", "virtual_ground/build_30/run_build30.py", add_dir=True)
