"""TensorBoard + console training logger."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from torch.utils.tensorboard import SummaryWriter


log = logging.getLogger(__name__)


class TrainingLogger:
    """Unified logger for RL training metrics.

    Writes scalar metrics to TensorBoard and optionally to the Python
    logging system (stdout-friendly).

    Parameters
    ----------
    log_dir:
        Directory for TensorBoard event files.
    run_name:
        Optional sub-directory name (e.g. ``"ppo_run_001"``).  If given, the
        actual log directory becomes ``log_dir / run_name``.
    console_interval:
        Log a summary to the console every *console_interval* global steps.
        Set to 0 or None to disable console output.
    """

    def __init__(
        self,
        log_dir: str | Path = "runs",
        run_name: Optional[str] = None,
        console_interval: Optional[int] = 1000,
    ) -> None:
        log_dir = Path(log_dir)
        if run_name:
            log_dir = log_dir / run_name
        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_dir = log_dir
        self.console_interval = console_interval or 0
        self._writer = SummaryWriter(log_dir=str(log_dir))
        self._step = 0

    # ------------------------------------------------------------------
    # Core logging API
    # ------------------------------------------------------------------

    def log_scalar(self, tag: str, value: float, step: Optional[int] = None) -> None:
        """Write a single scalar to TensorBoard.

        Parameters
        ----------
        tag:
            Metric name, e.g. ``"loss/policy"`` or ``"eval/win_rate"``.
        value:
            Scalar float value.
        step:
            Global step counter.  Defaults to the internal step tracked by
            :meth:`step`.
        """
        global_step = step if step is not None else self._step
        self._writer.add_scalar(tag, value, global_step=global_step)

    def log_dict(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None,
        prefix: str = "",
    ) -> None:
        """Write every entry in *metrics* to TensorBoard.

        Parameters
        ----------
        metrics:
            Dict of tag → scalar value pairs.
        step:
            Global step counter (falls back to internal counter).
        prefix:
            Optional prefix prepended to every tag, e.g. ``"train/"`` or
            ``"eval/"``.
        """
        global_step = step if step is not None else self._step
        for tag, value in metrics.items():
            full_tag = f"{prefix}{tag}" if prefix else tag
            self._writer.add_scalar(full_tag, value, global_step=global_step)

        if self.console_interval and global_step % self.console_interval == 0:
            metric_str = "  ".join(
                f"{tag}={value:.4f}" for tag, value in metrics.items()
            )
            log.info("[step %d] %s%s", global_step, prefix, metric_str)

    def log_hyperparams(self, hparams: Dict[str, float | int | str]) -> None:
        """Write hyper-parameters to TensorBoard's HParams tab.

        Call this once at the start of training.
        """
        self._writer.add_hparams(hparams, metric_dict={})

    # ------------------------------------------------------------------
    # Step counter
    # ------------------------------------------------------------------

    def step(self, n: int = 1) -> int:
        """Advance the internal step counter by *n* and return the new value."""
        self._step += n
        return self._step

    @property
    def global_step(self) -> int:
        """Current value of the internal step counter."""
        return self._step

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Flush and close the TensorBoard writer."""
        self._writer.close()

    def __enter__(self) -> "TrainingLogger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
