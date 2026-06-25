"""Numerically verify U_H concavity and α_H=1 optimality in the independent benchmark.

Checks across a broad range of parameter combinations:
1. For each (α_H, α_L) grid point, compute U_H and its numerical second derivative.
2. For each fixed α_L, find the α_H that maximizes U_H.
3. Report when concavity fails and when α_H=1 is NOT optimal.
"""

import numpy as np

def U_H(alpha_H, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L):
    """U_H per equation (eq:utility-alpha-ind-new)."""
    T = nH * alpha_H + nL * alpha_L
    if T <= 0:
        return -mu_H  # autarky limit

    P = nH * alpha_H * mu_H + nL * alpha_L * mu_L
    V = nH * alpha_H**2 * sigma2_H + nL * alpha_L**2 * sigma2_L

    mean_term = alpha_H * (mu_H - P / T)
    var_term = (sigma2_H * (1 - alpha_H)**2
                + 2 * sigma2_H * (1 - alpha_H) * alpha_H**2 / T
                + alpha_H**2 * V / T**2)

    return -mu_H + mean_term - (gamma / 2) * var_term


def check_concavity_and_optimality(nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L,
                                    n_alpha_H=200, n_alpha_L=50):
    """For each α_L, find optimal α_H and verify concavity via numerical 2nd deriv."""
    alphas_H = np.linspace(0, 1, n_alpha_H)
    alphas_L = np.linspace(0, 1, n_alpha_L)

    results = []
    for alpha_L in alphas_L:
        # Find max by brute force on grid
        uh_vals = np.array([U_H(ah, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L)
                           for ah in alphas_H])
        best_idx = np.argmax(uh_vals)
        best_alpha_H = alphas_H[best_idx]

        # Compare U_H(1, α_L) vs U_H(best, α_L)
        uh_at_1 = U_H(1.0, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L)
        uh_at_best = uh_vals[best_idx]
        is_1_optimal = np.isclose(best_alpha_H, 1.0, atol=1e-3) or (uh_at_1 >= uh_at_best - 1e-10)

        # Numerical second derivative at interior points
        h = 1e-4
        max_d2 = -np.inf
        n_concavity_failures = 0
        for ah in alphas_H:
            if ah < h or ah > 1 - h:
                continue
            f0 = U_H(ah, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L)
            fp = U_H(ah + h, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L)
            fm = U_H(ah - h, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L)
            d2 = (fp - 2*f0 + fm) / (h*h)
            max_d2 = max(max_d2, d2)
            if d2 > 1e-6:
                n_concavity_failures += 1

        results.append({
            'alpha_L': alpha_L,
            'best_alpha_H': best_alpha_H,
            'is_1_optimal': is_1_optimal,
            'uh_at_1': uh_at_1,
            'uh_at_best': uh_at_best,
            'gap': uh_at_1 - uh_at_best,
            'max_d2': max_d2,
            'n_concavity_failures': n_concavity_failures,
        })

    return results


