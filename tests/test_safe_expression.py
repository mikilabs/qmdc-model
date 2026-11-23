"""The LintRule expression language is deliberately smaller than Python."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from qmdc_model.linter import UnsafeExpression, compile_expression  # noqa: E402


@pytest.mark.parametrize(
    "expr",
    [
        "().__class__.__mro__[1].__subclasses__()",
        "open('/etc/hostname').read()",
        "__import__('os').system('id')",
        "(lambda: 1)()",
        "[x for x in [] if (yield x)]",
        "[x for x in all_of('Thing')]",
        "set(x for x in all_of('Thing'))",
        "overlaps(set(field('a')), set(field('b')))",
        "overlaps(list(field('a')), list(field('b')))",
        "overlaps(sorted(field('a')), ['b'])",
        "sum([1 if has('a') else 0, 1 if field('global') else 0]) * 2",
        "'x' * 10000 * 10000",
        "[0] * (1000000 - 1)",
        "all(x for x in all_of('A') for y in all_of('B') for z in all_of('C'))",
        "any(any(any(z for z in all_of('C')) for y in all_of('B')) for x in all_of('A'))",
        "x if [0 for x in []] else 1",
        "sum((all_of('K') for a in all_of('K')), [])",
        "sum((list(a) for a in all_of('K')), ())",
        "has(str('typo'))",
        "has('typo'[0:99])",
        "has(['typo'][0])",
        "refs_of(obj, str('field'))",
        "all(len(str(all_of('Book'))) > 0 for a in all_of('Book') for b in all_of('Book'))",
        "all(len(list(all_of('Book'))) > 0 for a in all_of('Book') for b in all_of('Book'))",
        "any(a in all_of('Book') for a in all_of('Book'))",
        "obj['__class__']",
        "obj.get('__kind')",
        "obj.get('__file')",
        "all(y for y in (len(all_of('Thing')) for z in refs('tags')))",
        "all(w for w in (len(all_of('KindSchema')) for z in all_of('LintRule')))",
        "all(a for a in all_of('K') for a in all_of('K'))",
        "[0 for __builtins__ in []] and __builtins__.get('eval')",
    ],
)
def test_python_escape_hatches_are_rejected_before_eval(expr: str):
    with pytest.raises(UnsafeExpression):
        compile_expression(expr)


@pytest.mark.parametrize(
    "expr",
    [
        "has('name') and count('members') >= 2",
        "len(incoming(kind='Version', via='parent')) > 0",
        "all(exists(r) and kind_of(r) == 'Module' for r in refs('modules'))",
        "refs_of(target('task'), 'target') == refs('target')",
        "same_members(refs('left'), refs('right')) or is_subset(refs('left'), refs('right'))",
        "target('owner').get('status') in ('active', 'planned')",
        "sum([1 if has('a') else 0, 1 if field('global') else 0]) == 1",
        "all(id_of(a) == id_of(b) or not overlaps(refs_of(a, 'tables'), refs_of(b, 'tables')) for a in all_of('Booking') for b in all_of('Booking'))",
        "all(id_of(a) != id_of(b) or kind_of(id_of(a)) == kind_of(id_of(b)) for a in all_of('Module') for b in all_of('Module'))",
        "all(is_subset(refs_of(mv, 'module'), refs_of(sv, 'modules')) for sv in all_of('SystemVision') for mv in all_of('ModuleVersion'))",
    ],
)
def test_documented_expression_forms_compile(expr: str):
    assert compile_expression(expr) is not None
