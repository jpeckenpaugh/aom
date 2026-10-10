"""Shared delegation base for first-pass subsystem managers."""


class GameBackedManager:
    """Proxy manager state reads and writes to the owning Game instance."""

    def __init__(self, game):
        object.__setattr__(self, "game", game)

    def __getattr__(self, name):
        return getattr(self.game, name)

    def __setattr__(self, name, value):
        if name == "game":
            object.__setattr__(self, name, value)
        else:
            setattr(self.game, name, value)
