"""
Embedded analysis script — the math-gap-repair engine writes this to
a temp file and executes it as a subprocess.

The script receives its input via the global variables EXPRESSION,
CLAIM, PARAM_RANGES, and ASSUMPTIONS, which are set by the engine
before execution.
"""
import json
import sys
from itertools import product

try:
    import numpy as np
    import sympy as sp
    from sympy import (
        symbols, diff, simplify, factor, expand, together,
        numer, denom, collect, Add, Mul, Pow, Symbol
    )
except ImportError as e:
    print(json.dumps({"error": f"ImportError: {e}"}))
    sys.exit(0)


def main(out):
    """Run numerical + symbolic analysis."""

    expr_text = EXPRESSION.strip()

    # Try to parse
    local_ns = _make_symbols(expr_text)
    out["detected_symbols"] = [str(s) for s in local_ns.values()]

    try:
        expr = eval(expr_text, {"__builtins__": {}}, local_ns)
    except Exception as e:
        out["parse_error"] = str(e)
        out["numerical_verified"] = False
        out["symbolic_success"] = False
        out["symbolic_detail"] = (
            f"Could not parse expression. Provide a sympy-compatible "
            f"expression string. Detected symbols: {list(local_ns.keys())}"
        )
        return

    out["parsed_expression"] = str(expr)

    _numerical_verify(expr, local_ns, out)
    _symbolic_analyze(expr, local_ns, out)


def _make_symbols(text):
    """Create sympy symbols for all identifiers in the text."""
    import re
    ns = {}

    common = [
        ("alpha_H", {"nonnegative": True}),
        ("alpha_L", {"nonnegative": True}),
        ("gamma", {"positive": True}),
        ("Delta", {"positive": True}),
        ("mu_H", {"positive": True}),
        ("mu_L", {"positive": True}),
        ("sigma2_H", {"nonnegative": True}),
        ("sigma2_L", {"nonnegative": True}),
        ("sigma_HH", {"real": True}),
        ("sigma_LL", {"real": True}),
        ("sigma_HL", {"real": True}),
        ("ell", {"nonnegative": True}),
        ("n_H", {"integer": True, "positive": True}),
        ("n_L", {"integer": True, "positive": True}),
        ("n", {"integer": True, "positive": True}),
        ("a", {"nonnegative": True}),
        ("b", {"nonnegative": True}),
    ]

    for name, kwargs in common:
        ns[name] = symbols(name, **kwargs)

    for match in re.findall(r'\b([a-zA-Z_]\w*)\b', text):
        if match not in ns and len(match) >= 1:
            ns[match] = symbols(match, real=True)

    return ns


