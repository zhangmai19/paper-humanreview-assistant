"""Symbolically derive ∂²U_H/∂α_H² under independent risks.

Goal: find conditions under which U_H(·, ℓ) is concave on [0,1].
"""

import sympy as sp
from sympy import simplify, factor, expand, collect, together, numer, denom

# Define symbols
α_H, α_L = sp.symbols('α_H α_L', real=True, nonnegative=True)
n_H, n_L = sp.symbols('n_H n_L', integer=True, positive=True)
γ = sp.symbols('γ', real=True, positive=True)
μ_H, μ_L = sp.symbols('μ_H μ_L', real=True, positive=True)
σ2_H, σ2_L = sp.symbols('σ2_H σ2_L', real=True, nonnegative=True)

# Assume μ_H > μ_L
# (this doesn't affect derivatives but matters for sign discussion)

# --- Intermediate objects ---
T = n_H * α_H + n_L * α_L
P = n_H * α_H * μ_H + n_L * α_L * μ_L
V = n_H * α_H**2 * σ2_H + n_L * α_L**2 * σ2_L

# Derivatives of T, P, V w.r.t. α_H
Tp = n_H   # ∂T/∂α_H
Pp = n_H * μ_H  # ∂P/∂α_H
Vp = 2 * n_H * α_H * σ2_H  # ∂V/∂α_H
Vpp = 2 * n_H * σ2_H  # ∂²V/∂α_H²

# --- Mean component ---
# M = α_H * (μ_H - P/T)
M = α_H * (μ_H - P / T)
dM = sp.diff(M, α_H)
d2M = sp.diff(dM, α_H)

print("=== Mean component ===")
print(f"∂M/∂α_H = {simplify(dM)}")
print(f"∂²M/∂α_H² = {simplify(d2M)}")
print()

# --- Variance component ---
# Var = σ_H²(1-α_H)² + 2σ_H²(1-α_H)α_H²/T + α_H²V/T²
Var = σ2_H * (1 - α_H)**2 + 2 * σ2_H * (1 - α_H) * α_H**2 / T + α_H**2 * V / T**2

dVar = sp.diff(Var, α_H)
d2Var = sp.diff(dVar, α_H)

dV_simple = simplify(dVar)
d2V_simple = simplify(d2Var)

print("=== Variance component ===")
print(f"∂Var/∂α_H = ({dV_simple})")
print()
print("∂²Var/∂α_H² = ")
# Print numerator and denominator separately
d2V_together = together(d2Var)
d2V_num = simplify(numer(d2V_together))
d2V_den = denom(d2V_together)
print(f"  Numerator: ({d2V_num})")
print(f"  Denominator: {d2V_den}")
print()

# --- Full U_H ---
U = -μ_H + M - (γ/2) * Var
dU = sp.diff(U, α_H)
d2U_raw = sp.diff(dU, α_H)
d2U_together = together(d2U_raw)
d2U_num = simplify(numer(d2U_together))
d2U_den = denom(d2U_together)

print("=== Full U_H ===")
print(f"Denominator = {d2U_den}")
print(f"Numerator degree in α_H: {sp.degree(d2U_num, α_H)}")
print()

# Factor the numerator
print("Attempting to factor numerator...")
d2U_factored = factor(d2U_num)
print(f"Factored form: {d2U_factored}")
print()

# --- Try to express numerator as -(positive terms) ---
# Expand and collect by powers of α_H
d2U_expanded = expand(d2U_num)
print("=== Expanded numerator (by α_H powers) ===")
for k in range(sp.degree(d2U_num, α_H) + 1):
    coeff = collect(d2U_expanded, α_H**k)
    if coeff != 0:
        term = coeff.coeff(α_H, k) if k > 0 else coeff
        print(f"  α_H^{k}: {term}")

print()

# --- Key question: can we bound the sign? ---
# Denominator T^3 > 0 always, so sign of d2U = sign of numerator.
# Let's check: what is the sign of each term in the numerator?

print("=== Attempting to separate into dominant negative terms ===")
# The variance contribution is nonnegative (variance is convex in general)
# Let's check d2Var directly

print("\n--- d²Var/dα_H² analysis ---")
# For independent risks, Var of net loss should be convex in α_H
# because variance of a portfolio is convex in weights
print("(We expect variance to be convex → d²Var ≥ 0)")
print(f"d²Var simplified: {simplify(d2V_simple)}")
