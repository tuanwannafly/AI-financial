"""Best-effort sandbox for internal pandas_query execution.

Not a security boundary for untrusted external code. Timeout still applies on Windows
where resource.setrlimit is unavailable.
"""
from __future__ import annotations

import multiprocessing as mp
from typing import Any, Tuple

SAFE_BUILTINS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "float": float,
    "int": int,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "sorted": sorted,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
}


def _worker(query: str, csv_path: str, q: mp.Queue) -> None:
    try:
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (1_000_000_000, 1_000_000_000))
        except Exception:
            pass
        import numpy as np
        import pandas as pd

        df = pd.read_csv(csv_path)
        safe_globals = {"__builtins__": SAFE_BUILTINS, "df": df, "df1": df, "pd": pd, "np": np}
        result = eval(query, safe_globals)
        q.put(("ok", result))
    except Exception as e:
        q.put(("error", str(e)))


def safe_execute(query: str, csv_path: str, timeout: float = 5.0) -> Tuple[str, Any]:
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(query, csv_path, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return ("timeout", None)
    return q.get() if not q.empty() else ("error", "no result")


def execute_inline(query: str, csv_path: str):
    """Faster in-process exec for trusted template queries (same builtins)."""
    import numpy as np
    import pandas as pd

    df = pd.read_csv(csv_path)
    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "df": df,
        "df1": df,
        "pd": pd,
        "np": np,
    }
    return eval(query, safe_globals)


def execute_inline_code(code: str, csv_path: str):
    """exec() variant: read local_vars['answer'] (or last expr via eval fallback)."""
    import numpy as np
    import pandas as pd

    df = pd.read_csv(csv_path)
    # ``df1`` lives in BOTH globals and locals so that lambdas / closures
    # defined inside ``exec`` can still resolve it without relying on the
    # merged-namespace eval fallback (which silently lost ``df1`` for some
    # argmax/argmin queries with the lambda form, see #lambda-NameError).
    local_vars: dict = {"df": df, "df1": df, "pd": pd, "np": np}
    g = {"__builtins__": SAFE_BUILTINS, "df": df, "df1": df, "pd": pd, "np": np}
    try:
        exec(code, g, local_vars)
        if "answer" in local_vars:
            return local_vars["answer"]
    except SyntaxError:
        return eval(code, {**g, **local_vars})
    except Exception as exec_error:
        if "answer" not in local_vars:
            try:
                return eval(code, {**g, **local_vars})
            except Exception:
                raise exec_error
        raise
    if "answer" not in local_vars:
        return eval(code, {**g, **local_vars})
    return local_vars.get("answer")


def _worker_exec(code: str, csv_path: str, q: mp.Queue) -> None:
    try:
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (1_000_000_000, 1_000_000_000))
        except Exception:
            pass
        val = execute_inline_code(code, csv_path)
        q.put(("ok", val))
    except Exception as e:
        q.put(("error", str(e)))


def safe_execute_code(code: str, csv_path: str, timeout: float = 5.0) -> Tuple[str, Any]:
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker_exec, args=(code, csv_path, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return ("timeout", None)
    return q.get() if not q.empty() else ("error", "no result")
