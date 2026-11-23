"""
Metamodel linter — config-driven, two-phase.

Reads KindSchema + LintRule objects from a QMD workspace and checks domain objects against
them. Emits structured issues so results are stable and comparable (used by data-driven
tests).

**This module never parses QMD.** Everything comes from the `qmdc` toolchain: the parser's
workspace file manifest; objects, their global identities and typed field values from
qmdc's `objects` table; the RESOLVED reference graph from its `edges` table (source,
target, field and role, already resolved across namespace boundaries); and structural
diagnostics from `qmdc workspace validate`. No regex over `[[#ref]]`, no splitting of list
syntax — a source file qmdc discovers but does not index is an error, never silently absent.

**A LintRule governs the namespace ENCLOSING the one it is declared in**, and must be
declared in a metamodel namespace (`_metamodel` at the workspace root, `<ns>._metamodel`
beneath a namespace) or in the workspace root itself — anywhere else is
`rule_bad_placement` and the rule does not run. So exactly two scopes are reachable: the
whole workspace (root) and one namespace with its descendants (nested metamodel). The scope
bounds which objects a rule judges, which field names it may reference, and what `all_of()`
enumerates — so one extension cannot turn a project's lint red on a sibling extension's
data, and cannot have its own rule invalidated by a neighbour's field vocabulary. Reference
traversal (`refs`/`target`/`incoming`) stays global: evidence may come from anywhere.

Checks:
  - structural            : passthrough of `qmdc workspace validate`
  - missing_required      : a required field is absent
  - unexpected_field      : strict Kind has a field beyond required+optional
  - enum_violation        : scalar value not in the allowed literal set
  - target_kind_violation : a reference points at a disallowed Kind
  - min_count_violation   : a present field holds fewer values than its declared minimum
  - max_count_violation   : a present field holds more values than its declared maximum
  - rule_failed           : a LintRule assert returned false
  - rule_eval_failed      : a LintRule assert could not be evaluated (broken metamodel)
  - rule_no_selector      : a LintRule declares no scope selector
  - rule_bad_placement    : a LintRule is declared outside a metamodel namespace
  - rule_bad_selector     : a LintRule declares a scope selector this linter cannot run
  - rule_selector_conflict: a LintRule declares more than one scope selector
  - rule_unknown_kind     : for_each names a Kind that does not exist
  - rule_unknown_field    : an assert names no field of its selected Kind
  - rule_bad_severity     : severity is not error/warning/info
  - rule_bad_message      : message is not a non-empty string
  - rule_empty_scope      : a valid selector currently matches no domain objects
  - retired_rule          : a valid/invalid retired rule is disclosed but not executed
  - retired_object        : retired domain object is disclosed and skipped
  - schema_field_list     : required/optional contains a non-field-name value
  - schema_field_overlap  : one field is both required and optional
  - schema_bad_kind       : KindSchema kind is not one non-empty string
  - schema_bad_strict     : strict is not a QMD boolean
  - schema_bad_child      : constraints/cardinality is not exactly one expected child
  - schema_bad_placement  : schema helper object has the wrong qmdc parent
  - schema_bad_target_kind: target_kind points at something other than a KindSchema
  - schema_unknown_field_constraint: a constraint names no declared field
  - schema_empty_constraint: a FieldConstraints entry has no enum/reference value
  - duplicate_kind_schema : more than one KindSchema claims a Kind (one issue per claim)
  - constraint_value_shape: domain value switches enum/reference representation
  - cardinality_bad_bound : min_count/max_count is not a non-negative integer
  - cardinality_bad_range : min_count is greater than max_count
  - cardinality_bad_shape : count bounds are not in a FieldCardinality child
  - workspace_not_found   : lint target is not a directory
  - workspace_empty       : qmdc parsed no objects
  - source_unparsed       : qmdc discovered a file but indexed no object from it
  - source_symlink        : QMD source path is redirected through a symlink
  - source_bad_extension  : QMD-like extension is not lowercase `.qmd.md`
  - qmdc_failed           : qmdc failed or returned an invalid response
  - missing_metaschema    : initialized workspace lost its vendored base kinds
  - missing_kind_schema   : observed domain Kind has no KindSchema
  - retired_schema        : retired KindSchema is disclosed and no longer claims its Kind
  - lifecycle_bad_value   : reserved lifecycle field is not exactly `removed`
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field as dc_field
from pathlib import Path

RETIRED = "removed"


@dataclass(frozen=True)
class Issue:
    severity: str          # error | warning | info
    code: str              # check code (see module docstring)
    object: str = ""       # __id of the offending object
    field: str = ""        # field involved, if any
    detail: str = ""       # extra context (e.g. rule id)
    message: str = ""      # human-readable text (not used for comparison)
    global_id: str = ""    # qmdc identity; disambiguates equal local ids across namespaces
    file: str = ""         # source file, from qmdc
    line: int = 0          # source line, from qmdc

    def key(self):
        """Structural identity for comparison (message and location excluded)."""
        return (self.severity, self.code, self.global_id or self.object,
                self.field, self.detail)

    def where(self) -> str:
        return f"{self.file}:{self.line}" if self.file else ""


# --------------------------------------------------------------------------- io

def qmdc_executable() -> str:
    """The `qmdc` that ships with this install, else the one on PATH.

    qmdc is a dependency. Its wheel bundles the native binary behind a Python
    launcher that costs ~40 ms per call, so the binary is used directly when the
    installed qmdc exposes it; next comes the console script beside this
    interpreter (`uv tool install`, `uvx`, a venv), then PATH. The bundled copies
    win over PATH, so the linter runs the qmdc version this package resolved.
    """
    try:
        from qmdc._launcher import _bundled_binary
        native = _bundled_binary()
    except Exception:  # older/newer qmdc without that helper: fall through
        native = None
    if native is not None:
        return str(native)
    script = shutil.which("qmdc", path=str(Path(sys.executable).parent))
    return script or shutil.which("qmdc") or "qmdc"


def run_qmdc(args):
    try:
        return subprocess.run([qmdc_executable()] + args, capture_output=True, text=True)
    except OSError as e:
        raise RuntimeError(f"could not execute qmdc: {e}") from e


OBJECT_COLUMNS = ("__global_id", "__id", "__local_id", "__kind", "__label", "__namespace",
                  "__file", "__line", "__parent", "__level")


def _query(ws: Path, sql: str) -> list[dict]:
    """Run one read-only query through qmdc and return rows as dicts."""
    r = run_qmdc(["query", str(ws), sql, "--format", "json"])
    if r.returncode != 0:
        raise RuntimeError(f"qmdc query failed:\n{r.stderr}")
    if not r.stdout.strip():
        return []
    payload = json.loads(r.stdout)
    if isinstance(payload, list):
        if not all(isinstance(row, dict) for row in payload):
            raise ValueError("qmdc query returned a non-object row")
        return payload
    if not isinstance(payload, dict):
        raise ValueError(f"qmdc query returned {type(payload).__name__}, expected object")
    cols, rows = payload.get("columns"), payload.get("rows")
    if not isinstance(cols, list) or not isinstance(rows, list):
        raise ValueError("qmdc query result must contain columns[] and rows[]")
    result = []
    for row in rows:
        if isinstance(row, (list, tuple)):
            if len(row) != len(cols):
                raise ValueError("qmdc query row width does not match columns")
            result.append(dict(zip(cols, row)))
        elif isinstance(row, dict):
            result.append(row)
        else:
            raise ValueError("qmdc query returned a scalar row")
    return result


def load_objects(ws: Path) -> list[dict]:
    """Objects as qmdc sees them: its own global id, its own field values.

    Taken from qmdc's object table rather than `workspace parse`, because only the table
    carries `__global_id` — the identity every edge is expressed in. Field values arrive as
    the parser typed them (a list stays a list), in the `data` column.
    """
    objects = []
    for row in _query(ws, f"SELECT {', '.join(OBJECT_COLUMNS)}, data FROM objects"):
        if not isinstance(row, dict):
            raise ValueError("qmdc objects query returned a non-object row")
        obj = {c: row.get(c) for c in OBJECT_COLUMNS if row.get(c) is not None}
        raw = row.get("data")
        fields = raw if isinstance(raw, dict) else json.loads(raw or "{}")
        if not isinstance(fields, dict):
            raise ValueError(f"qmdc object data must be an object, got {type(fields).__name__}")
        obj.update({k: v for k, v in fields.items() if not k.startswith("__")})
        obj["__line"] = int(obj.get("__line") or 0)
        objects.append(obj)
    return objects


def load_edges(ws: Path) -> list[dict]:
    """qmdc's own RESOLVED reference graph: one row per (source, target, field, role)."""
    return _query(ws, "SELECT source_id, target_id, source_field, edge_type FROM edges")


