"""Goal-oriented semantic communication for collaborating AI agents over 6G."""

from .config import Config

__all__ = ["Config", "Simulation", "run_episode", "RealisticSimulation", "run_realistic"]


def __getattr__(name):
    """Load simulation modules lazily so ``python -m mosaic_comm.simulator`` is quiet."""
    if name in {"Simulation", "run_episode"}:
        from .simulator import Simulation, run_episode

        globals().update(Simulation=Simulation, run_episode=run_episode)
        return globals()[name]
    if name in {"RealisticSimulation", "run_realistic"}:
        from .realistic import RealisticSimulation, run_realistic

        globals().update(RealisticSimulation=RealisticSimulation, run_realistic=run_realistic)
        return globals()[name]
    raise AttributeError(name)
