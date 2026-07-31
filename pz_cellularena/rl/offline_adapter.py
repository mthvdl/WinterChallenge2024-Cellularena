"""Interfaces for game-specific offline replay adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from rl.experience import Transition


class ReplayTransitionAdapter(ABC):
    """Convert replay files into generic RL transitions.

    Implementations are game-specific and should live outside core RL modules
    whenever possible (for example under a game package).
    """

    @abstractmethod
    def iter_transitions(self, replay_path: Path) -> Iterable[Transition]:
        """Yield transitions extracted from one replay file."""