def load_files(ws: Path) -> list[str]:
    """QMD files qmdc discovered, from qmdc's parser manifest (never filesystem parsing)."""
    r = run_qmdc(["workspace", "parse", str(ws), "--format", "full"])
    if r.returncode != 0:
        raise RuntimeError(f"qmdc workspace parse failed (exit {r.returncode}): "
                           f"{(r.stderr or r.stdout).strip()}")
    payload = json.loads(r.stdout) if r.stdout.strip() else None
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise ValueError("qmdc workspace parse result must contain files[]")
    if not all(isinstance(path, str) for path in payload["files"]):
        raise ValueError("qmdc workspace parse files[] must contain strings")
    return payload["files"]


def validate_structural(ws: Path) -> list[Issue]:
    r = run_qmdc(["workspace", "validate", str(ws)])
    try:
        errs = json.loads(r.stdout) if r.stdout.strip() else None
    except json.JSONDecodeError as e:
        detail = (r.stderr or r.stdout).strip()
        return [Issue("error", "qmdc_failed",
                      message=f"qmdc workspace validate returned invalid JSON "
                              f"(exit {r.returncode}): {e}; {detail}")]
    if not isinstance(errs, list):
        detail = (r.stderr or r.stdout).strip()
        return [Issue("error", "qmdc_failed",
                      message=f"qmdc workspace validate returned no diagnostic array "
                              f"(exit {r.returncode}): {detail}")]
    if r.returncode != 0 and not errs:
        detail = (r.stderr or "no diagnostic detail").strip()
        return [Issue("error", "qmdc_failed",
                      message=f"qmdc workspace validate failed with empty diagnostics "
                              f"(exit {r.returncode}): {detail}")]
    issues = []
    for e in errs:
        if not isinstance(e, dict):
            return [Issue("error", "qmdc_failed",
                          message=f"qmdc workspace validate returned a non-object diagnostic: {e!r}")]
        try:
            line = int(e.get("line") or 0)
        except (TypeError, ValueError):
            return [Issue("error", "qmdc_failed",
                          message=f"qmdc workspace validate returned invalid line "
                                  f"{e.get('line')!r} in diagnostic {e!r}")]
        issues.append(Issue("error", "structural", e.get("objectId", ""), "",
                            e.get("type", ""), f"{e.get('type')}: {e.get('message')}",
                            file=e.get("file", ""), line=line))
    return issues


# ------------------------------------------------------------------- the index

@dataclass
class Index:
    """Objects and qmdc's resolved edges, addressable by identity.

    An object is keyed by the ``__global_id`` qmdc assigned it. For convenience in a
    LintRule, the alias map also accepts only the alternative identities qmdc explicitly
    exposed (`__id`, `__local_id`); this code never splits or reconstructs an id.
    """

    objects: list[dict] = dc_field(default_factory=list)
    by_kind: dict[str, list[dict]] = dc_field(default_factory=dict)
    by_global: dict[str, dict] = dc_field(default_factory=dict)
    aliases: dict[str, list[dict]] = dc_field(default_factory=dict)
    out_edges: dict[tuple[str, str], list[str]] = dc_field(default_factory=dict)
    in_edges: dict[str, list[tuple[str, str, str]]] = dc_field(default_factory=dict)

    @classmethod
    def build(cls, objects: list[dict], edges: list[dict]) -> "Index":
        ix = cls(objects=objects)
        for o in objects:
            ix.by_kind.setdefault(o.get("__kind", ""), []).append(o)
            gid = str(o.get("__global_id") or o.get("__id") or "")
            if gid:
                ix.by_global[gid] = o
            for alias in {str(o.get(k)) for k in ("__global_id", "__id", "__local_id")
                          if o.get(k)}:
                ix.aliases.setdefault(alias, []).append(o)
        for e in edges:
            src, tgt = str(e.get("source_id", "")), str(e.get("target_id", ""))
            fname = str(e.get("source_field", ""))
            edge_type = str(e.get("edge_type", ""))
            if not (src and tgt and fname):
                continue
            ix.out_edges.setdefault((src, fname), []).append(tgt)
            ix.in_edges.setdefault(tgt, []).append((src, fname, edge_type))
        return ix

    # -- identity -----------------------------------------------------------
    def gid(self, obj: dict) -> str:
        return str(obj.get("__global_id") or obj.get("__id") or "")

    def resolve(self, ref) -> dict | None:
        """The object a reference denotes, or None when absent or ambiguous."""
        if isinstance(ref, dict):
            return ref
        if ref is None:
            return None
        key = str(ref).strip()
        if key in self.by_global:
            return self.by_global[key]
        hits = self.aliases.get(key) or []
        return hits[0] if len(hits) == 1 else None

    def same(self, a: dict, b: dict) -> bool:
        ka, kb = self.gid(a), self.gid(b)
        return bool(ka) and ka == kb

    def child(self, obj: dict, name: str) -> dict:
        """A nested child of an object (e.g. a KindSchema's `constraints`), via its edge."""
        for tgt in self.out_edges.get((self.gid(obj), name), []):
            child = self.by_global.get(tgt)
            if child is not None:
                return child
        return {}

    # -- references (always qmdc's, never ours) -----------------------------
    def refs(self, obj: dict, fname: str) -> list[str]:
        return list(self.out_edges.get((self.gid(obj), fname), []))

    def has_refs(self, obj: dict, fname: str) -> bool:
        return bool(self.out_edges.get((self.gid(obj), fname)))

    def value_count(self, obj: dict, fname: str) -> int:
        """How many values a field holds: resolved references, else the parsed value."""
        refs = self.refs(obj, fname)
        if refs:
            return len(refs)
        v = obj.get(fname)
        if v is None:
            return 0
        if isinstance(v, (list, tuple)):
            return len(v)
        return 0 if str(v).strip() == "" else 1


# ------------------------------------------------------------------ utilities

