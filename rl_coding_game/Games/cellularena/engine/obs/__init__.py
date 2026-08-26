"""Observation utilities for Cellularena.

Keep feature construction in one place so training, offline prefill, and
CodinGame runtime can share the same observation contract.
"""

from .feature_builder import TemporalObservationBuilder, flatten_obs_dict
__all__ = [
	"TemporalObservationBuilder",
	"flatten_obs_dict",
]
