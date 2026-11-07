# Build 20 regression sources

These two source files are copied unchanged from Build 20 so Build 21's test suite can re-verify the earlier finite-ground results.

- `virtual_ground.py`: Rotor-4 reversible finite transformation ground.
- `partial_ground.py`: Support-9 irreversible symbolic support ground.

They are not dependencies of `flow_ground.py`; the Build 21 engine is standalone.
