"""cellularena package.

The environment wrapper is exported lazily so code that imports only
`Games.cellularena.engine.*` does not require PettingZoo-related dependencies.
"""

__all__ = ["CellularenaEnv"]


def __getattr__(name):
    if name == "CellularenaEnv":
        from Games.cellularena.engine.env import CellularenaEnv

        return CellularenaEnv
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
