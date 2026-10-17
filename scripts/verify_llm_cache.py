"""Replay one cached mission per paper LLM and scheme without an Ollama server."""

import json

from mosaic_comm import Config, llm_agent, run_episode
from mosaic_comm.paths import RESULTS_DIR

ROOT = RESULTS_DIR
CASES = (
    ("llm_mixed.jsonl", "mixed", "small_reasoner", 0),
    ("llm_mixed.jsonl", "mixed_alt", "small_reasoner_alt", 0),
    ("llm_extended.jsonl", "mixed_large", "large_reasoner", 0),
)
METRICS = (
    "completion_time",
    "symbols",
    "bits",
    "found",
    "false_declarations",
    "llm_decisions",
    "llm_fallbacks",
)


class CacheMiss(BaseException):
    pass


def no_network(_body):
    raise CacheMiss("Cache miss: an online Ollama request would be required")


def main():
    failures = []
    for filename, team, model, seed in CASES:
        with (ROOT / "results" / filename).open() as f:
            rows = [json.loads(line) for line in f]
        client = llm_agent.LLMClient(model, transport=no_network)
        llm_agent._CLIENTS[model] = client
        assert client.cache, f"{model}: empty cache"
        for scheme in ("sem", "gosc"):
            expected = next(
                r for r in rows if r["team"] == team and r["scheme"] == scheme and r["seed"] == seed
            )
            cfg = Config().with_(llm_agents=(0, 2, 4), llm_model=model)
            try:
                actual = run_episode(cfg, scheme, seed)
            except CacheMiss:
                failures.append(f"{team} {scheme}")
                print(
                    f"{team} {scheme}: cache miss after {client.hits} hits "
                    f"({len(client.cache)} cached responses)",
                    flush=True,
                )
                continue
            mismatches = {
                key: (expected[key], actual[key])
                for key in METRICS
                if key in expected and expected[key] != actual[key]
            }
            assert not mismatches, f"{team} {scheme}: {mismatches}"
            assert actual["llm_fallbacks"] == 0, f"{team} {scheme}: LLM fallback"
            print(
                f"{team} {scheme}: T={actual['completion_time']} "
                f"uses={actual['symbols']} cache_hits={client.hits}",
                flush=True,
            )
        assert client.calls == 0, f"{model}: {client.calls} online calls"
    if failures:
        raise SystemExit(f"Cache incomplete for: {', '.join(failures)}")


if __name__ == "__main__":
    main()
