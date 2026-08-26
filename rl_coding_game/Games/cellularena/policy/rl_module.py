"""Backward-compatible imports for generic RLModule mask helpers."""

from Core.action_mask import ActionMaskingRLModuleMixin, mask_action_dist_inputs

__all__ = ["ActionMaskingRLModuleMixin", "mask_action_dist_inputs"]