def as_int(v):
    """Integer value of a constraint bound, or None when absent / not a number."""
    if v is None or isinstance(v, bool):
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def name_list(v) -> list[str]:
    """Field names declared on a schema. qmdc hands us a real list for `[a, b]` syntax;
    a bare string is ONE name — this linter does not split strings itself."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v]
    s = str(v).strip()
    return [s] if s else []


def retirement(obj: dict) -> bool:
    """Only the reserved lifecycle field controls validation."""
    return str(obj.get("lifecycle", "")).strip() == RETIRED


def _at(obj: dict) -> dict:
    return {"global_id": str(obj.get("__global_id", "")),
            "file": str(obj.get("__file", "")), "line": int(obj.get("__line") or 0)}


def _where(obj: dict) -> str:
    """`file:line` of an object, for naming another place inside a message."""
    path = str(obj.get("__file", ""))
    return f"{path}:{int(obj.get('__line') or 0)}" if path else ""


def _scope_note(scope: str) -> str:
    """Names the namespace subtree a rule governs; the whole workspace needs no note."""
    return f" — rule governs namespace '{scope}' and its descendants" if scope else ""


# ----------------------------------------------- LintRule assert helper vocab


class UnsafeExpression(ValueError):
    """The LintRule expression uses syntax outside the documented, side-effect-free DSL."""


SAFE_CALLS = {
    "field", "has", "refs", "count", "target", "targets", "kind_of", "exists",
    "incoming", "all_of", "refs_of", "id_of", "overlaps", "same_members", "is_subset",
    "len", "all", "any", "str", "int", "bool", "sum",
}
SAFE_METHODS = {"get", "startswith", "endswith", "lower", "upper"}
SAFE_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Load, ast.Store,
    ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.UAdd, ast.USub,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.IfExp, ast.Call, ast.keyword, ast.Attribute,
    ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Subscript, ast.Slice,
    ast.GeneratorExp, ast.comprehension,
)


class ExpressionValidator(ast.NodeVisitor):
    """Reject everything except the small expression language documented in the SOP.

    In particular, attribute access is call-only and limited to harmless methods on the
    parser-produced strings/dicts. Python's object-model escape hatches (`__class__`,
    `__subclasses__`, import loaders, file/process APIs) never reach `eval`.
    """

    def __init__(self, tree: ast.AST):
        self.bound: set[str] = set()
        self.comprehension_depth = 0
        self.in_comprehension_iterator = False

    def generic_visit(self, node):
        if not isinstance(node, SAFE_NODES):
            raise UnsafeExpression(f"syntax '{type(node).__name__}' is not allowed")
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name):  # noqa: N802
        if node.id not in SAFE_CALLS | {"obj", "id", "True", "False", "None"} | self.bound:
            raise UnsafeExpression(f"name '{node.id}' is not allowed")

    def visit_Constant(self, node: ast.Constant):  # noqa: N802
        if isinstance(node.value, str) and len(node.value) > 2000:
            raise UnsafeExpression("string literal is longer than 2000 characters")
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if abs(node.value) > 1_000_000:
                raise UnsafeExpression("numeric literal is larger than 1000000")

    def visit_Attribute(self, node: ast.Attribute):  # noqa: N802
        if node.attr not in SAFE_METHODS:
            raise UnsafeExpression(f"method/attribute '{node.attr}' is not allowed")
        self.visit(node.value)

    def visit_Subscript(self, node: ast.Subscript):  # noqa: N802
        if (isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)
                and node.slice.value.startswith("__")):
            raise UnsafeExpression("dunder metadata access is not allowed")
        self.generic_visit(node)

    def _visit_comprehension(self, node, values):
        added = []
        previous_depth = self.comprehension_depth
        previous_iterator = self.in_comprehension_iterator
        self.comprehension_depth += 1
        try:
            for comp in node.generators:
                self.in_comprehension_iterator = True
                self.visit(comp.iter)
                self.in_comprehension_iterator = False
                if not isinstance(comp.target, ast.Name):
                    raise UnsafeExpression("comprehension target must be one simple name")
                name = comp.target.id
                if name.startswith("_") or name in SAFE_CALLS | {"obj", "id"}:
                    raise UnsafeExpression(f"comprehension target '{name}' is reserved")
                if name in self.bound:
                    raise UnsafeExpression(f"comprehension target '{name}' shadows an active name")
                self.bound.add(name)
                added.append(name)
                for condition in comp.ifs:
                    self.visit(condition)
            self.in_comprehension_iterator = False
            for value in values:
                self.visit(value)
        finally:
            self.comprehension_depth = previous_depth
            self.in_comprehension_iterator = previous_iterator
            for name in reversed(added):
                self.bound.remove(name)

    def visit_GeneratorExp(self, node: ast.GeneratorExp):  # noqa: N802
        self._visit_comprehension(node, [node.elt])

    def visit_ListComp(self, node: ast.ListComp):  # noqa: N802
        raise UnsafeExpression("list comprehensions are not allowed; use all()/any() with a generator")

    def visit_SetComp(self, node: ast.SetComp):  # noqa: N802
        raise UnsafeExpression("set comprehensions are not allowed; use a generator")

    def visit_DictComp(self, node: ast.DictComp):  # noqa: N802
        raise UnsafeExpression("dict comprehensions are not allowed; use a generator")

    def visit_Call(self, node: ast.Call):  # noqa: N802
        if isinstance(node.func, ast.Name) and node.func.id == "sum":
            if len(node.args) != 1 or node.keywords:
                raise UnsafeExpression("sum() accepts exactly one argument; a start value is not allowed")
        if any(isinstance(arg, ast.GeneratorExp) for arg in node.args):
            if not isinstance(node.func, ast.Name) or node.func.id not in {"all", "any", "sum"}:
                raise UnsafeExpression("generator expressions may only be consumed by all(), any(), or sum()")
        if isinstance(node.func, ast.Name):
            if node.func.id not in SAFE_CALLS:
                raise UnsafeExpression(f"call '{node.func.id}' is not allowed")
            if node.func.id == "all_of":
                if (len(node.args) != 1 or not isinstance(node.args[0], ast.Constant)
                        or not isinstance(node.args[0].value, str)):
                    raise UnsafeExpression("all_of() Kind must be one string literal")
                if self.comprehension_depth and not self.in_comprehension_iterator:
                    raise UnsafeExpression("all_of() cannot run inside a comprehension body")
            if node.func.id in FIELD_HELPERS:
                if (not node.args or not isinstance(node.args[0], ast.Constant)
                        or not isinstance(node.args[0].value, str)):
                    raise UnsafeExpression(f"{node.func.id}() field name must be a string literal")
                if node.args[0].value.startswith("__"):
                    raise UnsafeExpression("dunder metadata access is not allowed")
            if node.func.id == "refs_of":
                if (len(node.args) < 2 or not isinstance(node.args[1], ast.Constant)
                        or not isinstance(node.args[1].value, str)):
                    raise UnsafeExpression("refs_of() field name must be a string literal")
                if node.args[1].value.startswith("__"):
                    raise UnsafeExpression("dunder metadata access is not allowed")
        elif isinstance(node.func, ast.Attribute):
            if (node.func.attr == "get" and node.args and
                    isinstance(node.args[0], ast.Constant) and
                    isinstance(node.args[0].value, str) and
                    node.args[0].value.startswith("__")):
                raise UnsafeExpression("dunder metadata access is not allowed")
            self.visit_Attribute(node.func)
        else:
            raise UnsafeExpression("only documented helper and safe method calls are allowed")
        for arg in node.args:
            self.visit(arg)
        for keyword in node.keywords:
            if keyword.arg is None:
                raise UnsafeExpression("**kwargs expansion is not allowed")
            self.visit(keyword.value)


FIELD_HELPERS = {"field", "has", "refs", "count", "target", "targets"}


def analyze_expression(expr: str):
    if len(expr) > 4000:
        raise UnsafeExpression("expression is longer than 4000 characters")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise UnsafeExpression(e.msg) from e
    if sum(1 for _ in ast.walk(tree)) > 500:
        raise UnsafeExpression("expression has more than 500 syntax nodes")
    comprehensions = [n for n in ast.walk(tree)
                      if isinstance(n, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp))]
    loop_degree = sum(len(n.generators) for n in comprehensions)
    if loop_degree > 2:
        raise UnsafeExpression("comprehensions may contain at most two total generators")
    ExpressionValidator(tree).visit(tree)
    fields = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in FIELD_HELPERS and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            fields.add(node.args[0].value)
    return compile(tree, "<LintRule assert>", "eval"), fields


def compile_expression(expr: str):
    """Compile a validated expression; public helper used by the security tests."""
    return analyze_expression(expr)[0]


def make_context(obj: dict, index: Index, scope: str = ""):
    """Assert vocabulary for one object. ``scope`` limits wholesale ENUMERATION (`all_of`)
    to a namespace subtree, so an extension's rule cannot judge a sibling's objects.
    Reference traversal stays global: evidence may legitimately come from anywhere."""
    def field(name): return obj.get(name)
    def refs(name): return index.refs(obj, name)
    def count(name): return index.value_count(obj, name)
    def has(name):
        v = obj.get(name)
        return v is not None and v != "" and v != []
    def target(rf):
        r = index.refs(obj, rf)
        return (index.resolve(r[0]) or {}) if r else {}
    def targets(rf):
        return [t for t in (index.resolve(r) for r in index.refs(obj, rf)) if t]
    def kind_of(ref):
        return (index.resolve(ref) or {}).get("__kind")
    def exists(ref):
        return index.resolve(ref) is not None
    def incoming(kind=None, via=None):
        out = []
        for src, _source_field, edge_type in index.in_edges.get(index.gid(obj), []):
            if via and edge_type != via:
                continue
            other = index.by_global.get(src)
            if other is None or index.same(other, obj):
                continue
            if kind and other.get("__kind") != kind:
                continue
            if other not in out:
                out.append(other)
        return out
    def all_of(kind):
        return [o for o in index.by_kind.get(kind, []) if in_namespace(o, scope)]
    def refs_of(o, fname):
        resolved = o if isinstance(o, dict) else index.resolve(o)
        return index.refs(resolved, fname) if resolved else []
    def id_of(o):
        resolved = o if isinstance(o, dict) and o else index.resolve(o)
        identity = index.gid(resolved) if resolved else ""
        if not identity:
            raise ValueError("id_of() requires a resolved qmdc object")
        return identity
    def _members(value, helper):
        allowed = (list, tuple, set, frozenset)
        if not isinstance(value, allowed):
            raise ValueError(f"{helper} requires parsed lists/sets (use refs()/refs_of() for references)")
        try:
            return set(value)
        except TypeError as e:
            raise ValueError(f"{helper} members must be hashable scalar ids/literals; "
                             f"use refs()/refs_of() for objects") from e
    def overlaps(left, right):
        return bool(_members(left, "overlaps()") & _members(right, "overlaps()"))
    def same_members(left, right):
        return _members(left, "same_members()") == _members(right, "same_members()")
    def is_subset(left, right):
        return _members(left, "is_subset()") <= _members(right, "is_subset()")
    return {
        "__builtins__": {},
        "len": len, "all": all, "any": any, "str": str, "int": int, "bool": bool,
        "sum": sum,
        "obj": obj, "field": field, "refs": refs, "count": count, "has": has,
        "target": target, "targets": targets, "kind_of": kind_of, "exists": exists,
        "incoming": incoming, "all_of": all_of, "refs_of": refs_of, "id_of": id_of,
        "overlaps": overlaps, "same_members": same_members, "is_subset": is_subset,
        "id": index.gid(obj),
    }


# ---------------------------------------------------------------------- checks

def parent_object(index: Index, obj: dict) -> dict | None:
    parent_id = obj.get("__parent")
    if not parent_id:
        return None
    candidates = [o for o in index.objects
                  if o.get("__id") == parent_id
                  and o.get("__namespace") == obj.get("__namespace")]
    return candidates[0] if len(candidates) == 1 else None


def check_lifecycle(index: Index) -> list[Issue]:
    issues = []
    for obj in index.objects:
        if "lifecycle" not in obj:
            continue
        value = obj.get("lifecycle")
        kind = obj.get("__kind")
        if value != RETIRED:
            message = f"lifecycle is reserved for the exact value 'removed', got {value!r}"
        elif kind in {"FieldConstraints", "Cardinality", "FieldCardinality"} or kind in SYSTEM_KINDS:
            message = f"lifecycle retirement is not supported on schema helper Kind '{kind}'"
        else:
            continue
        issues.append(Issue("error", "lifecycle_bad_value", obj.get("__id", ""),
                            "lifecycle", message=message, **_at(obj)))
    return issues


def check_schema_placement(index: Index) -> list[Issue]:
    expected = {
        "FieldConstraints": "KindSchema",
        "Cardinality": "KindSchema",
        "FieldCardinality": "Cardinality",
    }
    issues = []
    for kind, parent_kind in expected.items():
        for obj in index.by_kind.get(kind, []):
            parent = parent_object(index, obj)
            if parent is None or parent.get("__kind") != parent_kind:
                issues.append(Issue("error", "schema_bad_placement", obj.get("__id", ""),
                                    detail=kind,
                                    message=f"{kind} '{obj.get('__id', '')}' must be nested "
                                            f"under {parent_kind}, got "
                                            f"{parent.get('__kind') if parent else None!r}",
                                    **_at(obj)))
    return issues


def check_schemas(index: Index) -> list[Issue]:
    issues: list[Issue] = []
    claims: dict[str, list[dict]] = {}
    for candidate in index.by_kind.get("KindSchema", []):
        claimed = candidate.get("kind")
        if isinstance(claimed, str) and claimed and not retirement(candidate):
            claims.setdefault(claimed, []).append(candidate)
    duplicate_kinds = {kind for kind, schemas in claims.items() if len(schemas) > 1}
    for kind in sorted(duplicate_kinds):
        # Every claim is equally guilty: blame each one at its own location, and name them
        # all by global identity — concise ids repeat across namespaces, so a list of those
        # can read as "schema_issue conflicts with schema_issue".
        schemas = sorted(claims[kind], key=lambda s: (index.gid(s), str(s.get("__file", ""))))
        roster = ", ".join(f"{index.gid(s)} ({_where(s)})" for s in schemas)
        for schema in schemas:
            issues.append(Issue("error", "duplicate_kind_schema", schema.get("__id", ""),
                                "kind", detail=kind,
                                message=f"Kind '{kind}' is claimed by {len(schemas)} "
                                        f"KindSchemas: {roster}",
                                **_at(schema)))

    for schema in index.by_kind.get("KindSchema", []):
        kind = schema.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            issues.append(Issue("error", "schema_bad_kind", schema.get("__id", ""), "kind",
                                message=f"KindSchema '{schema.get('__id', '')}': kind must be "
                                        f"one non-empty string, got {kind!r}", **_at(schema)))
            continue
        schema_retired = retirement(schema)
        if kind in duplicate_kinds and not schema_retired:
            continue
        sid = schema.get("__id", "")
        required, optional = [], []
        for slot, raw in (("required", schema.get("required")), ("optional", schema.get("optional"))):
            names = []
            malformed = False
            if raw is None:
                values = []
            elif index.has_refs(schema, slot):
                values = []
                malformed = True
                issues.append(Issue("error", "schema_field_list", sid, slot,
                                    message=f"KindSchema '{sid}': '{slot}' must contain field "
                                            f"name strings, not object references", **_at(schema)))
            elif isinstance(raw, str):
                values = [raw]  # one scalar field name is accepted as a convenience
            elif isinstance(raw, (list, tuple)):
                values = list(raw)
            else:
                values = [raw]
            for value in values:
                if (not isinstance(value, str) or not value.strip()
                        or "," in value or any(ch.isspace() for ch in value)):
                    malformed = True
                    issues.append(Issue("error", "schema_field_list", sid, slot,
                                        message=f"KindSchema '{sid}': '{slot}' entry {value!r} "
                                                f"is not one field-name string; write e.g. "
                                                f"{slot}: [a, b]", **_at(schema)))
                else:
                    names.append(value)
            if not malformed:
                (required if slot == "required" else optional).extend(names)
        overlap = sorted(set(required) & set(optional))
        for duplicate in overlap:
            issues.append(Issue("error", "schema_field_overlap", sid, duplicate,
                                message=f"KindSchema '{sid}': field '{duplicate}' is both "
                                        f"required and optional", **_at(schema)))
        raw_strict = schema.get("strict")
        if raw_strict is not None and not isinstance(raw_strict, bool):
            issues.append(Issue("error", "schema_bad_strict", sid, "strict",
                                message=f"KindSchema '{sid}': strict must be QMD boolean "
                                        f"true or false, got {raw_strict!r}", **_at(schema)))
        strict = raw_strict is True

        # Both schema extension points have exactly one object-valued child. qmdc may parse
        # an array here, but half-applying only its first edge would silently drop checks.
        def schema_child(slot: str, expected_kind: str) -> dict:
            refs = index.refs(schema, slot)
            direct = [o for o in index.by_kind.get(expected_kind, [])
                      if o.get("__parent") == schema.get("__id")
                      and o.get("__namespace") == schema.get("__namespace")]
            if not refs:
                if slot in schema or direct:
                    found = ", ".join(str(o.get("__local_id") or o.get("__id")) for o in direct)
                    issues.append(Issue("error", "schema_bad_child", sid, slot,
                                        message=f"KindSchema '{sid}': expected one nested "
                                                f"{expected_kind} child with id '{slot}', but qmdc "
                                                f"resolved none" +
                                                (f" (misnamed child: {found})" if found else ""),
                                        **_at(schema)))
                return {}
            if len(refs) != 1:
                issues.append(Issue("error", "schema_bad_child", sid, slot,
                                    message=f"KindSchema '{sid}': '{slot}' must reference "
                                            f"exactly one {expected_kind} child; found {len(refs)}",
                                    **_at(schema)))
                return {}
            child = index.resolve(refs[0]) or {}
            child_name = child.get("__local_id") or child.get("__id")
            if (child.get("__kind") != expected_kind or child_name != slot
                    or len(direct) != 1 or direct[0] is not child):
                names = [str(o.get("__local_id") or o.get("__id")) for o in direct]
                issues.append(Issue("error", "schema_bad_child", sid, slot,
                                    message=f"KindSchema '{sid}': '{slot}' must be its only "
                                            f"nested {expected_kind} child with id '{slot}'; "
                                            f"resolved {child_name!r}, direct children={names}",
                                    **_at(schema)))
                return {}
            return child

        # Field Constraints: a field whose value is a REFERENCE constrains the target Kind;
        # a field whose value is a literal list is an enum. qmdc's edges tell the two apart.
        cons = schema_child("constraints", "FieldConstraints")
        declared_fields = set(required) | set(optional)
        enums, target_kinds = {}, {}
        constraint_keys = [k for k in cons if not k.startswith("__") and k != "lifecycle"]
        if cons and not constraint_keys:
            issues.append(Issue("error", "schema_empty_constraint",
                                cons.get("__id", sid), "constraints",
                                message=f"KindSchema '{sid}': FieldConstraints child is empty; "
                                        f"remove it or declare at least one constraint",
                                **_at(cons)))
        for k in constraint_keys:
            v = cons[k]
            if k not in declared_fields:
                issues.append(Issue("error", "schema_unknown_field_constraint",
                                    cons.get("__id", sid), k,
                                    message=f"KindSchema '{sid}': constraint names undeclared "
                                            f"field '{k}' (add it to required or optional)",
                                    **_at(cons)))
                continue
            refs = index.refs(cons, k)
            if not refs and v in (None, "", []):
                issues.append(Issue("error", "schema_empty_constraint",
                                    cons.get("__id", sid), k,
                                    message=f"KindSchema '{sid}': constraint '{k}' is empty; "
                                            f"declare a literal enum list or KindSchema reference",
                                    **_at(cons)))
                continue
            if refs:
                allowed = []
                invalid = False
                for target_id in refs:
                    target_schema = index.resolve(target_id)
                    if (target_schema is None or target_schema.get("__kind") != "KindSchema"
                            or not isinstance(target_schema.get("kind"), str)):
                        issues.append(Issue("error", "schema_bad_target_kind",
                                            cons.get("__id", sid), k,
                                            message=f"KindSchema '{sid}': target_kind constraint "
                                                    f"'{k}' must reference a KindSchema, got "
                                                    f"'{target_id}'", **_at(cons)))
                        invalid = True
                    else:
                        allowed.append(target_schema["kind"])
                if not invalid:
                    target_kinds[k] = allowed
            else:
                enums[k] = name_list(v)

        # Cardinality: one FieldCardinality child per constrained field, nested under the
        # schema's `cardinality` child. The child's id IS the field name.
        card = schema_child("cardinality", "Cardinality")
        cardinality = {}
        cardinality_keys = [k for k in card if not k.startswith("__") and k != "lifecycle"]
        if card and not cardinality_keys:
            issues.append(Issue("error", "cardinality_bad_shape",
                                card.get("__id", sid), "cardinality",
                                message=f"KindSchema '{sid}': Cardinality child is empty; "
                                        f"remove it or declare at least one field bound",
                                **_at(card)))
        for fname in cardinality_keys:
            if fname not in declared_fields:
                issues.append(Issue("error", "schema_unknown_field_constraint",
                                    card.get("__id", sid), fname,
                                    message=f"KindSchema '{sid}': cardinality names undeclared "
                                            f"field '{fname}' (add it to required or optional)",
                                    **_at(card)))
                continue
            refs = index.refs(card, fname)
            if len(refs) != 1:
                issues.append(Issue("error", "cardinality_bad_shape",
                                    card.get("__id", sid), fname,
                                    message=f"Cardinality field '{fname}' must reference exactly "
                                            f"one nested FieldCardinality child with the same id; "
                                            f"found {len(refs)}", **_at(card)))
                continue
            spec = index.resolve(refs[0]) or {}
            spec_name = spec.get("__local_id") or spec.get("__id")
            if spec.get("__kind") != "FieldCardinality" or spec_name != fname:
                issues.append(Issue("error", "cardinality_bad_shape",
                                    card.get("__id", sid), fname,
                                    message=f"Cardinality field '{fname}' must point at a nested "
                                            f"FieldCardinality whose id is exactly '{fname}', got "
                                            f"{spec_name!r}", **_at(card)))
                continue
            at_spec = _at(spec)
            parsed = {}
            invalid = False
            extra_bounds = sorted(k for k in spec
                                  if not k.startswith("__") and
                                  k not in {"min_count", "max_count", "lifecycle"})
            for extra in extra_bounds:
                issues.append(Issue("error", "cardinality_bad_shape",
                                    spec.get("__id", fname), extra,
                                    message=f"FieldCardinality '{fname}' has unknown field "
                                            f"'{extra}'; use only min_count/max_count",
                                    **at_spec))
                invalid = True
            if spec.get("min_count") is None and spec.get("max_count") is None:
                issues.append(Issue("error", "cardinality_bad_shape",
                                    spec.get("__id", fname), fname,
                                    message=f"FieldCardinality '{fname}' must declare "
                                            f"min_count, max_count, or both", **at_spec))
                invalid = True
            for bound in ("min_count", "max_count"):
                raw = spec.get(bound)
                if raw is None:
                    parsed[bound] = None
                    continue
                value = as_int(raw)
                if value is None or value < 0:
                    issues.append(Issue("error", "cardinality_bad_bound",
                                        spec.get("__id", fname), bound,
                                        message=f"FieldCardinality '{fname}': {bound} must be "
                                                f"a non-negative integer, got {raw!r}",
                                        **at_spec))
                    invalid = True
                parsed[bound] = value
            lo, hi = parsed.get("min_count"), parsed.get("max_count")
            if not invalid and lo is not None and hi is not None and lo > hi:
                issues.append(Issue("error", "cardinality_bad_range",
                                    spec.get("__id", fname), fname,
                                    message=f"FieldCardinality '{fname}': min_count {lo} is "
                                            f"greater than max_count {hi}", **at_spec))
                invalid = True
            if not invalid and (lo is not None or hi is not None):
                cardinality[fname] = (lo, hi)

        if schema_retired:
            issues.append(Issue("info", "retired_schema", sid, "lifecycle", detail=kind,
                                message=f"KindSchema '{sid}' for Kind '{kind}' is retired and "
                                        f"does not enforce domain objects", **_at(schema)))
            continue

        for obj in index.by_kind.get(kind, []):
            oid = obj.get("__id", "")
            at = _at(obj)
            marker = retirement(obj)
            if marker:
                if kind not in CONFIG_KINDS:
                    issues.append(Issue("info", "retired_object", oid, "lifecycle",
                                        message=f"[{kind}] '{oid}' is retired and skipped by schema "
                                                f"checks and LintRules", **at))
                continue
            fields = {k for k in obj if not k.startswith("__")}

            for req in required:
                if kind == "KindSchema" and req == "kind":
                    continue
                if kind == "LintRule" and req in {"severity", "assert", "message"}:
                    continue
                if req not in fields:
                    issues.append(Issue("error", "missing_required", oid, req,
                                        message=f"[{kind}] '{oid}': missing required field '{req}'",
                                        **at))
            if strict:
                for extra in sorted(fields - set(required) - set(optional) - {"lifecycle"}):
                    issues.append(Issue("error", "unexpected_field", oid, extra,
                                        message=f"[{kind}] '{oid}': unexpected field '{extra}' "
                                                f"(Kind is strict: required+optional only)",
                                        **at))
            for fname, allowed in enums.items():
                if (kind == "KindSchema" and fname == "strict") or (
                        kind == "LintRule" and fname == "severity"):
                    continue
                val = obj.get(fname)
                if val in (None, ""):
                    continue
                if index.has_refs(obj, fname):
                    issues.append(Issue("error", "constraint_value_shape", oid, fname,
                                        message=f"[{kind}] '{oid}': enum-constrained field "
                                                f"'{fname}' must hold literals, not references",
                                        **at))
                    continue
                for one in (val if isinstance(val, (list, tuple)) else [val]):
                    if str(one) not in allowed:
                        issues.append(Issue("error", "enum_violation", oid, fname,
                                            message=f"[{kind}] '{oid}': '{fname}'='{one}' not in {allowed}",
                                            **at))
            for fname, allowed_kinds in target_kinds.items():
                value = obj.get(fname)
                target_refs = index.refs(obj, fname)
                if value not in (None, "", []) and not target_refs:
                    issues.append(Issue("error", "constraint_value_shape", oid, fname,
                                        message=f"[{kind}] '{oid}': target_kind-constrained field "
                                                f"'{fname}' must hold resolved references, not a literal",
                                        **at))
                    continue
                for tref in target_refs:
                    tk = (index.resolve(tref) or {}).get("__kind")
                    if tk and allowed_kinds and tk not in allowed_kinds:
                        issues.append(Issue("error", "target_kind_violation", oid, fname,
                                            message=f"[{kind}] '{oid}': '{fname}' -> '{tref}' is "
                                                    f"{tk}, expected {allowed_kinds}",
                                            **at))
            for fname, (lo, hi) in cardinality.items():
                if fname not in fields:
                    continue  # an absent field is missing_required's business
                n = index.value_count(obj, fname)
                if lo is not None and n < lo:
                    issues.append(Issue("error", "min_count_violation", oid, fname,
                                        message=f"[{kind}] '{oid}': '{fname}' holds {n} value(s), "
                                                f"minimum is {lo}", **at))
                if hi is not None and n > hi:
                    issues.append(Issue("error", "max_count_violation", oid, fname,
                                        message=f"[{kind}] '{oid}': '{fname}' holds {n} value(s), "
                                                f"maximum is {hi}", **at))
    return issues


SELECTORS = ("for_each", "for_each_with", "global")
SEVERITIES = ("error", "warning", "info")
CONFIG_KINDS = {"KindSchema", "FieldConstraints", "Cardinality", "FieldCardinality", "LintRule"}
SYSTEM_KINDS = {"__Workspace", "__Namespace", "__Document", "__TextBlock", "__Object"}


def is_domain_object(obj: dict) -> bool:
    kind = str(obj.get("__kind", ""))
    return bool(kind) and kind not in SYSTEM_KINDS and kind not in CONFIG_KINDS


def namespace_of(obj: dict) -> str:
    """The namespace qmdc placed an object in; the workspace root is the empty string."""
    return str(obj.get("__namespace") or "")


METAMODEL_NS = "_metamodel"


def is_metamodel_namespace(ns: str) -> bool:
    """A namespace that carries the schema layer OF the namespace enclosing it.

    Named by the convention `qmdc-model init` writes and the SOP mandates: `_metamodel` at
    the workspace root, `<ns>._metamodel` beneath a namespace. The name is a REQUIREMENT
    here, not an assumption: a rule declared anywhere else is `rule_bad_placement` and does
    not run, so renaming a metamodel namespace fails loudly instead of widening a rule's
    scope to the whole workspace.
    """
    return ns == METAMODEL_NS or ns.endswith("." + METAMODEL_NS)


def enclosing_namespace(ns: str) -> str:
    """The namespace one level out. The workspace root encloses itself."""
    return ns.rsplit(".", 1)[0] if "." in ns else ""


def in_namespace(obj: dict, scope: str) -> bool:
    """Whether an object lies in a namespace subtree. Root scope contains everything."""
    if not scope:
        return True
    ns = namespace_of(obj)
    return ns == scope or ns.startswith(scope + ".")


def rule_scope(rule: dict) -> str:
    """The namespace subtree a LintRule governs: the one ENCLOSING where it is declared.

    With placement enforced (see `is_metamodel_namespace`) exactly two shapes are reachable:
    a metamodel nested under namespace `a` (`a._metamodel`) governs `a` and its descendants,
    and the workspace root governs the whole workspace. Derived from qmdc's namespace tree.
    """
    return enclosing_namespace(namespace_of(rule))


def check_rules(index: Index) -> list[Issue]:
    issues: list[Issue] = []
    # Kind DECLARATIONS stay workspace-global (one KindSchema per Kind, from anywhere);
    # only the objects a rule judges and the field names it may reference are scoped.
    known_kinds = set(index.by_kind)
    known_kinds.update(s.get("kind") for s in index.by_kind.get("KindSchema", [])
                       if isinstance(s.get("kind"), str) and not retirement(s))
    schemas = index.by_kind.get("KindSchema", [])

    def fields_for(kinds, objects) -> set[str]:
        known = {"lifecycle"}
        for schema in schemas:
            claimed_kind = schema.get("kind")
            if (not retirement(schema) and isinstance(claimed_kind, str)
                    and claimed_kind in kinds):
                known.update(name_list(schema.get("required")))
                known.update(name_list(schema.get("optional")))
        for item in objects:
            if item.get("__kind") in kinds:
                known.update(k for k in item if not k.startswith("__"))
        return known

    scoped_objects: dict[str, list[dict]] = {}

    def objects_in(scope: str) -> list[dict]:
        """Every object inside a namespace subtree, memoized per scope."""
        if scope not in scoped_objects:
            scoped_objects[scope] = [o for o in index.objects if in_namespace(o, scope)]
        return scoped_objects[scope]

    for rule in index.by_kind.get("LintRule", []):
        marker = retirement(rule)
        rid = rule.get("__id", "")
        at = _at(rule)
        scope = rule_scope(rule)
        scope_objects = objects_in(scope)
        scope_domain_kinds = {o.get("__kind") for o in scope_objects if is_domain_object(o)}
        scope_domain_fields = fields_for(scope_domain_kinds, scope_objects)
        if marker:
            issues.append(Issue("info", "retired_rule", rid, "lifecycle", detail=rid,
                                message=f"LintRule '{rid}' is retired and will not execute",
                                **at))
        sev, msg, expr = rule.get("severity"), rule.get("message"), rule.get("assert")

        # Validate configuration FIRST. A rule we cannot run is never allowed to disappear
        # into an empty pool or masquerade as a domain violation.
        bad_config = False
        declared_ns = namespace_of(rule)
        if declared_ns and not is_metamodel_namespace(declared_ns):
            # Placement IS the scope, so an unrecognized home would silently hand this rule
            # the enclosing namespace — usually the whole workspace, judging other people's
            # objects. Refuse to run it instead.
            issues.append(Issue("error", "rule_bad_placement", rid, detail=rid,
                                message=f"LintRule '{rid}' is declared in namespace "
                                        f"'{declared_ns}', which is not a metamodel namespace "
                                        f"(named '{METAMODEL_NS}' at the workspace root, or "
                                        f"'<owner>.{METAMODEL_NS}' under the namespace it "
                                        f"describes): placement is what bounds a rule's scope, "
                                        f"so declare it in '{declared_ns}.{METAMODEL_NS}' to "
                                        f"govern '{declared_ns}' and its descendants, or in the "
                                        f"root '{METAMODEL_NS}' to govern the whole workspace",
                                **at))
            bad_config = True
        if sev not in SEVERITIES:
            issues.append(Issue("error", "rule_bad_severity", rid, "severity", detail=rid,
                                message=f"LintRule '{rid}': severity must be one of "
                                        f"{', '.join(SEVERITIES)}, got {sev!r}", **at))
            bad_config = True
        if not isinstance(msg, str) or not msg:
            issues.append(Issue("error", "rule_bad_message", rid, "message", detail=rid,
                                message=f"LintRule '{rid}': message must be a non-empty string, "
                                        f"got {msg!r}", **at))
            bad_config = True

        unsupported = []
        for key in rule:
            if key.startswith("__") or key in SELECTORS:
                continue
            lower = key.lower()
            if lower.startswith("for_") or "selector" in lower:
                unsupported.append(key)
        for bad in sorted(unsupported):
            issues.append(Issue("error", "rule_bad_selector", rid, bad, detail=rid,
                                message=f"LintRule '{rid}': selector '{bad}' is not supported "
                                        f"(use one of {', '.join(SELECTORS)})", **at))
            bad_config = True

        declared = []
        for selector in SELECTORS:
            if selector not in rule:
                continue
            value = rule[selector]
            declared.append(selector)
            valid = (value is True) if selector == "global" else (
                isinstance(value, str) and bool(value.strip()))
            if not valid:
                issues.append(Issue("error", "rule_bad_selector", rid, selector, detail=rid,
                                    message=f"LintRule '{rid}': selector '{selector}' has invalid "
                                            f"value {value!r}", **at))
                bad_config = True

        if not declared:
            if not unsupported:
                issues.append(Issue("error", "rule_no_selector", rid, detail=rid,
                                    message=f"LintRule '{rid}' has no scope selector "
                                            f"(one of {', '.join(SELECTORS)})", **at))
            continue
        if len(declared) > 1:
            issues.append(Issue("error", "rule_selector_conflict", rid, detail=rid,
                                message=f"LintRule '{rid}' has multiple scope selectors: "
                                        f"{', '.join(declared)} — declare exactly one", **at))
            bad_config = True

        if declared == ["for_each"] and isinstance(rule.get("for_each"), str):
            selected_kind = rule["for_each"]
            if selected_kind not in known_kinds:
                issues.append(Issue("error", "rule_unknown_kind", rid, "for_each", detail=rid,
                                    message=f"LintRule '{rid}': for_each names unknown Kind "
                                            f"'{selected_kind}' (declare its KindSchema first)", **at))
                bad_config = True

        if not isinstance(expr, str) or not expr.strip():
            issues.append(Issue("error", "rule_eval_failed", rid, "assert", detail=rid,
                                message=f"LintRule '{rid}': 'assert' must be a string EXPRESSION, "
                                        f"got {expr!r} — write e.g. has('field') or "
                                        f"count('field') >= 1", **at))
            bad_config = True
            code, referenced_fields = None, set()
        else:
            try:
                code, referenced_fields = analyze_expression(expr)
            except (UnsafeExpression, ValueError) as e:
                issues.append(Issue("error", "rule_eval_failed", rid, "assert", detail=rid,
                                    message=f"LintRule '{rid}': unsafe or invalid assert: {e}", **at))
                bad_config = True
                code, referenced_fields = None, set()

        if bad_config:
            continue

        pool = []
        if declared == ["for_each"] and isinstance(rule.get("for_each"), str):
            pool = [o for o in index.by_kind.get(rule["for_each"], []) if in_namespace(o, scope)]
            allowed_fields = (fields_for({rule["for_each"]}, scope_objects)
                              if rule["for_each"] in known_kinds else referenced_fields)
        elif declared == ["for_each_with"] and isinstance(rule.get("for_each_with"), str):
            selected_field = rule["for_each_with"]
            pool = [o for o in scope_objects
                    if is_domain_object(o) and o.get(selected_field) is not None]
            pool_kinds = {o.get("__kind") for o in pool}
            allowed_fields = (fields_for(pool_kinds, scope_objects) if pool
                              else scope_domain_fields)
            if selected_field not in scope_domain_fields:
                issues.append(Issue("error", "rule_unknown_field", rid, selected_field, detail=rid,
                                    message=f"LintRule '{rid}': for_each_with names unknown domain "
                                            f"field '{selected_field}'"
                                            f"{_scope_note(scope)}", **at))
                bad_config = True
        else:
            allowed_fields = set()  # global has no current object; use all_of()/refs_of()

        if not bad_config:
            for unknown in sorted(referenced_fields - allowed_fields):
                selector_scope = rule.get("for_each") or rule.get("for_each_with") or "global"
                issues.append(Issue("error", "rule_unknown_field", rid, unknown, detail=rid,
                                    message=f"LintRule '{rid}': assert references field '{unknown}' "
                                            f"outside selector scope '{selector_scope}'"
                                            f"{_scope_note(scope)}", **at))
                bad_config = True
        if bad_config:
            continue
        if marker:
            continue
        if declared == ["global"]:
            pool = [{}]
        elif not pool:
            selector = declared[0]
            issues.append(Issue("info", "rule_empty_scope", rid, selector, detail=rid,
                                message=f"LintRule '{rid}' is valid but selector '{selector}' "
                                        f"currently matches no domain objects"
                                        f"{_scope_note(scope)}", **at))
            continue

        for obj in pool:
            if retirement(obj):
                continue
            oid = obj.get("__id", "")
            loc = _at(obj) if obj else at
            try:
                verdict = eval(code, make_context(obj, index, scope))  # validated side-effect-free AST
            except Exception as e:
                issues.append(Issue("error", "rule_eval_failed", oid, detail=rid,
                                    message=f"[{rid}] assert could not be evaluated on "
                                            f"'{oid}': {type(e).__name__}: {e} — rule says: "
                                            f"{msg.replace('{id}', oid)}", **loc))
                continue
            if not verdict:
                issues.append(Issue(sev, "rule_failed", oid, detail=rid,
                                    message=f"[{rid}] " + msg.replace("{id}", oid), **loc))
    return issues


# --------------------------------------------------------- workspace contract

BASE_META_KINDS = {"KindSchema", "FieldConstraints", "Cardinality", "FieldCardinality", "LintRule"}


def is_managed_workspace(index: Index, ws: Path) -> bool:
    """Evidence that qmdc-model owns the workspace, independent of namespace object ids."""
    if (ws / "_metamodel").is_dir():
        return True
    if index.by_kind.get("KindSchema") or index.by_kind.get("LintRule"):
        return True
    return any(str(o.get("__file", "")).endswith(".vendor.qmd.md")
               for o in index.objects)


def check_workspace_contract(index: Index, ws: Path) -> list[Issue]:
    """Coverage never switches off; managed workspaces additionally require base kinds."""
    issues = []
    schemas = index.by_kind.get("KindSchema", [])
    declared = {s.get("kind") for s in schemas
                if isinstance(s.get("kind"), str) and not retirement(s)}

    if is_managed_workspace(index, ws):
        missing_base = sorted(BASE_META_KINDS - declared)
        if missing_base:
            metamodel = next((o for o in index.objects
                              if str(o.get("__file", "")).startswith("_metamodel/")),
                             index.objects[0])
            issues.append(Issue("error", "missing_metaschema",
                                metamodel.get("__id", "_metamodel"),
                                message="workspace is missing vendored base meta-kinds: " +
                                        ", ".join(missing_base) +
                                        " — run 'qmdc-model upgrade <workspace>'",
                                **_at(metamodel)))

    observed = {o.get("__kind") for o in index.objects if is_domain_object(o)}
    for kind in sorted(observed - declared):
        first = next(o for o in index.objects if o.get("__kind") == kind)
        retired = [s for s in schemas if s.get("kind") == kind and retirement(s)]
        if retired:
            reason = ("only retired KindSchema(s) exist: " +
                      ", ".join(str(s.get("__id")) for s in retired) +
                      "; add/activate one schema before keeping live objects")
        else:
            reason = "no KindSchema exists; check for a Kind-name typo or declare its schema"
        issues.append(Issue("error", "missing_kind_schema", first.get("__id", ""), "",
                            detail=str(kind),
                            message=f"Kind '{kind}' has objects but {reason}",
                            **_at(first)))
    return issues


# ------------------------------------------------------------------- top level

def source_symlinks(ws: Path) -> list[Path]:
    """Source/file-tree redirects that could move qmdc reads outside the workspace."""
    return sorted(path for path in ws.rglob("*")
                  if path.is_symlink() and
                  (path.is_dir() or path.name.casefold().endswith(".qmd.md")))


def bad_source_extensions(ws: Path) -> list[Path]:
    return sorted(path for path in ws.rglob("*")
                  if path.is_file() and not path.is_symlink()
                  and path.name.casefold().endswith(".qmd.md")
                  and not path.name.endswith(".qmd.md"))


def lint_workspace(ws: Path, *, enforce_workspace_contract: bool = True) -> list[Issue]:
    ws = Path(ws)
    if not ws.is_dir():
        return [Issue("error", "workspace_not_found", message=f"workspace is not a directory: {ws}")]
    redirected = source_symlinks(ws)
    if redirected:
        return [Issue("error", "source_symlink", file=str(path.relative_to(ws)),
                      message=f"refusing symlinked source path: {path} -> "
                              f"{path.resolve(strict=False)}")
                for path in redirected]
    bad_extensions = bad_source_extensions(ws)
    prefix = [Issue("error", "source_bad_extension", file=str(path.relative_to(ws)),
                    message=f"QMD source extension is case-sensitive; rename '{path.name}' "
                            f"to end with lowercase '.qmd.md'")
              for path in bad_extensions]
    try:
        issues = prefix + validate_structural(ws)
    except RuntimeError as e:
        return prefix + [Issue("error", "qmdc_failed", message=str(e))]
    if any(i.code == "qmdc_failed" for i in issues):
        return issues
    try:
        files = load_files(ws)
        index = Index.build(load_objects(ws), load_edges(ws))
    except (RuntimeError, json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
        issues.append(Issue("error", "qmdc_failed",
                            message=f"could not load qmdc workspace index: {type(e).__name__}: {e}"))
        return issues
    indexed_files = {str(o.get("__file", "")) for o in index.objects if o.get("__file")}
    for path in sorted(set(files) - indexed_files):
        issues.append(Issue("error", "source_unparsed", file=path,
                            message=f"qmdc discovered '{path}' but produced no object from it; "
                                    f"the file may be empty, unreadable, or invalid UTF-8"))
    if not index.objects:
        issues.append(Issue("error", "workspace_empty",
                            message=f"qmdc parsed no objects from workspace: {ws}"))
        return issues
    if enforce_workspace_contract:
        issues += check_workspace_contract(index, ws)
    issues += check_lifecycle(index)
    issues += check_schema_placement(index)
    issues += check_schemas(index)
    issues += check_rules(index)
    return issues


def issues_to_json(issues: list[Issue]) -> str:
    payload = sorted(({k: v for k, v in asdict(i).items() if v} for i in issues),
                     key=lambda d: (d.get("code", ""), d.get("object", ""), d.get("field", "")))
    return json.dumps({"issues": payload}, indent=2, ensure_ascii=False)
