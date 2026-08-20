import math
import re
from typing import Any

from app.services.schema_tools import get_path


def evaluate(expr: Any, data: dict[str, Any]) -> Any:
    if not isinstance(expr, dict) or "op" not in expr:
        return expr
    op = expr["op"]
    if op == "path":
        try:
            return get_path(data, expr["path"])
        except (KeyError, IndexError, TypeError, ValueError):
            return None
    args = [evaluate(arg, data) for arg in expr.get("args", [])]
    left = evaluate(expr.get("left"), data)
    right = evaluate(expr.get("right"), data)
    if op == "exists": return left is not None
    if op == "eq": return left == right
    if op == "neq": return left != right
    if op == "gt": return left > right
    if op == "gte": return left >= right
    if op == "lt": return left < right
    if op == "lte": return left <= right
    if op == "and": return all(args)
    if op == "or": return any(args)
    if op == "not": return not evaluate(expr.get("arg"), data)
    if op == "add": return sum(args)
    if op == "subtract": return left - right
    if op == "multiply": return math.prod(args)
    if op == "divide": return left / right
    if op == "in": return left in right
    if op == "regex": return bool(re.search(str(expr.get("pattern", "")), str(left or "")))
    if op == "approx_equal":
        tolerance = float(expr.get("tolerance", 0.02))
        return abs(float(left) - float(right)) <= max(abs(float(right)) * tolerance, tolerance)
    raise ValueError(f"Unsupported rule operator: {op}")

