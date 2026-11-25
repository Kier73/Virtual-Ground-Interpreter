"""Executable 2**128-to-8 symbolic observer-quotient demonstration."""
from __future__ import annotations

import json

from vgi.symbolic_reduction import (
    AffineAction, AffineGround, admit_symbolic_reduction,
    discover_symbolic_reduction,
)


def build_demo(n: int = 128) -> AffineGround:
    p = 2
    # Visible subsystem (x0,x1,x2): binary affine recurrence.
    # Hidden subsystem (x3..x127): rotating register that never affects the first 3.
    rows = [[int(i == j) for j in range(n)] for i in range(n)]
    rows[0] = [int(j == 1) for j in range(n)]
    rows[1] = [int(j == 2) for j in range(n)]
    rows[2] = [int(j in (0, 1)) for j in range(n)]
    for i in range(3, n):
        rows[i] = [int(j == (i+1 if i+1 < n else 3)) for j in range(n)]
    pulse = AffineAction('pulse', tuple(tuple(row) for row in rows),
                         (1, 0, 1) + (0,) * (n-3))
    other = [[int(i == j) for j in range(n)] for i in range(n)]
    other[0][2] = 1
    probe = AffineAction('probe', tuple(tuple(row) for row in other), (0,) * n)
    return AffineGround(p, n, (probe, pulse),
                        (tuple(int(i == 0) for i in range(n)),), (1,))


def main() -> None:
    source = build_demo()
    candidate = discover_symbolic_reduction(source)
    admitted = admit_symbolic_reduction(source, json.dumps(candidate))
    source_initial = (0,)*source.dimension
    quotient_initial = admitted.project(source_initial)
    future = admitted.jump_word(quotient_initial, ('pulse','probe'), 10**100)
    result = {
        'source_sha256': source.fingerprint,
        'certificate_sha256': admitted.certificate_sha256,
        'source_state_count': str(admitted.source_states),
        'certified_quotient_state_count': admitted.quotient_states,
        'quotient_dimension': admitted.dimension,
        'repeated_macro_periods': '10^100',
        'future_observation': list(admitted.observe(future)),
        'word_witnesses': candidate['witnesses'],
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
