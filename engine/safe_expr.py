"""Avaliador seguro de expressões das regras YAML (apenas comparações e aritmética)."""
from __future__ import annotations

import ast
import operator as op
from typing import Any

_BIN = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv}
_CMP = {ast.Gt: op.gt, ast.GtE: op.ge, ast.Lt: op.lt, ast.LtE: op.le, ast.Eq: op.eq,
        ast.NotEq: op.ne}


def evaluate(expr: str, env: dict[str, Any]) -> Any:
    return _eval(ast.parse(expr, mode="eval").body, env)


def _eval(n: ast.AST, env: dict[str, Any]) -> Any:
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        if n.id not in env:
            raise KeyError(f"variável desconhecida na regra: {n.id}")
        return env[n.id]
    if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
        return _BIN[type(n.op)](_eval(n.left, env), _eval(n.right, env))
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        return -_eval(n.operand, env)
    if isinstance(n, ast.BoolOp):
        vals = [_eval(v, env) for v in n.values]
        return all(vals) if isinstance(n.op, ast.And) else any(vals)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
        return not _eval(n.operand, env)
    if isinstance(n, ast.Compare):
        left = _eval(n.left, env)
        for o, c in zip(n.ops, n.comparators):
            right = _eval(c, env)
            if type(o) not in _CMP or not _CMP[type(o)](left, right):
                return False
            left = right
        return True
    raise ValueError(f"expressão não permitida: {ast.dump(n)}")
