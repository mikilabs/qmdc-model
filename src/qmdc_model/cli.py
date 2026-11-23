"""qmdc-model command-line interface: init, upgrade, lint, sop."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import sys
import tempfile
import unicodedata
from importlib import resources
from pathlib import Path
from string import Template

from . import __version__
from .linter import lint_workspace, issues_to_json


def _asset(*parts: str) -> str:
    return resources.files("qmdc_model").joinpath(*parts).read_text(encoding="utf-8")


def _asset_path(*parts: str) -> Path:
    """Filesystem path of a packaged asset (wheels install unzipped, so this is real)."""
    return Path(str(resources.files("qmdc_model").joinpath(*parts)))


def _workspace_id(name: str) -> str:
    """Derive a valid, stable QMD id from a directory name, preserving Unicode letters."""
    normalized = unicodedata.normalize("NFKC", name).casefold()
    slug = re.sub(r"_+", "_", "".join(ch if ch.isalnum() else "_" for ch in normalized)).strip("_")
    if not slug:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        return f"ws_{digest}"
    if slug[0].isdigit():
        return f"ws_{slug}"
    return slug


def _workspace_label(name: str) -> str:
    """A one-line human label that cannot inject another QMD object declaration."""
    label = re.sub(r"\s+", " ", name).strip() or "Workspace"
    return label.replace("[", "［").replace("]", "］")


# `*.vendor.qmd.md` files are OWNED by this tool: `upgrade` creates, overwrites and
# deletes them to match the installed version, so hand edits are always lost. Everything
# else init writes is a seed the author then owns.
VENDOR_SUFFIX = ".vendor.qmd.md"
MARKER_OPEN = "<!-- qmdc-model "


def _vendor_marker() -> str:
    return (f"{MARKER_OPEN}{__version__} — generated file owned by the tool: "
            f"`qmdc-model upgrade` rewrites or deletes it. Do not edit by hand. -->\n\n")


def _strip_marker(text: str) -> str:
    """Drop the generated-file marker so two vendored copies compare by body alone."""
    if text.startswith(MARKER_OPEN):
        return text.partition("-->")[2].lstrip("\n")
    return text


def _shipped_vendor() -> dict[str, str]:
    """Vendored files this version ships: file name -> body (without the marker)."""
    vendor_dir = _asset_path("vendor")
    return {p.name: p.read_text(encoding="utf-8")
            for p in sorted(vendor_dir.glob("*" + VENDOR_SUFFIX))}


class UpgradePathError(ValueError):
    pass


def _assert_no_symlink(ws: Path, path: Path) -> None:
    """Every component below ws must be a real path, never a redirect elsewhere."""
    try:
        rel = path.relative_to(ws)
    except ValueError as e:
        raise UpgradePathError(f"path is outside workspace: {path}") from e
    cursor = ws
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            target = cursor.resolve(strict=False)
            raise UpgradePathError(f"refusing symlink inside workspace: {cursor} -> {target}")
    resolved_parent = path.parent.resolve(strict=False)
    if not resolved_parent.is_relative_to(ws):
        raise UpgradePathError(f"path resolves outside workspace: {path} -> {resolved_parent}")


def _metamodel_dirs(ws: Path) -> list[Path]:
    """Every real `_metamodel` namespace contained in the workspace."""
    found = []
    for path in sorted(ws.rglob("_metamodel")):
        _assert_no_symlink(ws, path)
        if path.is_dir():
            found.append(path)
        elif path.exists():
            raise UpgradePathError(f"_metamodel path is not a directory: {path}")
    return found


def _validate_vendor_path(ws: Path, path: Path) -> None:
    _assert_no_symlink(ws, path)
    if path.exists() and not path.is_file():
        raise UpgradePathError(f"vendor path is not a regular file: {path}")


def _preflight_plan(ws: Path, plan, *, require_writable: bool) -> None:
    """Refuse unsafe paths always; check mutability before a real apply."""
    for verb, path, _body, _why in plan:
        _validate_vendor_path(ws, path)
        if not require_writable:
            continue
        if path.exists():
            immutable = getattr(stat, "UF_IMMUTABLE", 0) | getattr(stat, "SF_IMMUTABLE", 0)
            if getattr(path.stat(), "st_flags", 0) & immutable:
                raise UpgradePathError(f"vendor path is immutable: {path}")
        if verb == "update" and not os.access(path, os.W_OK):
            raise UpgradePathError(f"vendor file is not writable: {path}")
        if verb in {"create", "delete"} and not os.access(path.parent, os.W_OK):
            raise UpgradePathError(f"vendor directory is not writable: {path.parent}")


def _write_owned_file(path: Path, content: str) -> None:
    """Atomically replace one tool-owned file without following/altering a hard link."""
    temp_name = None
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".qmdc-model-", suffix=".tmp",
                                         delete=False) as temp:
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
            temp_name = Path(temp.name)
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            temp_name.unlink(missing_ok=True)


def _build_upgrade_plan(ws: Path, shipped: dict[str, str], *, require_writable: bool):
    mm_dirs = _metamodel_dirs(ws)
    if not mm_dirs:
        return [], []
    primary = ws / "_metamodel"
    if primary not in mm_dirs:
        primary = mm_dirs[0]

    found: dict[str, list[Path]] = {}
    for mm in mm_dirs:
        for path in sorted(mm.glob("*" + VENDOR_SUFFIX)):
            _validate_vendor_path(ws, path)
            found.setdefault(path.name, []).append(path)

    plan: list[tuple[str, Path, str | None, str]] = []
    for name, body in shipped.items():
        copies = sorted(found.get(name, []), key=lambda p: (p.parent != primary, len(p.parts)))
        if not copies:
            plan.append(("create", primary / name, body, ""))
            continue
        keep, extra = copies[0], copies[1:]
        if keep.read_text(encoding="utf-8") != _vendor_marker() + body:
            plan.append(("update", keep, body, ""))
        for duplicate in extra:
            plan.append(("delete", duplicate, None,
                         "duplicate copy — vendored once per workspace"))
    for name, copies in found.items():
        if name not in shipped:
            plan.extend(("delete", p, None, "not shipped by this version") for p in copies)

    _preflight_plan(ws, plan, require_writable=require_writable)
    return mm_dirs, plan


def cmd_init(args) -> int:
    if args.workspace == "":
        print("error: workspace path must not be empty")
        return 2
    ws = Path(args.workspace).resolve()
    if ws.exists() and not ws.is_dir():
        print(f"error: workspace path '{ws}' exists and is not a directory")
        return 2
    created_dir = not ws.exists()
    try:
        ws.mkdir(parents=True, exist_ok=True)
        mm = ws / "_metamodel"
        _assert_no_symlink(ws, mm)
        if mm.exists() and not mm.is_dir():
            print(f"error: _metamodel path exists and is not a directory: {mm}")
            return 2
        mm.mkdir(exist_ok=True)
    except (OSError, UpgradePathError) as e:
        print(f"error: cannot initialize workspace: {e}")
        return 2

    root_readme = Template(_asset("templates", "workspace-readme.qmd.md")).substitute(
        label=_workspace_label(ws.name), id=_workspace_id(ws.name)
    )
    targets = {
        "readme.qmd.md": root_readme,
        "_metamodel/readme.qmd.md": _asset("templates", "metamodel-readme.qmd.md"),
    }
    for name, body in _shipped_vendor().items():
        targets[f"_metamodel/{name}"] = _vendor_marker() + body

    created, skipped = [], []
    try:
        for rel, content in targets.items():
            dest = ws / rel
            if rel.endswith(VENDOR_SUFFIX):
                _validate_vendor_path(ws, dest)
            if dest.exists() or dest.is_symlink():
                skipped.append(rel)
            else:
                dest.write_text(content, encoding="utf-8")
                created.append(rel)
    except (OSError, UpgradePathError) as e:
        print(f"error: cannot initialize workspace: {e}")
        return 2

    if created_dir:
        print(f"  created  {ws}/")
    for rel in created:
        print(f"  created  {rel}")
    for rel in skipped:
        print(f"  skipped  {rel} (exists)")
    print(f"Initialized workspace {ws}")
    return 0


def cmd_upgrade(args) -> int:
    """Re-vendor the workspace so its vendored files match this version of the tool.

    The tool owns `*.vendor.qmd.md` outright: a missing one is created, a stale one is
    rewritten, and one this version no longer ships is deleted. Nothing else is touched —
    the workspace's own readmes, KindSchemas and LintRules are the author's.

    A vendored file is kept as ONE copy per workspace even though `_metamodel` namespaces
    are many: the base meta-kinds carry fixed object ids, so a second copy makes every
    reference inside them ambiguous. Extra copies are therefore removed, and the linter
    finds the surviving one by `__kind` from anywhere in the workspace.
    """
    if args.workspace == "":
        print("error: workspace path must not be empty")
        return 2
    ws = Path(args.workspace).resolve()
    if not ws.is_dir():
        print(f"error: workspace '{ws}' is not a directory")
        return 2

    try:
        shipped = _shipped_vendor()
        mm_dirs, plan = _build_upgrade_plan(ws, shipped,
                                             require_writable=not args.dry_run)
    except (OSError, UpgradePathError) as e:
        print(f"error: cannot plan upgrade: {e}")
        return 2
    if not mm_dirs:
        print(f"no _metamodel namespace under {ws} — run 'qmdc-model init' first")
        return 0

    if not plan:
        print(f"vendored metaschema already at {__version__}: one workspace copy across "
              f"{len(mm_dirs)} _metamodel namespace(s) — nothing to do")
        return 0

    done = {"create": "created", "update": "updated", "delete": "deleted"}
    try:
        for verb, path, body, why in plan:
            rel = path.relative_to(ws)
            note = f"  ({why})" if why else ""
            if args.dry_run:
                print(f"  would {verb}  {rel}{note}")
                continue
            if verb == "delete":
                path.unlink()
            else:
                _write_owned_file(path, _vendor_marker() + body)
            print(f"  {done[verb]}  {rel}{note}")
    except OSError as e:
        print(f"error: upgrade failed while applying {path}: {e}")
        return 2

    if args.dry_run:
        print(f"dry run: {len(plan)} change(s) pending, nothing written")
    else:
        print(f"Upgraded vendored metaschema to {__version__} in {ws}")
    return 0


SOP_ASSET = ("sop", "sop-metamodel-creation.md")

def cmd_sop(args) -> int:
    """Emit the metamodel-creation SOP shipped with — and version-locked to — this tool."""
    if args.path:
        p = _asset_path(*SOP_ASSET)
        if not p.is_file():
            print("error: the SOP ships inside the package but is not a file on disk")
            return 2
        print(p)
        return 0
    print(_asset(*SOP_ASSET), end="")
    return 0


def cmd_lint(args) -> int:
    if args.workspace == "":
        print("error: workspace path must not be empty")
        return 2
    ws = Path(args.workspace)
    issues = lint_workspace(ws)

    if args.json:
        print(issues_to_json(issues))
    else:
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]
        infos = [i for i in issues if i.severity == "info"]
        print(f"METAMODEL LINT  ({ws})")
        if not issues:
            print("  ✅ ok")
        icons = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
        for i in issues:
            icon = icons.get(i.severity, "❓")
            location = f" {i.file}:{i.line}" if i.file else ""
            print(f"  {icon} [{i.code}]{location} {i.message or i.object}")
        print(f"RESULT: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} infos")
        print("🎉 Lint PASSED" if not errors else "⛔ Lint FAILED")

    return 1 if any(i.severity == "error" for i in issues) else 0


def _tolerate_narrow_console() -> None:
    """Never crash on output: a cp1252 stdout (Windows pipes) cannot encode ✅/🎉.

    Such streams keep their encoding but replace what they cannot show with '?'.
    """
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if enc != "utf8" and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def main(argv=None) -> int:
    _tolerate_narrow_console()
    p = argparse.ArgumentParser(prog="qmdc-model", description="Metamodel operator and linter for QMD workspaces")
    p.add_argument("--version", action="version", version=f"qmdc-model {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser(
        "init",
        help="Create the workspace directory if missing, scaffold its root readme and the "
             "_metamodel namespace, and vendor the base meta-kinds",
    )
    pi.add_argument("workspace", nargs="?", default=".")
    pi.set_defaults(func=cmd_init)

    pu = sub.add_parser(
        "upgrade",
        help="Re-vendor the workspace to this version: the tool owns *.vendor.qmd.md and "
             "creates, rewrites or deletes them (one copy per workspace); nothing else is "
             "touched",
    )
    pu.add_argument("workspace", nargs="?", default=".")
    pu.add_argument("--dry-run", action="store_true",
                    help="Print the changes without writing or deleting anything")
    pu.set_defaults(func=cmd_upgrade)

    pl = sub.add_parser("lint", help="Lint a workspace against its metaschema and KindSchemas (two-phase)")
    pl.add_argument("workspace", nargs="?", default=".")
    pl.add_argument("--json", action="store_true", help="Emit structured issues as JSON")
    pl.set_defaults(func=cmd_lint)

    ps = sub.add_parser(
        "sop",
        help="Print the metamodel-creation SOP shipped with this version (the procedure "
             "is version-locked to the checks the linter enforces)",
    )
    ps.add_argument("--path", action="store_true",
                    help="Print the SOP's path on disk instead of its text")
    ps.set_defaults(func=cmd_sop)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
