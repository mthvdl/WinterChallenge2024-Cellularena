# Moved to rl/rainbow/.  Re-exported here for backward compatibility.
from rl.rainbow.network import NoisyLinear as NoisyLinear                          # noqa: F401
from rl.rainbow.network import QRDuelingNoisyNetwork as QRDuelingNoisyNetwork      # noqa: F401
from rl.rainbow.bot import DQNBot as DQNBot                                        # noqa: F401
from rl.rainbow.trainer import RainbowTrainer as RainbowTrainer                    # noqa: F401

__all__ = ["NoisyLinear", "QRDuelingNoisyNetwork", "DQNBot", "RainbowTrainer"]
