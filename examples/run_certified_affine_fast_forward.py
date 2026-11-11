"""Run a bounded modular-affine fast-forward over a verified VGI orbit."""
import json

from vgi import (
    GroundTransitionSystem, OrbitNavigator, OrbitPolicy, OrbitTimeCoordinate,
    TransitionObservation, TransitionOutcome,
)
from vgi.affine import AffineOrbitCertificate, ModularAffineMap


states = ("s0", "s1", "s2", "s3")
successors = {"s0": "s1", "s1": "s2", "s2": "s3", "s3": "s3"}
ground = GroundTransitionSystem(
    states=states, actions=("ADVANCE",), initial_state="s0",
    channels=("out",),
    observations=tuple(
        TransitionObservation(
            state, "ADVANCE", (TransitionOutcome(successors[state], (0,)),),
        )
        for state in states
    ),
)
policy = OrbitPolicy.from_mapping(ground, {state: "ADVANCE" for state in states})
origin = OrbitTimeCoordinate("affine-example-clock", 100)
orbit = OrbitNavigator.compile(
    ground, policy, start_state="s0", start_time=origin,
)

# x -> 2x mod 8 gives 1 -> 2 -> 4 -> 0 -> 0.
transform = ModularAffineMap(modulus=8, matrix=((2,),), offset=(0,))
certificate = AffineOrbitCertificate.certify(
    orbit, transform,
    {"s0": (1,), "s1": (2,), "s2": (4,), "s3": (0,)},
)

result = certificate.state_at(origin.advance(10**12))
print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
