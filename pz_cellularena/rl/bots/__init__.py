"""Bot implementations.

Available bots and trainers
---------------------------
- :class:`~rl.bots.ppo_bot.PPOBot`       -- Proximal Policy Optimisation (on-policy, actor-critic)
- :class:`~rl.bots.ppo_bot.PPOTrainer`   -- on-policy trainer for PPOBot
- :class:`~rl.bots.dqn_bot.DQNBot`       -- Deep Q-Network / Rainbow (off-policy, value-based)
- :class:`~rl.bots.dqn_bot.RainbowTrainer` -- off-policy PER + n-step trainer for DQNBot
"""
from rl.bots.dqn_bot import DQNBot, RainbowTrainer
from rl.bots.ppo_bot import PPOBot, PPOTrainer

__all__ = ["DQNBot", "RainbowTrainer", "PPOBot", "PPOTrainer"]
