"""cellularena package.

The environment wrapper is exported lazily so code that imports only
`games.cellularena.game.*` does not require PettingZoo-related dependencies.
"""

__all__ = ["CellularenaEnv"]


def __getattr__(name):
	if name == "CellularenaEnv":
		from games.cellularena.env import CellularenaEnv

		return CellularenaEnv
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
