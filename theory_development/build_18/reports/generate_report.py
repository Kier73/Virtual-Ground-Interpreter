import json
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import relational_atlas as ra

q = ra.q_normalize(np.array([0.3, -0.2, 0.4, 0.5]))
q_antipode = -q
beta = float(np.pi / 3)
q_fibre = ra.q_mul(q, ra.fibre_element(beta))
q_opposite = ra.q_mul(q, ra.fibre_element(np.pi))

hopf_same_base = float(np.linalg.norm(ra.hopf_map(q) - ra.hopf_map(q_fibre)))

fibre_modes = []
for n in range(6):
    avg = ra.fibre_average_rep(q, n, samples=256)
    expected = ra.su2_irrep(q, n) @ ra.fibre_projector_expected(n)
    fibre_modes.append({
        "highest_weight_n": n,
        "spin_j": n / 2,
        "dimension": n + 1,
        "antipodal_parity": "even" if n % 2 == 0 else "odd",
        "zero_weight_dimension": int(np.linalg.matrix_rank(ra.fibre_projector_expected(n))),
        "fibre_average_frobenius_norm": float(np.linalg.norm(avg)),
        "fibre_projector_residual": float(np.linalg.norm(avg - expected)),
    })

schur_18k = ra.haar_schur_error(n=1, count=18000, seed=77)
schur_30k = ra.haar_schur_error(n=1, count=30000, seed=1802)
intertwiner = ra.unitary_intertwiner_demo()

path = np.array([[0., 0.], [1., 0.], [1., 1.]])
reverse = path[::-1].copy()
sig_path = ra.truncated_path_signature(path, depth=3)
sig_reverse = ra.truncated_path_signature(reverse, depth=3)
backtrack = np.array([[0.,0.],[1.,0.],[0.,0.]])
sig_backtrack = ra.truncated_path_signature(backtrack, depth=4)
sig_identity = [np.array(1.0)] + [np.zeros((2,)*k) for k in range(1,5)]

x = np.array([[0.,0.],[1.,0.],[1.,1.]])
time_a = np.array([0.,1.,2.])
time_b = np.array([0.,2.,4.])
clock_free_a = ra.truncated_path_signature(x, depth=3)
clock_free_b = ra.truncated_path_signature(x, depth=3)
timed_a = ra.truncated_path_signature(np.column_stack([time_a, x]), depth=3)
timed_b = ra.truncated_path_signature(np.column_stack([time_b, x]), depth=3)

results = {
    "build": 18,
    "provenance": "mathematical_fixture_and_numerical_verification_only",
    "empirical_sensor_data_processed": False,
    "quaternion_hopf": {
        "same_base_fibre_residual_beta_pi_over_3": hopf_same_base,
        "s3_distance_for_beta_pi_over_3": ra.q_distance_s3(q, q_fibre),
        "antipodal_base_residual": float(np.linalg.norm(ra.hopf_map(q) - ra.hopf_map(q_antipode))),
        "antipodal_s3_geodesic_distance": ra.q_distance_s3(q, q_antipode),
        "q_vs_fibre_beta_pi_hopf_residual": float(np.linalg.norm(ra.hopf_map(q) - ra.hopf_map(q_opposite))),
        "q_vs_fibre_beta_pi_s3_distance": ra.q_distance_s3(q, q_opposite),
    },
    "su2_harmonic_sectors": fibre_modes,
    "schur_orthogonality_monte_carlo": {
        "spin": 0.5,
        "samples_18000_seed_77_max_entrywise_error": schur_18k,
        "samples_30000_seed_1802_max_entrywise_error": schur_30k,
        "interpretation": "sampling_error_against_exact_schur_orthogonality",
    },
    "observer_intertwiner_demo": intertwiner,
    "path_signature": {
        "forward_reverse_signature_distance_depth_3": ra.signature_error(sig_path, sig_reverse),
        "tree_like_backtrack_identity_residual_depth_4": ra.signature_error(sig_backtrack, sig_identity),
        "clock_free_signature_difference_same_state_path": ra.signature_error(clock_free_a, clock_free_b),
        "time_augmented_signature_difference_duration_scale_1_vs_2": ra.signature_error(timed_a, timed_b),
        "note": "finite_depth_signature_is_not_a_complete_path_identifier",
    },
    "tests": {
        "expected_count": 21,
        "command": "python -m unittest discover -s tests -v",
    },
}
out = ROOT / "reports" / "build_18_results.json"
out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
print(out)
