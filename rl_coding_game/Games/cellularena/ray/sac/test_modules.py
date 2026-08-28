import torch

from Games.cellularena.ray.sac.modules import _ResidualBlock


def test_zero_initialized_residual_output_receives_gradients() -> None:
    block = _ResidualBlock(4)
    inputs = torch.randn(2, 4, 5, 5)

    block(inputs).sum().backward()

    output_conv = block.layers[2]
    assert output_conv.weight.grad is not None
    assert torch.count_nonzero(output_conv.weight.grad) == output_conv.weight.grad.numel()