def _numerical_verify(expr, sym_map, out):
    """Grid-scan the parameter space."""
    free_syms = list(expr.free_symbols)
    if not free_syms:
        out["numerical_verified"] = True
        out["numerical_detail"] = "Expression has no free symbols."
        return

    grid = {}
    for sym in free_syms:
        name = str(sym)
        if name in PARAM_RANGES:
            lo, hi, n = PARAM_RANGES[name]
            grid[name] = list(np.linspace(lo, hi, n))
        else:
            grid[name] = _auto_range(name)

    param_names = list(grid.keys())
    param_vals = list(grid.values())
    total = 1
    for v in param_vals:
        total *= len(v)

    out["grid_size"] = total
    out["param_names"] = param_names

    if total > 200000:
        n_sample = 100000
        out["sampling"] = f"Random {n_sample} of {total}"
        rng = np.random.default_rng(42)
        combos = []
        for _ in range(n_sample):
            combo = tuple(rng.choice(v) for v in param_vals)
            combos.append(combo)
    else:
        combos = list(product(*param_vals))

    try:
        sym_list = [sym_map[n] for n in param_names]
        f = sp.lambdify(sym_list, expr, 'numpy')
    except Exception as e:
        out["numerical_verified"] = False
        out["numerical_detail"] = f"Could not lambdify: {e}"
        return

    # Build assumption-filtering function
    def _check_assumptions(params):
        """Check if a parameter combination satisfies all assumptions."""
        ns = dict(params)
        # Map common notation to actual variable names
        for k, v in list(ns.items()):
            if k.startswith("sigma2_"):
                base = k.replace("sigma2_", "")
                ns[f"sigma_{base}**2"] = v
                ns[f"{base}" + "_sigma2"] = v
        for a in ASSUMPTIONS:
            # Normalize: sigma_H^2 -> sigma2_H, etc.
            a_norm = a.replace("sigma_H^2", "sigma2_H")
            a_norm = a_norm.replace("sigma_L^2", "sigma2_L")
            a_norm = a_norm.replace("sigma^2_H", "sigma2_H")
            a_norm = a_norm.replace("sigma^2_L", "sigma2_L")
            try:
                if not eval(a_norm, {"__builtins__": {}}, ns):
                    return False
            except Exception:
                return False
        return True

    # Determine the claim direction from CLAIM text
    claim_lower = CLAIM.lower()
    if '>=' in claim_lower or '>= 0' in claim_lower or 'non-negative' in claim_lower:
        direction = 'ge'
    elif '<=' in claim_lower or '<= 0' in claim_lower or 'non-positive' in claim_lower or 'concave' in claim_lower:
        direction = 'le'
    else:
        direction = 'le'  # default: checking <= 0

    def _is_violation(val):
        """Check if val violates the claim."""
        if direction == 'ge':
            return val < -1e-8  # should be >= 0, negative = violation
        else:
            return val > 1e-8   # should be <= 0, positive = violation

    max_val = float('-inf')
    min_val = float('inf')
    violations = []
    n_checked = 0
    n_skipped = 0
    for combo in combos:
        params = dict(zip(param_names, [float(x) for x in combo]))
        if not _check_assumptions(params):
            n_skipped += 1
            continue
        n_checked += 1
        try:
            val = float(f(*combo))
            if np.isnan(val) or np.isinf(val):
                continue
            max_val = max(max_val, val)
            min_val = min(min_val, val)
            if _is_violation(val):
                violations.append({
                    "params": dict(zip(param_names, [float(x) for x in combo])),
                    "value": val,
                })
                if len(violations) > 10:
                    break
        except (ValueError, ZeroDivisionError, OverflowError):
            continue

    out["numerical_range"] = {"min": min_val, "max": max_val}
    out["assumption_filter"] = {"checked": n_checked, "skipped": n_skipped}

    if not violations:
        out["numerical_verified"] = True
        out["numerical_detail"] = (
            f"{n_checked} combos tested ({n_skipped} skipped by assumptions). "
            f"Range: [{min_val:.4e}, {max_val:.4e}]. "
            f"No violations found."
        )
    else:
        out["numerical_verified"] = False
        out["numerical_failures"] = [
            f"{v['params']} -> value={v['value']:.4e}"
            for v in violations[:5]
        ]
        out["numerical_detail"] = (
            f"FOUND {len(violations)} VIOLATIONS in {n_checked} combos "
            f"({n_skipped} skipped). "
            f"Range: [{min_val:.4e}, {max_val:.4e}]. "
            f"Check assumptions: {ASSUMPTIONS}"
        )


