"""Communication and collaboration experiments for heterogeneous agent teams."""

from mica_comm.core.config import Config

__all__ = ["Config", "Simulation", "run_episode", "RealisticSimulation", "run_realistic"]


def __getattr__(name):
    """Load the public simulation API and the shared LLM client module lazily."""
    if name == "llm_agent":
        from mica_comm.agents import llm_agent

        globals()[name] = llm_agent
        return llm_agent
    if name in {"Simulation", "run_episode"}:
        from mica_comm.simulation.simulator import Simulation, run_episode

        globals().update(Simulation=Simulation, run_episode=run_episode)
        return globals()[name]
    if name in {"RealisticSimulation", "run_realistic"}:
        from mica_comm.simulation.realistic import RealisticSimulation, run_realistic

        globals().update(RealisticSimulation=RealisticSimulation, run_realistic=run_realistic)
        return globals()[name]
    raise AttributeError(name)
