"""Derive ∂²U_H/∂α_H² analytically using sympy.
Goal: find the factorization and sign conditions.
"""
import sympy as sp
from sympy import simplify, factor, expand, collect, numer, denom, together

α_H, α_L = sp.symbols('a b', real=True, nonnegative=True)
n_H, n_L = sp.symbols('n nL', integer=True, positive=True)
γ = sp.symbols('g', real=True, positive=True)
μ_H, μ_L = sp.symbols('mH mL', real=True, positive=True)
Δ = sp.symbols('D', real=True, positive=True)  # Δ = μ_H - μ_L > 0
σ2_H, σ2_L = sp.symbols('sH sL', real=True, nonnegative=True)

# --- Build U_H ---
T = n_H * α_H + n_L * α_L
P = n_H * α_H * μ_H + n_L * α_L * μ_L
V = n_H * α_H**2 * σ2_H + n_L * α_L**2 * σ2_L

# Mean component
M = α_H * (μ_H - P / T)

# Variance component
Var = σ2_H * (1 - α_H)**2 + 2 * σ2_H * (1 - α_H) * α_H**2 / T + α_H**2 * V / T**2

# Full U_H
U = -μ_H + M - (γ/2) * Var

# --- Compute derivatives ---
dU = sp.diff(U, α_H)
d2U = sp.diff(dU, α_H)

# Put over common denominator
d2U_together = together(d2U)
d2U_num = simplify(numer(d2U_together))
d2U_den = denom(d2U_together)

print("Denominator:", d2U_den)
print(f"Numerator has {sp.count_ops(d2U_num)} ops")
print()

# Substitute Δ = μ_H - μ_L to simplify
d2U_num_D = simplify(sp.simplify(d2U_num.subs(μ_H, μ_L + Δ)))
print("=== Numerator (after collecting by Δ):")
# Show as A·Δ + B
d2U_num_noD = simplify(d2U_num_D.subs(Δ, 0))
d2U_num_Dpart = simplify(d2U_num_D - d2U_num_noD)
print(f"  Denominator = {d2U_den}")
print(f"  Structure: f(α_H,α_L,n_H,n_L,σ²)/T³")
print()

# The numerator should factor as: -(something involving Δ) - (something involving σ²)
# Let's check each monomial's sign

# Expand and group
expanded = expand(d2U_num_D)
print("=== Terms grouped by key parameters ===")
print(f"Δ (mean gap) terms:")
delta_terms = collect(d2U_num_D - d2U_num_noD, Δ)
print(f"  {factor(simplify(delta_terms / Δ))} × Δ")

print(f"\nRest (Δ=0, purely variance-driven):")
rest = factor(d2U_num_noD)
print(f"  {rest}")
print()

# Factor the full numerator
print("=== Attempting to factor full numerator ===")
factored = factor(d2U_num_D)
# If too large, try with specific assumptions
print(f"Factored: {factored}")
print()

# Check: is numerator always negative under reasonable conditions?
# Since T³ > 0 for T > 0, d2U ≤ 0 iff numerator ≤ 0.
# The numerator should be -(positive terms)

print("=== Key question: sign of numerator ===")
print("(For concavity, we need numerator ≤ 0 since denominator T³ > 0)")
print()

# Let's also compute the expression at α_H=1 to verify it's negative
d2U_at_1 = simplify(d2U_num_D.subs(α_H, 1))
print(f"Numerator at α_H=1: {factor(d2U_at_1)}")
print()

# And at α_H=0
d2U_at_0 = simplify(d2U_num_D.subs(α_H, 0))
print(f"Numerator at α_H=0: {factor(d2U_at_0)}")
print()

# Check ∂²Var separately
dVar = sp.diff(Var, α_H)
d2Var = sp.diff(dVar, α_H)
d2Var_together = together(d2Var)
d2Var_num = simplify(numer(d2Var_together))

print("=== ∂²Var/∂α_H² numerator ===")
print(f"  (Denominator: {denom(d2Var_together)})")
factored_var = factor(d2Var_num)
print(f"  Factored: {factored_var}")