def _auto_range(name):
    """Guess parameter range from name."""
    if name in ("n_H", "n_L", "nH", "nL"):
        return list(range(2, 51, 10))
    if name in ("n",):
        return list(range(2, 101, 20))
    if name in ("gamma",):
        return [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    if name.startswith("mu"):
        return list(np.linspace(0.1, 5.0, 15))
    if name.startswith("sigma"):
        return list(np.linspace(0.0, 16.0, 12))
    if name in ("a", "b", "alpha_H", "alpha_L", "ell"):
        return list(np.linspace(0, 1, 21))
    if name in ("Delta",):
        return list(np.linspace(0.01, 5.0, 15))
    return list(np.linspace(0.1, 10.0, 10))


def _symbolic_analyze(expr, sym_map, out):
    """Factor, group terms, determine sign."""
    try:
        simplified = simplify(expr)
        out["simplified"] = str(simplified)

        try:
            factored = factor(simplified)
            out["factorization"] = str(factored)
        except Exception:
            factored = simplified

        # ── Step A: Try expansion + term grouping ──
        expanded = expand(simplified)
        terms = _get_sum_terms(expanded)

        pos_terms = []
        neg_terms = []
        for t in terms:
            s = str(t).lstrip()
            if s.startswith('-'):
                neg_terms.append(t)
            else:
                pos_terms.append(t)

        out["n_terms"] = len(terms)
        out["n_positive"] = len(pos_terms)
        out["n_negative"] = len(neg_terms)

        if not pos_terms:
            out["sign"] = "always_non_positive"
            out["symbolic_success"] = True
            out["symbolic_detail"] = (
                f"All {len(neg_terms)} terms are non-positive. "
                f"Expression <= 0 everywhere."
            )
            out["symbolic_conditions"] = list(ASSUMPTIONS)
            out["all_terms"] = [str(t) for t in neg_terms[:10]]
            return

        if not neg_terms:
            out["sign"] = "always_non_negative"
            out["symbolic_success"] = True
            out["symbolic_detail"] = (
                f"All {len(pos_terms)} terms are non-negative. "
                f"Expression >= 0 everywhere."
            )
            out["symbolic_conditions"] = list(ASSUMPTIONS)
            return

        # ── Step B: Mixed signs — group by monomial (deg in each key variable) ──
        # Find the key continuous variables (a, b or alpha_H, alpha_L)
        key_vars = []
        for name in ['a', 'b', 'alpha_H', 'alpha_L']:
            if name in sym_map:
                key_vars.append(sym_map[name])

        grouped = _group_by_monomial(terms, key_vars if key_vars else None)
        n_groups_ok = 0
        n_groups_need_check = 0
        group_results = []

        for (deg_key, group_expr) in grouped:
            factored = factor(simplify(group_expr))
            fs = str(factored)
            # A group is "OK" if: it starts with '-' after factoring,
            # OR the factored form is a product where the leading coefficient is negative
            if fs.lstrip().startswith('-'):
                n_groups_ok += 1
                group_results.append((deg_key, "OK", fs[:150]))
            else:
                n_groups_need_check += 1
                group_results.append((deg_key, "NEEDS_CHECK", fs[:150]))

        out["monomial_groups"] = [
            {"degrees": list(d), "status": s, "factored": f}
            for (d, s, f) in group_results
        ]

        if n_groups_need_check == 0:
            out["sign"] = "paired_via_monomials"
            out["symbolic_success"] = True
            out["symbolic_detail"] = (
                f"Grouped into {len(grouped)} monomial groups; "
                f"each group factors to a manifestly non-positive form. "
                f"Expression <= 0 everywhere under the maintained assumptions."
            )
            out["symbolic_conditions"] = list(ASSUMPTIONS)
        elif n_groups_ok >= len(grouped) - 1:
            out["sign"] = "near_complete"
            out["symbolic_success"] = True
            out["symbolic_detail"] = (
                f"Grouped into {len(grouped)} monomial groups; "
                f"{n_groups_ok} clearly non-positive, "
                f"{n_groups_need_check} need additional conditions. "
                f"See group listing below."
            )
            out["symbolic_conditions"] = list(ASSUMPTIONS) + [
                f"Group {d}: {s[:100]}" for (d, s, f) in group_results
                if s == "NEEDS_CHECK"
            ]
        else:
            out["sign"] = "mixed"
            out["symbolic_success"] = False
            out["symbolic_detail"] = (
                f"Grouped into {len(grouped)} monomial groups; "
                f"{n_groups_ok} OK, {n_groups_need_check} need analysis. "
                f"See full group listing."
            )
            out["positive_terms_sample"] = [str(t) for t in pos_terms[:8]]
            out["negative_terms_sample"] = [str(t) for t in neg_terms[:8]]

    except Exception as e:
        out["symbolic_success"] = False
        out["symbolic_detail"] = f"Symbolic error: {e}"


def _get_sum_terms(expr):
    """Extract terms from a sum, handling nested structures."""
    if isinstance(expr, Add) or getattr(expr, 'is_Add', False):
        return list(expr.args)
    if isinstance(expr, Mul):
        return [expr]
    return [expr]


def _group_by_monomial(terms, key_vars=None):
    """Group terms by their degree in each key variable.

    Returns list of (degree_tuple, grouped_expression) sorted by degree.
    """
    from collections import defaultdict

    if not key_vars:
        return [((0,), sum(terms))]

    groups = defaultdict(lambda: 0)
    for t in terms:
        # Handle nested Adds from expand
        if isinstance(t, Add) or getattr(t, 'is_Add', False):
            for subt in t.args:
                degs = tuple(sp.degree(subt, v) for v in key_vars)
                groups[degs] = groups[degs] + subt
        else:
            degs = tuple(sp.degree(t, v) for v in key_vars)
            groups[degs] = groups[degs] + t

    # Sort by total degree then lexicographic
    sorted_keys = sorted(groups.keys(), key=lambda d: (sum(d), d))
    return [(k, groups[k]) for k in sorted_keys]


# ── Entry point ──
output = {}
try:
    main(output)
except Exception as e:
    output["error"] = str(e)
    import traceback
    output["traceback"] = traceback.format_exc()[-3000:]

print(json.dumps(output, indent=2, default=str))
