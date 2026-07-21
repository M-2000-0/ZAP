"""
Zap package manager.

Manages dependencies declared in zap.json. Supports:
  - Local packages (file: paths)
  - Git packages (git+https://...)
  - Registry packages (from a Zap registry, default: https://registry.zap-lang.org)

Dependencies are resolved into a zap.lock file for deterministic installs.
Installed packages go into the local .zap_modules/ directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field

ZAP_REGISTRY = "https://registry.zap-lang.org"
MODULES_DIR = ".zap_modules"
LOCKFILE = "zap.lock"
CONFIG = "zap.json"


@dataclass
class PackageSpec:
    name: str
    source: str  # "registry", "file", "git"
    version: str  # version range or path
    resolved: str = ""

    @classmethod
    def parse(cls, spec: str) -> "PackageSpec":
        if spec.startswith("file:"):
            path = spec[5:]
            return cls(name=os.path.basename(path), source="file", version=path)
        if spec.startswith("git+") or spec.startswith("git:"):
            name = spec.split("/")[-1].replace(".git", "")
            return cls(name=name, source="git", version=spec)
        if "@" in spec:
            name, version = spec.split("@", 1)
        else:
            name, version = spec, "*"
        return cls(name=name, source="registry", version=version)


@dataclass
class LockEntry:
    resolved: str
    integrity: str = ""

    def to_dict(self) -> dict:
        return {"resolved": self.resolved, "integrity": self.integrity}


@dataclass
class Lockfile:
    version: int = 1
    packages: dict[str, LockEntry] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str) -> "Lockfile":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        lf = cls(version=data.get("version", 1))
        for name, entry in data.get("packages", {}).items():
            lf.packages[name] = LockEntry(
                resolved=entry["resolved"],
                integrity=entry.get("integrity", ""),
            )
        return lf

    def save(self, path: str) -> None:
        data = {
            "version": self.version,
            "packages": {k: v.to_dict() for k, v in self.packages.items()},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def key_for(self, spec: PackageSpec) -> str:
        if spec.source == "file":
            return f"{spec.name}@file:{spec.version}"
        if spec.source == "git":
            return f"{spec.name}@git:{spec.version}"
        return f"{spec.name}@{spec.version}"


def load_config(project_dir: str) -> dict:
    config_path = os.path.join(project_dir, CONFIG)
    if not os.path.exists(config_path):
        return {"name": os.path.basename(project_dir), "dependencies": {}}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(project_dir: str, config: dict) -> None:
    config_path = os.path.join(project_dir, CONFIG)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _fetch_registry_metadata(name: str) -> dict:
    import urllib.request
    url = f"{ZAP_REGISTRY}/{name}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"failed to fetch {name} from registry: {e}")


def _resolve_version(meta: dict, version_range: str) -> str:
    versions = sorted(meta.get("versions", {}).keys())
    if not versions:
        raise RuntimeError("no versions available")
    if version_range == "*" or version_range == "":
        return versions[-1]
    if version_range.startswith("^"):
        major = int(version_range[1:].split(".")[0])
        for v in reversed(versions):
            if int(v.split(".")[0]) == major:
                return v
    if version_range in versions:
        return version_range
    for v in reversed(versions):
        if v.startswith(version_range.rstrip(".")):
            return v
    return versions[-1]


def _download_package(name: str, version: str, dest: str) -> str:
    import urllib.request
    url = f"{ZAP_REGISTRY}/{name}/{version}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            integrity = hashlib.sha256(data).hexdigest()
            os.makedirs(dest, exist_ok=True)
            pkg = json.loads(data.decode("utf-8"))
            for fname, content in pkg.get("files", {}).items():
                fpath = os.path.join(dest, fname)
                os.makedirs(os.path.dirname(fpath), exist_ok=True)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(content)
            return f"sha256:{integrity}"
    except Exception as e:
        raise RuntimeError(f"failed to download {name}@{version}: {e}")


def _copy_local_package(src: str, dest: str) -> str:
    if not os.path.exists(src):
        raise RuntimeError(f"local package not found: {src}")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)
    if os.path.isfile(src):
        # Single file: copy to dest/<filename>
        shutil.copy2(src, os.path.join(dest, os.path.basename(src)))
    else:
        shutil.copytree(src, dest)
    h = hashlib.sha256()
    for root, _, files in os.walk(dest):
        for f in sorted(files):
            if f.endswith(".zap"):
                with open(os.path.join(root, f), "rb") as fh:
                    h.update(fh.read())
    return f"sha256:{h.hexdigest()}"


def install(args, *, project_dir: str = None, diag_format: str = "text") -> int:
    from .diagnostics import runtime_error, emit

    project_dir = project_dir or os.getcwd()
    config = load_config(project_dir)
    deps = config.get("dependencies", {})

    if not deps:
        if diag_format == "json":
            emit([], fmt="json")
        print("No dependencies to install.")
        return 0

    modules_dir = os.path.join(project_dir, MODULES_DIR)
    lockfile = Lockfile.load(os.path.join(project_dir, LOCKFILE))
    errors = []

    for dep_name, dep_spec in deps.items():
        spec = PackageSpec.parse(dep_spec)
        key = lockfile.key_for(spec)
        pkg_dir = os.path.join(modules_dir, spec.name)

        if key in lockfile.packages and os.path.exists(pkg_dir):
            print(f"  {spec.name} - already installed")
            continue

        try:
            if spec.source == "file":
                src = spec.version
                if not os.path.isabs(src):
                    src = os.path.join(project_dir, src)
                integrity = _copy_local_package(src, pkg_dir)
                resolved = spec.version
            elif spec.source == "git":
                raise RuntimeError("git packages not yet supported")
            else:
                meta = _fetch_registry_metadata(spec.name)
                resolved_ver = _resolve_version(meta, spec.version)
                resolved = f"{spec.name}@{resolved_ver}"
                integrity = _download_package(spec.name, resolved_ver, pkg_dir)
                spec.version = resolved_ver
                key = lockfile.key_for(spec)

            lockfile.packages[key] = LockEntry(resolved=resolved, integrity=integrity)
            print(f"  {spec.name}@{spec.version} - installed")
        except Exception as e:
            errors.append(runtime_error(str(e), code="Z550", file=dep_name))

    if errors:
        emit(errors, fmt=diag_format)
        sys.exit(1)

    lockfile.save(os.path.join(project_dir, LOCKFILE))
    print(f"\nInstalled {len(lockfile.packages)} package(s)")
    print(f"Lockfile: {os.path.join(project_dir, LOCKFILE)}")
    return 0


def add(args, *, project_dir: str = None, diag_format: str = "text") -> int:
    from .diagnostics import runtime_error, emit

    if not args:
        print("usage: zap add <package-spec>", file=sys.stderr)
        sys.exit(1)

    project_dir = project_dir or os.getcwd()
    spec_str = args[0]
    spec = PackageSpec.parse(spec_str)

    config = load_config(project_dir)
    deps = config.setdefault("dependencies", {})

    deps[spec.name] = spec_str
    save_config(project_dir, config)
    print(f"Added {spec_str} to dependencies")

    install([], project_dir=project_dir, diag_format=diag_format)
    return 0
