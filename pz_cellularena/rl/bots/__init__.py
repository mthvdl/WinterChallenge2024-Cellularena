"""Bot implementations.

Available bots
--------------
- :class:`~rl.bots.ppo_bot.PPOBot`  – Proximal Policy Optimisation (on-policy, actor-critic)
- :class:`~rl.bots.dqn_bot.DQNBot`  – Deep Q-Network (off-policy, value-based)
"""
from rl.bots.dqn_bot import DQNBot
from rl.bots.ppo_bot import PPOBot

__all__ = ["PPOBot", "DQNBot"]
