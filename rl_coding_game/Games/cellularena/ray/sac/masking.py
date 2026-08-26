"""Backward-compatible imports for generic discrete mask utilities."""

from Core.action_mask import ActionMaskingRLModuleMixin, mask_action_dist_inputs, mask_logits

__all__ = ["ActionMaskingRLModuleMixin", "mask_action_dist_inputs", "mask_logits"]