def print_results(results, label):
    """Pretty-print the verification results."""
    any_non_optimal = any(not r['is_1_optimal'] for r in results)
    any_concave_fail = any(r['n_concavity_failures'] > 0 for r in results)

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")

    if not any_non_optimal:
        print(f"  ✅ α_H=1 is optimal for ALL α_L ∈ [0,1]")
    else:
        failures = [r for r in results if not r['is_1_optimal']]
        print(f"  ❌ α_H=1 FAILS for {len(failures)}/{len(results)} α_L values:")
        for f in failures[:5]:
            print(f"     α_L={f['alpha_L']:.4f}  best_α_H={f['best_alpha_H']:.4f}  "
                  f"U_H(1)={f['uh_at_1']:.6f}  U_H(best)={f['uh_at_best']:.6f}  "
                  f"gap={f['gap']:.2e}")

    if not any_concave_fail:
        print(f"  ✅ U_H concave in α_H for ALL grid points (all ∂²U_H/∂α_H² ≤ 0)")
    else:
        worst = max(results, key=lambda r: r['max_d2'])
        total_fails = sum(r['n_concavity_failures'] for r in results)
        print(f"  ❌ Concavity FAILS at {total_fails} grid points  "
              f"(worst max ∂²U_H/∂α_H² = {worst['max_d2']:.2e} at α_L={worst['alpha_L']:.4f})")

    # Show best_α_H vs α_L for a few points
    print(f"\n  α_L         best_α_H    U_H(1)       U_H(best)    concavity")
    print(f"  {'-'*60}")
    for r in results[::max(1, len(results)//10)]:
        concav = "✅" if r['n_concavity_failures'] == 0 else f"❌({r['n_concavity_failures']})"
        print(f"  {r['alpha_L']:.4f}      {r['best_alpha_H']:.4f}      "
              f"{r['uh_at_1']:+.6f}  {r['uh_at_best']:+.6f}  {concav}")


def param_sweep():
    """Sweep over plausible parameter ranges."""
    # Benchmark
    base = dict(nH=20, nL=20, gamma=2, mu_H=1.15, mu_L=1.0, sigma2_H=4.0, sigma2_L=1.0)

    # 1. Benchmark
    r = check_concavity_and_optimality(**base, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Benchmark (nH=nL=20, μ_H=1.15, μ_L=1, σ²_H=4, σ²_L=1)")

    # 2. Larger mean gap
    params = {**base, 'mu_H': 1.5}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Large mean gap (μ_H=1.5, μ_L=1)")

    # 3. Very large mean gap
    params = {**base, 'mu_H': 2.0}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Very large mean gap (μ_H=2.0, μ_L=1)")

    # 4. Small pool
    params = {**base, 'nH': 5, 'nL': 5}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Small pool (nH=nL=5)")

    # 5. Asymmetric pool
    params = {**base, 'nH': 5, 'nL': 50}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Asymmetric pool (nH=5, nL=50)")

    # 6. High risk aversion
    params = {**base, 'gamma': 5}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "High risk aversion (γ=5)")

    # 7. Low risk aversion
    params = {**base, 'gamma': 0.5}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Low risk aversion (γ=0.5)")

    # 8. Equal variances
    params = {**base, 'sigma2_H': 1.0, 'sigma2_L': 1.0}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Equal variances (σ²_H=σ²_L=1)")

    # 9. Large population
    params = {**base, 'nH': 200, 'nL': 200}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Large pool (nH=nL=200)")

    # 10. Extreme: very small n, large gap
    params = {'nH': 3, 'nL': 3, 'gamma': 2, 'mu_H': 3.0, 'mu_L': 1.0,
              'sigma2_H': 9.0, 'sigma2_L': 1.0}
    r = check_concavity_and_optimality(**params, n_alpha_H=300, n_alpha_L=100)
    print_results(r, "Extreme (nH=nL=3, μ_H=3, μ_L=1, σ²_H=9, σ²_L=1)")


def boundary_scan():
    """Scan the boundary where α_H=1 stops being optimal.

    Sweep μ_H-μ_L from 0 to 5, for various pool sizes.
    """
    print("\n\n")
    print("="*70)
    print("  BOUNDARY SCAN: when does α_H=1 stop being optimal?")
    print("="*70)

    configs = [
        (20, 20, 2, 4.0, 1.0),
        (5, 5, 2, 4.0, 1.0),
        (5, 50, 2, 4.0, 1.0),
        (20, 20, 5, 4.0, 1.0),
        (20, 20, 0.5, 4.0, 1.0),
    ]

    for nH, nL, gamma, sigma2_H, sigma2_L in configs:
        label = f"nH={nH}, nL={nL}, γ={gamma}, σ²_H={sigma2_H}, σ²_L={sigma2_L}"
        mu_L = 1.0
        worst_alpha_L = None
        worst_gap = 0
        worst_mu_H = None

        alphas_L = np.linspace(0, 1, 50)
        mu_H_values = np.linspace(1.0, 5.0, 200)

        for mu_H in mu_H_values:
            for alpha_L in alphas_L:
                # Find best α_H
                alphas_H = np.linspace(0, 1, 200)
                uh_vals = np.array([U_H(ah, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L)
                                   for ah in alphas_H])
                best_idx = np.argmax(uh_vals)
                best_ah = alphas_H[best_idx]

                uh_at_1 = U_H(1.0, alpha_L, nH, nL, gamma, mu_H, mu_L, sigma2_H, sigma2_L)
                gap = uh_at_1 - uh_vals[best_idx]

                if gap < worst_gap:
                    worst_gap = gap
                    worst_alpha_L = alpha_L
                    worst_mu_H = mu_H

        print(f"\n{label}")
        if worst_gap >= -1e-8:
            print(f"  ✅ α_H=1 always optimal across μ_H ∈ [1, 5]")
        else:
            print(f"  ❌ α_H=1 fails at μ_H={worst_mu_H:.2f}, α_L={worst_alpha_L:.4f}, "
                  f"worst gap={worst_gap:.4f}")


if __name__ == '__main__':
    param_sweep()
    boundary_scan()
